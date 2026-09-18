from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class TimeStampedModel(models.Model):
    """
    Abstract base class following Pattern 1 from OOP Extensibility Guide.
    Provides standard timestamp fields for inherited models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Architecture(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ImportedModel(TimeStampedModel):
    """
    Tracks metadata of uploaded models in the database.
    Note: The actual file is strictly stored in MLflow, not locally,
    per user requirements.
    """
    original_filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=20)
    file_size = models.PositiveBigIntegerField()
    file_hash = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=50, default="PENDING")
    
    # User Metadata fields
    model_type = models.CharField(max_length=100, default="Unknown")
    architecture = models.ForeignKey(Architecture, on_delete=models.SET_NULL, null=True, blank=True)
    accuracy = models.FloatField(
    default=0.0,
    validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
)
    priority = models.IntegerField(null=True, blank=True)
    deployment_points = models.JSONField(default=list)
    remarks = models.TextField(null=True, blank=True)
    is_deployable = models.BooleanField(default=False)
    versioning = models.CharField(max_length=50, default="Auto-increment")
    
    # MLflow integration fields
    mlflow_name = models.CharField(max_length=255, null=True, blank=True)
    mlflow_version = models.IntegerField(null=True, blank=True)
    run_id = models.CharField(max_length=255, null=True, blank=True)
    model_uri = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.original_filename} ({self.status})"
