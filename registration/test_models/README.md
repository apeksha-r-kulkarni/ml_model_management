# Test Models

This directory contains small, valid dummy ML models for testing the model registration system.

## Included Models

### PyTorch Models
1. **dummy_classifier.pt**
   - **Type:** PyTorch `nn.Module` (Linear layer: 10 -> 2)
   - **Input Shape:** `(BatchSize, 10)`
   - **Output Shape:** `(BatchSize, 2)`
   - **Generation:** Created using a basic subclass of `nn.Module` and saved with `torch.save()`.

2. **dummy_regressor.pt**
   - **Type:** PyTorch `nn.Module` (Linear layer: 5 -> 1)
   - **Input Shape:** `(BatchSize, 5)`
   - **Output Shape:** `(BatchSize, 1)`
   - **Generation:** Created using a basic subclass of `nn.Module` and saved with `torch.save()`.

### ONNX Models
3. **dummy_classifier.onnx**
   - **Type:** ONNX Model (Exported from dummy_classifier.pt)
   - **Input Shape:** `(1, 10)` named 'input'
   - **Output Shape:** `(1, 2)` named 'output'
   - **Generation:** Exported via `torch.onnx.export()`.

4. **dummy_regressor.onnx**
   - **Type:** ONNX Model (Exported from dummy_regressor.pt)
   - **Input Shape:** `(1, 5)` named 'input'
   - **Output Shape:** `(1, 1)` named 'output'
   - **Generation:** Exported via `torch.onnx.export()`.

## Verification

To verify that these artifacts are valid models that can be properly loaded:

```bash
# Requires torch, onnx, onnxruntime
python verify_models.py
```
The verification script loads `.pt` files using `torch.load()` and `.onnx` files using `onnxruntime` to ensure they are valid.
