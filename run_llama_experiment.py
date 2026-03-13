import sys
import json
import time
import os
import numpy as np

# 1. 引入新定义的稳定环境
from llama_env import LlamaEnv

# 2. 引入算法

from algorithm.GroupTunerAlg_llama import GroupTunerOptimizer
from algorithm.Nevergrad_alg_llama import NevergradOptimizer
from algorithm.CausalGuidedGA_llama import CausalGuidedGAOptimizer

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_llama_experiment.py <algo> [pop] [gen]")
        print("Supported: ga, grouptuner, nevergrad")
        sys.exit(1)

    algo_name = sys.argv[1]
    n_pop = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    n_gen = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    # --- 路径配置 (与 run_llama_ga.py 保持一致) ---
    BITCODE = "benchmarks/llama/llama-bench.bc"
    MODEL = "/data/compiler_demo/work/llama_bench/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    THREADS = 8
    PARALLEL_COMP = 4

    if not os.path.exists(BITCODE):
        print(f"Error: {BITCODE} not found.")
        return

    # --- 初始化环境 ---
    print(f"[*] Initializing LlamaEnv for {algo_name}...")
    # 使用 LlamaEnv 类
    env = LlamaEnv(BITCODE, MODEL, threads=THREADS, parallel_comp=PARALLEL_COMP)
    
    # 测基准
    baseline_throughput = env.get_baseline()
    print(f"[*] Baseline (O3): {baseline_throughput:.2f} t/s")

    # --- 定义 Fitness (Loss Function) ---
    def get_fitness(vector):
        # 确保转为 0/1 列表或数组
        if isinstance(vector, np.ndarray):
            vec_bin = (vector > 0.5).astype(int)
        else:
            vec_bin = [1 if x > 0.5 else 0 for x in vector]
            
        # 调用 batch 接口，虽然只评估一个
        results, _ = env.evaluate_batch([vec_bin])
        throughput = results[0]
        
        # 目标：最小化 (-Speedup)
        # 防止 throughput 为 0 (编译失败) 导致除零
        if throughput < 0.001: 
            return 0.0 # 或者一个很大的数
            
        speedup = throughput / baseline_throughput
        return -speedup

    # --- 运行算法 ---
    start_time = time.time()
    best_vec = None
    best_fit = 0
    curve = []

    print(f"[*] Running {algo_name}...")

    if algo_name == "ga":
        # 如果是 GA，我们直接用你提供的 run_llama_ga.py 的逻辑
        # 或者为了统一报告格式，我们用 ga_algorithm.py 调用 env
        # 这里假设使用 ga_algorithm.py (需要稍微修改适配 LlamaEnv)
        # 为了稳妥，这里先不建议改 GA，GA 单独跑 run_llama_ga.py 即可
        print("For GA, please run 'python run_llama_ga.py' directly.")
        return

    elif algo_name == "grouptuner":
        # GroupTuner 需要 all_flags (names)
        opt = GroupTunerOptimizer(all_flags=env.llvm_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(get_fitness)

    elif algo_name == "nevergrad":
        # Nevergrad 需要 n_flags (count)
        opt = NevergradOptimizer(n_flags=env.n_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(get_fitness)
    elif algo_name == "causalga":
        # 传入 env.llvm_flags 以便内部做映射
        opt = CausalGuidedGAOptimizer(env_flags=env.llvm_flags, n_pop=n_pop, n_gen=n_gen, bench_name="llama-bench")
        best_vec, best_fit, curve = opt.run(get_fitness)


    else:
        print(f"Unknown algo: {algo_name}")
        return

    elapsed = time.time() - start_time
    final_speedup = -best_fit
    
    # 构造结果字符串
    if best_vec is not None:
         best_pass_str = " ".join([env.llvm_flags[i] for i, v in enumerate(best_vec) if v == 1])
    else:
         best_pass_str = "Unknown"

    # --- 保存报告 ---
    report = {
        "benchmark": "llama",
        "algorithm": algo_name,
        "config": {"pop": n_pop, "gen": n_gen},
        "baseline": baseline_throughput,
        "best_speedup": final_speedup,
        "best_passes": best_pass_str,
        "time": elapsed,
        "curve": curve
    }

    output_file = f"report_llama_{algo_name}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"\nOptimization Finished!")
    print(f"Speedup: {final_speedup:.4f}x")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()