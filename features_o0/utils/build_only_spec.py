import os
import json
import subprocess
import time
import re
import glob
import sys

# Configuration
SPEC_DIR = "/data/spec2017"
CONFIG_FILE = "llvm14_tuned"
JSON_CONFIG_PATH = os.path.abspath("opt_config.json")

def create_config(flags):
    # 确保每个 flag 都以 '-' 开头，并用空格连接
    # 结果类似于 "-licm -gvn"
    formatted_flags = " ".join([f if f.startswith('-') else f'-{f}' for f in flags])
    config_data = {
        "params": formatted_flags
    }
    with open(JSON_CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)

def run_spec_benchmark(benchmark, flags, iterations=5):
    """
    Run a SPEC benchmark with specified compilation flags and return the average runtime.
    
    Args:
        benchmark (str): Name of the benchmark (e.g., '544.nab_r')
        flags (list): List of compilation flags (e.g., ['-licm', '-gvn'])
        iterations (int): Number of times to run the benchmark (default: 3)
        
    Returns:
        float: Average runtime in seconds, or None if the run fails.
    """
    create_config(flags)
    
    
    # Run SPEC with --rebuild to ensure compilation with new flags
    # Added --iterations={iterations} to control the number of runs
    cmd = f"cd {SPEC_DIR} && source shrc && runcpu --config=llvm14_tuned --action=build --rebuild --tune=base --size=test --define opt_cfg_json={JSON_CONFIG_PATH} {benchmark}"
    
    # cmd = (
    #     f"cd {SPEC_DIR} && source shrc && "
    #     f"runcpu --config=llvm14_tuned --action=run --rebuild "
    #     f"--size=test --iterations={iterations} --nosysinfo " # 核心优化点
    #     f"--define opt_cfg_json={JSON_CONFIG_PATH} {benchmark}"
    # )
    print(f"Running SPEC command for {benchmark} with flags: {' '.join(flags)} (Iterations: {iterations})...")
    
    # try:
    #     subprocess.run(['/bin/bash', '-c', cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # except subprocess.CalledProcessError:
    #     print(f"Run failed for {benchmark}.")
    #     return None
    try:
        # 将 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL 删掉或改为 None
        subprocess.run(['/bin/bash', '-c', cmd], check=True) 
    except subprocess.CalledProcessError:
        print(f"Run failed for {benchmark}.")
        return None

    # Parse results
    return None # build only

# def parse_results(benchmark):
#     # Find the latest result file
#     result_files = glob.glob(os.path.join(SPEC_DIR, "result", "CPU2017.*.fprate.test.txt"))
#     if not result_files:
#         return None

#     # Get the most recent file
#     latest_file = max(result_files, key=os.path.getmtime)
    
#     runtimes = []
#     with open(latest_file, 'r') as f:
#         for line in f:
#             if benchmark in line:
#                 parts = line.split()
#                 if len(parts) >= 3:
#                     try:
#                         runtime = float(parts[2])
#                         runtimes.append(runtime)
#                     except ValueError:
#                         continue
    
#     if runtimes:
#         return sum(runtimes) / len(runtimes)
#     return None
def parse_results(benchmark):
    result_dir = os.path.join(SPEC_DIR, "result")
    pattern = os.path.join(result_dir, "CPU2017.*.log")
    result_files = glob.glob(pattern)
    
    if not result_files:
        return None

    # 1. 找到本次运行最新的 log
    latest_log = max(result_files, key=os.path.getmtime)
    
    # 提取运行编号（例如从 CPU2017.084.log 提取出 084）
    log_num_match = re.search(r'CPU2017\.(\d+)\.log', latest_log)
    log_num = log_num_match.group(1) if log_num_match else None

    runtimes = []
    try:
        with open(latest_log, 'r') as f:
            for line in f:
                if "Success" in line and benchmark in line and "runtime=" in line:
                    match = re.search(r'runtime=([\d\.]+)', line)
                    if match:
                        val = float(match.group(1))
                        if val > 0: runtimes.append(val)
        
        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None

        # # --- 2. 核心清理逻辑：解析完立即删除相关文件 ---
        # if log_num:
        #     # a. 删除 result 目录下所有带该编号的文件 (.log, .txt, .html, .rsf)
        #     # 例如: CPU2017.084.*
        #     for f in glob.glob(os.path.join(result_dir, f"CPU2017.{log_num}.*")):
        #         try: os.remove(f)
        #         except: pass
            
        #     # b. 删除 config 目录下 SPEC 自动生成的备份配置文件
        #     # 例如: llvm14_tuned.cfg.084
        #     for f in glob.glob(os.path.join(SPEC_DIR, "config", f"*.cfg.{log_num}")):
        #         try: os.remove(f)
        #         except: pass
                
        return avg_runtime

    except Exception as e:
        print(f"Error parsing or cleaning log file: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_spec.py <benchmark> [flags...]")
        sys.exit(1)
    
    benchmark = sys.argv[1]
    # Default flags from util.py if none provided
    if len(sys.argv) > 2:
        flags = sys.argv[2:]
    else:
        # Default flags (O3 subset)
        flags = ['-tbaa', '-licm', '-gvn', '-instcombine', '-early-cse', '-simplifycfg']
    
    print(f"--- Debugging {benchmark} ---")
    
    start_time = time.time()
    avg_runtime = run_spec_benchmark(benchmark, flags, iterations=5)
    elapsed = time.time() - start_time
    
    if avg_runtime:
        print(f"Success! Average Runtime: {avg_runtime:.4f}s (Total time: {elapsed:.2f}s)")
        print(f"{avg_runtime:.4f}") # Explicitly print the value as requested
    else:
        print(f"Run failed or could not parse results.")

if __name__ == "__main__":
    main()
