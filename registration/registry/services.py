import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from dotenv import load_dotenv
import mlflow
from mlflow.tracking import MlflowClient
import boto3

# AWS credentials pop removed

ALIAS_TO_DP = {
    "deployed-lid": "LID",
    "deployed-asr": "ASR",
    "deployed-diarization": "Diarization",
    "deployed-speaker-identification": "Speaker Identification",
    "deployed-text-pipeline": "Text Pipeline",
    "deployed-uis": "UIS"
}
DP_TO_ALIAS = {v: k for k, v in ALIAS_TO_DP.items()}


# -----------------------------------------------------------------------------
# ADAPTER INTERFACES
# -----------------------------------------------------------------------------

class ModelRegistryAdapter(ABC):
    @abstractmethod
    def create_experiment(self, name: str) -> str: pass
    
    @abstractmethod
    def ensure_registered_model(self, name: str, model_type: str, purpose: str): pass

    @abstractmethod
    def create_model_version(self, name: str, source: str, run_id: str) -> Any: pass
    
    @abstractmethod
    def delete_model_version(self, name: str, version: str): pass
    
    @abstractmethod
    def delete_run(self, run_id: str): pass
    
    @abstractmethod
    def set_model_version_tag(self, name: str, version: str, key: str, value: str): pass
    
    @abstractmethod
    def search_registered_models(self, filter_string: str = "") -> List[Any]: pass
    
    @abstractmethod
    def search_model_versions(self, filter_string: str) -> List[Any]: pass
    
    @abstractmethod
    def get_registered_model(self, name: str) -> Any: pass
    
    @abstractmethod
    def get_model_version(self, name: str, version: str) -> Any: pass
    
    @abstractmethod
    def set_registered_model_tag(self, name: str, key: str, value: str): pass
    
    @abstractmethod
    def set_registered_model_alias(self, name: str, alias: str, version: str): pass
    
    @abstractmethod
    def delete_registered_model_alias(self, name: str, alias: str): pass
    
    @abstractmethod
    def delete_registered_model(self, name: str): pass
    
    @abstractmethod
    def start_run(self, experiment_id: str) -> Any: pass


class ArtifactStorageAdapter(ABC):
    @abstractmethod
    def upload_folder(self, local_dir: str, prefix: str): pass
    
    @abstractmethod
    def delete_folder(self, prefix: str): pass
    
    @abstractmethod
    def get_bucket(self) -> str: pass


# -----------------------------------------------------------------------------
# IMPLEMENTATIONS
# -----------------------------------------------------------------------------

class MLflowAdapter(ModelRegistryAdapter):
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
        
        self.tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.tracking_uri)
        
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def create_experiment(self, name: str) -> str:
        try:
            return self.client.create_experiment(name)
        except Exception:
            exp = self.client.get_experiment_by_name(name)
            if exp:
                if exp.lifecycle_stage != 'active':
                    self.client.restore_experiment(exp.experiment_id)
                return exp.experiment_id
            else:
                raise Exception(f"Failed to create or get experiment '{name}'")

    def ensure_registered_model(self, name: str, model_type: str, purpose: str):
        try:
            self.client.get_registered_model(name)
        except Exception:
            try:
                self.client.create_registered_model(name)
            except Exception:
                pass # Might have been created concurrently
                
        # Update RM tags
        rm_tags = {
            "model_type": model_type,
            "purpose": purpose
        }
        for k, v in rm_tags.items():
            if v:
                self.client.set_registered_model_tag(name, k, v)

    def create_model_version(self, name: str, source: str, run_id: str) -> Any:
        return self.client.create_model_version(name=name, source=source, run_id=run_id)

    def delete_model_version(self, name: str, version: str):
        self.client.delete_model_version(name, version)

    def delete_run(self, run_id: str):
        self.client.delete_run(run_id)

    def set_model_version_tag(self, name: str, version: str, key: str, value: str):
        self.client.set_model_version_tag(name, version, key, value)

    def search_registered_models(self, filter_string: str = "") -> List[Any]:
        return self.client.search_registered_models(filter_string=filter_string)

    def search_model_versions(self, filter_string: str) -> List[Any]:
        return self.client.search_model_versions(filter_string=filter_string)

    def get_registered_model(self, name: str) -> Any:
        return self.client.get_registered_model(name)

    def get_model_version(self, name: str, version: str) -> Any:
        return self.client.get_model_version(name, version)

    def set_registered_model_tag(self, name: str, key: str, value: str):
        self.client.set_registered_model_tag(name, key, value)

    def set_registered_model_alias(self, name: str, alias: str, version: str):
        self.client.set_registered_model_alias(name, alias, version)

    def delete_registered_model_alias(self, name: str, alias: str):
        self.client.delete_registered_model_alias(name, alias)

    def delete_registered_model(self, name: str):
        self.client.delete_registered_model(name)

    def start_run(self, experiment_id: str) -> Any:
        return mlflow.start_run(experiment_id=experiment_id)


