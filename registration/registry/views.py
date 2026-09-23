import os
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .manager import ModelManager
from .data_objects import Model
def get_manager():
    return ModelManager()

def register_page(request):
    """Render the main UI page."""
    return render(request, "index.html")

@csrf_exempt
@require_http_methods(["POST"])
def register_model(request):
    model_file = request.FILES.get("model")
    model_name = request.POST.get("model_name", "").strip()
    
    if not model_file:
        return JsonResponse({"success": False, "error": "No model file uploaded."}, status=400)
    if not model_name:
        return JsonResponse({"success": False, "error": "Model name is required."}, status=400)
        
    try:
        model_type = request.POST.get('model_type', 'Unknown').strip()
        accuracy = float(request.POST.get('accuracy', 0.0))
        architecture = request.POST.get('architecture', '').strip()
        priority_str = request.POST.get('priority', '').strip()
        priority = int(priority_str) if priority_str.isdigit() else None
        is_deployable = request.POST.get('is_deployable', '').lower() in ['true', 'on', '1']
        purpose = request.POST.get('purpose', '').strip()
        
        temp_dir = os.path.join(settings.BASE_DIR, 'scratch')
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, model_file.name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in model_file.chunks():
                destination.write(chunk)

        try:
            model_data = Model(
                name=model_name,
                model_type=model_type,
                purpose=purpose,
                architecture=architecture,
                accuracy=accuracy,
                priority=priority,
                is_deployable=is_deployable
            )
            # Simulated current user
            user = "authorized_user"
            result = get_manager().registerModel(
                file_path=file_path,
                original_filename=model_file.name,
                user=user,
                model=model_data
            )
            return JsonResponse(result)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@require_http_methods(["GET"])
def list_models(request):
    try:
        models = get_manager().listModels()
        data = [m.__dict__ for m in models]
        return JsonResponse({"success": True, "models": data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@require_http_methods(["GET"])
def find_model(request):
    purpose = request.GET.get('purpose', '')
    try:
        models = get_manager().findModel(purpose)
        data = [m.__dict__ for m in models]
        return JsonResponse({"success": True, "models": data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@require_http_methods(["GET"])
def list_purposes(request):
    try:
        purposes = get_manager().getPurposes()
        return JsonResponse({"success": True, "purposes": purposes})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_model(request):
    try:
        data = json.loads(request.body)
        user = "authorized_user"
        model_id = data.pop('id', None)
        if not model_id:
            return JsonResponse({"success": False, "error": "Model ID is required for update."}, status=400)
            
        updated_model = get_manager().updateModel(user, model_id, data)
        return JsonResponse({"success": True, "model": updated_model.__dict__})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_model(request, mlflow_name, version):
    try:
        user = "authorized_user"
        success = get_manager().deleteModel(user, mlflow_name, int(version))
        return JsonResponse({"success": success})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
