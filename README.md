# Project Framework and Setup Guide

**Note on Artifact Scope:** The preliminary causal inference steps require large-scale profiling and take significant time. To facilitate the evaluation, we omit the precursor scripts but provide the generated inference rules directly in `causal_config.py`. Reviewers can directly execute the core search algorithm (`causalga`) which relies on these rules.

This project integrates multiple benchmark suites for compiler optimization tuning. The origins and setup procedures for each component are detailed below.

## Quick Start (Artifact Evaluation)

To quickly verify that the core search algorithm functions correctly, you can run a fast functional test:

```bash
# Install dependencies
pip install -r requirements.txt

# Run a quick functional test (population: 10, generations: 10)
python run_llama_experiment.py causalga 10 10
```

*Note: The `10 10` parameters are for a quick functional test. To fully reproduce the results in the paper, you may need to increase the population size and generations (e.g., `50 100`), which will take significantly longer to complete.*

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
pip install -r requirements.txt
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


cmake -S /home/lenovo/llama.cpp-master -B /home/lenovo/llama.cpp-master/build_O0 -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_FLAGS='-O0' -DCMAKE_CXX_FLAGS='-O0' -DLLAMA_CURL=OFF -DBUILD_SHARED_LIBS=OFF && cmake --build /home/lenovo/llama.cpp-master/build_O0 --target llama-bench -j$(nproc)
```
```

### 3. Verification & Bitcode Extraction

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

## RL Environment Configuration: Understanding `llama.cpp` Parameters

When running commands (e.g., via `llama-bench`), parameters like `-n` and `-t` are core control switches. Understanding their impact is crucial for designing the Reinforcement Learning (RL) reward function.

### 1. `-t` or `--threads` (Thread Count)
*   **Meaning**: Number of CPU cores/threads used for inference.
*   **Function**: `llama.cpp` splits large matrix computations across multiple threads.
*   **RL Impact**: More threads generally mean faster computation, but synchronization overhead increases. **Recommendation**: Set to the number of physical cores (e.g., 4 or 8).

### 2. `-n` or `--n-predict` (Prediction Length)
*   **Meaning**: Maximum number of tokens to output after processing the prompt.
*   **Function**: Controls the length of the generated text.
*   **RL Impact**: Directly affects runtime. `-n 32` finishes quickly; `-n 2048` may take minutes. For RL training, use a moderate value (e.g., **128** or **256**) to balance evaluation speed and accuracy.

### 3. `-p` or `--prompt` (Prompt Text)
*   **Meaning**: The input text.
*   **Function**: Context for the model to understand and continue.
*   **RL Impact**: The length of the prompt directly affects the **Prompt t/s** measurement. Longer prompts increase the proportion of pre-computation time.

### 4. `-m` or `--model` (Model Path)
*   **Meaning**: Path to the `.gguf` model file.
*   **Function**: Loads the specific model weights (the "brain").

### 5. `--temp` or `--temperature` (Sampling Temperature)
*   **Meaning**: Controls the randomness of the output.
*   **Function**:
    *   `temp 0`: **Deterministic**. Identical input yields identical output.
    *   `temp 0.8`: **Random**. More creative but less predictable.
*   **RL Impact**: **ALWAYS use `--temp 0` for performance evaluation.** This ensures consistent execution paths across runs, eliminating randomness as a factor in runtime variance.

---

## Known Issues & Notes

### Compilation Time vs. Performance
We observed that `opt` and `clang` processes take a significant amount of time. Attempts to extract and compile components separately resulted in degraded performance, likely due to suboptimal function inlining when separating translation units.

### Recommended Testing Command
For consistent benchmarking, use the following command structure:

```bash
# Compile the O3 baseline or tuned bitcode
clang++ -march=native llama-bench-O3.bc -o bench_O3_front -lpthread -ldl -lm -lrt

# Run the benchmark
./bench_O3_front -m /data/compiler_demo/work/llama_bench/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -p 128 -n 128 -t 8
```
