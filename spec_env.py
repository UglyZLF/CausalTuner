import os
import json
import subprocess
import re
import glob
import time
import shutil
from util import Util

class SpecEnv:
    def __init__(self, benchmark, spec_dir="/data/spec2017", config_name="llvm14_tuned"):
        self.benchmark = benchmark
        self.spec_dir = spec_dir
        self.config_name = config_name
        self.json_path = os.path.abspath(f"opt_config_{benchmark}.json")
        
        # 使用 util.py 获取过滤后的合法 Flags 空间
        u = Util()
        self.all_flags = u.gain_flags()
        self.n_flags = len(self.all_flags)

        # 基准值字典 (对应 -O3)
        self.baselines = {
            "511.povray_r": 1.1455,
            "531.deepsjeng_r": 17.4039,
            "544.nab_r": 3.1951
        }
        self.baseline = self.baselines.get(benchmark, 1.0)
        
    def get_fitness(self, binary_vector):
        """
        核心评价函数：
        输入：[0, 1, 0, 0...] 长度为 n_flags 的向量
        输出：负的加速比 (为了让算法最小化)
        """
        # 1. 转换二进制向量为 Flag 字符串
        selected_flags = [self.all_flags[i] for i, val in enumerate(binary_vector) if val == 1]
        pass_str = " ".join(selected_flags)

        # 2. 写入 JSON 配置
        with open(self.json_path, 'w') as f:
            json.dump({"params": pass_str}, f, indent=4)

        # 3. 执行 SPEC
        cmd = (
            f"cd {self.spec_dir} && source ./shrc && "
            f"runcpu --config={self.config_name} --action=run --rebuild "
            f"--size=test --iterations=1 --output_format=txt "
            f"--define opt_cfg_json={self.json_path} {self.benchmark}"
        )
        
        runtime = 9999.0
        try:
            # 设定 10 分钟超时防止挂死
            res = subprocess.run(['/bin/bash', '-c', cmd], capture_output=True, text=True, timeout=600)
            if res.returncode == 0:
                runtime = self._parse_log()
        except Exception as e:
            print(f"Error executing {self.benchmark}: {e}")

        # 4. 计算加速比
        speedup = self.baseline / runtime if runtime < 9000 else 0.0
        print(f"[{self.benchmark}] Runtime: {runtime:.4f}s | Speedup: {speedup:.4f}x")
        
        # 返回负加速比，因为优化器通常寻找最小值
        return -speedup

    def _parse_log(self):
        result_dir = os.path.join(self.spec_dir, "result")
        logs = glob.glob(os.path.join(result_dir, "CPU2017.*.log"))
        if not logs: return 9999.0
        
        latest_log = max(logs, key=os.path.getmtime)
        log_num = re.search(r'CPU2017\.(\d+)\.log', latest_log).group(1)
        
        runtime = 9999.0
        with open(latest_log, 'r') as f:
            for line in f:
                if "Success" in line and self.benchmark in line and "runtime=" in line:
                    m = re.search(r'runtime=([\d\.]+)', line)
                    if m: runtime = float(m.group(1))
        
        # 立即清理文件防止磁盘溢出
        for f in glob.glob(os.path.join(result_dir, f"CPU2017.{log_num}.*")):
            try: os.remove(f)
            except: pass
        return runtime