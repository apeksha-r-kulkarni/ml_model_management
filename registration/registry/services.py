import os
import torch
import onnx
import mlflow
from typing import Dict, Any, List
from .models import LogicalModel, ModelVersion

def format_size(size_bytes: int) -> str:
    if not size_bytes:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_model_size_from_mlflow(client, model_version) -> int:
    try:
        run_id = model_version.run_id
        artifacts = client.list_artifacts(run_id, path="model")
        total_size = 0
        for item in artifacts:
            if item.file_size:
                total_size += item.file_size
        return total_size
    except:
        return None

class ModelServices:

    @staticmethod
    def register_model(
        file_path: str,
        original_filename: str,
        model_name: str,
        model_type: str,
        accuracy: float,
        file_size: int,
        architecture: str = "",
        priority: int = None,
        is_deployable: bool = False,
        versioning: str = "Auto-increment",
        deployment_points: list = [],
        remarks: str = ""
    ):
        file_format = original_filename.split(".")[-1].lower() if "." in original_filename else "unknown"
        
        if file_format not in ["pt", "onnx"]:
            raise ValueError(f"Unsupported model format: {file_format}. Only .pt and .onnx are supported.")
        
        # 1. Validate/Load Model
        try:
            if file_format == "pt":
                model_obj = torch.load(file_path, weights_only=False)
            elif file_format == "onnx":
                model_obj = onnx.load(file_path)
        except Exception as e:
            raise Exception(f"Model validation failed: {str(e)}")

        # 2. Get or Create LogicalModel, check Model Type consistency
        logical_model = LogicalModel.objects.filter(name=model_name).first()
        if logical_model:
            if logical_model.model_type != model_type:
                raise ValueError(f"Model name '{model_name}' already exists with Model Type '{logical_model.model_type}'. Cannot register new version as '{model_type}'.")
        else:
            logical_model = LogicalModel.objects.create(
                name=model_name,
                model_type=model_type,
                mlflow_name=model_name
            )

        # 3. Log to MLflow
        try:
            tags = {"model_type": model_type, "framework": file_format}
            if architecture:
                tags["architecture"] = architecture
            tags["is_deployable"] = str(is_deployable)
            tags["versioning"] = versioning
            
            metrics = {"accuracy": accuracy}
            if priority is not None:
                metrics["priority"] = float(priority)
            
            with mlflow.start_run() as run:
                mlflow.set_tags(tags)
                mlflow.log_metrics(metrics)
                
                if file_format == "pt":
                    mlflow.pytorch.log_model(model_obj, artifact_path="model", serialization_format="pickle")
                elif file_format == "onnx":
                    mlflow.onnx.log_model(model_obj, artifact_path="model")
                    
                run_id = run.info.run_id
                
            model_uri = f"runs:/{run_id}/model"
            result = mlflow.register_model(model_uri=model_uri, name=model_name)
            
        except Exception as e:
            raise Exception(f"MLflow registration failed: {str(e)}")

        # 4. Create ModelVersion DB Record
        db_version = ModelVersion.objects.create(
            logical_model=logical_model,
            version_number=result.version,
            architecture=architecture,
            accuracy=accuracy,
            priority=priority,
            is_deployable=is_deployable,
            remarks=remarks,
            deployment_points=deployment_points,
            original_filename=original_filename,
            file_format=file_format,
            file_size=file_size,
            run_id=run_id,
            status="REGISTERED"
        )
        
        return {
            "model_name": model_name,
            "version": result.version,
            "run_id": run_id,
            "db_record_id": db_version.id,
            "formatted_size": format_size(file_size)
        }

    @staticmethod
    def list_models():
        client = mlflow.MlflowClient()
        try:
            registered_models = client.search_registered_models()
        except Exception as e:
            raise Exception(f"Could not connect to MLflow: {e}")

        # Sync deleted models logic
        active_name_vers = set()
        for model in registered_models:
            versions = client.search_model_versions(f"name='{model.name}'")
            for v in versions:
                active_name_vers.add((model.name, int(v.version)))

        # Update local DB if versions were deleted in MLflow directly
        for mv in ModelVersion.objects.filter(status="REGISTERED"):
            if (mv.logical_model.mlflow_name, int(mv.version_number)) not in active_name_vers:
                mv.delete()
                
        # Clean up logical models that have no versions
        for lm in LogicalModel.objects.all():
            if lm.versions.count() == 0:
                lm.delete()

        # Build list output
        local_dict = {}
        for mv in ModelVersion.objects.all().select_related('logical_model'):
            local_dict[f"{mv.logical_model.mlflow_name}_{mv.version_number}"] = mv

        results = []
        for rm in registered_models:
            versions = client.search_model_versions(f"name='{rm.name}'")
            versions_data = []
            for mv in versions:
                size_bytes = get_model_size_from_mlflow(client, mv)
                db_record = local_dict.get(f"{rm.name}_{int(mv.version)}")
                
                if size_bytes is None and db_record and db_record.file_size:
                    size_bytes = db_record.file_size
                
                versions_data.append({
                    "version": int(mv.version),
                    "status": mv.status,
                    "run_id": mv.run_id,
                    "model_uri": mv.source,
                    "creation_timestamp": mv.creation_timestamp,
                    "size_bytes": size_bytes,
                    "formatted_size": format_size(size_bytes),
                    "original_filename": db_record.original_filename if db_record else None,
                    "framework": db_record.file_format if db_record else "Unknown",
                    "model_type": db_record.logical_model.model_type if db_record else "Unknown",
                    "architecture": db_record.architecture if db_record else "",
                    "priority": db_record.priority if db_record else "",
                    "is_deployable": db_record.is_deployable if db_record else False,
                    "deployment_points": db_record.deployment_points if db_record else [],
                    "remarks": db_record.remarks if db_record else "",
                    "accuracy": db_record.accuracy if db_record else 0.0,
                    "db_id": db_record.id if db_record else None
                })
            
            versions_data.sort(key=lambda x: x["version"], reverse=True)
            if versions_data:
                results.append({
                    "name": rm.name,
                    "creation_timestamp": rm.creation_timestamp,
                    "all_versions": versions_data
                })
        
        return results

    @staticmethod
    def delete_model_version(mlflow_name, version, db_id=None):
        client = mlflow.MlflowClient()
        try:
            # Find the local record first to extract the exact run_id
            if db_id:
                qs = ModelVersion.objects.filter(id=db_id)
            else:
                qs = ModelVersion.objects.filter(logical_model__mlflow_name=mlflow_name, version_number=version)
                
            mv = qs.first()
            if not mv:
                raise Exception(f"ModelVersion not found in local database for {mlflow_name} v{version}")
                
            run_id = mv.run_id

            # 1. Delete from MLflow Registry
            client.delete_model_version(name=mlflow_name, version=version)
            
            versions = client.search_model_versions(f"name='{mlflow_name}'")
            if not versions:
                try:
                    client.delete_registered_model(name=mlflow_name)
                except Exception:
                    pass
            
            # 2. Delete the associated MLflow run
            if run_id:
                try:
                    # In MLflow 2.x, deleted runs are moved to "deleted" lifecycle_stage
                    client.delete_run(run_id)
                except Exception as e:
                    raise Exception(f"Failed to delete underlying MLflow run {run_id}: {str(e)}")
                    
            # 3. Delete local database record
            lm = mv.logical_model
            mv.delete()
            if lm.versions.count() == 0:
                lm.delete()
                
            return True
        except Exception as e:
            raise Exception(f"Failed to delete model version {mlflow_name} v{version}: {e}")
