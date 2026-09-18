from dataclasses import dataclass
from . import db_repository
from . import model_loaders
from . import mlflow_client
from .utils import format_size, compute_file_hash

class ModelRegistrationError(Exception):
    """Custom exception raised when model registration fails."""
    pass

@dataclass
class ModelUploadData:
    file_path: str
    model_name: str
    original_filename: str
    file_size: int
    model_type: str
    architecture: str
    accuracy: float
    priority: int
    deployment_points: list
    remarks: str
    is_deployable: bool
    versioning: str

class MLManager:
    @staticmethod
    def register_new_model(data: ModelUploadData) -> dict:
        if data.file_size == 0:
            raise ModelRegistrationError("its empty")
        
        file_hash = compute_file_hash(data.file_path)
        file_format = data.original_filename.split(".")[-1].lower() if "." in data.original_filename else "unknown"
        
        arch_obj = None
        if data.architecture:
            arch_obj = db_repository.get_architecture_by_id(int(data.architecture))

        db_record = db_repository.create_pending_model(
            original_filename=data.original_filename,
            file_format=file_format,
            file_size=data.file_size,
            file_hash=file_hash,
            mlflow_name=data.model_name,
            model_type=data.model_type,
            architecture=arch_obj,
            accuracy=data.accuracy,
            priority=data.priority,
            deployment_points=data.deployment_points,
            remarks=data.remarks,
            is_deployable=data.is_deployable,
            versioning=data.versioning
        )

        try:
            model_obj = model_loaders.load_and_validate_model(data.file_path, file_format)
        except ValueError:
            db_repository.update_model_status_failed_loading(db_record.id)
            raise ModelRegistrationError("Unsupported file extension.")
        except Exception as load_err:
            print(f"LOAD ERROR: {load_err}")
            db_repository.update_model_status_failed_loading(db_record.id)
            raise ModelRegistrationError(f"it is fake and cant be deserialized (invalid .{file_format}): {load_err}") from load_err

        tags = {
            "model_type": data.model_type,
            "architecture": arch_obj.name if arch_obj else "N/A",
            "deployment_points": ", ".join(data.deployment_points),
            "remarks": data.remarks or "",
            "is_deployable": str(data.is_deployable),
            "versioning": data.versioning,
            "framework": "pytorch" if file_format == "pt" else "onnx"
        }
        
        metrics = {"accuracy": data.accuracy}
        if data.priority is not None:
            metrics["priority"] = data.priority

        try:
            version, run_id, model_uri, mlflow_size = mlflow_client.log_and_register_model(
                model_obj=model_obj,
                model_name=data.model_name,
                ext=file_format,
                tags=tags,
                metrics=metrics
            )
        except Exception as mlflow_err:
            db_repository.update_model_status_failed_mlflow(db_record.id)
            raise ModelRegistrationError(f"MLflow registration failed: {mlflow_err}") from mlflow_err

        final_size = mlflow_size if mlflow_size is not None else data.file_size

        db_repository.update_model_status_registered(
            db_record_id=db_record.id,
            mlflow_version=version,
            run_id=run_id,
            model_uri=model_uri
        )

        return {
            "model_name": data.model_name,
            "version": version,
            "run_id": run_id,
            "model_uri": model_uri,
            "db_record_id": db_record.id,
            "size_bytes": final_size,
            "formatted_size": format_size(final_size),
        }

    @staticmethod
    def get_registry_summary() -> list[dict]:
        try:
            registered_models = list(mlflow_client.get_all_registered_models())
        except Exception as err:
            raise ModelRegistrationError(f"Could not connect to MLflow: {err}") from err

        active_name_vers = set()
        for model, versions_data_raw in registered_models:
            for v_raw in versions_data_raw:
                active_name_vers.add((model.name, int(v_raw["version"])))

        db_repository.sync_deleted_models(active_name_vers)

        imported_by_run, imported_by_name_ver = db_repository.get_all_imported_models_indexed()

        results = []
        for model, versions_data_raw in registered_models:
            versions_data = []
            for v_raw in versions_data_raw:
                ver_num = v_raw["version"]
                size_bytes = v_raw["size_bytes"]
                
                imp = imported_by_run.get(v_raw["run_id"]) or imported_by_name_ver.get((model.name, ver_num))
                if size_bytes is None and imp and imp.file_size:
                    size_bytes = imp.file_size

                original_filename = imp.original_filename if imp else None
                framework = imp.file_format if imp else "Unknown"
                model_type = imp.model_type if imp else "Unknown"
                accuracy = imp.accuracy if imp else 0.0
                priority = imp.priority if imp else None
                is_deployable = imp.is_deployable if imp else False
                architecture = imp.architecture.name if imp and imp.architecture else "N/A"
                deployment_points = imp.deployment_points if imp and imp.deployment_points else []

                versions_data.append({
                    "version": ver_num,
                    "status": v_raw["status"],
                    "run_id": v_raw["run_id"],
                    "model_uri": v_raw["model_uri"],
                    "creation_timestamp": v_raw["creation_timestamp"],
                    "size_bytes": size_bytes,
                    "formatted_size": format_size(size_bytes),
                    "original_filename": original_filename,
                    "framework": framework,
                    "model_type": model_type,
                    "accuracy": accuracy,
                    "priority": priority,
                    "is_deployable": is_deployable,
                    "architecture": architecture,
                    "deployment_points": deployment_points,
                })

            if not versions_data:
                continue

            versions_data.sort(key=lambda x: x["version"], reverse=True)
            results.append({
                "name": model.name,
                "all_versions": versions_data,
                "creation_timestamp": model.creation_timestamp,
                "last_updated_timestamp": model.last_updated_timestamp,
            })

        return results
