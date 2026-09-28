import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
import mlflow
from mlflow.tracking import MlflowClient

# Force removal of AWS credentials so the process proves it doesn't need them
os.environ.pop("AWS_ACCESS_KEY_ID", None)
os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
os.environ.pop("MLFLOW_S3_ENDPOINT_URL", None)

ALIAS_TO_DP = {
    "deployed-lid": "LID",
    "deployed-asr": "ASR",
    "deployed-diarization": "Diarization",
    "deployed-speaker-identification": "Speaker Identification",
    "deployed-text-pipeline": "Text Pipeline",
    "deployed-uis": "UIS"
}
DP_TO_ALIAS = {v: k for k, v in ALIAS_TO_DP.items()}

class MLflowService:
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
        
        self.tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.tracking_uri)
        
        self.client = MlflowClient(tracking_uri=self.tracking_uri)
        
    def _ensure_registered_model(self, name: str, model_type: str, purpose: str):
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

    def register_model_folder(self, local_dir: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        model_name = metadata.get("model_name")
        
        # Ensure experiment exists for this model to group its artifacts
        exp_name = model_name
        try:
            exp_id = self.client.create_experiment(exp_name)
        except Exception:
            exp = self.client.get_experiment_by_name(exp_name)
            if exp:
                if exp.lifecycle_stage != 'active':
                    self.client.restore_experiment(exp.experiment_id)
                exp_id = exp.experiment_id
            else:
                raise Exception(f"Failed to create or get experiment '{exp_name}'")
                
        self._ensure_registered_model(
            name=model_name,
            model_type=metadata.get("model_type", ""),
            purpose=metadata.get("purpose", "")
        )
        
        import boto3
        bucket = os.environ.get("MINIO_BUCKET")
        ignore_tls = os.environ.get("MLFLOW_S3_IGNORE_TLS", "false").lower() in ["true", "1"]
        
        s3 = boto3.client(
            's3',
            endpoint_url="http://" + os.environ.get("MINIO_ENDPOINT") if not (os.environ.get("MINIO_SECURE", "false").lower() in ["true", "1"]) else "https://" + os.environ.get("MINIO_ENDPOINT"),
            aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY"),
            verify=not ignore_tls
        )
        
        with mlflow.start_run(experiment_id=exp_id) as run:
            run_id = run.info.run_id
            
        # Create the model version with a dummy source to secure the actual version number
        dummy_source = f"s3://{bucket}/{model_name}/django_managed_artifacts_{run_id}"
        
        mv = self.client.create_model_version(
            name=model_name,
            source=dummy_source,
            run_id=run_id
        )
        
        actual_version = mv.version
        expected_s3_path = f"s3://{bucket}/{model_name}/v{actual_version}"
        
        try:
            # Upload folder directly to MinIO using the actual assigned version
            for root, _, files in os.walk(local_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_path, local_dir)
                    s3_key = f"{model_name}/v{actual_version}/{rel_path}".replace("\\", "/")
                    s3.upload_file(local_path, bucket, s3_key)
        except Exception as e:
            # Rollback if upload fails
            self.client.delete_model_version(model_name, actual_version)
            if run_id:
                self.client.delete_run(run_id)
            raise Exception(f"Failed to upload model folder to MinIO: {e}")
            
        # Apply MV tags
        deployment_points = metadata.get("deployment_points", [])
        if isinstance(deployment_points, str):
            try:
                deployment_points = json.loads(deployment_points)
            except:
                deployment_points = [deployment_points]
                
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
                self.client.set_model_version_tag(
                    name=model_name,
                    version=mv.version,
                    key=k,
                    value=v
                )
                
        return {
            "success": True,
            "model_name": mv.name,
            "version": mv.version,
            "artifact_path": mv.source
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
            "artifact_path": mv.source,
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
        rms = self.client.search_registered_models()
        results = []
        for rm in rms:
            mvs = self.client.search_model_versions(f"name='{rm.name}'")
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
        rms = self.client.search_registered_models(filter_string=f"tags.purpose = '{purpose}'")
        results = []
        for rm in rms:
            mvs = self.client.search_model_versions(f"name='{rm.name}'")
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
        mvs = self.client.search_model_versions("")
        architectures = set()
        for mv in mvs:
            arch = mv.tags.get("architecture")
            if arch:
                architectures.add(arch)
        return sorted(list(architectures))

    def list_purposes(self) -> List[str]:
        rms = self.client.search_registered_models("")
        purposes = set()
        for rm in rms:
            purpose = rm.tags.get("purpose")
            if purpose:
                purposes.add(purpose)
        return sorted(list(purposes))

    def get_model_version(self, name: str, version: int) -> Optional[Dict[str, Any]]:
        try:
            rm = self.client.get_registered_model(name)
            mv = self.client.get_model_version(name, str(version))
            return self._format_model_version(mv, rm)
        except Exception:
            return None

    def update_model_version(self, name: str, version: int, update_data: Dict[str, Any]) -> bool:
        # Update RM tags
        if "model_type" in update_data:
            self.client.set_registered_model_tag(name, "model_type", update_data["model_type"])
        if "purpose" in update_data:
            self.client.set_registered_model_tag(name, "purpose", update_data["purpose"])
            
        # Update MV tags
        mv_keys = ["architecture", "accuracy", "priority", "is_deployable", "remarks"]
        for k in mv_keys:
            if k in update_data:
                self.client.set_model_version_tag(name, str(version), k, str(update_data[k]))
                
        if "deployment_points" in update_data:
            dp = update_data["deployment_points"]
            if isinstance(dp, str):
                try:
                    dp = json.loads(dp)
                except:
                    dp = [dp]
            self.client.set_model_version_tag(name, str(version), "deployment_points", json.dumps(dp))
            
        return True

    def delete_model_version(self, name: str, version: int) -> bool:
        try:
            # Check if this version has any deployment aliases and remove them first
            rm = self.client.get_registered_model(name)
            for alias, aliased_version in (rm.aliases or {}).items():
                if aliased_version == str(version):
                    self.client.delete_registered_model_alias(name, alias)
            
            self.client.delete_model_version(name, str(version))
            
            # Delete RM if empty
            remaining = self.client.search_model_versions(f"name='{name}'")
            if len(remaining) == 0:
                self.client.delete_registered_model(name)
                
            return True
        except Exception as e:
            raise Exception(f"Failed to delete MLflow model version: {str(e)}")

    def set_deployed_version(self, name: str, version: int, deployment_point: str) -> bool:
        # Validate deployment point alias mapping
        alias = DP_TO_ALIAS.get(deployment_point)
        if not alias:
            raise ValueError(f"Invalid deployment point: {deployment_point}")

        # Validate RM and MV exist
        self.client.get_registered_model(name)
        mv = self.client.get_model_version(name, str(version))
        
        # Validate MV has this deployment point
        dp_raw = mv.tags.get("deployment_points", "[]")
        try:
            dp_list = json.loads(dp_raw)
        except:
            dp_list = []
            
        if deployment_point not in dp_list:
            raise ValueError(f"Deployment point '{deployment_point}' is not assigned to this model version's metadata.")
            
        self.client.set_registered_model_alias(name, alias, str(version))
        return True
