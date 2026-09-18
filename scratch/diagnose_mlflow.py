import os
import django
import sys
import mlflow
from mlflow.tracking import MlflowClient

# Setup Django env
sys.path.append('/home/apeksha-ssi021/Shyena/ml_model_management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def diagnose():
    print("--- 1. Checking MLflow URIs ---")
    print(f"Django mlflow.get_tracking_uri(): {mlflow.get_tracking_uri()}")
    print(f"Django mlflow.get_registry_uri(): {mlflow.get_registry_uri()}")
    
    print("\n--- 2. Checking existing models in MLflow ---")
    client = MlflowClient()
    try:
        models = client.search_registered_models()
        for m in models:
            versions = client.search_model_versions(f"name='{m.name}'")
            print(f"Model: {m.name} | Versions: {[v.version for v in versions]}")
    except Exception as e:
        print(f"Error querying MLflow: {e}")

diagnose()
