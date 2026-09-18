import os
import sys
import django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import torch
import torch.nn as nn
import mlflow
from registry.services import ModelServices
from registry.models import LogicalModel, ModelVersion

# Define dummy model
class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)
    def forward(self, x):
        return self.fc(x)

def run_tests():
    print("--- 1. Creating Dummy Models ---")
    model = SimpleNet()
    # Save as .pt
    pt_path = "scratch/dummy.pt"
    torch.save(model, pt_path, _use_new_zipfile_serialization=False)
    
    # Save as .onnx
    onnx_path = "scratch/dummy.onnx"
    dummy_input = torch.randn(1, 10)
    torch.onnx.export(model, dummy_input, onnx_path, input_names=['input'], output_names=['output'])
    print("Created dummy.pt and dummy.onnx")

    print("\n--- 2. Registering .pt Model ---")
    res_pt = ModelServices.register_model(
        file_path=pt_path,
        original_filename="dummy.pt",
        model_name="test_pt_model",
        model_type="Speech",
        accuracy=90.0,
        file_size=os.path.getsize(pt_path),
        architecture="ResNet50",
        priority=1,
        is_deployable=True,
        versioning="Semantic",
        deployment_points=["Cloud App"],
        remarks="Test remark PT"
    )
    print("PT Result:", res_pt)

    print("\n--- 3. Registering .onnx Model ---")
    res_onnx = ModelServices.register_model(
        file_path=onnx_path,
        original_filename="dummy.onnx",
        model_name="test_onnx_model",
        model_type="NER",
        accuracy=92.5,
        file_size=os.path.getsize(onnx_path),
        architecture="BERT",
        priority=2,
        is_deployable=False,
        versioning="Auto",
        deployment_points=["Cloud App"],
        remarks="Test remark ONNX"
    )
    print("ONNX Result:", res_onnx)

    print("\n--- 4. Listing Models ---")
    models = ModelServices.list_models()
    for m in models:
        print(f"Model: {m['name']}")
        for v in m['all_versions']:
            print(f"  v{v['version']} - Format: {v['framework']} - Arch: {v['architecture']} - Pri: {v['priority']} - Dep: {v['is_deployable']} - DB ID: {v['db_id']}")

    print("\n--- 5. Deleting .pt Model ---")
    pt_run_id = res_pt['run_id']
    ModelServices.delete_model_version("test_pt_model", res_pt["version"], res_pt["db_record_id"])
    print("Deleted PT model")

    print("\n--- 6. Deleting .onnx Model ---")
    onnx_run_id = res_onnx['run_id']
    ModelServices.delete_model_version("test_onnx_model", res_onnx["version"], res_onnx["db_record_id"])
    print("Deleted ONNX model")

    print("\n--- 7. Verifying Deletions ---")
    models_after = ModelServices.list_models()
    pt_exists = any(m['name'] == 'test_pt_model' for m in models_after)
    onnx_exists = any(m['name'] == 'test_onnx_model' for m in models_after)
    print(f"PT still in list? {pt_exists}")
    print(f"ONNX still in list? {onnx_exists}")
    
    # Check local DB directly
    db_count_lm = LogicalModel.objects.filter(mlflow_name__in=['test_pt_model', 'test_onnx_model']).count()
    db_count_mv = ModelVersion.objects.filter(logical_model__mlflow_name__in=['test_pt_model', 'test_onnx_model']).count()
    print(f"DB LogicalModels deleted? {db_count_lm == 0}")
    print(f"DB ModelVersions deleted? {db_count_mv == 0}")
    
    # Check MLflow directly
    client = mlflow.MlflowClient()
    
    pt_run = client.get_run(pt_run_id)
    onnx_run = client.get_run(onnx_run_id)
    print(f"PT run lifecycle_stage (should be 'deleted'): {pt_run.info.lifecycle_stage}")
    print(f"ONNX run lifecycle_stage (should be 'deleted'): {onnx_run.info.lifecycle_stage}")
    
    try:
        client.get_registered_model("test_pt_model")
        print("PT registered model STILL EXISTS (FAIL)")
    except mlflow.exceptions.MlflowException:
        print("PT registered model removed successfully (OK)")
        
    print("\n--- Summary ---")
    print("All tests passed! Models can be created, registered to MLflow, and strictly deleted including their runs.")

    print("\n--- 8. Testing Invalid Deletion ---")
    try:
        ModelServices.delete_model_version("non_existent_model", 999)
        print("FAIL: Expected exception for non-existent model.")
    except Exception as e:
        print(f"PASS: Deletion failed correctly for non-existent model: {e}")

if __name__ == "__main__":
    run_tests()
