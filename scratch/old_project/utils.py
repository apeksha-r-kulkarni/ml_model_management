import os
import tempfile
import hashlib
from contextlib import contextmanager
from typing import Generator

@contextmanager
def save_upload_to_temp(uploaded_file) -> Generator[str, None, None]:
    """
    Saves an uploaded Django file to a temporary file on disk,
    yielding the path. Automatically deletes the file when exiting the context.
    """
    ext = ".pt" if uploaded_file.name.lower().endswith(".pt") else ".onnx"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        yield tmp_path
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def compute_file_hash(file_path: str) -> str:
    """Computes the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def format_size(size_bytes: int | None) -> str:
    """Format byte count into a clean, human-readable string (e.g. 182.4 KB, 1.8 MB)."""
    if size_bytes is None or size_bytes < 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
