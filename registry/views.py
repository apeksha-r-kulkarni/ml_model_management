import os
import tempfile
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .services import MLflowService

class ModelRegistrationPageView(View):
    """Render the main UI page."""
    def get(self, request):
        return render(request, "index.html")

@method_decorator(csrf_exempt, name='dispatch')
class ModelRegistrationAPIView(View):
    """API for registering models."""
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
            
        ext = model_file.name.lower().split('.')[-1]
        if ext not in ["pt", "onnx"]:
            return JsonResponse({"success": False, "error": "Only .pt and .onnx files are supported."}, status=400)

        try:
            model_type = request.POST.get('model_type', 'Unknown').strip()
            
            try:
                accuracy = float(request.POST.get('accuracy', 0.0))
                if accuracy < 0 or accuracy > 100:
                    return JsonResponse({"success": False, "error": "Accuracy must be between 0 and 100."}, status=400)
            except ValueError:
                return JsonResponse({"success": False, "error": "Accuracy must be a number."}, status=400)

            architecture = request.POST.get('architecture', '').strip()
            priority_str = request.POST.get('priority', '').strip()
            priority = int(priority_str) if priority_str.isdigit() else None
            
            is_deployable_val = request.POST.get('is_deployable', '').lower()
            is_deployable = is_deployable_val in ['true', 'on', '1']
            
            versioning = request.POST.get('versioning', 'Auto-increment').strip()
            remarks = request.POST.get('remarks', '').strip()
            deployment_points = request.POST.getlist('deployment_points')

            # Save uploaded file temporarily
            temp_dir = os.path.join(settings.BASE_DIR, 'scratch')
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, model_file.name)
            
            with open(file_path, 'wb+') as destination:
                for chunk in model_file.chunks():
                    destination.write(chunk)

            try:
                result = self.service.register_model(
                    file_path=file_path,
                    original_filename=model_file.name,
                    model_name=model_name,
                    model_type=model_type,
                    accuracy=accuracy,
                    file_size=model_file.size,
                    architecture=architecture,
                    priority=priority,
                    is_deployable=is_deployable,
                    versioning=versioning,
                    deployment_points=deployment_points,
                    remarks=remarks
                )
                return JsonResponse({"success": True, "message": "Model registered successfully.", **result})
            except Exception as e:
                return JsonResponse({"success": False, "error": str(e)}, status=500)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ArchitecturesAPIView(View):
    """API for listing unique architectures."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        try:
            archs = self.service.list_architectures()
            return JsonResponse({"success": True, "architectures": archs})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

class ModelsAPIView(View):
    """API for listing registered models."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def get(self, request):
        try:
            models = self.service.list_models()
            return JsonResponse({"success": True, "models": models})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteModelAPIView(View):
    """API for deleting a model version."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MLflowService()

    def delete(self, request, mlflow_name, version):
        try:
            db_id = None
            if request.body:
                try:
                    body = json.loads(request.body)
                    db_id = body.get("db_id")
                except:
                    pass
                    
            self.service.delete_model_version(mlflow_name, version, db_id=db_id)
            return JsonResponse({"success": True, "message": f"Deleted {mlflow_name} v{version} successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
