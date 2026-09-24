import os
import torch
import onnx
import mlflow
from pathlib import Path
from typing import Dict, Any, List
from typing import Dict, Any, List
from dotenv import load_dotenv

# Absolute path to the project-level .env file
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


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

class MLflowService:
    """Object-oriented service for interacting with MLflow."""

    def __init__(self):
        """Initialize the MLflow client and configure connection from environment."""
        load_dotenv(_ENV_FILE, override=True)
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.tracking_uri)
        from mlflow.tracking import MlflowClient
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def register_model(
        self,
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
        deployment_points: list = None,
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

        # 2. Log to MLflow
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
                run_id = run.info.run_id

            try:
                self.client.create_registered_model(model_name)
            except Exception:
                pass  # already exists

            mv = self.client.create_model_version(
                name=model_name,
                source=f"runs:/{run_id}",
                run_id=run_id,
                tags=tags,
                description=remarks,
            )
            result_version = mv.version

        except Exception as e:
            raise Exception(f"MLflow registration failed: {str(e)}")

        return {
            "model_name": model_name,
            "version": result_version,
            "run_id": run_id,
            "formatted_size": format_size(file_size)
        }

    def list_architectures(self):
        archs = set()
        try:
            registered_models = self.client.search_registered_models()
            for rm in registered_models:
                versions = self.client.search_model_versions(f"name='{rm.name}'")
                for mv in versions:
                    if mv.tags and "architecture" in mv.tags:
                        arch_name = mv.tags["architecture"].strip()
                        if arch_name:
                            archs.add(arch_name)
        except Exception:
            pass
        return sorted(list(archs))

    def list_models(self):
        try:
            registered_models = self.client.search_registered_models()
        except Exception as e:
            raise Exception(f"Could not connect to MLflow: {e}")

        results = []
        for rm in registered_models:
            versions = self.client.search_model_versions(f"name='{rm.name}'")
            versions_data = []
            for mv in versions:
                size_bytes = get_model_size_from_mlflow(self.client, mv)
                
                # Fetch tags and description directly from the MLflow model version
                tags = mv.tags or {}
                
                versions_data.append({
                    "version": int(mv.version),
                    "status": mv.status,
                    "run_id": mv.run_id,
                    "model_uri": mv.source,
                    "creation_timestamp": mv.creation_timestamp,
                    "size_bytes": size_bytes,
                    "formatted_size": format_size(size_bytes) if size_bytes else "Unknown",
                    "framework": tags.get("framework", "Unknown"),
                    "model_type": tags.get("model_type", "Unknown"),
                    "architecture": tags.get("architecture", ""),
                    "priority": "", # Stored in metrics, not easily retrieved here without fetching run
                    "is_deployable": tags.get("is_deployable", "False") == "True",
                    "deployment_points": [], # Was stored in DB
                    "remarks": mv.description or "",
                    "accuracy": 0.0, # Stored in metrics
                    "db_id": None
                })
            
            versions_data.sort(key=lambda x: x["version"], reverse=True)
            if versions_data:
                results.append({
                    "name": rm.name,
                    "creation_timestamp": rm.creation_timestamp,
                    "all_versions": versions_data
                })
        
        return results

    def delete_model_version(self, mlflow_name, version, db_id=None):
        try:
            # 1. Delete from MLflow Registry
            try:
                mv = self.client.get_model_version(mlflow_name, version)
                run_id = mv.run_id
            except Exception:
                run_id = None
                
            self.client.delete_model_version(name=mlflow_name, version=version)
            
            versions = self.client.search_model_versions(f"name='{mlflow_name}'")
            if not versions:
                try:
                    self.client.delete_registered_model(name=mlflow_name)
                except Exception:
                    pass
            
            # 2. Delete the associated MLflow run
            if run_id:
                try:
                    # In MLflow 2.x, deleted runs are moved to "deleted" lifecycle_stage
                    self.client.delete_run(run_id)
                except Exception as e:
                    pass
                    
            return True
        except Exception as e:
            raise Exception(f"Failed to delete model version {mlflow_name} v{version}: {e}")
