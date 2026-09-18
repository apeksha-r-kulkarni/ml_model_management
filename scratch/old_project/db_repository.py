from .models import ImportedModel, Architecture
from typing import Optional, List, Dict, Any

def get_architecture_by_id(arch_id: int) -> Optional[Architecture]:
    try:
        return Architecture.objects.get(id=arch_id)
    except (ValueError, Architecture.DoesNotExist):
        return None

def get_all_architectures() -> List[Dict[str, Any]]:
    return list(Architecture.objects.values("id", "name"))

def get_or_create_architecture(name: str) -> Architecture:
    arch, _ = Architecture.objects.get_or_create(name=name)
    return arch

def create_pending_model(
    original_filename: str,
    file_format: str,
    file_size: int,
    file_hash: str,
    mlflow_name: str,
    model_type: str,
    architecture: Optional[Architecture],
    accuracy: float,
    priority: Optional[int],
    deployment_points: List[str],
    remarks: str,
    is_deployable: bool,
    versioning: str
) -> ImportedModel:
    return ImportedModel.objects.create(
        original_filename=original_filename,
        file_format=file_format,
        file_size=file_size,
        file_hash=file_hash,
        status="PENDING",
        mlflow_name=mlflow_name,
        model_type=model_type,
        architecture=architecture,
        accuracy=accuracy,
        priority=priority,
        deployment_points=deployment_points,
        remarks=remarks,
        is_deployable=is_deployable,
        versioning=versioning
    )

def update_model_status_failed_loading(db_record_id: int):
    try:
        record = ImportedModel.objects.get(id=db_record_id)
        record.status = "FAILED_LOADING"
        record.save()
    except ImportedModel.DoesNotExist:
        pass

def update_model_status_failed_mlflow(db_record_id: int):
    try:
        record = ImportedModel.objects.get(id=db_record_id)
        record.status = "FAILED_MLFLOW"
        record.save()
    except ImportedModel.DoesNotExist:
        pass

def update_model_status_registered(
    db_record_id: int, 
    mlflow_version: int, 
    run_id: str, 
    model_uri: str
):
    try:
        record = ImportedModel.objects.get(id=db_record_id)
        record.status = "REGISTERED"
        record.mlflow_version = mlflow_version
        record.run_id = run_id
        record.model_uri = model_uri
        record.save()
    except ImportedModel.DoesNotExist:
        pass

def sync_deleted_models(active_name_vers: set):
    """
    Marks local ImportedModel records as DELETED if their MLflow version is no longer active.
    Only evaluates models that are currently marked as REGISTERED.
    """
    records = ImportedModel.objects.filter(
        status="REGISTERED"
    ).exclude(
        mlflow_name__isnull=True
    ).exclude(
        mlflow_version__isnull=True
    )
    
    for imp in records:
        if (imp.mlflow_name, int(imp.mlflow_version)) not in active_name_vers:
            imp.status = "DELETED"
            imp.save(update_fields=["status"])


def get_all_imported_models_indexed() -> tuple[Dict[str, ImportedModel], Dict[tuple[str, int], ImportedModel]]:
    imported_by_run = {}
    imported_by_name_ver = {}
    try:
        for imp in ImportedModel.objects.exclude(status="DELETED"):
            if imp.run_id:
                imported_by_run[imp.run_id] = imp
            if imp.mlflow_name and imp.mlflow_version is not None:
                imported_by_name_ver[(imp.mlflow_name, int(imp.mlflow_version))] = imp
    except Exception:
        pass
    return imported_by_run, imported_by_name_ver
