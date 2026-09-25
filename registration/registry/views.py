import os
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .services import MLflowService

class ModelRegistrationPageView(View):
    def get(self, request):
        return render(request, "index.html")

@method_decorator(csrf_exempt, name='dispatch')
class ModelRegistrationAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def post(self, request):
        model_file = request.FILES.get("model")
        model_name = request.POST.get("model_name", "").strip()
        
        if not model_file:
            return JsonResponse({"success": False, "error": "No model file uploaded."}, status=400)
        if not model_name:
            return JsonResponse({"success": False, "error": "Model name is required."}, status=400)
            
        try:
            # Gather metadata
            metadata = {
                "model_name": model_name,
                "model_type": request.POST.get('model_type', 'Unknown').strip(),
                "architecture": request.POST.get('architecture', '').strip(),
                "model_subtype": request.POST.get('model_subtype', '').strip(),
                "language": request.POST.get('language', '').strip(),
                "environment": request.POST.get('environment', '').strip(),
                "priority": int(request.POST.get('priority', '').strip()) if request.POST.get('priority', '').strip().isdigit() else None,
                "is_deployable": request.POST.get('is_deployable', '').lower() in ['true', 'on', '1'],
                "purpose": request.POST.get('purpose', '').strip(),
                "deployment_points": request.POST.getlist('deployment_points'),
                "remarks": request.POST.get('remarks', '').strip()
            }
            
            # Accuracy
            accuracy_str = request.POST.get('accuracy', '').strip()
            try:
                metadata["accuracy"] = float(accuracy_str) if accuracy_str else 0.0
            except ValueError:
                return JsonResponse({"success": False, "error": "Accuracy must be a valid number."}, status=400)
                
            if metadata["accuracy"] < 0.0 or metadata["accuracy"] > 100.0:
                return JsonResponse({"success": False, "error": "Accuracy must be between 0 and 100."}, status=400)

            # Automatic subtype logic from old code (can be moved to service later, keeping here for now)
            if metadata["model_type"] == "NER":
                metadata["model_subtype"] = "Text Pipeline"
                metadata["language"] = ""
                metadata["environment"] = ""
            elif metadata["model_type"] == "FileClassifier":
                metadata["model_subtype"] = "UIS"
                metadata["language"] = ""
                metadata["environment"] = ""
            elif metadata["model_type"] != "Speech":
                metadata["language"] = ""
                metadata["environment"] = ""

            # Temporarily save file to disk
            temp_dir = os.path.join(settings.BASE_DIR, 'scratch')
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, model_file.name)
            
            with open(file_path, 'wb+') as destination:
                for chunk in model_file.chunks():
                    destination.write(chunk)

            try:
                # Delegate to MLflowService
                result = self.service.register_model(
                    local_file_path=file_path,
                    original_filename=model_file.name,
                    metadata=metadata
                )
                return JsonResponse(result)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ModelsAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        try:
            models = self.service.list_models()
            return JsonResponse({"success": True, "models": models})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class FindModelAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        purpose = request.GET.get('purpose', '')
        try:
            models = self.service.find_models(purpose)
            return JsonResponse({"success": True, "models": models})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateModelAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def post(self, request):
        return self.put(request)

    def put(self, request):
        try:
            data = json.loads(request.body)
            # Find the ID logic: frontend currently sends 'id' which might be DB ID.
            # Wait, if we removed DB ID, the frontend might be sending name and version.
            # We need name and version to update via MLflow.
            name = data.get("name")
            version = data.get("version")
            if not name or not version:
                return JsonResponse({"success": False, "error": "Model name and version are required for update."}, status=400)
                
            self.service.update_model_version(name, int(version), data)
            updated_model = self.service.get_model_version(name, int(version))
            return JsonResponse({"success": True, "model": updated_model})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteModelAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def delete(self, request, mlflow_name, version):
        try:
            success = self.service.delete_model_version(mlflow_name, int(version))
            return JsonResponse({"success": success})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class PurposesAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        try:
            purposes = self.service.list_purposes()
            return JsonResponse({"success": True, "purposes": purposes})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ArchitecturesAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        try:
            architectures = self.service.list_architectures()
            return JsonResponse({"success": True, "architectures": architectures})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

# Stubs for deprecated/missing endpoints that might be called
class LanguagesAPIView(View):
    def get(self, request):
        return JsonResponse({"success": True, "languages": []})

class EnvironmentsAPIView(View):
    def get(self, request):
        return JsonResponse({"success": True, "environments": []})

@method_decorator(csrf_exempt, name='dispatch')
class SetDeployedVersionAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()
        
    def post(self, request):
        # Could use MLflow alias "champion" in the future
        return JsonResponse({"success": True})
