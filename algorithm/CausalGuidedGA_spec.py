import numpy as np
import random
import math
from tqdm import tqdm

class CausalGuidedGAOptimizer:
    def __init__(self, all_flags, n_pop=10, n_gen=50):
        """
        Causal Guided GA Optimizer adapted for SPEC experimental environment
        :param all_flags: List of strings, e.g. ['-licm', '-gvn', ...]
        """
        self.all_flags = all_flags
        self.n_flags = len(all_flags)
        self.n_pop = n_pop
        self.n_gen = n_gen
        
        # Genetic Algorithm Hyperparameters
        self.CR = 0.9
        self.MR_T1 = 0.01   # Tier 1 Mutation Rate (Very low, maintain stability)
        self.MR_T2 = 0.05   # Tier 2 Mutation Rate
        self.MR_Res = 0.15  # Residual Mutation Rate (High, explore space)

        # 1. Dynamic Subspace Partitioning (Simulate causal mining results)
        self.t1_idx, self.t2_idx, self.res_idx = self._setup_tiers()
        self.active_set = self.t1_idx + self.t2_idx
        
    def _setup_tiers(self):
        """
        Forcibly partition Tier levels based on Pass functionality.
        Tier 1: Core Scalar Optimization and Memory Optimization (Usually have the greatest impact)
        Tier 2: Loop Optimization and Global Optimization
        Residual: Others
        """
        tier1_names = ['-simplifycfg', '-instcombine', '-sroa', '-mem2reg', '-early-cse', '-reassociate']
        tier2_names = ['-licm', '-loop-rotate', '-loop-unroll', '-inline', '-gvn', '-ipsccp', '-jump-threading']
        
        t1 = [i for i, f in enumerate(self.all_flags) if f in tier1_names]
        t2 = [i for i, f in enumerate(self.all_flags) if f in tier2_names]
        
        # Ensure T1 is not empty, if no match, take the first 5
        if not t1: t1 = list(range(min(5, self.n_flags)))
        
        assigned = set(t1 + t2)
        res = [i for i in range(self.n_flags) if i not in assigned]
        
        return t1, t2, res

    def find_causal_seed(self, fitness_func):
        """Phase 1: Heuristic seed search in active subspace (Tier 1 & 2)"""
        best_seed_bits = np.zeros(self.n_flags, dtype=int)
        best_fit = float('inf')
        
        # To control SPEC runtime, limit sampling count
        search_limit = min(20, 2**len(self.active_set)) if len(self.active_set) > 0 else 5
        
        print(f"Searching for causal seed in active subspace (size: {len(self.active_set)})...")
        for _ in range(search_limit):
            current_bits = np.zeros(self.n_flags, dtype=int)
            # Randomly enable optimization in active subspace
            for idx in self.active_set:
                current_bits[idx] = random.randint(0, 1)
            
            fit = fitness_func(current_bits.tolist())
            if fit < best_fit:
                best_fit = fit
                best_seed_bits = current_bits.copy()
        
        return best_seed_bits, best_fit

    def tiered_mutation(self, individual):
        """Tiered Mutation Logic: Use different mutation rates based on the Tier the bit belongs to"""
        new_ind = individual.copy()
        for i in range(self.n_flags):
            if i in self.t1_idx: prob = self.MR_T1
            elif i in self.t2_idx: prob = self.MR_T2
            else: prob = self.MR_Res
                
            if random.random() < prob:
                new_ind[i] = 1 - new_ind[i]
        return new_ind

    def run(self, fitness_func):
        """
        Main execution flow
        """
        curve = []
        
        # 1. Causal Seed Search
        causal_seed, seed_fit = self.find_causal_seed(fitness_func)
        curve.append(seed_fit)
        
        # 2. Population Initialization (Fine-tune based on seed)
        print(f"Initializing population based on causal seed...")
        X = []
        fit = np.full(self.n_pop, float('inf'))
        
        for i in range(self.n_pop):
            ind = causal_seed.copy()
            # 50% population randomizes residual space, 50% fully inherits seed
            if i > self.n_pop // 2:
                for r_idx in self.res_idx: 
                    ind[r_idx] = random.randint(0, 1)
            X.append(ind)
        X = np.array(X)
        
        best_fit = seed_fit
        best_vec = causal_seed.copy()

        # 3. GA Iteration
        pbar = tqdm(total=self.n_gen)
        for g in range(self.n_gen):
            # Evaluate Population
            for i in range(self.n_pop):
                fit[i] = fitness_func(X[i].tolist())
                if fit[i] < best_fit:
                    best_fit = fit[i]
                    best_vec = X[i].copy()
            
            curve.append(best_fit)
            
            # Generate Next Generation
            new_pop = [best_vec.copy()] # Elite Preservation
            
            while len(new_pop) < self.n_pop:
                # Tournament Selection
                idx1, idx2 = random.sample(range(self.n_pop), 2)
                parent = X[idx1] if fit[idx1] < fit[idx2] else X[idx2]
                
                # Mutation (Causal Guided Mutation)
                child = self.tiered_mutation(parent)
                new_pop.append(child)
                
            X = np.array(new_pop)
            pbar.set_description(f"Gen {g} Best: {-best_fit:.4f}x")
            pbar.update(1)
            
        pbar.close()
        return best_vec.tolist(), best_fit, curve
