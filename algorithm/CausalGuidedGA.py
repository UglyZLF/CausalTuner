import numpy as np
import random
import os
import sys
import itertools
from tqdm import tqdm

# ================= Critical Path Processing =================
# Get absolute path of current file (CausalGuidedGA.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get project root directory (parent of algorithm)
root_path = os.path.dirname(current_dir)

# Add root directory to sys.path to find util, causal_config, and core folders
if root_path not in sys.path:
    sys.path.append(root_path)

# Now imports can work correctly
import util
import causal_config
from core.features import get_bench_raw_features # Explicitly import from core directory
from core.prog_classifier import get_prog_group
# ===============================================

# Group definitions here must match causal mining
GROUP1_PROGS = ["bzip2d", "telecom_gsm", "office_rsynth", "bzip2e", "automotive_susan_e", 
                "automotive_susan_s", "network_dijkstra", "automotive_bitcount", "security_blowfish_d"]

class CausalGuidedGA(util.Util):
    def __init__(self, bench_name, n_pop=10, n_gen=30):
        """
        Adapt to main.py parameter interface
        """
        super().__init__()
        self.compile_files = bench_name
        self.n_pop = n_pop
        self.n_gen = n_gen
        self.CR = 0.9
        self.MR = 0.05
        self.early_stop_rounds = 500
        self.times = 0 # main.py records call counts
        
        # 1. Automatically determine Group ID
        # self.group_id = 1 if bench_name in GROUP1_PROGS else 2
        self.group_id = get_prog_group(bench_name) 
        self.total_dims = 14 if self.group_id == 1 else 22
        
        # 2. Extract features and get causal indices
        self.features = get_bench_raw_features(bench_name)
        if self.features is None: self.features = {}
        
        self.t1_idx, self.t2_idx, self.res_idx = causal_config.get_search_tier_indices(
            self.group_id, self.features
        )
        self.active_set = list(set(self.t1_idx + self.t2_idx))
        
        # 3. Initialize convergence curve (for main.py plotting)
        self.curve = np.zeros(self.n_gen)

    def find_causal_seed(self):
        """Phase 1 & 2: Subspace Heuristic Search"""
        best_seed_bits = np.zeros(self.total_dims, dtype=int)
        best_fit = float('inf')
        
        # Subspace scale control
        search_limit = 12 if len(self.active_set) > 6 else (2**len(self.active_set))
        
        # If subspace is very small, use traversal; otherwise use random sampling
        if len(self.active_set) <= 6 and len(self.active_set) > 0:
            iterator = itertools.product([0, 1], repeat=len(self.active_set))
        else:
            iterator = ([random.randint(0, 1) for _ in range(len(self.active_set))] for _ in range(search_limit))

        for combination in iterator:
            current_bits = np.zeros(self.total_dims, dtype=int)
            for i, val in enumerate(combination):
                current_bits[self.active_set[i]] = val
            
            passes = causal_config.decode_to_passes(self.group_id, current_bits)
            fit = self.run_procedure2(self.compile_files, passes)
            self.times += 1
            
            if fit < best_fit:
                best_fit = fit
                best_seed_bits = current_bits.copy()
        
        return best_seed_bits, best_fit

    def tiered_mutation(self, individual):
        """Tiered Mutation Logic"""
        new_ind = individual.copy()
        for i in range(self.total_dims):
            if i in self.t1_idx: prob = 0.01
            elif i in self.t2_idx: prob = 0.05
            else: prob = 0.15
                
            if random.random() < prob:
                new_ind[i] = 1 - new_ind[i]
        return new_ind

    def start(self):
        """
        Adapt to model.start() interface in main.py
        Return format: [best_flags, min_time], total_times
        """
        # 1. Causal Seed Search
        causal_seed, seed_fit = self.find_causal_seed()
        
        # 2. Population Initialization
        X = []
        for i in range(self.n_pop):
            ind = causal_seed.copy()
            # Half of the population randomizes in residual space, half fully inherits seed
            if i > self.n_pop // 2:
                for r_idx in self.res_idx: ind[r_idx] = random.randint(0, 1)
            X.append(ind)
        X = np.array(X)
        
        fit = np.full(self.n_pop, float('inf'))
        X_best = causal_seed.copy()
        fit_best = seed_fit
        
        # 3. GA Iteration
        no_improve = 0
        for g in range(self.n_gen):
            # Evaluate
            for i in range(self.n_pop):
                passes = causal_config.decode_to_passes(self.group_id, X[i])
                fit[i] = self.run_procedure2(self.compile_files, passes)
                self.times += 1
                if fit[i] < fit_best:
                    fit_best = fit[i]
                    X_best = X[i].copy()
                    no_improve = 0
            
            self.curve[g] = fit_best
            if no_improve >= self.early_stop_rounds: break
            no_improve += 1
            
            # Generate Next Generation
            new_pop = []
            # Elite Preservation
            new_pop.append(X_best.copy())
            while len(new_pop) < self.n_pop:
                # Tournament Selection
                a, b = random.sample(range(self.n_pop), 2)
                parent = X[a] if fit[a] < fit[b] else X[b]
                # Mutation
                child = self.tiered_mutation(parent)
                new_pop.append(child)
            X = np.array(new_pop)

        return [X_best, fit_best], self.times
