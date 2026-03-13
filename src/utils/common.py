import os
import shutil
import subprocess
import re
import sys
import glob
import hashlib
import json
from src.utils.feature_extraction import pass_stats_keys
# ==============================================================================
# 1. 基础配置 (建议优先从根目录 config.py 导入，此处为 fallback)
# ==============================================================================
try:
    from config import DEFAULT_SPEC_ROOT, DEFAULT_WORK_DIR, LLVM_BIN_PATH
except ImportError:
    DEFAULT_SPEC_ROOT = "/data/speccpu2006/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006"
    DEFAULT_WORK_DIR = "/data/compiler_assignment/work"
    LLVM_BIN_PATH = "" # 如果 opt 在环境变量中，留空即可

# ==============================================================================
# 2. Benchmark 类：集成 manage_spec.py 的核心编译逻辑
# ==============================================================================
class Benchmark:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.src_dir = os.path.join(path, "src")
        self.spec_dir = os.path.join(path, "Spec")
        
        self.sources = []
        self.lang = "C" 
        self.cflags = []
        self.need_math = False
        
        # Detect SPEC version based on name (SPEC 2017 starts with 5xx or 6xx)
        if self.name.startswith("5") or self.name.startswith("6"):
            self.defines = ["-DSPEC", "-DNDEBUG", "-DSPEC_LP64", "-DSPEC_LINUX_X64"]
            if sys.byteorder == 'little':
                self.defines.append("-DSPEC_LITTLE_ENDIAN")
            else:
                self.defines.append("-DSPEC_BIG_ENDIAN")
            
            # Special handling for 505.mcf_r include path
            if "505.mcf_r" in self.name:
                self.cflags.append(f"-I{os.path.join(self.src_dir, 'spec_qsort')}")
            
            # General fix for SPEC 2017 includes: add all subdirectories to include path
            for root, dirs, files in os.walk(self.src_dir):
                for d in dirs:
                    self.cflags.append(f"-I{os.path.join(root, d)}")
        else:
            # SPEC 2006
            self.defines = ["-DSPEC_CPU", "-DNDEBUG", "-DSPEC_CPU_LINUX", "-DSPEC_CPU_LP64"]
            if sys.byteorder == 'little':
                self.defines.append("-DSPEC_CPU_LITTLE_ENDIAN")
            else:
                self.defines.append("-DSPEC_CPU_BIG_ENDIAN")
        
        self._parse_object_pm()

    def _parse_object_pm(self):
        """解析 SPEC 的配置文件以获取源文件和编译参数"""
        pm_path = os.path.join(self.spec_dir, "object.pm")
        if not os.path.exists(pm_path): return

        with open(pm_path, 'r', errors='ignore') as f:
            content = f.read()

        src_match = re.search(r'@sources\s*=\s*qw\s*\((.*?)\);', content, re.DOTALL)
        if src_match:
            self.sources = list(set(src_match.group(1).split()))
        
        lang_match = re.search(r"\$benchlang\s*=\s*['\"](.*?)['\"]", content)
        if lang_match: self.lang = lang_match.group(1)

        flags_match = re.findall(r"\$bench_(?:c|cxx)?flags\s*=\s*['\"](.*?)['\"]", content)
        for flags in flags_match: self.cflags.extend(flags.split())

        # Fix for naive parsing of object.pm conditional flags (e.g. 473.astar)
        if sys.byteorder == 'little':
            self.cflags = [f for f in self.cflags if f != "-DSPEC_CPU_BIG_ENDIAN"]
        else:
            self.cflags = [f for f in self.cflags if f != "-DSPEC_CPU_LITTLE_ENDIAN"]

        if re.search(r"\$need_math\s*=\s*['\"]yes['\"]", content):
            self.need_math = True

    def compile_to_base_bc(self, work_dir):
        """将所有源文件编译并链接为一个基础的 .bc 文件 (O0 无优化)"""
        if "481.wrf" in self.name: return False
        
        bench_work_dir = os.path.join(work_dir, self.name)
        os.makedirs(bench_work_dir, exist_ok=True)
        
        bc_files = []
        clang_name = "clang++" if self.lang in ["CXX", "C++"] else "clang"
        compiler = os.path.join(LLVM_BIN_PATH, clang_name) if LLVM_BIN_PATH else clang_name
        opt_executable = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"

        for src in self.sources:
            src_path = os.path.join(self.src_dir, src)
            
            # Prefer local source in work directory if it exists (for debugging/patching)
            local_src = os.path.join(bench_work_dir, src)
            # print(f"Checking local source: {local_src}")
            if os.path.exists(local_src):
                src_path = local_src
                print(f"  [Info] Using local source: {src}")

            if not os.path.exists(src_path): continue
                
            bc_path = os.path.join(bench_work_dir, os.path.splitext(src)[0] + ".bc")
            os.makedirs(os.path.dirname(bc_path), exist_ok=True)
            
            cmd = [compiler, "-O0", "-Xclang", "-disable-O0-optnone", "-emit-llvm", "-c", src_path, "-o", bc_path]
            
            if self.lang in ["CXX", "C++"]:
                cmd.extend(["-std=gnu++98", "-include", "stdio.h", "-include", "stdlib.h"])
            
            cmd.extend(self.defines + self.cflags + ["-I", self.src_dir, "-w"])
            
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0:
                bc_files.append(bc_path)
            else:
                print(f"[Error] Failed to compile {src}:")
                print(res.stderr.decode('utf-8', errors='ignore')[:500])


        output_bc = os.path.join(bench_work_dir, f"{self.name}.bc")
        link_tool = os.path.join(LLVM_BIN_PATH, "llvm-link") if LLVM_BIN_PATH else "llvm-link"
        
        if bc_files:
            subprocess.run([link_tool, "-o", output_bc] + bc_files)
            return output_bc
        return None

    def setup_benchmark(self, bench_work_dir):
        if "482.sphinx3" in self.name:
            is_little = sys.byteorder == 'little'
            endian_suffix = "le" if is_little else "be"
            
            be_raws = glob.glob(os.path.join(bench_work_dir, "*.be.raw"))
            
            ctl_path = os.path.join(bench_work_dir, "ctlfile")
            try:
                with open(ctl_path, "w") as ctl:
                    for be_path in sorted(be_raws):
                        basename = os.path.basename(be_path).replace(".be.raw", "")
                        src_name = f"{basename}.{endian_suffix}.raw"
                        src_path = os.path.join(bench_work_dir, src_name)
                        
                        if not os.path.exists(src_path): continue
                            
                        dest_name = f"{basename}.raw"
                        dest_path = os.path.join(bench_work_dir, dest_name)
                        shutil.copy2(src_path, dest_path)
                        
                        size = os.path.getsize(src_path)
                        ctl.write(f"{basename} {size}\n")
            except Exception: pass

    def copy_dir_content(self, src, dst):
        if not os.path.exists(src): return
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            dest_root = os.path.join(dst, rel_path)
            if rel_path == ".": dest_root = dst
            
            if not os.path.exists(dest_root):
                os.makedirs(dest_root)
            
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(dest_root, f))

    def get_run_args(self, bench_work_dir):
        cmd_args = []
        stdin_file = None
        
        if "401.bzip2" in self.name:
            cmd_args = ["dryer.jpg", "2"]
        elif "429.mcf" in self.name:
            cmd_args = ["inp.in"]
        elif "433.milc" in self.name:
            stdin_file = "su3imp.in"
        elif "444.namd" in self.name:
            cmd_args = ["--input", "namd.input", "--iterations", "1", "--output", "namd.out"]
        elif "450.soplex" in self.name:
            mps_files = glob.glob(os.path.join(bench_work_dir, "*.mps"))
            if mps_files:
                # Default to test workload args if unsure
                cmd_args = ["-m1200", os.path.basename(mps_files[0])]
        elif "458.sjeng" in self.name:
            cmd_args = ["test.txt"]
        elif "462.libquantum" in self.name:
            cmd_args = ["33", "5"]
        elif "470.lbm" in self.name:
            in_files = glob.glob(os.path.join(bench_work_dir, "*.in"))
            if in_files:
                with open(in_files[0], 'r') as f:
                    cmd_args = f.read().strip().split()
        elif "473.astar" in self.name:
             cfgs = glob.glob(os.path.join(bench_work_dir, "*.cfg"))
             if cfgs: cmd_args = [os.path.basename(cfgs[0])]
        elif "482.sphinx3" in self.name:
             cmd_args = ["ctlfile", ".", "args.an4"]
        elif "483.xalancbmk" in self.name:
             cmd_args = ["-v", "test.xml", "xalanc.xsl"]
        elif "456.hmmer" in self.name:
             cmd_args = ["--fixed", "0", "--mean", "325", "--num", "45000", "--sd", "200", "--seed", "0", "bombesin.hmm"]
        elif "999.specrand" in self.name or "998.specrand" in self.name:
            control_file = os.path.join(bench_work_dir, "control")
            if os.path.exists(control_file):
                with open(control_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'): continue
                        parts = line.split()
                        if len(parts) >= 2:
                            cmd_args = parts[:2]
                            break
        else:
            # Generic Fallback
            control_file = os.path.join(bench_work_dir, "control")
            if os.path.exists(control_file):
                 with open(control_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'): continue
                        parts = line.split()
                        if len(parts) >= 1:
                            cmd_args = parts
                            break
            
            if not cmd_args:
                in_files = glob.glob(os.path.join(bench_work_dir, "*.in"))
                if in_files:
                    try:
                        with open(in_files[0], 'r') as f:
                            content = f.read().strip()
                            if len(content) < 1000 and "\n" not in content:
                                cmd_args = content.split()
                            else:
                                cmd_args = [os.path.basename(in_files[0])]
                    except: pass
            
            if not cmd_args:
                in_files = glob.glob(os.path.join(bench_work_dir, "*.input"))
                if in_files:
                    cmd_args = [os.path.basename(in_files[0])]

        return cmd_args, stdin_file

    def run_test(self, work_dir, exe_path, timeout=10):
        """执行测试，返回执行状态 (Success/Timeout/Failed/Error)"""
        bench_work_dir = os.path.join(work_dir, self.name)
        
        # 1. 准备输入文件
        input_dirs = [
            os.path.join(self.path, "data/all/input"),
            os.path.join(self.path, "data/test/input")
        ]
        for d in input_dirs:
            self.copy_dir_content(d, bench_work_dir)
        
        self.setup_benchmark(bench_work_dir)
        
        # 2. 获取运行参数
        cmd_args, stdin_file = self.get_run_args(bench_work_dir)
        
        full_cmd = [exe_path] + cmd_args
        stdin_handle = None
        if stdin_file:
            stdin_path = os.path.join(bench_work_dir, stdin_file)
            if os.path.exists(stdin_path):
                stdin_handle = open(stdin_path, 'r')
        
        try:
            ret = subprocess.run(
                full_cmd, 
                cwd=bench_work_dir, 
                stdin=stdin_handle, 
                capture_output=True, 
                timeout=timeout
            )
            if stdin_handle: stdin_handle.close()
            
            if ret.returncode == 0:
                return "Success"
            else:
                print(f"\n[DEBUG] {self.name} Failed with Exit_{ret.returncode}")
                try:
                    print(f"Stdout:\n{ret.stdout.decode(errors='replace')[-2000:]}")
                    print(f"Stderr:\n{ret.stderr.decode(errors='replace')[-2000:]}")
                except: pass
                return f"Exit_{ret.returncode}"
        except subprocess.TimeoutExpired:
            if stdin_handle: stdin_handle.close()
            return "Timeout"
        except Exception:
            if stdin_handle: stdin_handle.close()
            return "RunError"

# ==============================================================================
# 3. 工具函数：测量与提取
# ==============================================================================

def get_text_segment_size(exe_path):
    """提取二进制文件的 .text 段大小 (代码体积)"""
    if not os.path.exists(exe_path): return -1
    try:
        # 使用 size 命令获取段信息
        ret = subprocess.run(["size", "-A", "-d", exe_path], capture_output=True, text=True)
        for line in ret.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == ".text":
                return int(parts[1])
    except Exception:
        pass
    return -1

# def compile_and_measure(bench_obj, work_dir, pipeline_str, measure_type="text"):
#     """
#     measure_type: "text" 表示只测代码段, "full" 表示测量整个文件
#     核心接口：应用 Pass 序列 -> 编译链接 -> 测量大小
#     """
#     # 1. 准备路径
#     base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
#     if not os.path.exists(base_bc):
#         base_bc = bench_obj.compile_to_base_bc(work_dir)
    
#     if not base_bc: return -1

#     tmp_dir = os.path.join(work_dir, bench_obj.name, "ga_tmp")
#     os.makedirs(tmp_dir, exist_ok=True)
    
#     # 使用 hash 防止并发运行时的文件名冲突
#     tag = hash(pipeline_str + str(os.getpid()))
#     opt_bc = os.path.join(tmp_dir, f"opt_{tag}.bc")
#     exe_out = os.path.join(tmp_dir, f"exe_{tag}.out")

#     opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
#     compiler = "clang++" if bench_obj.lang in ["CXX", "C++"] else "clang"

#     try:
#         # 2. 运行 opt
#         res_opt = subprocess.run([opt_tool, f"-passes={pipeline_str}", base_bc, "-o", opt_bc], capture_output=True)
#         if res_opt.returncode != 0: return -1

#         # 3. 编译为 Executable (使用 -O0 避免后端干扰)
#         cmd_link = [compiler, opt_bc, "-O0", "-o", exe_out]
#         if bench_obj.need_math: cmd_link.append("-lm")
#         res_link = subprocess.run(cmd_link, capture_output=True)
#         if res_link.returncode != 0: return -1

#         # 4. 测量体积
#         subprocess.run(["strip", exe_out], capture_output=True) # 移除符号表
#         if measure_type == "full":
#             # 返回整个文件的字节数
#             return os.path.getsize(exe_out)
#         else:
#             # 返回 .text 段大小
#             return get_text_segment_size(exe_out)

#     except Exception:
#         return -1
        
#     finally:
#         # 5. 【核心改进】无论 try 块中是正常 return 还是发生 Exception，都会执行这里
#         if os.path.exists(opt_bc): 
#             os.remove(opt_bc)
#         if os.path.exists(exe_out): 
#             os.remove(exe_out)
def compile_and_measure(bench_obj, work_dir, pipeline_str, measure_type="full"):
    """
    measure_type: "text" 表示只测代码段, "full" 表示测量整个文件
    核心接口：应用自定义 Pass 序列 -> 后端使用 -Oz 编译链接 -> 测量二进制体积
    """
    # 1. 准备路径
    base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
    if not os.path.exists(base_bc):
        base_bc = bench_obj.compile_to_base_bc(work_dir)
    
    if not base_bc: return -1

    tmp_dir = os.path.join(work_dir, bench_obj.name, "ga_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    
    # 使用 hash 和 进程 ID 防止并发冲突
    tag = hash(pipeline_str + str(os.getpid()))
    opt_bc = os.path.join(tmp_dir, f"opt_{tag}.bc")
    exe_out = os.path.join(tmp_dir, f"exe_{tag}.out")

    opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    clang_name = "clang++" if bench_obj.lang in ["CXX", "C++"] else "clang"
    compiler = os.path.join(LLVM_BIN_PATH, clang_name) if LLVM_BIN_PATH else clang_name

    size = -1 # 默认初始值
    # === 新增：自动嵌套与稳定性补丁 ===
    if pipeline_str and "default<" not in pipeline_str:
        passes = pipeline_str.split(',')
        fixed_passes = []
        for p in passes:
            # 如果包含 loop 相关的 pass，自动插入规范化 pass
            if any(x in p for x in ["loop", "licm", "lcssa", "indvars"]):
                fixed_passes.append("function(loop-simplify)")
                fixed_passes.append("function(lcssa)")
            fixed_passes.append(p)
        actual_pipeline = ",".join(fixed_passes)
    else:
        actual_pipeline = pipeline_str
    # ==============================

    try:
        # 2. 运行 opt (应用你通过 GA 找到的中端 Pass 序列)
        res_opt = subprocess.run([opt_tool, f"-passes={actual_pipeline}", base_bc, "-o", opt_bc], capture_output=True)
        if res_opt.returncode != 0: return -1

        # 3. 编译为 Executable (【关键修改】后端使用 -Oz 确保指令被压缩打包)
        # 这样你的自定义序列将与官方后端 Oz 强强联手
        cmd_link = [compiler, opt_bc, "-Oz", "-o", exe_out]
        if bench_obj.need_math: cmd_link.append("-lm")
        res_link = subprocess.run(cmd_link, capture_output=True)
        if res_link.returncode != 0: return -1

        # 4. 测量体积
        subprocess.run(["strip", exe_out], capture_output=True) # 移除调试符号

        if measure_type == "full":
            size = os.path.getsize(exe_out)
        else:
            size = get_text_segment_size(exe_out)
        
        return size

    except Exception:
        return -1
        
    finally:
        # 5. 清理临时生成的中间文件，防止磁盘溢出
        if os.path.exists(opt_bc): 
            os.remove(opt_bc)
        if os.path.exists(exe_out): 
            os.remove(exe_out)

# def compile_extract_and_measure(bench_obj, work_dir, pipeline_str, measure_type="text"):
#     """
#     输入：Benchmark对象、工作目录、Pass序列字符串
#     输出：(特征字典, 最终二进制体积)
#     """
#     # 1. 基础路径准备
#     base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
#     if not os.path.exists(base_bc):
#         base_bc = bench_obj.compile_to_base_bc(work_dir)
#     if not base_bc: return {}, -1

#     tmp_dir = os.path.join(work_dir, bench_obj.name, "feat_tmp")
#     os.makedirs(tmp_dir, exist_ok=True)
    
#     # 使用 MD5 哈希确保文件名的唯一性
#     tag = hashlib.md5(pipeline_str.encode('utf-8')).hexdigest()[:8]
#     opt_bc = os.path.join(tmp_dir, f"opt_{tag}.bc")
#     exe_out = os.path.join(tmp_dir, f"exe_{tag}.out")

#     opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
#     compiler = "clang++" if bench_obj.lang in ["CXX", "C++"] else "clang"

#     extracted_features = {}
#     size = -1

#     fixed_pipeline = []
#     for p in pipeline_str.split(','):
#         if 'loop(' in p or 'loop-mssa(' in p:
#             # 强制插入 simplify 以维护 LCSSA 形式
#             fixed_pipeline.append("function(loop-simplify)")
#         fixed_pipeline.append(p)
    
#     pipeline_str = ",".join(fixed_pipeline)

#     try:
#         # 2. 运行 opt 并开启统计收集
#         # -stats -stats-json 会将 Pass 运行详情输出为 JSON 格式
#         cmd_opt = [opt_tool, f"-passes={pipeline_str}", base_bc, "-o", opt_bc, "-stats", "-stats-json"]
#         res_opt = subprocess.run(cmd_opt, capture_output=True, text=True)
        
#         if res_opt.returncode != 0:
#             print(f"Opt failed with return code {res_opt.returncode}")
#             print(f"Opt stderr: {res_opt.stderr}")
#         else:
#             try:
#                 # LLVM 统计数据通常在 stderr 输出
#                 all_stats = json.loads(res_opt.stderr)
#                 # 直接使用从 feature_extraction.py 导入的 pass_stats_keys 进行过滤
#                 extracted_features = {k: v for k, v in all_stats.items() if k in pass_stats_keys}
#             except json.JSONDecodeError:
#                 # 兼容性处理：防止 stderr 包含非 JSON 提示字符
#                 json_match = re.search(r'\{.*\}', res_opt.stderr, re.DOTALL)
#                 if json_match:
#                     all_stats = json.loads(json_match.group())
#                     extracted_features = {k: v for k, v in all_stats.items() if k in pass_stats_keys}

#         # 3. 编译为可执行文件 (后端使用 -Oz 确保压缩)
#         cmd_link = [compiler, opt_bc, "-Oz", "-o", exe_out]
#         if bench_obj.need_math: cmd_link.append("-lm")
#         res_link = subprocess.run(cmd_link, capture_output=True)
        
#         if res_link.returncode == 0:
#             # 4. 测量代码段体积 (.text size)
#             subprocess.run(["strip", exe_out], capture_output=True)
#             if measure_type == "full":
#                 size = os.path.getsize(exe_out)
#             else:
#                 size = get_text_segment_size(exe_out)
#         else:
#             print(f"Link failed with return code {res_link.returncode}")
#             print(f"Link stderr: {res_link.stderr.decode('utf-8', errors='ignore')}")

#     except Exception as e:
#         print(f"Extraction Error for {bench_obj.name}: {e}")
#     finally:
#         # 5. 清理临时文件，防止 10 核并行产生大量垃圾文件
#         if os.path.exists(opt_bc): os.remove(opt_bc)
#         if os.path.exists(exe_out): os.remove(exe_out)

#     return extracted_features, size
# 
def compile_extract_and_measure(bench_obj, work_dir, pipeline_str, measure_type="full", link_opts=None):
    """
    输入：Benchmark对象、工作目录、Pass序列字符串
    输出：(特征字典, 最终体积)
    """
    # 默认链接选项为 -Oz (RL场景下通常是优化目标)
    if link_opts is None:
        link_opts = ["-Oz"]

    # --- 1. 路径隔离准备 (PID隔离) ---
    rank_id = os.getpid()
    tmp_dir = os.path.join(work_dir, bench_obj.name, f"feat_tmp_{rank_id}")
    os.makedirs(tmp_dir, exist_ok=True)
    
    base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
    if not os.path.exists(base_bc):
        base_bc = bench_obj.compile_to_base_bc(work_dir)
        if not base_bc: return {}, -1

    # 生成哈希文件名
    tag = hashlib.md5((pipeline_str + str(link_opts)).encode('utf-8')).hexdigest()[:8]
    opt_bc = os.path.join(tmp_dir, f"opt_{tag}.bc")
    exe_out = os.path.join(tmp_dir, f"exe_{tag}.out")

    opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    compiler = "clang++" if bench_obj.lang in ["CXX", "C++"] else "clang"

    extracted_features = {}
    size = -1

    try:
        # --- 2. 自动化稳定性补丁 (修复 LCSSA) ---
        # 如果 pipeline 为空或特殊标记，跳过此步
        if pipeline_str and "default<" not in pipeline_str:
            passes = pipeline_str.split(',')
            fixed_passes = []
            for p in passes:
                if any(x in p for x in ["loop", "licm", "lcssa"]):
                    fixed_passes.append("function(loop-simplify)")
                    fixed_passes.append("function(lcssa)")
                fixed_passes.append(p)
            actual_pipeline = ",".join(fixed_passes)
        else:
            actual_pipeline = pipeline_str

        # --- 3. 运行 opt 提取特征 ---
        # 注意：如果 pipeline_str 是 "default<O0>"，opt 可能会报错，
        # 但 RL 训练时通常传的是具体的 Pass 列表或 default<Oz>，所以这里保持现状即可
        cmd_opt = [opt_tool, f"-passes={actual_pipeline}", base_bc, "-o", opt_bc, "-stats", "-stats-json"]
        
        # 增加超时处理
        res_opt = subprocess.run(cmd_opt, capture_output=True, text=True, timeout=60)
        
        # 解析特征 (即使 returncode != 0 也尝试解析，因为有时 crash 前会有输出)
        try:
            all_stats = json.loads(res_opt.stderr)
            extracted_features = {k: v for k, v in all_stats.items() if k in pass_stats_keys}
        except:
            json_match = re.search(r'\{.*\}', res_opt.stderr, re.DOTALL)
            if json_match:
                try:
                    all_stats = json.loads(json_match.group())
                    extracted_features = {k: v for k, v in all_stats.items() if k in pass_stats_keys}
                except: pass

        if res_opt.returncode != 0:
            # 如果 opt 失败（比如不支持 default<O0>），直接返回失败，不进行后续编译
            # print(f"Opt Failed: {res_opt.stderr}") 
            return extracted_features, -1

        # --- 4. 编译链接 (关键修正) ---
        # 【修正】：使用传入的 link_opts，并追加 strip-all
        cmd_link = [compiler, opt_bc] + link_opts + ["-Wl,--strip-all", "-o", exe_out, "-w"]
        
        if bench_obj.need_math: cmd_link.append("-lm")
        
        # 设置超时防止链接卡死
        res_link = subprocess.run(cmd_link, capture_output=True, timeout=30)
        
        if res_link.returncode == 0:
            # 链接成功
            # 再次 strip 只是双重保险，如果 link 阶段支持 -Wl,--strip-all 则此步由于文件已 strip 可能会静默
            subprocess.run(["strip", exe_out], capture_output=True)
            
            if measure_type == "full":
                size = os.path.getsize(exe_out)
            else:
                # 默认 text
                size = get_text_segment_size(exe_out)
        else:
            # 链接失败回退策略 (仅用于防止 RL 环境崩溃，O0 验证时不应依赖此值)
            size = os.path.getsize(opt_bc)

    except Exception as e:
        print(f"Extraction Error: {e}")
    finally:
        # --- 5. 清理临时文件 ---
        for f in [opt_bc, exe_out]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        try:
            if os.path.exists(tmp_dir) and not os.listdir(tmp_dir):
                os.rmdir(tmp_dir)
        except: pass

    return extracted_features, size
    
def get_benchmarks(root):
    """遍历目录获取所有 Benchmark 对象"""
    benchmarks = []
    if not os.path.exists(root): return []
    for d in sorted(os.listdir(root)):
        path = os.path.join(root, d)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "src")):
            benchmarks.append(Benchmark(d, path))
    return benchmarks

def _parse_loop_info(bc_file):
    """
    内部私有函数：通过解析 print<loops> 获取循环结构特征
    """
    opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    cmd = [opt_tool, "-passes=print<loops>", bc_file, "-disable-output"]
    
    # 注意：LLVM 分析类 Pass 的打印信息在 stderr
    res = subprocess.run(cmd, capture_output=True, text=True)
    output = res.stderr
    
    loop_matches = re.findall(r"Loop at depth (\d+)", output)
    num_loops = len(loop_matches)
    max_depth = 0
    num_nested = 0
    
    if loop_matches:
        depths = [int(d) for d in loop_matches]
        max_depth = max(depths)
        num_nested = len([d for d in depths if d > 1])
        
    return {
        "NumLoops": num_loops,
        "MaxLoopDepth": max_depth,
        "NumNestedLoops": num_nested
    }

# def extract_initial_autophase(bench_obj, work_dir):
#     """
#     提取程序的完整初始静态特征 (InstCount + LoopInfo)
#     """
#     base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
#     if not os.path.exists(base_bc):
#         base_bc = bench_obj.compile_to_base_bc(work_dir)
        
#     opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    
#     # 1. 获取指令统计 (原有逻辑)
#     cmd_inst = [opt_tool, "-passes=instcount", base_bc, "-o", "/dev/null", "-stats", "-stats-json"]
#     res_inst = subprocess.run(cmd_inst, capture_output=True, text=True)
    
#     all_features = {}
#     if res_inst.returncode == 0:
#         try:
#             all_features = json.loads(res_inst.stderr)
#         except:
#             all_features = {}

#     # 2. 获取循环统计 (新集成的逻辑)
#     # 将结果映射到符合 AutoPhase 定义的 Key 名上
#     loop_data = _parse_loop_info(base_bc)
#     all_features["static_loop.NumLoops"] = loop_data["NumLoops"]
#     all_features["static_loop.MaxLoopDepth"] = loop_data["MaxLoopDepth"]
#     all_features["static_loop.NumNestedLoops"] = loop_data["NumNestedLoops"]
    
#     return all_features
def extract_feature_autophase(current_bc_path):
    """
    对指定的 bc 文件进行 instcount 和 loop 分析，提取 Autophase 风格特征
    """
    if not os.path.exists(current_bc_path):
        return {}
        
    opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    
    # 1. 获取指令统计 (instcount)
    # 注意：这里直接对 current_bc_path 进行分析
    cmd_inst = [opt_tool, "-passes=instcount", current_bc_path, "-o", "/dev/null", "-stats", "-stats-json"]
    res_inst = subprocess.run(cmd_inst, capture_output=True, text=True)
    
    all_features = {}
    if res_inst.returncode == 0:
        try:
            # LLVM 的 stats 输出通常在 stderr
            all_features = json.loads(res_inst.stderr)
        except:
            # 尝试正则提取，防止有额外日志干扰 JSON 解析
            import re
            json_match = re.search(r'\{.*\}', res_inst.stderr, re.DOTALL)
            if json_match:
                 all_features = json.loads(json_match.group())

    # 2. 获取循环统计 (复用你的逻辑，但也需要改传入参数)
    loop_data = _parse_loop_info(current_bc_path) 
    
    # 3. 整合
    all_features["static_loop.NumLoops"] = loop_data["NumLoops"]
    all_features["static_loop.MaxLoopDepth"] = loop_data["MaxLoopDepth"]
    all_features["static_loop.NumNestedLoops"] = loop_data["NumNestedLoops"]
    
    return all_features
# def extract_initial_autophase(bench_obj, work_dir):
#     """
#     提取程序的初始静态特征（Autophase/InstCount）
#     """
#     base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
#     if not os.path.exists(base_bc):
#         base_bc = bench_obj.compile_to_base_bc(work_dir)
        
#     opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
    
#     # 使用 instcount 分析 Pass
#     # -stats 会输出几乎涵盖 Autophase 要求的全部指令统计
#     cmd = [opt_tool, "-passes=instcount", base_bc, "-o", "/dev/null", "-stats", "-stats-json"]
#     res = subprocess.run(cmd, capture_output=True, text=True)
    
#     if res.returncode == 0:
#         try:
#             # 解析并提取静态统计项
#             raw_stats = json.loads(res.stderr)
#             # 你可以进一步编写一个过滤逻辑，只保留 Autophase 官方定义的 56 个 key
#             return raw_stats 
#         except:
#             return {}
#     return {}


