import os
import random
import copy
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from src.utils.actions import Actions
from src.utils.common import compile_and_measure

# ==============================================================================
# 1. 评估辅助函数 (必须在类外定义，以便多进程序列化)
# ==============================================================================
def fitness_worker(bench_obj, work_dir, pipeline_str, baseline_size):
    """
    子进程执行的任务：编译 -> 测量 -> 返回体积和适应度
    """
    size = compile_and_measure(bench_obj, work_dir, pipeline_str)
    if size > 0 and baseline_size > 0:
        fitness = (baseline_size - size) / baseline_size
    else:
        fitness = -1.0
    return pipeline_str, size, fitness

# ==============================================================================
# 2. 个体类
# ==============================================================================
class Individual:
    def __init__(self, genes=None, max_len=50):
        # 随机初始化
        self.genes = genes if genes else [
            random.choice(list(Actions)).value for _ in range(random.randint(5, max_len))
        ]
        self.fitness = -float('inf')
        self.size = 0  # 存储具体的字节数

    def serialize(self):
        return ",".join(self.genes)
    
    def __str__(self):
        return self.serialize()

# ==============================================================================
# 3. 遗传算法优化器
# ==============================================================================
class SpecGAOptimizer:
    def __init__(self, config, synergy_kb=None, start_pass_weights=None):
        """
        config 需要包含: 
        bench_obj, work_dir, population_size, generations, num_threads 等
        """
        self.config = config
        self.bench = config['bench_obj']
        self.work_dir = config['work_dir']
        
        self.pop_size = config['population_size']
        self.generations = config['generations']
        
        # 初始种群
        self.population = [Individual(max_len=config['max_pipeline_length']) for _ in range(self.pop_size)]
        
        # 计算基准 (-Oz)
        print(f"[{self.bench.name}] Calculating Baseline (-Oz)...")
        self.baseline_size = compile_and_measure(self.bench, self.work_dir, "default<Oz>")
        self.oz_inst_count = self.baseline_size # 兼容 main_run 的调用名
        
        self.best_individual = None
        self.best_fitness = -float('inf')

    def _parallel_evaluate(self):
        """利用 ProcessPoolExecutor 在 10 核上并行评估整个种群"""
        with ProcessPoolExecutor(max_workers=self.config['num_threads']) as executor:
            futures = {
                executor.submit(
                    fitness_worker, 
                    self.bench, 
                    self.work_dir, 
                    ind.serialize(), 
                    self.baseline_size
                ): ind for ind in self.population
            }

            for future in as_completed(futures):
                ind = futures[future]
                try:
                    _, size, fitness = future.result()
                    ind.size = size
                    ind.fitness = fitness
                except Exception as e:
                    print(f"Evaluation Error: {e}")
                    ind.fitness = -1.0

    def _selection(self):
        """锦标赛选择"""
        new_pop = []
        # 精英保留
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        new_pop.append(copy.deepcopy(self.population[0]))
        
        while len(new_pop) < self.pop_size:
            # 随机选 3 个进行比赛
            tournament = random.sample(self.population, min(3, len(self.population)))
            winner = max(tournament, key=lambda x: x.fitness)
            new_pop.append(copy.deepcopy(winner))
        return new_pop

    def _crossover(self, p1, p2):
        """单点交叉"""
        if len(p1.genes) < 2 or len(p2.genes) < 2:
            return copy.deepcopy(p1)
        split = random.randint(1, min(len(p1.genes), len(p2.genes)) - 1)
        child_genes = p1.genes[:split] + p2.genes[split:]
        return Individual(child_genes)

    def _mutation(self, ind):
        """突变逻辑"""
        if not ind.genes: return
        idx = random.randint(0, len(ind.genes)-1)
        prob = random.random()
        if prob < 0.4: # 替换
            ind.genes[idx] = random.choice(list(Actions)).value
        elif prob < 0.7: # 插入
            ind.genes.insert(idx, random.choice(list(Actions)).value)
        else: # 删除
            if len(ind.genes) > 1: ind.genes.pop(idx)

    def run(self):
        """主循环"""
        print(f"Starting GA for {self.bench.name}. Baseline: {self.baseline_size} bytes")
        
        for gen in range(self.generations):
            # 1. 并行评估
            self._parallel_evaluate()
            
            # 2. 排序并记录最佳
            self.population.sort(key=lambda x: x.fitness, reverse=True)
            current_best = self.population[0]
            
            if current_best.fitness > self.best_fitness:
                self.best_fitness = current_best.fitness
                self.best_individual = copy.deepcopy(current_best)
            
            print(f"Gen {gen}: Best Fitness = {current_best.fitness:.4%}, Size = {current_best.size} B")

            # 3. 进化操作
            parents = self._selection()
            next_gen = [parents[0]] # 保留本代最强个体
            
            while len(next_gen) < self.pop_size:
                p1, p2 = random.sample(parents, 2)
                # 交叉
                if random.random() < self.config['crossover_rate']:
                    child = self._crossover(p1, p2)
                else:
                    child = copy.deepcopy(p1)
                
                # 突变
                if random.random() < self.config['mutation_rate']:
                    self._mutation(child)
                    
                next_gen.append(child)
            
            self.population = next_gen

        return self.best_individual, self.oz_inst_count