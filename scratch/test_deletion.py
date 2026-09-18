import os
import django
import sys
import mlflow
from mlflow.tracking import MlflowClient

sys.path.append('/home/apeksha-ssi021/Shyena/ml_model_management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from registry.services import ModelServices

client = MlflowClient()

print("--- Registering dummy model ---")
with open("dummy.pt", "w") as f:
    f.write("dummy")

import torch
import torch.nn as nn
class DummyNet(nn.Module):
    def forward(self, x):
        return x
torch.save(DummyNet(), "dummy.pt")

res = ModelServices.register_model(
    file_path="dummy.pt",
    original_filename="dummy.pt",
    model_name="deletion_test",
    model_type="Speech",
    accuracy=90.0,
    file_size=123,
    architecture="Arch",
    priority=1,
    is_deployable=True
)
print("Registered:", res)

print("\n--- Verifying MLflow has it ---")
versions = client.search_model_versions(f"name='deletion_test'")
print(f"Versions in MLflow: {[v.version for v in versions]}")

print("\n--- Deleting using ModelServices ---")
ModelServices.delete_model_version("deletion_test", res["version"], res["db_record_id"])

print("\n--- Verifying MLflow after deletion ---")
try:
    versions = client.search_model_versions(f"name='deletion_test'")
    print(f"Versions in MLflow after delete: {[v.version for v in versions]}")
except Exception as e:
    print(f"Error querying after delete: {e}")

try:
    model = client.get_registered_model("deletion_test")
    print(f"Registered model still exists! {model.name}")
except Exception as e:
    print(f"Registered model error (expected if deleted): {e}")

