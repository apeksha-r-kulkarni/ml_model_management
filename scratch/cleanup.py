import os
import sys
import django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import mlflow
from registry.models import ImportedModel

client = mlflow.MlflowClient()
for rm in client.search_registered_models():
    for mv in client.search_model_versions(f"name='{rm.name}'"):
        client.delete_model_version(name=rm.name, version=mv.version)
    client.delete_registered_model(name=rm.name)

ImportedModel.objects.all().delete()
print("Cleaned up MLflow and DB")
