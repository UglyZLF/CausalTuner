import numpy as np
import random
import json
import os
import itertools
import sys
from tqdm import tqdm

# Assume causal_config.py is located in the sibling directory algorithm/
# If an ImportError occurs, ensure the directory structure is correct or adjust the path
try:
    from algorithm import causal_config
except ImportError:
    import causal_config

class CausalGuidedGAOptimizer:
    def __init__(self, env_flags, n_pop=10, n_gen=30, bench_name="llama-bench"):
        """
        :param env_flags: self.llvm_flags in LlamaEnv (100+ dimensional list)
        """
        self.env_flags = env_flags
        self.n_pop = n_pop
        self.n_gen = n_gen
        self.bench_name = bench_name
        self.early_stop_rounds = 500
        
        # === 1. Feature Reading and Grouping ===
        # Llama is generally considered a complex application, classified as Group 2 (Global)
        self.group_id = 2 
        self.total_dims = 22 # Dimensions for Group 2
        
        # Read features
        self.features = self._get_llama_features()
        
        # === 2. Get Causal Tier Indices (Tier 1/2/3) ===
        # Utilize logic from causal_config
        self.t1_idx, self.t2_idx, self.res_idx = causal_config.get_search_tier_indices(
            self.group_id, self.features
        )
        # Active Set = Tier 1 + Tier 2
        self.active_set = list(set(self.t1_idx + self.t2_idx))
        # print(f"[CausalGA] Tier1: {self.t1_idx}, Tier2: {self.t2_idx}")
        # print(f"[CausalGA] Residual: {self.res_idx}")
        # print(f"[CausalGA] Active Set: {self.active_set}")
        
        print(f"[CausalGA] Group: {self.group_id}, Active Dims: {len(self.active_set)}/{self.total_dims}")
        print(f"[CausalGA] Tier1: {self.t1_idx}, Tier2: {self.t2_idx}")

    def _get_llama_features(self):
        """Read feature file from the specified path"""
        feature_path = "/data/compiler_lctes26/features_o0/llama-bench_features.json"
        
        if not os.path.exists(feature_path):
            print(f"[Warning] Feature file not found at {feature_path}. Using empty features.")
            return {}
            
        try:
            with open(feature_path, 'r') as f:
                data = json.load(f)
            # Assume JSON structure is { "instcount.NumAddInst": 123, ... } 
            # If it is a nested structure { "llama-bench": { ... } }, adjustments are needed
            if self.bench_name in data:
                return data[self.bench_name]
            return data
        except Exception as e:
            print(f"[Error] Failed to load features: {e}")
            return {}

    def _map_causal_to_env_vector(self, causal_bits):
        """
        Core Adapter Function:
        Map CausalGA's short vector (14/22 bits) -> Parse pass name list -> Map back to LlamaEnv's long vector (100+ bits)
        """
        # 1. Decode specific Pass name list (e.g. ['-sroa', '-mem2reg'])
        pass_names = causal_config.decode_to_passes(self.group_id, causal_bits)
        
        # 2. Construct the 0/1 vector required by LlamaEnv
        env_vec = np.zeros(len(self.env_flags), dtype=int)
        
        for name in pass_names:
            # Remove potential '--' prefix differences (some in causal_config are --mem2reg)
            clean_name = name.replace('--', '-')
            if not clean_name.startswith('-'):
                clean_name = '-' + clean_name
                
            # Find index in env_flags
            if clean_name in self.env_flags:
                idx = self.env_flags.index(clean_name)
                env_vec[idx] = 1
            else:
                # This situation may occur if a pass in causal_config is not in llama_env's supported list
                # Choose to ignore here, or you can print a warning
                pass
                
        return env_vec

    def find_causal_seed(self, fitness_func):
        """Phase 1: Subspace search based on causal features"""
        best_bits = np.zeros(self.total_dims, dtype=int)
        best_fit = float('inf')
        
      
        search_limit = 32
        use_full_search = len(self.active_set) <= 5
        
        if use_full_search and len(self.active_set) > 0:
            iterator = itertools.product([0, 1], repeat=len(self.active_set))
            total_steps = 2**len(self.active_set)
        else:
            iterator = ([random.randint(0, 1) for _ in range(len(self.active_set))] for _ in range(search_limit))
            total_steps = search_limit

        print(f"[CausalGA] Phase 1: Seeding (Steps: {total_steps})...")
        
        for combination in iterator:
            # Construct current short vector
            current_bits = np.zeros(self.total_dims, dtype=int)
            for i, val in enumerate(combination):
                current_bits[self.active_set[i]] = val
            
            # Map and evaluate
            env_vec = self._map_causal_to_env_vector(current_bits)
            fit = fitness_func(env_vec)
            
            if fit < best_fit:
                best_fit = fit
                best_bits = current_bits.copy()
                
        return best_bits, best_fit

    def tiered_mutation(self, individual):
        """Tiered Mutation: Tier1/2 have very low mutation rates, Residual has high mutation rate"""
        new_ind = individual.copy()
        for i in range(self.total_dims):
            if i in self.t1_idx: 
                prob = 0.01
            elif i in self.t2_idx: 
                prob = 0.05
            else: 
                prob = 0.15 # Free exploration in non-causal regions
                
            if random.random() < prob:
                new_ind[i] = 1 - new_ind[i]
        return new_ind

    def run(self, fitness_func):
        """
        Main execution flow
        :param fitness_func: Receives env_vector (100+ dims), returns -speedup
        """
        curve = []
        
        # 1. Seed Search
        causal_seed, seed_fit = self.find_causal_seed(fitness_func)
        print(f"[CausalGA] Seed Found. Fit: {seed_fit:.4f}")
        
        # 2. Initialize Population
        # Strategy: Half of the population inherits the seed completely, the other half is randomly perturbed in non-critical regions (Residual)
        X = []
        for i in range(self.n_pop):
            ind = causal_seed.copy()
            if i >= self.n_pop // 2:
                for r_idx in self.res_idx:
                    ind[r_idx] = random.randint(0, 1)
            X.append(ind)
        
        print(f"[CausalGA] Initial Population: {X}")
        # Initial Evaluation
        fits = np.zeros(self.n_pop)
        for i in range(self.n_pop):
            env_vec = self._map_causal_to_env_vector(X[i])
            fits[i] = fitness_func(env_vec)

        # Record Global Best (Short Vector and Fitness)
        best_idx = np.argmin(fits)
        global_best_bits = X[best_idx].copy()
        global_best_fit = fits[best_idx]
        curve.append(global_best_fit)

        # 3. GA Iteration
        pbar = tqdm(range(self.n_gen), desc="CausalGA")
        no_improve_rounds = 0
        
        for g in pbar:
            # --- Elite Preservation ---
            new_pop = []
            new_pop.append(global_best_bits.copy()) # Always preserve the best
            
            # --- Generate Next Generation ---
            while len(new_pop) < self.n_pop:
                # Tournament Selection
                a, b = random.sample(range(self.n_pop), 2)
                parent = X[a] if fits[a] < fits[b] else X[b]
                
                # Mutation
                child = self.tiered_mutation(parent)
                new_pop.append(child)
            
            X = np.array(new_pop)
            
            # --- Evaluation ---
            # This step can be parallelized, but to adapt to the evaluate_batch interface, we collect all vectors first
            env_vectors = [self._map_causal_to_env_vector(ind) for ind in X]
            
            # If calling batch interface is inconvenient, loop call fitness_func
            # Assume fitness_func is a single call (get_fitness defined in run_llama_experiment is single)
            # If you want to use LlamaEnv's evaluate_batch parallel capability, adjustments are needed in run_llama_experiment
            # For simplicity, keep single loop call here (LlamaEnv.evaluate_batch is parallel internally, but we pass single here)
            # **Optimization**: We should design fitness_func externally, or manually loop here
            
            current_gen_best_fit = float('inf')
            
            for i in range(self.n_pop):
                # Elites do not need to be rerun, but run for simple logic (or cache)
                if i == 0 and g > 0: 
                    fits[i] = global_best_fit
                else:
                    fits[i] = fitness_func(env_vectors[i])
                
                if fits[i] < current_gen_best_fit:
                    current_gen_best_fit = fits[i]
            
            # --- Update Global Best ---
            if current_gen_best_fit < global_best_fit:
                global_best_fit = current_gen_best_fit
                idx = np.argmin(fits)
                global_best_bits = X[idx].copy()
                no_improve_rounds = 0
            else:
                no_improve_rounds += 1
            
            curve.append(global_best_fit)
            pbar.set_postfix({"Best Speedup": f"{-global_best_fit:.4f}x"})
            
            if no_improve_rounds >= self.early_stop_rounds:
                print(f"\n[CausalGA] Early stopping at gen {g}")
                break
                
        # Return result: Need to convert best short bits back to env vector
        final_best_vec = self._map_causal_to_env_vector(global_best_bits)
        return final_best_vec, global_best_fit, curve
