import os
import json
import uuid
import shutil
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .services import ModelManager, ModelDAO, MLflowAdapter, MinIOAdapter

def get_model_manager():
    registry_adapter = MLflowAdapter()
    storage_adapter = MinIOAdapter()
    dao = ModelDAO(registry_adapter, storage_adapter)
    return ModelManager(dao)

class ModelRegistrationPageView(View):
    def get(self, request):
        return render(request, "index.html")

@method_decorator(csrf_exempt, name='dispatch')
class ModelRegistrationAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def post(self, request):
        model_files = request.FILES.getlist("model_files")
        model_paths = request.POST.getlist("model_paths")
        model_name = request.POST.get("model_name", "").strip()
        
        if not model_files:
            return JsonResponse({"success": False, "error": "No model files uploaded."}, status=400)
        if not model_name:
            return JsonResponse({"success": False, "error": "Model name is required."}, status=400)
            
        try:
            metadata = {
                "model_name": model_name,
                "model_type": request.POST.get("model_type"),
                "architecture": request.POST.get("architecture"),
                "accuracy": request.POST.get("accuracy"),
                "priority": request.POST.get("priority"),
                "is_deployable": request.POST.get("is_deployable") == 'true',
                "remarks": request.POST.get("remarks"),
                "deployment_points": request.POST.getlist("deployment_points")
            }

            upload_id = str(uuid.uuid4())
            upload_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads", upload_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            try:
                if len(model_files) == 1 and (not model_paths or '/' not in model_paths[0]):
                    f = model_files[0]
                    file_path = os.path.join(upload_dir, f.name)
                    with open(file_path, 'wb+') as dest:
                        for chunk in f.chunks():
                            dest.write(chunk)
                else:
                    for idx, f in enumerate(model_files):
                        rel_path = model_paths[idx] if idx < len(model_paths) else f.name
                        file_path = os.path.join(upload_dir, rel_path)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'wb+') as dest:
                            for chunk in f.chunks():
                                dest.write(chunk)
                                
                result = self.service.register_model_folder(upload_dir, metadata)
                return JsonResponse(result)
            finally:
                if os.path.exists(upload_dir):
                    shutil.rmtree(upload_dir, ignore_errors=True)
                    
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ModelsAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def get(self, request):
        try:
            models = self.service.list_models()
            return JsonResponse({"success": True, "models": models})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class FindModelAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

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
        self.service = get_model_manager()

    def post(self, request):
        return self.put(request)

    def put(self, request):
        try:
            data = json.loads(request.body)
            model_name = data.get("name")
            version = data.get("version")
            
            if not model_name or not version:
                return JsonResponse({"success": False, "error": "Model name and version required"}, status=400)
                
            update_data = {
                k: v for k, v in data.items() 
                if k not in ["name", "version", "id"]
            }
            
            self.service.update_model_version(model_name, version, update_data)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteModelAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def delete(self, request, mlflow_name, version):
        try:
            self.service.delete_model_version(mlflow_name, version)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SetDeployedVersionAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def post(self, request):
        try:
            data = json.loads(request.body)
            name = data.get("name")
            version = data.get("version")
            deployment_point = data.get("deployment_point")
            
            if not all([name, version, deployment_point]):
                return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)
                
            self.service.set_deployed_version(name, version, deployment_point)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class PurposesAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def get(self, request):
        try:
            purposes = self.service.list_purposes()
            return JsonResponse({"success": True, "purposes": purposes})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ArchitecturesAPIView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = get_model_manager()

    def get(self, request):
        try:
            architectures = self.service.list_architectures()
            return JsonResponse({"success": True, "architectures": architectures})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class LanguagesAPIView(View):
    def get(self, request):
        return JsonResponse({"success": True, "languages": []})

class EnvironmentsAPIView(View):
    def get(self, request):
        return JsonResponse({"success": True, "environments": []})
