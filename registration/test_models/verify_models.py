import sys
import os

try:
    import torch
    import onnx
    import onnxruntime as ort
except ImportError:
    print("Please install torch, onnx, and onnxruntime to run this verification script.")
    sys.exit(1)

def verify_pt(filepath):
    try:
        model = torch.load(filepath, weights_only=False)
        # Check if it has a forward pass mechanism
        if hasattr(model, 'forward'):
            return True
        return False
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return False

def verify_onnx(filepath):
    try:
        onnx_model = onnx.load(filepath)
        onnx.checker.check_model(onnx_model)
        
        # Also try to load with onnxruntime
        ort_session = ort.InferenceSession(filepath)
        if len(ort_session.get_inputs()) > 0:
            return True
        return False
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return False

def main():
    files = {
        "dummy_classifier.pt": verify_pt,
        "dummy_regressor.pt": verify_pt,
        "dummy_classifier.onnx": verify_onnx,
        "dummy_regressor.onnx": verify_onnx
    }
    
    all_passed = True
    
    for filename, verifier in files.items():
        if not os.path.exists(filename):
            print(f"FAIL: {filename} does not exist.")
            all_passed = False
            continue
            
        if verifier(filename):
            print(f"PASS: {filename}")
        else:
            print(f"FAIL: {filename}")
            all_passed = False
            
    if not all_passed:
        sys.exit(1)
        
    print("All models passed validation!")

if __name__ == "__main__":
    main()
