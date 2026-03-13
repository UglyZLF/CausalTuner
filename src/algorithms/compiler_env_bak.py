import gymnasium as gym
import numpy as np
from gymnasium import spaces
from src.utils.actions import Actions
from src.utils.common import compile_extract_and_measure
# 【关键修改】直接导入你现有的特征 Key 列表
from src.utils.feature_extraction import pass_stats_keys

class CompilerEnv(gym.Env):
    def __init__(self, bench_obj, work_dir, max_steps=50):
        super(CompilerEnv, self).__init__()
        self.bench = bench_obj
        self.work_dir = work_dir
        self.max_steps = max_steps
        
        # 动作空间：对应 Actions 中的所有 Pass
        self.action_list = [a.value for a in Actions]
        self.action_space = spaces.Discrete(len(self.action_list))
        
        # 【关键修改】状态空间维度：自动跟随 pass_stats_keys 的长度
        self.obs_dim = len(pass_stats_keys)
        # print(f"DEBUG: Observation Space Dimension = {self.obs_dim}")
        
        # 定义状态空间 (0 到 无穷大)
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(self.obs_dim,), dtype=np.float32)
        
        # 预计算基准 (Baseline) -Oz
        # 注意：这里我们只计算一次作为参考，PPO 训练中的 Reward 计算依赖 step 中的动态变化
        _, self.baseline_size = compile_extract_and_measure(self.bench, self.work_dir, "default<Oz>", link_opts=["-Oz"])
        if self.baseline_size <= 0: self.baseline_size = 1 

    def reset(self, seed=None, options=None):
        # 处理随机种子
        super().reset(seed=seed)
        
        self.current_pipeline = []
        self.steps = 0
        self.last_size = self.baseline_size # 或者使用 O0 大小作为初始 last_size
        
        # 【关键修改】初始状态
        # 因为我们用的是“优化Pass的统计数据”(如 NumInlined)，
        # 在初始时刻(没有任何Pass)时，这些统计量理应全是 0。
        obs = np.zeros(self.obs_dim, dtype=np.float32)
        
        return obs, {}

    def _process_obs(self, feat_dict):
        # 将字典转为固定顺序的向量
        # 如果某个 key 在本次测量中没有出现(比如没有触发内联)，get 返回 0
        obs = [float(feat_dict.get(k, 0)) for k in pass_stats_keys]
        return np.array(obs, dtype=np.float32)

    def step(self, action_idx):
        action_name = self.action_list[action_idx]
        self.current_pipeline.append(action_name)
        self.steps += 1
        
        # 应用当前累积的 Pass 序列并测量
        pipeline_str = ",".join(self.current_pipeline)
        
        # 调用 common.py 中的测量函数
        # 注意：opt -stats 输出的是累积的统计信息，这正是我们需要作为 State 的东西
        features, new_size = compile_extract_and_measure(self.bench, self.work_dir, pipeline_str, link_opts=["-Oz"])
        
        # 奖励设计：
        # 1. 编译失败 (new_size = -1) -> 给大负分
        # 2. 编译成功 -> 奖励为 (上次体积 - 当前体积) / 基准体积
        if new_size > 0:
            reward = (self.last_size - new_size) / self.baseline_size
            self.last_size = new_size
        else:
            reward = -1.0 # 编译/链接失败的惩罚
            new_size = self.last_size # 保持上次大小，不更新
            # 如果失败了，其实特征也是空的，这里返回全0或者保持上一步状态
            features = {} 

        # 转换特征为向量
        obs = self._process_obs(features)
        
        # 判断结束条件
        terminated = False
        truncated = self.steps >= self.max_steps
        
        return obs, reward, terminated, truncated, {"size": new_size}