class MinIOAdapter(ArtifactStorageAdapter):
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
        
        self.bucket = os.environ.get("MINIO_BUCKET")
        ignore_tls = os.environ.get("MLFLOW_S3_IGNORE_TLS", "false").lower() in ["true", "1"]
        
        self.s3 = boto3.client(
            's3',
            endpoint_url="http://" + os.environ.get("MINIO_ENDPOINT") if not (os.environ.get("MINIO_SECURE", "false").lower() in ["true", "1"]) else "https://" + os.environ.get("MINIO_ENDPOINT"),
            aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY"),
            verify=not ignore_tls
        )
        
    def get_bucket(self) -> str:
        return self.bucket

    def upload_folder(self, local_dir: str, prefix: str):
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, local_dir)
                s3_key = f"{prefix}/{rel_path}".replace("\\", "/")
                self.s3.upload_file(local_path, self.bucket, s3_key)
                
    def delete_folder(self, prefix: str):
        # List and delete all objects with the given prefix
        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if 'Contents' in page:
                delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
                self.s3.delete_objects(Bucket=self.bucket, Delete=delete_keys)


# -----------------------------------------------------------------------------
# DAO
# -----------------------------------------------------------------------------

class ModelDAO:
    def __init__(self, registry_adapter: ModelRegistryAdapter, storage_adapter: ArtifactStorageAdapter):
        self.registry = registry_adapter
        self.storage = storage_adapter
        
    def create_experiment(self, name: str) -> str: return self.registry.create_experiment(name)
    def ensure_registered_model(self, name: str, model_type: str, purpose: str): return self.registry.ensure_registered_model(name, model_type, purpose)
    def start_run(self, experiment_id: str): return self.registry.start_run(experiment_id)
    def create_model_version(self, name: str, source: str, run_id: str) -> Any: return self.registry.create_model_version(name, source, run_id)
    def set_model_version_tag(self, name: str, version: str, key: str, value: str): return self.registry.set_model_version_tag(name, version, key, value)
    def delete_model_version(self, name: str, version: str): return self.registry.delete_model_version(name, version)
    def delete_run(self, run_id: str): return self.registry.delete_run(run_id)
    def search_registered_models(self, filter_string: str = "") -> List[Any]: return self.registry.search_registered_models(filter_string)
    def search_model_versions(self, filter_string: str) -> List[Any]: return self.registry.search_model_versions(filter_string)
    def get_registered_model(self, name: str) -> Any: return self.registry.get_registered_model(name)
    def get_model_version(self, name: str, version: str) -> Any: return self.registry.get_model_version(name, version)
    def set_registered_model_tag(self, name: str, key: str, value: str): return self.registry.set_registered_model_tag(name, key, value)
    def set_registered_model_alias(self, name: str, alias: str, version: str): return self.registry.set_registered_model_alias(name, alias, version)
    def delete_registered_model_alias(self, name: str, alias: str): return self.registry.delete_registered_model_alias(name, alias)
    def delete_registered_model(self, name: str): return self.registry.delete_registered_model(name)
    
    def get_bucket(self) -> str: return self.storage.get_bucket()
    def upload_folder(self, local_dir: str, prefix: str): return self.storage.upload_folder(local_dir, prefix)
    def delete_folder(self, prefix: str): return self.storage.delete_folder(prefix)


