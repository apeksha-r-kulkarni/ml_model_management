from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Model:
    """Pure Python data object representing an ML model as per UML."""
    id: Optional[int] = None
    name: str = ""
    model_type: str = ""
    version: int = 1
    purpose: str = ""
    architecture: str = ""
    accuracy: float = 0.0
    priority: Optional[int] = None
    is_deployable: bool = False
    status: str = "PENDING"
    modelArtifactPath: str = ""
