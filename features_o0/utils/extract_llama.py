import sys
import os

# Ensure we can import fix_features from the same directory
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

try:
    import fix_features
except ImportError:
    # If fix_features is not found in path, try adding it explicitly
    sys.path.append("/data/compiler_lctes26/features_o0/utils")
    import fix_features

def main():
    bc_path = "/data/compiler_lctes26/llama-bench.bc"
    if not os.path.exists(bc_path):
        print(f"Error: {bc_path} not found.")
        sys.exit(1)

    print(f"Processing {bc_path}...")
    
    # fix_and_extract handles disassembly, stripping attributes, reassembly, 
    # feature extraction, and saving the JSON to FEATURES_DIR
    success = fix_features.fix_and_extract(bc_path)
    
    if success:
        print("Feature extraction completed successfully.")
        # Print the location of the output file
        base_name = os.path.basename(bc_path).replace(".bc", "")
        json_name = f"{base_name}_features.json"
        json_path = os.path.join(fix_features.FEATURES_DIR, json_name)
        print(f"Features saved to: {json_path}")
    else:
        print("Feature extraction failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
