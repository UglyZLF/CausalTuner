import sys
import json
import time
import os
from spec_env import SpecEnv
from algorithm.Nevergrad_alg_spec import NevergradOptimizer
from algorithm.GroupTunerAlg_spec import GroupTunerOptimizer
from algorithm.BOCA_spec import BOCAOptimizer
from algorithm.OpenTuner_spec import OpenTunerOptimizer
from util import Util
from algorithm.RandomSearch_spec import RandomSearchOptimizer
from algorithm.CausalGuidedGA_spec import CausalGuidedGAOptimizer
# from algorithms.GAnew import GAOptimizer # 如果你重构了 GA
u = Util()
valid_flags = u.gain_flags()
def main():
    if len(sys.argv) < 3:
        print("Usage: python run_spec_exp.py <benchmark> <algo> [pop] [gen]")
        sys.exit(1)

    benchmark = sys.argv[1]
    algo_name = sys.argv[2]
    n_pop = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    n_gen = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    # 1. 初始化环境 (自动包含 Baseline 和 Flag 空间)
    env = SpecEnv(benchmark)
    
    # 2. 准备结果记录
    start_time = time.time()
    budget = 500
    
    # 3. 选择算法并运行
    if algo_name == "nevergrad":
        opt = NevergradOptimizer(n_flags=env.n_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "grouptuner":
        # 注意：GroupTuner 需要传入 all_flags 以便分组
        # opt = GroupTunerOptimizer(env.all_flags, n_pop=n_pop, n_gen=n_gen)
        opt = GroupTunerOptimizer(all_flags=valid_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "boca":
        # 初始化 BOCA
        opt = BOCAOptimizer(n_flags=env.n_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "opentuner":
        # OpenTuner 内部会自动分配 pop 和 gen 的逻辑
        opt = OpenTunerOptimizer(env.n_flags, budget=budget)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "random":
        # 初始化 RandomSearch
        opt = RandomSearchOptimizer(n_flags=env.n_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "causal_ga":
        # 使用 CausalGuidedGAOptimizer，传入 valid_flags 进行层级划分
        opt = CausalGuidedGAOptimizer(all_flags=valid_flags, n_pop=n_pop, n_gen=n_gen)
        best_vec, best_fit, curve = opt.run(env.get_fitness)
    elif algo_name == "ga":
        # opt = GAOptimizer(...)
        pass
    
    elapsed = time.time() - start_time

    # 4. 汇总输出
    best_flags_str = " ".join([env.all_flags[i] for i, v in enumerate(best_vec) if v == 1])
    
    report = {
        "benchmark": benchmark,
        "algorithm": algo_name,
        "baseline": env.baseline,
        "best_speedup": -best_fit,  # 转换回正数加速比
        "best_flags": best_flags_str,
        "cost_time": elapsed,
        "curve": curve
    }

    output_file = f"report_{benchmark}_{algo_name}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=4)
    
    print(f"\nOptimization Finished! Final Speedup: {-best_fit:.4f}x")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()