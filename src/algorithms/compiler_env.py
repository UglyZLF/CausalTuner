import gymnasium as gym
import numpy as np
from gymnasium import spaces
import os
import shutil
import subprocess
import json
import hashlib
from src.utils.actions import Actions
from src.utils.common import compile_extract_and_measure, get_text_segment_size, LLVM_BIN_PATH

# Autophase 风格的核心特征键名 (基于 instcount 和 loop-info 实际输出)
AUTOPHASE_KEYS = [
    'TotalInsts', 'TotalBlocks', 'TotalFuncs', 'TotalLoops', 'MaxLoopDepth', 'NumNestedLoops',
    'NumAShrInst', 'NumAddInst', 'NumAllocaInst', 'NumAndInst', 'NumBrInst', 'NumCallInst', 
    'NumExtractValueInst', 'NumFAddInst', 'NumFCmpInst', 'NumFDivInst', 'NumFMulInst', 
    'NumFNegInst', 'NumFPExtInst', 'NumFPToSIInst', 'NumFPTruncInst', 'NumFSubInst', 
    'NumGetElementPtrInst', 'NumICmpInst', 'NumInsertValueInst', 'NumInvokeInst', 
    'NumLandingPadInst', 'NumLoadInst', 'NumMulInst', 'NumOrInst', 'NumPHIInst', 
    'NumResumeInst', 'NumRetInst', 'NumSDivInst', 'NumSExtInst', 'NumSIToFPInst', 
    'NumSRemInst', 'NumSelectInst', 'NumShlInst', 'NumStoreInst', 'NumSubInst', 
    'NumTruncInst', 'NumZExtInst', 'NumBitCastInst', 'NumPtrToIntInst', 'NumIntToPtrInst',
    'NumSwitchInst', 'NumUnreachableInst', 'NumFenceInst', 'NumAtomicCmpXchgInst', 'NumAtomicRMWInst',
    'NumLShrInst', 'NumUDivInst', 'NumVAArgInst', 'NumUserInst'
]

