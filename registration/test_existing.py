import os
import django
os.environ['DJANGO_SECRET_KEY'] = 'dummy_secret_key'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from registry.services import MLflowService

service = MLflowService()

with open("dummy_model_existing.pt", "w") as f: f.write("existing_model_data")

try:
    print("Registering new version for EntityRecognitionModel...")
    res = service.register_model("dummy_model_existing.pt", "dummy_model_existing.pt", {"model_name": "EntityRecognitionModel"})
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()

