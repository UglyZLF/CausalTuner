
import os
import glob
import subprocess
import shutil
import json
import sys
import hashlib
import re

# Add path to import build_only_spec and core.features
sys.path.append("/data/compiler_lctes26")
import build_only_spec
from core.features import extract_ir_features

FEATURES_DIR = "/data/compiler_lctes26/features_o0"
IR_CACHE_DIR = os.path.expanduser("~/.spec_ir_cache")
LLVM_BIN = "/data/llvm14_0_0/bin"

def fix_and_extract(bc_path):
    """
    1. Disassemble bc
    2. Strip optnone/noinline
    3. Assemble back to _fixed.bc
    4. Extract features
    5. Save features to json
    """
    print(f"Processing {bc_path}...")
    base_name = os.path.basename(bc_path).replace(".bc", "")
    ll_path = bc_path.replace(".bc", ".ll")
    fixed_bc_path = bc_path.replace(".bc", "_fixed.bc")
    
    # 1. Disassemble
    cmd_dis = ["llvm-dis", bc_path, "-o", ll_path]
    try:
        subprocess.run(cmd_dis, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Disassembly failed for {bc_path}: {e}")
        return False
    
    # 2. Remove optnone and noinline
    # We use sed for efficiency
    cmd_sed = f"sed -i 's/ optnone//g; s/ noinline//g' {ll_path}"
    subprocess.run(cmd_sed, shell=True, check=True)
    
    # 3. Assemble
    cmd_as = ["llvm-as", ll_path, "-o", fixed_bc_path]
    try:
        subprocess.run(cmd_as, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Assembly failed for {ll_path}: {e}")
        return False
    
    # 4. Extract features
    print(f"Extracting features from {fixed_bc_path}...")
    features = extract_ir_features(fixed_bc_path)
    
    if features:
        # Save to json
        # The filename should be {bench}_features.json
        # The input bc is usually {bench}_o0.bc or similar
        # We want to keep the benchmark name
        if "_o0" in base_name:
            json_name = base_name.replace("_o0", "_features.json")
        else:
            json_name = f"{base_name}_features.json"
            
        json_path = os.path.join(FEATURES_DIR, json_name)
        with open(json_path, 'w') as f:
            json.dump(features, f, indent=4)
        print(f"Saved features to {json_path}")
        # print(json.dumps(features, indent=2))
        return True
    else:
        print(f"Failed to extract features from {fixed_bc_path}")
        return False

def build_and_collect(bench):
    print(f"\nBuilding {bench}...")
    
    # Clear cache
    if os.path.exists(IR_CACHE_DIR):
        shutil.rmtree(IR_CACHE_DIR)
    os.makedirs(IR_CACHE_DIR, exist_ok=True)
    
    # Build
    build_only_spec.run_spec_benchmark(bench, [])
    
    # Collect IRs
    # bc_files = glob.glob(os.path.join(IR_CACHE_DIR, "*_base.bc"))
    
    # Identify build directory
    bench_build_dir = os.path.join("/data/spec2017/benchspec/CPU", bench, "build")
    # Find the latest build_base_none.* directory
    build_subdirs = sorted([d for d in os.listdir(bench_build_dir) if d.startswith("build_base_none")], reverse=True)
    if not build_subdirs:
        print(f"No build directory found for {bench}")
        return False
        
    build_dir = os.path.join(bench_build_dir, build_subdirs[0])
    print(f"Using build directory: {build_dir}")
    
    # Find Makefile.spec
    # The format is Makefile.{bench_name}.spec
    # But bench name might be slightly different from 511.povray_r (e.g. povray_r)
    # Let's search for Makefile.*.spec
    makefile_specs = glob.glob(os.path.join(build_dir, "Makefile.*.spec"))
    
    bc_files = []
    
    if makefile_specs:
        # Use the first one or filter for correct one
        # Usually there's only one relevant one if we ignore deps/utilities
        # For povray, we saw Makefile.povray_r.spec and Makefile.imagevalidate_511.spec
        # We want the one that matches the benchmark name suffix
        bench_short = bench.split('.')[1]
        target_spec = None
        for spec in makefile_specs:
            if f"Makefile.{bench_short}.spec" in spec:
                target_spec = spec
                break
        
        if not target_spec and makefile_specs:
             # Fallback to first one if not found
             target_spec = makefile_specs[0]
             
        if target_spec:
            print(f"Parsing sources from {target_spec}")
            with open(target_spec, 'r') as f:
                lines = f.readlines()
            
            # Simple parsing for SOURCES = ... \ ...
            sources = []
            in_sources = False
            for line in lines:
                line = line.strip()
                if line.startswith("SOURCES"):
                    in_sources = True
                    # Remove SOURCES = or SOURCES=
                    parts = line.split("=", 1)
                    if len(parts) > 1:
                        val = parts[1].strip()
                    else:
                        continue # Should not happen
                    
                    if val.endswith("\\"):
                        val = val[:-1].strip()
                    else:
                        in_sources = False
                    sources.extend(val.split())
                elif in_sources:
                    if line.endswith("\\"):
                        val = line[:-1].strip()
                    else:
                        val = line.strip()
                        in_sources = False
                    sources.extend(val.split())
            
            print(f"Found {len(sources)} sources.")
            
            # Map sources to IR files
            # Note: sources are relative paths in Makefile
            # but they might be just filenames if in same dir, or relative paths like base/foo.cpp
            # The build happens in build_dir.
            # So abs path is os.path.join(build_dir, src)
            
            for src in sources:
                # Resolve absolute path
                # Need to be careful about relative paths
                abs_src = os.path.abspath(os.path.join(build_dir, src))
                # Compute MD5
                md5_hash = hashlib.md5(abs_src.encode('utf-8')).hexdigest()
                ir_file = os.path.join(IR_CACHE_DIR, f"{md5_hash}_base.bc")
                if os.path.exists(ir_file):
                    bc_files.append(ir_file)
                else:
                    # Try simple filename if path fails?
                    # Sometimes clangopt might receive relative path or absolute path differently.
                    # But clangopt wrapper usually does os.path.abspath(src_file)
                    # Let's double check if sources have leading ./ or not
                    # print(f"Warning: IR file for {src} ({abs_src}) not found: {ir_file}")
                    pass
    
    if not bc_files:
        print(f"No IR files found via Makefile parsing for {bench}, falling back to all in cache.")
        bc_files = glob.glob(os.path.join(IR_CACHE_DIR, "*_base.bc"))
    
    if not bc_files:
        print(f"No IR files found for {bench}")
        return False
        
    print(f"Found {len(bc_files)} IR files.")
    
    # Link
    linked_bc = os.path.join(FEATURES_DIR, f"{bench}_o0.bc")
    llvm_link = os.path.join(LLVM_BIN, "llvm-link")
    
    cmd = [llvm_link, "-o", linked_bc] + bc_files
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        print(f"Linked to {linked_bc}")
        return linked_bc
    except subprocess.CalledProcessError as e:
        print(f"Link failed for {bench}: {e.stderr.decode() if e.stderr else str(e)}")
        # Try linking only C/C++ object files, ignoring potential conflicts
        # Or just return False
        return False

def main():
    if not os.path.exists(FEATURES_DIR):
        os.makedirs(FEATURES_DIR)

    benchmarks = ["511.povray_r", "531.deepsjeng_r", "544.nab_r"]
    
    for bench in benchmarks:
        bc_path = os.path.join(FEATURES_DIR, f"{bench}_o0.bc")
        
        # Check if already exists
        if os.path.exists(bc_path):
            print(f"Found existing {bc_path}")
            # Even if exists, we should fix it and extract features
            fix_and_extract(bc_path)
        else:
            print(f"{bc_path} not found, building...")
            # Rebuild logic
            try:
                linked_bc = build_and_collect(bench)
                if linked_bc:
                     fix_and_extract(linked_bc)
            except Exception as e:
                print(f"Build failed for {bench}: {e}")

if __name__ == "__main__":
    main()