class CompilerEnv(gym.Env):
    def __init__(self, bench_obj, work_dir, max_steps=45):
        super(CompilerEnv, self).__init__()
        self.bench = bench_obj
        self.work_dir = work_dir
        self.max_steps = max_steps
        
        # 1. 定义动作空间
        self.action_list = [a.value for a in Actions]
        self.action_space = spaces.Discrete(len(self.action_list))
        
        # 2. 定义观测空间 (Autophase 特征维度)
        self.obs_dim = len(AUTOPHASE_KEYS)
        # 使用 log(x+1) 处理特征，范围通常在 0 到 20 之间
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(self.obs_dim,), dtype=np.float32
        )
        
        # 3. 设置临时目录 (每个环境独立，防止并行冲突)
        # 使用 PID 区分不同进程
        self.env_id = os.getpid()
        self.tmp_dir = os.path.join(work_dir, bench_obj.name, f"env_tmp_{self.env_id}")
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        # 4. 路径定义
        self.base_bc = os.path.join(work_dir, bench_obj.name, f"{bench_obj.name}.bc")
        self.current_bc = os.path.join(self.tmp_dir, "current.bc")
        self.next_bc = os.path.join(self.tmp_dir, "next.bc")
        
        # 5. 确保 Base BC 存在
        if not os.path.exists(self.base_bc):
            print(f"Compiling base BC for {bench_obj.name}...")
            bench_obj.compile_to_base_bc(work_dir)

        # 6. 计算基准分母 (initial_size)
        # 基准 Oz 大小 (Target to beat)
        _, self.baseline_oz_size = compile_extract_and_measure(
            self.bench, self.work_dir, "", link_opts=["-Oz"]
        )
        
        # 基准 O0 大小 (用于计算 Reward 的分母，使得奖励更密集)
        _, self.baseline_o0_size = compile_extract_and_measure(
            self.bench, self.work_dir, "", link_opts=["-O0"]
        )
        
        if self.baseline_oz_size <= 0:
            self.baseline_oz_size = 1000000 # Fallback
        if self.baseline_o0_size <= 0:
            self.baseline_o0_size = self.baseline_oz_size * 1.5 # Fallback estimate

        self.oz_size = self.baseline_oz_size
        self.last_size = self.baseline_o0_size # 初始状态我们假设是从 O0 开始优化 (或者实际上 current.bc 是 O0)


    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 清理并初始化 current.bc
        shutil.copy(self.base_bc, self.current_bc)
        
        self.current_pipeline = []
        self.steps = 0
        # 初始状态是从 O0 开始，所以 last_size 设为 O0 baseline
        self.last_size = self.baseline_o0_size
        
        # 获取初始特征 (针对 current.bc)
        obs = self._get_autophase_features(self.current_bc)
        
        return obs, {}

    def step(self, action_idx):
        action_name = self.action_list[action_idx]
        self.steps += 1
        self.current_pipeline.append(action_name)
        
        # --- 1. 执行 Action (应用 Pass) ---
        # 输入: self.current_bc -> 输出: self.next_bc
        success = self._apply_pass(self.current_bc, self.next_bc, action_name)
        
        info = {}
        reward = 0
        terminated = False
        truncated = self.steps >= self.max_steps
        
        if not success:
            # 编译失败惩罚
            reward = -1.0
            # 状态保持不变 (obs 还是旧的)
            obs = self._get_autophase_features(self.current_bc)
        else:
            # --- 2. 测量新体积 ---
            # 关键：这里我们虽然用 -Oz 链接来测量 Reward，
            # 但 environment 内部维护的 bc 文件只应用了 action pass，还没有做链接优化。
            current_size = self._measure_size(self.next_bc)
            
            if current_size > 0:
                # --- 3. 计算 Reward (User Requested Logic) ---
                # 逻辑 A: (上一步体积 - 当前体积) / O0基准体积
                # 这样奖励数值会比较大且密集
                reward = (self.last_size - current_size) / self.baseline_o0_size
            
                # 逻辑 B: 如果打破了 Oz 的记录，给予额外奖励
                if current_size < self.baseline_oz_size:
                    # 额外奖励可以是固定的，也可以是成比例的
                    # 例如：(Oz基准 - 当前体积) / Oz基准 * 5
                    bonus = (self.baseline_oz_size - current_size) / self.baseline_oz_size * 5.0
                    reward += bonus
                
                self.last_size = current_size
                
                # 更新 current.bc 为 next.bc (状态推进)
                shutil.move(self.next_bc, self.current_bc)
            else:
                reward = -1.0 # 测量失败
            
            # --- 4. 提取新特征 (针对更新后的 bc) ---
            obs = self._get_autophase_features(self.current_bc)
            
            info = {
                "size": current_size,
                "oz_size": self.baseline_oz_size,
                "o0_size": self.baseline_o0_size,
                "pipeline": ",".join(self.current_pipeline)
            }

        return obs, reward, terminated, truncated, info

    def _apply_pass(self, input_bc, output_bc, pass_name):
        """调用 opt 执行单个 pass"""
        opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
        
        # 如果是 loop pass，通常需要前置 loop-simplify
        actual_pass = pass_name
        if any(x in pass_name for x in ["loop", "lcssa", "licm"]):
             actual_pass = f"function(loop-simplify),{pass_name}"
             
        cmd = [opt_tool, f"-passes={actual_pass}", input_bc, "-o", output_bc]
        
        try:
            # 设置超时防止死锁
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except subprocess.CalledProcessError:
            return False
        except subprocess.TimeoutExpired:
            return False

    def _measure_size(self, bc_file):
        """将当前的 bc 文件使用 -Oz 链接并测量体积"""
        compiler = "clang++" if self.bench.lang in ["CXX", "C++"] else "clang"
        tmp_exe = os.path.join(self.tmp_dir, "tmp.exe")
        
        cmd_link = [
            compiler, bc_file, 
            "-Oz",               # 保持后端优化，看 Agent 能否锦上添花
            "-Wl,--strip-all",   # 剥离符号表，只看指令密度
            "-o", tmp_exe
        ]
        if self.bench.need_math: cmd_link.append("-lm")
        
        try:
            subprocess.run(cmd_link, check=True, capture_output=True, timeout=60)
            # 再次确保 strip
            subprocess.run(["strip", tmp_exe], check=False, capture_output=True)
            return os.path.getsize(tmp_exe)
        except:
            return -1
        finally:
            if os.path.exists(tmp_exe): os.remove(tmp_exe)

    def _get_autophase_features(self, bc_file):
        """
        针对指定的 bc_file 提取 instcount 和 loops 信息
        返回 np.array
        """
        opt_tool = os.path.join(LLVM_BIN_PATH, "opt") if LLVM_BIN_PATH else "opt"
        features = {k: 0 for k in AUTOPHASE_KEYS}
        
        # 1. 运行 instcount
        # 注意：instcount 的输出在 stderr
        cmd = [opt_tool, "-passes=instcount", bc_file, "-o", "/dev/null", "-stats", "-stats-json"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            # 尝试解析 JSON
            try:
                data = json.loads(res.stderr)
                # 映射 instcount 的键到 features
                for key, val in data.items():
                    # instcount 的 key 通常是 "instcount.TotalInsts" 格式
                    short_key = key.split('.')[-1]
                    if short_key in features:
                        features[short_key] = val
            except json.JSONDecodeError:
                # 如果 JSON 解析失败，尝试正则兜底 (针对某些旧版本 LLVM 输出非标准 JSON)
                # 格式如: "  123 instcount - Number of Add insts" (比较难解析，尽量依赖 stats-json)
                pass 
        except:
            pass
            
        # 2. 运行 print<loops> 获取循环深度
        try: 
            cmd_loop = [opt_tool, "-passes=print<loops>", bc_file, "-disable-output"] 
            res_loop = subprocess.run(cmd_loop, capture_output=True, text=True, timeout=5) 
            output = res_loop.stderr 
            
            import re 
            loops = re.findall(r"Loop at depth (\d+)", output) 
            if loops: 
                depths = [int(d) for d in loops] 
                features['TotalLoops'] = len(depths) 
                features['MaxLoopDepth'] = max(depths) 
                features['NumNestedLoops'] = len([d for d in depths if d > 1]) 
        except: 
            pass 

        # 3. 转换为向量并归一化 
        vec = [features[k] for k in AUTOPHASE_KEYS] 
        # 使用 log(x+1) 进行数值压缩，利于神经网络处理 
        vec = np.log1p(np.array(vec, dtype=np.float32)) 
        
        return vec

    def close(self):
        # 清理临时目录
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)