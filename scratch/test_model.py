import os
import sys
sys.path.append(os.getcwd())
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from registry.services import ModelServices
from registry.models import ImportedModel
import torch
import torch.nn as nn
class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)
    def forward(self, x):
        return self.fc(x)

model = SimpleNet()
torch.save(model, "scratch/dummy.pt")
print("Saved dummy model")

res = ModelServices.register_model(
    file_path="scratch/dummy.pt",
    original_filename="dummy.pt",
    model_name="test_model_123",
    model_type="Classification",
    accuracy=95.5,
    file_size=os.path.getsize("scratch/dummy.pt")
)
print("Registered:", res)
models = ModelServices.list_models()
print("Models listed:", [m['name'] for m in models])
ModelServices.delete_model_version(mlflow_name="test_model_123", version=res["version"], db_id=res["db_record_id"])
print("Deleted model version")
