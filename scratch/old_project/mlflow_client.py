import os
import mlflow
import mlflow.pytorch
import mlflow.onnx
from mlflow.exceptions import MlflowException

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")

def get_model_size_from_mlflow(client: mlflow.MlflowClient, version_obj) -> int | None:
    source = getattr(version_obj, "source", "") or ""
    run_id = getattr(version_obj, "run_id", "") or ""

    if source.startswith("models:/"):
        model_id = source.replace("models:/", "")
        try:
            artifacts = client.list_logged_model_artifacts(model_id)
            total_size = sum(a.file_size for a in artifacts if getattr(a, "file_size", None) is not None)
            if total_size > 0:
                return total_size
        except Exception:
            pass

    if run_id:
        try:
            artifacts = client.list_artifacts(run_id, path="model")
            if not artifacts:
                artifacts = client.list_artifacts(run_id)
            total_size = sum(a.file_size for a in artifacts if getattr(a, "file_size", None) is not None)
            if total_size > 0:
                return total_size
        except Exception:
            pass

    return None

def log_and_register_model(model_obj, model_name: str, ext: str, tags: dict, metrics: dict) -> tuple[int, str, str, int | None]:
    """
    Starts an MLflow run, logs the model object via the correct framework module,
    registers it, and returns (version_number, run_id, model_uri, final_size).
    Raises Exception if MLflow fails.
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    with mlflow.start_run() as run:
        mlflow.set_tags(tags)
        for k, v in metrics.items():
            if v is not None:
                mlflow.log_metric(k, v)
        
        if ext == "pt":
            mlflow.pytorch.log_model(model_obj, artifact_path="model", serialization_format="pickle")
        elif ext == "onnx":
            mlflow.onnx.log_model(model_obj, artifact_path="model")
        else:
            raise ValueError(f"Unsupported extension for MLflow logging: {ext}")
            
        run_id = run.info.run_id
        
    model_uri = f"runs:/{run_id}/model"
    result = mlflow.register_model(model_uri=model_uri, name=model_name)
    
    mlflow_size = None
    try:
        client = mlflow.MlflowClient()
        mv = client.get_model_version(name=result.name, version=result.version)
        mlflow_size = get_model_size_from_mlflow(client, mv)
    except Exception:
        pass
        
    return int(result.version), run_id, model_uri, mlflow_size

def get_all_registered_models():
    """
    Queries MLflow for all registered models and all their versions.
    Yields (model_info, [version_info, ...]) where version_info contains size.
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.MlflowClient()
    registered_models = client.search_registered_models()
    
    for model in registered_models:
        all_versions = client.search_model_versions(f"name='{model.name}'")
        versions_data = []
        for v in all_versions:
            size_bytes = get_model_size_from_mlflow(client, v)
            versions_data.append({
                "version": int(v.version),
                "status": v.status,
                "run_id": v.run_id,
                "model_uri": f"runs:/{v.run_id}/model",
                "creation_timestamp": v.creation_timestamp,
                "size_bytes": size_bytes
            })
        yield model, versions_data