# -----------------------------------------------------------------------------
# FACADE / MANAGER
# -----------------------------------------------------------------------------

class ModelManager:
    def __init__(self, dao: ModelDAO):
        self.dao = dao
        
    def register_model_folder(self, local_dir: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        model_name = metadata.get("model_name")
        exp_id = self.dao.create_experiment(model_name)
        
        self.dao.ensure_registered_model(
            name=model_name,
            model_type=metadata.get("model_type", ""),
            purpose=metadata.get("purpose", "")
        )
        
        with self.dao.start_run(experiment_id=exp_id) as run:
            run_id = run.info.run_id
            
        bucket = self.dao.get_bucket()
        dummy_source = f"s3://{bucket}/{model_name}/django_managed_artifacts_{run_id}"
        
        mv = self.dao.create_model_version(
            name=model_name,
            source=dummy_source,
            run_id=run_id
        )
        
        actual_version = mv.version
        expected_s3_path = f"s3://{bucket}/{model_name}/v{actual_version}"
        prefix = f"{model_name}/v{actual_version}"
        
        try:
            self.dao.upload_folder(local_dir, prefix)
        except Exception as e:
            self.dao.delete_folder(prefix)
            self.dao.delete_model_version(model_name, actual_version)
            if run_id:
                self.dao.delete_run(run_id)
            raise Exception(f"Failed to upload model folder to MinIO: {e}")
            
        deployment_points = metadata.get("deployment_points", [])
        if isinstance(deployment_points, str):
            try:
                deployment_points = json.loads(deployment_points)
            except:
                deployment_points = [deployment_points]
                
        valid_dp = {"LID", "ASR", "Diarization", "Speaker Identification", "Text Pipeline", "UIS"}
        for dp in deployment_points:
            if dp not in valid_dp:
                raise ValueError(f"Invalid deployment point: {dp}")
                
        mv_tags = {
            "architecture": metadata.get("architecture", ""),
            "accuracy": str(metadata.get("accuracy", 0.0)),
            "priority": str(metadata.get("priority", "")),
            "is_deployable": str(metadata.get("is_deployable", False)),
            "deployment_points": json.dumps(deployment_points),
            "remarks": metadata.get("remarks", ""),
            "artifact_path": expected_s3_path
        }
        
        for k, v in mv_tags.items():
            if v:
                self.dao.set_model_version_tag(
                    name=model_name,
                    version=mv.version,
                    key=k,
                    value=v
                )
                
        return {
            "success": True,
            "model_name": mv.name,
            "version": mv.version,
            "artifact_path": expected_s3_path
        }

    def _format_model_version(self, mv, rm) -> Dict[str, Any]:
        tags = mv.tags
        rm_tags = rm.tags if rm else {}
        
        dp_raw = tags.get("deployment_points", "[]")
        try:
            dp_list = json.loads(dp_raw)
        except:
            dp_list = []
            
        return {
            "name": mv.name,
            "version": mv.version,
            "model_type": rm_tags.get("model_type", ""),
            "purpose": rm_tags.get("purpose", ""),
            "architecture": tags.get("architecture", ""),
            "accuracy": float(tags.get("accuracy", "0.0")),
            "priority": int(tags.get("priority")) if tags.get("priority", "").isdigit() else None,
            "is_deployable": tags.get("is_deployable", "False").lower() == "true",
            "deployment_points": dp_list,
            "remarks": tags.get("remarks", ""),
            "artifact_path": tags.get("artifact_path", ""),
            "run_id": mv.run_id,
            "status": mv.status
        }

    def _get_currently_deployed(self, rm) -> Dict[str, str]:
        currently_deployed = {}
        for alias, version in (rm.aliases or {}).items():
            dp = ALIAS_TO_DP.get(alias)
            if dp:
                currently_deployed[dp] = version
        return currently_deployed

    def list_models(self) -> List[Dict[str, Any]]:
        rms = self.dao.search_registered_models()
        results = []
        for rm in rms:
            mvs = self.dao.search_model_versions(f"name='{rm.name}'")
            versions = [self._format_model_version(mv, rm) for mv in mvs]
            results.append({
                "name": rm.name,
                "model_type": rm.tags.get("model_type", ""),
                "purpose": rm.tags.get("purpose", ""),
                "currently_deployed": self._get_currently_deployed(rm),
                "all_versions": sorted(versions, key=lambda x: int(x["version"]), reverse=True)
            })
        return results

    def find_models(self, purpose: str) -> List[Dict[str, Any]]:
        rms = self.dao.search_registered_models(filter_string=f"tags.purpose = '{purpose}'")
        results = []
        for rm in rms:
            mvs = self.dao.search_model_versions(f"name='{rm.name}'")
            versions = [self._format_model_version(mv, rm) for mv in mvs]
            results.append({
                "name": rm.name,
                "model_type": rm.tags.get("model_type", ""),
                "purpose": rm.tags.get("purpose", ""),
                "currently_deployed": self._get_currently_deployed(rm),
                "all_versions": sorted(versions, key=lambda x: int(x["version"]), reverse=True)
            })
        return results

    def list_architectures(self) -> List[str]:
        mvs = self.dao.search_model_versions("")
        architectures = set()
        for mv in mvs:
            arch = mv.tags.get("architecture")
            if arch:
                architectures.add(arch)
        return sorted(list(architectures))

    def list_purposes(self) -> List[str]:
        rms = self.dao.search_registered_models("")
        purposes = set()
        for rm in rms:
            purpose = rm.tags.get("purpose")
            if purpose:
                purposes.add(purpose)
        return sorted(list(purposes))

    def get_model_version(self, name: str, version: int) -> Optional[Dict[str, Any]]:
        try:
            rm = self.dao.get_registered_model(name)
            mv = self.dao.get_model_version(name, str(version))
            return self._format_model_version(mv, rm)
        except Exception:
            return None

    def update_model_version(self, name: str, version: int, update_data: Dict[str, Any]) -> bool:
        if "model_type" in update_data:
            self.dao.set_registered_model_tag(name, "model_type", update_data["model_type"])
        if "purpose" in update_data:
            self.dao.set_registered_model_tag(name, "purpose", update_data["purpose"])
            
        mv_keys = ["architecture", "accuracy", "priority", "is_deployable", "remarks"]
        for k in mv_keys:
            if k in update_data:
                self.dao.set_model_version_tag(name, str(version), k, str(update_data[k]))
                
        if "deployment_points" in update_data:
            dp = update_data["deployment_points"]
            if isinstance(dp, str):
                try:
                    dp = json.loads(dp)
                except:
                    dp = [dp]
            valid_dp = {"LID", "ASR", "Diarization", "Speaker Identification", "Text Pipeline", "UIS"}
            for p in dp:
                if p not in valid_dp:
                    raise ValueError(f"Invalid deployment point: {p}")
            self.dao.set_model_version_tag(name, str(version), "deployment_points", json.dumps(dp))
            
        return True

    def delete_model_version(self, name: str, version: int) -> bool:
        try:
            rm = self.dao.get_registered_model(name)
            for alias, aliased_version in (rm.aliases or {}).items():
                if aliased_version == str(version):
                    self.dao.delete_registered_model_alias(name, alias)
            
            self.dao.delete_model_version(name, str(version))
            
            # Delete artifacts from MinIO
            self.dao.delete_folder(f"{name}/v{version}")
            
            remaining = self.dao.search_model_versions(f"name='{name}'")
            if len(remaining) == 0:
                self.dao.delete_registered_model(name)
                
            return True
        except Exception as e:
            raise Exception(f"Failed to delete model version: {str(e)}")

    def set_deployed_version(self, name: str, version: int, deployment_point: str) -> bool:
        alias = DP_TO_ALIAS.get(deployment_point)
        if not alias:
            raise ValueError(f"Invalid deployment point: {deployment_point}")

        self.dao.get_registered_model(name)
        mv = self.dao.get_model_version(name, str(version))
        
        dp_raw = mv.tags.get("deployment_points", "[]")
        try:
            dp_list = json.loads(dp_raw)
        except:
            dp_list = []
            
        if deployment_point not in dp_list:
            raise ValueError(f"Deployment point '{deployment_point}' is not assigned to this model version's metadata.")
            
        self.dao.set_registered_model_alias(name, alias, str(version))
        return True

