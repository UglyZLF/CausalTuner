import os

# Project Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# Tools
LLVM_TOOLS_DIR = os.path.join(BIN_DIR, "llvm_tools")
LLVM_BIN_PATH = "/data/llvm14_0_0/bin"

# Work Directory (for compilation artifacts)
DEFAULT_WORK_DIR = os.path.join(PROJECT_ROOT, "work")
if not os.path.exists(DEFAULT_WORK_DIR):
    os.makedirs(DEFAULT_WORK_DIR)

# Spec Root
DEFAULT_SPEC_ROOT = "/data/spec2017/benchspec/CPU"

# RL Parameters
STATE_DIM = 70 # Approximate, adjust based on env
ACTION_DIM = 252 # Based on Actions Enum
