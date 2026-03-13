# Project Framework and Setup Guide

**Important Note:** Due to the double-blind review process of the paper submission, the source code for the causal inference configuration (`causal_config.py`) is **NOT** provided in this repository. Algorithms relying on this file (e.g., `causalga`) may not function as intended without it.

This project integrates multiple benchmark suites for compiler optimization tuning. The origins and setup procedures for each component are detailed below.

## Execution Logic

This framework provides two main entry points for running experiments:

### 1. Llama-Bench Experiment (`run_llama_experiment.py`)

This script is designed to tune compiler flags for `llama.cpp` performance.

*   **Usage**: `python run_llama_experiment.py <algo> [pop] [gen]`
*   **Supported Algorithms**: `causalga`.
*   **Workflow**:
    1.  Initializes `LlamaEnv` with the specified bitcode and model.
    2.  Measures the **O3 baseline throughput** (tokens/second).
    3.  Runs the optimization loop:
        *   The optimizer generates a binary vector representing compiler flags.
        *   `LlamaEnv` compiles the bitcode with these flags.
        *   Runs `llama-bench` to measure throughput.
    4.  Outputs the best found configuration and speedup.

### 2. SPEC CPU Experiment (`run_experiment_spec.py`)

This script is designed to tune compiler flags for SPEC CPU benchmarks.

*   **Usage**: `python run_experiment_spec.py <benchmark> <algo> [pop] [gen]`
*   **Supported Algorithms**: `causal_ga`.
*   **Workflow**:
    1.  Initializes `SpecEnv` for the specific benchmark.
    2.  Sets up the optimization budget (default 500 evaluations).
    3.  Instantiates the selected optimizer.
    4.  Runs the optimization loop:
        *   Similar to Llama, it compiles and runs the SPEC benchmark.
        *   Fitness is typically execution time or speedup relative to baseline.
    5.  Saves a JSON report (`report_{benchmark}_{algo}.json`) containing:
        *   Baseline performance.
        *   Best speedup found.
        *   Best compiler flags.
        *   Optimization curve and total cost time.

## Framework Origins

*   **cbench & PolyBench**: The running framework is derived from **EATuner**.
*   **SPEC CPU**: The running framework references **LLVMTuner**.
*   **llama.cpp**: Custom environment setup and integration.

---

## llama.cpp Environment Setup

The `llama.cpp` environment is prepared manually. Follow the steps below to replicate the setup.

### 1. Prerequisites & Source Code

```bash
# Clone the repository
git clone https://github.com/ggml-org/llama.cpp /data/llama.cpp-master

# Install dependencies
pip install wllvm
sudo apt-get install libomp-dev
```

### 2. Build Configuration

We use `wllvm` to extract bitcode and disable shared libraries for easier analysis.

```bash
# Create build directory
mkdir -p /data/llama.cpp-master/build_bc
cd /data/llama.cpp-master/build_bc
rm -rf *

# Set LLVM compiler environment variable
export LLVM_COMPILER=clang

# Configure CMake with specific flags
# Key flags:
# - DCMAKE_C_COMPILER=wllvm / DCMAKE_CXX_COMPILER=wllvm++: For bitcode extraction
# - DBUILD_SHARED_LIBS=OFF: Critical for static linking analysis
# - DLLAMA_SERVER=OFF / DLLAMA_CURL=OFF: Minimal build
cmake .. -DCMAKE_C_COMPILER=wllvm \
         -DCMAKE_CXX_COMPILER=wllvm++ \
         -DCMAKE_C_FLAGS="-O0" \
         -DCMAKE_CXX_FLAGS="-O0" \
         -DBUILD_SHARED_LIBS=OFF \
         -DLLAMA_SERVER=OFF \
         -DLLAMA_CURL=OFF
```

### 3. Compilation

Compile only the necessary targets. **Note:** `llama-bench` is used for performance testing, not `llama-cli`.

```bash
# Compile llama-cli (optional, for basic verification)
make llama-cli -j$(nproc)

# Compile llama-bench (REQUIRED for testing)
make llama-bench -j$(nproc)
```

### 4. Verification & Bitcode Extraction

After compilation, you can attempt to compile the extracted bitcode into a standalone binary to verify integrity.

```bash
cd /data/llama.cpp-master/build_bc/bin/


# Compile the extracted .bc file to a standalone executable
extract-bc bin/llama-bench
# We add -O0 and necessary linking libraries (pthread, dl, m, rt)
clang++  llama-bench.bc -o llama_bc_runner -lpthread -ldl -lm -lrt

# If no "undefined reference" errors occur, the .bc file is complete.
# Run a test inference:
./llama_bc_runner  -m ./tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -p 128 -n 128 -t 8
```



---

## Known Issues & Notes

We observed that `opt` and `clang` processes take a significant amount of time. Attempts to extract and compile components separately resulted in degraded performance, likely due to suboptimal function inlining when separating translation units.

### Recommended Testing Command
For consistent benchmarking, use the following command structure:

```bash
# Compile the O3 baseline or tuned bitcode
clang++ -march=native llama-bench-O3.bc -o bench_O3_front -lpthread -ldl -lm -lrt

# Run the benchmark 
./bench_O3_front -m /data/compiler_demo/work/llama_bench/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -p 128 -n 128 -t 8
```
