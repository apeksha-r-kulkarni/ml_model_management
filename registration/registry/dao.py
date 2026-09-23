from .models import LogicalModel, ModelVersion
from .data_objects import Model
from typing import List, Optional

class ModelDAO:
    """DAO for interacting with PostgreSQL via Django ORM."""
    
    def connect(self):
        # Connection managed by Django ORM
        pass
        
    def disconnect(self):
        # Connection managed by Django ORM
        pass
        
    def _map_to_data_object(self, db_logical: LogicalModel, db_version: ModelVersion) -> Model:
        return Model(
            id=db_version.id,
            name=db_logical.name,
            model_type=db_logical.model_type,
            version=db_version.version_number,
            purpose=db_logical.purpose,
            architecture=db_version.architecture,
            accuracy=db_version.accuracy,
            priority=db_version.priority,
            is_deployable=db_version.is_deployable,
            status=db_version.status,
            modelArtifactPath=db_version.model_artifact_path
        )

    def getModel(self, name: str, version: int) -> Optional[Model]:
        try:
            db_version = ModelVersion.objects.select_related('logical_model').get(
                logical_model__name=name, version_number=version
            )
            return self._map_to_data_object(db_version.logical_model, db_version)
        except ModelVersion.DoesNotExist:
            return None

    def getModelById(self, model_id: int) -> Optional[Model]:
        try:
            db_version = ModelVersion.objects.select_related('logical_model').get(id=model_id)
            return self._map_to_data_object(db_version.logical_model, db_version)
        except ModelVersion.DoesNotExist:
            return None

    def getLatestVersion(self, name: str) -> int:
        from django.db.models import Max
        res = ModelVersion.objects.filter(logical_model__name=name).aggregate(Max('version_number'))
        return res['version_number__max'] or 0

    def getUniquePurposes(self) -> List[str]:
        return list(LogicalModel.objects.exclude(purpose="").values_list('purpose', flat=True).distinct())

    def getModelList(self, use_case: Optional[str] = None) -> List[Model]:
        qs = ModelVersion.objects.select_related('logical_model').all()
        if use_case:
            use_case = use_case.strip()
            qs = qs.filter(logical_model__purpose__iexact=use_case)
            
        return [self._map_to_data_object(v.logical_model, v) for v in qs]

    def storeModel(self, model: Model, original_filename: str, file_format: str, file_size: int, run_id: str):
        logical, created = LogicalModel.objects.get_or_create(
            name=model.name,
            defaults={
                'model_type': model.model_type,
                'mlflow_name': model.name,
                'purpose': model.purpose
            }
        )
        
        db_version = ModelVersion.objects.create(
            logical_model=logical,
            version_number=model.version,
            architecture=model.architecture,
            accuracy=model.accuracy,
            priority=model.priority,
            is_deployable=model.is_deployable,
            model_artifact_path=model.modelArtifactPath,
            original_filename=original_filename,
            file_format=file_format,
            file_size=file_size,
            run_id=run_id,
            status=model.status
        )
        model.id = db_version.id
        return model

    def updateModel(self, model: Model):
        try:
            db_version = ModelVersion.objects.select_related('logical_model').get(id=model.id)
            db_version.architecture = model.architecture
            db_version.accuracy = model.accuracy
            db_version.priority = model.priority
            db_version.is_deployable = model.is_deployable
            db_version.status = model.status
            db_version.model_artifact_path = model.modelArtifactPath
            db_version.save()
            
            # update logical
            db_version.logical_model.purpose = model.purpose
            db_version.logical_model.save()
            return True
        except ModelVersion.DoesNotExist:
            return False

    def deleteModel(self, name: str, version: int) -> bool:
        try:
            db_version = ModelVersion.objects.get(logical_model__name=name, version_number=version)
            lm = db_version.logical_model
            db_version.delete()
            if lm.versions.count() == 0:
                lm.delete()
            return True
        except ModelVersion.DoesNotExist:
            return False
