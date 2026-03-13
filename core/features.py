import re
import os
import json
import subprocess
from collections import defaultdict

def extract_ir_features(bc_path, llvm_bin_path="llvm-dis"):
    """
    通过 LLVM opt 工具提取指令统计 (instcount) 和循环分析特征。
    直接保留 opt -stats-json 的原始键名。
    """
    if not os.path.exists(bc_path):
        return None
    
    # 确定 opt 工具路径
    opt_tool = "opt"
    
    features = {}

    # --- 执行 instcount 和 loop analysis ---
    # 使用 -stats-json 获取标准化的统计数据
    # 同时使用 print<loops> 获取循环深度信息
    # 2> 输出包含了 JSON (stats) 和 文本 (loops)
    cmd = [
        opt_tool, 
        "-passes=instcount,print<loops>", 
        bc_path, 
        "-o", "/dev/null", 
        "-disable-output", 
        "-stats", 
        "-stats-json"
    ]
    
    try:
        # LLVM 的 stats 和 loop info 都在 stderr
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = res.stderr
        
        # 1. 解析 JSON Stats (instcount 等)
        # 寻找 JSON 对象 { ... }
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            try:
                raw_stats = json.loads(json_match.group())
                # 直接保留所有统计特征，不做重命名
                features.update(raw_stats)
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse stats JSON for {bc_path}")
        
        # 2. 解析 Loop Info (文本)
        # 统计 "Loop at depth X" 出现的次数
        depths = re.findall(r'Loop at depth (\d+)', output)
        if depths:
            depth_ints = [int(d) for d in depths]
            features["static_loop.NumLoops"] = len(depth_ints)
            features["static_loop.MaxLoopDepth"] = max(depth_ints)
            features["static_loop.NumNestedLoops"] = len([d for d in depth_ints if d > 1])
        else:
            features["static_loop.NumLoops"] = 0
            features["static_loop.MaxLoopDepth"] = 0
            features["static_loop.NumNestedLoops"] = 0

    except Exception as e:
        print(f"Error extracting features: {e}")
        return None

    return features
    
def transform_to_isp(json_data):
    """
    将原始特征转换为 ISP (Instruction Set Property) 特征
    """
    total = json_data.get("instcount.TotalInsts", 1)
    if total == 0:
        total = 1
    
    isp = {
        "mem_density": (json_data.get("instcount.NumLoadInst", 0) + 
                        json_data.get("instcount.NumStoreInst", 0) + 
                        json_data.get("instcount.NumGetElementPtrInst", 0)) / total,
        
        "control_intensity": (json_data.get("instcount.NumBrInst", 0) + 
                              json_data.get("instcount.NumPHIInst", 0)) / total,
        
        "arith_logic_ratio": (json_data.get("instcount.NumAddInst", 0) + 
                              json_data.get("instcount.NumAndInst", 0)) / total,
        
        "loop_depth": json_data.get("static_loop.MaxLoopDepth", 0),
        
        "nested_ratio": json_data.get("static_loop.NumNestedLoops", 0) / (json_data.get("static_loop.NumLoops", 0) + 1e-5)
    }
    return isp

def transform_to_raw_features(json_data):
    """
    将原始特征转换为归一化的指令比例特征 (Normalized Instruction Counts)
    """
    total = json_data.get("instcount.TotalInsts", 1)
    if total == 0: total = 1
    
    # 我们选择编译器优化最相关的核心指令类别
    # 不建议放几百个特征，FCI 会跑不动，选这 12 个最具代表性的
    core_insts = [
        "instcount.NumAddInst", "instcount.NumSubInst", "instcount.NumMulInst", 
        "instcount.NumLoadInst", "instcount.NumStoreInst", "instcount.NumGetElementPtrInst",
        "instcount.NumBrInst", "instcount.NumPHIInst", "instcount.NumCallInst",
        "instcount.NumICmpInst", "instcount.NumBitCastInst", "instcount.NumAllocaInst"
    ]
    
    features = {}
    for inst in core_insts:
        # 归一化：指令数 / 总指令数
        features[inst] = json_data.get(inst, 0) / total
    
    # 保留循环特征，这对因果分析极度重要
    features["loop.MaxLoopDepth"] = json_data.get("static_loop.MaxLoopDepth", 0)
    features["loop.NestedRatio"] = json_data.get("static_loop.NumNestedLoops", 0) / (json_data.get("static_loop.NumLoops", 0) + 1e-5)
    
    return features

def get_bench_raw_features(bench_name, root_dir=None):
    """
    根据 benchmark 名称，自动查找并加载 features json，然后返回 ISP 特征。
    """
    if root_dir is None:
        # 假设 root_dir 是 core/.. 即项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    # 定义可能的搜索路径
    # 1. cbench: testsuite/{bench_name}/src/{bench_name}_features.json
    # 2. polybench: testsuite/{bench_name}/{bench_name}_features.json
    
    # 尝试构建路径
    paths_to_try = [
        os.path.join(root_dir, "testsuite", bench_name, "src", f"{bench_name}_features.json"),
        os.path.join(root_dir, "testsuite", bench_name, f"{bench_name}_features.json"),
        # 也可能在 features_o0 目录下
        os.path.join(root_dir, "features_o0", f"{bench_name}_features.json")
    ]
    
    json_path = None
    for p in paths_to_try:
        if os.path.exists(p):
            json_path = p
            break
            
    if not json_path:
        print(f"Warning: Features file for {bench_name} not found.")
        return None
        
    try:
        with open(json_path, 'r') as f:
            features = json.load(f)
            return transform_to_raw_features(features)
    except Exception as e:
        return None