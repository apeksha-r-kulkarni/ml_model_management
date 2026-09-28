import torch
import torch.nn as nn

def generate_models():
    # 1. Generate PyTorch Classifier using built-in nn.Sequential
    clf = nn.Sequential(
        nn.Linear(10, 2)
    )
    torch.save(clf, "dummy_classifier.pt")
    
    # 2. Generate PyTorch Regressor using built-in nn.Sequential
    reg = nn.Sequential(
        nn.Linear(5, 1)
    )
    torch.save(reg, "dummy_regressor.pt")
    
    # 3. Generate ONNX Classifier
    dummy_input_clf = torch.randn(1, 10)
    torch.onnx.export(clf, dummy_input_clf, "dummy_classifier.onnx", 
                      input_names=['input'], output_names=['output'])
                      
    # 4. Generate ONNX Regressor
    dummy_input_reg = torch.randn(1, 5)
    torch.onnx.export(reg, dummy_input_reg, "dummy_regressor.onnx",
                      input_names=['input'], output_names=['output'])

if __name__ == "__main__":
    generate_models()
    print("Successfully generated test models.")
