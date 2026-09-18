def load_pytorch(file_path: str):
    """Loads a PyTorch model from disk and returns the model object."""
    import torch
    return torch.load(file_path, map_location='cpu')

def load_onnx(file_path: str):
    """Loads an ONNX model from disk, checks its validity, and returns the model object."""
    import onnx
    model = onnx.load(file_path)
    onnx.checker.check_model(model)
    return model

# Registry of supported loaders by extension
LOADERS = {
    "pt": load_pytorch,
    "onnx": load_onnx
}

def load_and_validate_model(file_path: str, extension: str):
    """
    Looks up the appropriate loader for the given extension,
    loads the model, and returns it. Raises ValueError if unsupported.
    """
    loader = LOADERS.get(extension.lower())
    if not loader:
        raise ValueError(f"Unsupported file extension: {extension}")
    return loader(file_path)
