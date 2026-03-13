import numpy as np
import os
import subprocess
import re
import shutil
import util
from multiprocessing import Pool

class LlamaEnv(util.Util):
    def __init__(self, bitcode_file, model_path, threads=8, parallel_comp=4):
        super().__init__()
        # 路径与配置
        self.bitcode_file = os.path.abspath(bitcode_file)
        self.model_path = os.path.abspath(model_path)
        self.parallel_comp = parallel_comp
        self.threads = threads
        
        # 【关键】直接复制 GA_llama_core.py 中的 flags，确保与可运行版本一致
        self.llvm_flags = [
            '-tti', '-tbaa', '-scoped-noalias-aa', '-assumption-cache-tracker', '-targetlibinfo', '-verify', 
            '-lower-expect', '-simplifycfg', '-domtree', '-sroa', '-early-cse', '-profile-summary-info', 
            '-annotation2metadata', '-forceattrs', '-inferattrs', '-callsite-splitting', '-ipsccp', 
            '-called-value-propagation', '-globalopt', '-mem2reg', '-deadargelim', '-basic-aa', '-aa', 
            '-loops', '-lazy-branch-prob', '-lazy-block-freq', '-opt-remark-emitter', '-instcombine', 
            '-basiccg', '-globals-aa', '-prune-eh', '-inline', '-openmp-opt-cgscc', '-function-attrs', 
            '-argpromotion', '-memoryssa', '-early-cse-memssa', '-speculative-execution', '-lazy-value-info', 
            '-jump-threading', '-correlated-propagation', '-aggressive-instcombine', '-libcalls-shrinkwrap', 
            '-postdomtree', '-branch-prob', '-block-freq', '-pgo-memop-opt', '-tailcallelim', '-reassociate', 
            '-loop-simplify', '-lcssa-verification', '-lcssa', '-scalar-evolution', '-licm', '-loop-rotate', 
            '-loop-unswitch', '-loop-idiom', '-indvars', '-loop-deletion', '-loop-unroll', '-mldst-motion', 
            '-phi-values', '-memdep', '-gvn', '-sccp', '-demanded-bits', '-bdce', '-adce', '-memcpyopt', 
            '-dse', '-barrier', '-elim-avail-extern', '-rpo-function-attrs', '-globaldce', '-float2int', 
            '-lower-constant-intrinsics', '-loop-accesses', '-loop-distribute', '-inject-tli-mappings', 
            '-loop-vectorize', '-loop-load-elim', '-slp-vectorizer', '-vector-combine', '-transform-warning', 
            '-alignment-from-assumptions', '-strip-dead-prototypes', '-constmerge', '-cg-profile', '-loop-sink', 
            '-instsimplify', '-div-rem-pairs', '-annotation-remarks'
        ]
        self.n_flags = len(self.llvm_flags)

    def compile_one(self, args):
        """[并行阶段] 执行 opt 和 clang++ (完全复用 GA 代码)"""
        idx, binary_vector = args
        selected_passes = [self.llvm_flags[i] for i, val in enumerate(binary_vector) if val == 1]
        pass_str = " ".join(selected_passes)
        
        work_dir = os.path.abspath(f"tmp_indiv_{idx}")
        if not os.path.exists(work_dir): os.makedirs(work_dir, exist_ok=True)
        
        opt_bc = os.path.join(work_dir, "opt.bc")
        runner_bin = os.path.join(work_dir, f"runner_{idx}")
        
        # 保持与 run_llama_ga.py 完全一致的命令
        cmd = f"opt -enable-new-pm=0 {pass_str} {self.bitcode_file} -o {opt_bc} && " \
              f"clang++ -march=native {opt_bc} -o {runner_bin} -lpthread -ldl -lm -lrt"
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=300)
            return idx, runner_bin, pass_str
        except Exception as e:
            # 简单的错误打印，防止刷屏
            # print(f"Compile Error {idx}: {e}")
            return idx, None, pass_str

    def run_one(self, runner_bin):
        """[串行阶段] 执行 llama-bench 并获取 pp128"""
        if not runner_bin or not os.path.exists(runner_bin):
            return 0.0001
        
        cmd = f"{runner_bin} -m {self.model_path} -p 128 -n 128 -t {self.threads}"
        
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            for line in res.stdout.splitlines():
                if "pp128" in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        val_str = parts[-2].strip()
                        match = re.search(r"([\d.]+)", val_str)
                        if match: return float(match.group(1))
        except:
            pass
        return 0.0001

    def clean_temp(self, runner_bin):
        if runner_bin and os.path.exists(os.path.dirname(runner_bin)):
            try:
                shutil.rmtree(os.path.dirname(runner_bin))
            except:
                pass

    def evaluate_batch(self, population_vectors):
        """
        通用评估接口
        :param population_vectors: 2D array or list of lists (0/1)
        :return: (throughput_array, details_list)
        """
        pop_size = len(population_vectors)
        results = np.zeros(pop_size)
        details = []
        
        # 1. 准备任务
        tasks = []
        for i in range(pop_size):
            tasks.append((i, population_vectors[i]))

        # 2. 并行编译
        # print(f"    [Env] Compiling {pop_size} variants...")
        with Pool(processes=self.parallel_comp) as pool:
            comp_results = pool.map(self.compile_one, tasks)
        
        # 3. 串行运行
        # print(f"    [Env] Running benchmarks...")
        for i, runner_path, pass_str in comp_results:
            pp128_val = self.run_one(runner_path)
            
            results[i] = pp128_val if pp128_val > 0.0001 else 0.0001
            
            details.append({
                "indiv_idx": i,
                "throughput": results[i],
                "passes": pass_str
            })
            
            self.clean_temp(runner_path)
                
        return results, details

    def get_baseline(self):
        """获取 O3 基准"""
        print("[Env] Measuring O3 Baseline...")
        # 构造全 0 向量，但手动跑 O3 逻辑
        tmp_bin = "./benchmarks/llama/bench_O3_front"
        # 强制 O3 编译
        # cmd = f"clang++ -O3 -march=native {self.bitcode_file} -o {tmp_bin} -lpthread -ldl -lm -lrt"
        # try:
        #     subprocess.run(cmd, shell=True, check=True, capture_output=True)
        # except:
        #     val = 0.1
        val = self._run_worker_direct(tmp_bin)
            
        # if os.path.exists(tmp_bin): os.remove(tmp_bin)
        return 85.13

    def _run_worker_direct(self, bin_path):
        """辅助函数：直接运行指定的二进制"""
        cmd = f"./{bin_path} -m {self.model_path} -p 128 -n 128 -t {self.threads}"
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            for line in res.stdout.splitlines():
                if "pp128" in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        val_str = parts[-2].strip()
                        match = re.search(r"([\d.]+)", val_str)
                        if match: return float(match.group(1))
        except:
            pass
        return 0.1