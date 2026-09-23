import os
import torch
import onnx
import mlflow
from typing import List, Optional, Dict, Any

from .data_objects import Model
from .dao import ModelDAO
from .iam import ModelIAMAdapter
from .model_config import ModelConfig
from .security import ModelEncrypt
from .minio_client import MinioStorageService

class ModelManager:
    """Facade for managing ML models according to UML specifications."""

    def __init__(self):
        self.dao = ModelDAO()
        self.iam_adapter = ModelIAMAdapter()
        self.config = ModelConfig()
        self.encrypt = ModelEncrypt()
        self.storage = MinioStorageService(
            endpoint=self.config.minio_endpoint,
            access_key=self.config.minio_access_key,
            secret_key=self.config.minio_secret_key,
            bucket_name=self.config.minio_bucket,
            secure=self.config.minio_secure
        )
        
        # Set up MLflow
        mlflow.set_tracking_uri(self.config.tracking_uri)

    def registerModel(
        self,
        file_path: str,
        original_filename: str,
        user: str,
        model: Model
    ) -> Dict[str, Any]:
        """Registers a model, storing metadata in DB, artifact in MinIO, and tracking in MLflow."""
        # 1. IAM Check
        if not self.iam_adapter.checkAccess(user, "register", model):
            raise PermissionError("Access denied to register model.")
            
        file_format = original_filename.split(".")[-1].lower() if "." in original_filename else "unknown"
        if file_format not in ["pt", "onnx"]:
            raise ValueError(f"Unsupported model format: {file_format}. Only .pt and .onnx are supported.")
            
        # Predict next version using MLflow (Authoritative source)
        from mlflow.tracking import MlflowClient
        client = MlflowClient(tracking_uri=self.config.tracking_uri)
        
        # Ensure registered model exists so we don't fail later
        try:
            client.get_registered_model(model.name)
        except Exception:
            try:
                client.create_registered_model(model.name)
            except Exception:
                pass # Might have been created concurrently
                
        # Predict next version by mimicking MLflow's internal MAX(version) logic directly from the DB.
        # This handles MLflow's soft-deleted versions correctly, which client.search_model_versions hides.
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                # MLflow and Django share the same PostgreSQL DB
                cursor.execute("SELECT MAX(version) FROM model_versions WHERE name=%s", [model.name])
                result = cursor.fetchone()[0]
                predicted_version = (result or 0) + 1
        except Exception:
            predicted_version = 1
            
        model.version = predicted_version

        # 1.5 Duplicate Check (Fallback safety in Postgres)
        existing_model = self.dao.getModel(model.name, model.version)
        if existing_model:
            return {
                "success": False,
                "error": f"Model {existing_model.name} v{existing_model.version} already exists in database. Registration skipped."
            }

        # Validate Model
        try:
            if file_format == "pt":
                model_obj = torch.load(file_path, weights_only=False)
            elif file_format == "onnx":
                model_obj = onnx.load(file_path)
        except Exception as e:
            raise Exception(f"Model validation failed: {str(e)}")

        file_size = os.path.getsize(file_path)

        # 2. MinIO Upload (Encrypt placeholder)
        with open(file_path, "rb") as f:
            raw_data = f.read()
        encrypted_data = self.encrypt.encrypt(raw_data)
        
        # Since encrypt is a no-op, we can just upload the file directly, but for pure UML adherence
        # we can write it to a temp file or use put_object. For simplicity, we just use upload_model.
        object_name = f"models/{model.name}_v{model.version}.{file_format}"
        upload_res = self.storage.upload_model(file_path, object_name)
        if not upload_res["success"]:
            raise Exception(f"Failed to upload artifact to MinIO: {upload_res.get('error')}")
            
        model.modelArtifactPath = upload_res["path"]

        # 3. MLflow Tracking
        tags = {"model_type": model.model_type, "framework": file_format, "is_deployable": str(model.is_deployable)}
        if model.architecture:
            tags["architecture"] = model.architecture
        metrics = {"accuracy": model.accuracy}
        if model.priority is not None:
            metrics["priority"] = float(model.priority)

        try:
            with mlflow.start_run() as run:
                mlflow.set_tags(tags)
                mlflow.log_metrics(metrics)
                run_id = run.info.run_id
                
            # Register in MLflow Registry
            mlflow_model = mlflow.register_model(model_uri=f"s3://{self.config.minio_bucket}/{object_name}", name=model.name)
            
            # CAPTURE ACTUAL MLFLOW VERSION
            actual_version = int(mlflow_model.version)
            model.version = actual_version
            
            # If the actual version differs from predicted, the MinIO path has the predicted version string. 
            # This is acceptable as the path invariant holds (DB path == MLflow path == MinIO path).
            
        except Exception as e:
            # Rollback MinIO
            self.storage.delete_model(object_name)
            raise Exception(f"MLflow registration failed: {str(e)}")

        # 4. Store in PostgreSQL
        try:
            stored_model = self.dao.storeModel(
                model=model,
                original_filename=original_filename,
                file_format=file_format,
                file_size=file_size,
                run_id=run_id
            )
        except Exception as e:
            # Rollback MLflow and MinIO
            client.delete_model_version(name=model.name, version=str(model.version))
            self.storage.delete_model(object_name)
            raise Exception(f"Database save failed, rolled back MLflow and MinIO: {str(e)}")
        
        return {
            "success": True,
            "model_id": stored_model.id,
            "artifact_path": stored_model.modelArtifactPath
        }

    def listModels(self) -> List[Model]:
        return self.dao.getModelList()

    def findModel(self, useCase: str) -> List[Model]:
        return self.dao.getModelList(use_case=useCase)

    def getPurposes(self) -> List[str]:
        return self.dao.getUniquePurposes()

    def updateModel(self, user: str, model_id: int, update_data: dict) -> Model:
        model = self.dao.getModelById(model_id)
        if not model:
            raise ValueError("Model not found.")
            
        if not self.iam_adapter.checkAccess(user, "update", model):
            raise PermissionError("Access denied to update model.")
            
        # Apply partial updates
        if 'purpose' in update_data:
            model.purpose = update_data['purpose'].strip()
        if 'architecture' in update_data:
            model.architecture = update_data['architecture'].strip()
        if 'accuracy' in update_data:
            model.accuracy = float(update_data['accuracy'])
        if 'priority' in update_data:
            model.priority = int(update_data['priority']) if update_data['priority'] not in [None, ""] else None
        if 'is_deployable' in update_data:
            model.is_deployable = bool(update_data['is_deployable'])
        if 'status' in update_data:
            model.status = update_data['status'].strip()
            
        success = self.dao.updateModel(model)
        if not success:
            raise Exception("Failed to update model in database.")
            
        return model

    def deleteModel(self, user: str, name: str, version: int) -> bool:
        model = self.dao.getModel(name, version)
        if not model:
            raise ValueError("Model not found.")
            
        if not self.iam_adapter.checkAccess(user, "delete", model):
            raise PermissionError("Access denied to delete model.")

        # 1. Delete from MLflow Registry
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient(tracking_uri=self.config.tracking_uri)
            # Delete the specific version
            client.delete_model_version(name=name, version=str(version))
            
            # If no remaining versions exist, delete the registered model container
            remaining_versions = client.search_model_versions(f"name='{name}'")
            if len(remaining_versions) == 0:
                client.delete_registered_model(name=name)
        except Exception as e:
            # We don't silently report success if it fails, but if it's a 404 (ResourceDoesNotExist),
            # we might want to continue. For now, strict failure per requirements.
            if "RESOURCE_DOES_NOT_EXIST" not in str(e):
                raise Exception(f"Failed to delete model from MLflow: {str(e)}")

        # 2. Delete from MinIO
        if model.modelArtifactPath:
            object_name = model.modelArtifactPath.split(f"{self.config.minio_bucket}/")[-1]
            del_res = self.storage.delete_model(object_name)
            if not del_res.get("success"):
                raise Exception(f"Failed to delete artifact from MinIO: {del_res.get('error')}")
            
        # 3. Delete from PostgreSQL
        success = self.dao.deleteModel(name, version)
        if not success:
            raise Exception("Failed to delete model metadata from PostgreSQL.")
            
        return True
