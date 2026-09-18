import os

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .manager import MLManager, ModelRegistrationError


def register_page(request):
    """Render the model registration page."""
    return render(request, "register.html")


@csrf_exempt
@require_http_methods(["POST"])
def register_model(request):
    """
    POST /api/models/register/

    Accepts multipart/form-data with:
        model_name  (str)  — name to register the model under in MLflow
        model       (file) — a .pkl file produced by joblib/sklearn

    Returns JSON on success or failure.

    ⚠️  SECURITY NOTE:
    Joblib/pickle files can execute arbitrary Python code when deserialized.
    Only accept .pkl files from trusted sources. This endpoint must NOT be
    exposed to the public internet without additional authentication.
    """

    # ── 1. Input validation (before any file I/O) ────────────────────────────

    model_file = request.FILES.get("model")
    model_name = request.POST.get("model_name", "").strip()
    model_type = request.POST.get("model_type", "").strip()
    architecture = request.POST.get("architecture", "").strip()
    
    accuracy_str = request.POST.get("accuracy", "").strip()
    priority_str = request.POST.get("priority", "").strip()
    
    # Checkbox gives "on" or "true" if checked
    is_deployable = request.POST.get("is_deployable", "").lower() in ["on", "true", "1", "yes"]
    
    # Multiselect might come as multiple values or a single list string depending on JS
    deployment_points = request.POST.getlist("deployment_points")
    if not deployment_points:
        dp_single = request.POST.get("deployment_points", "")
        if dp_single:
            import json
            try:
                deployment_points = json.loads(dp_single)
            except:
                deployment_points = [dp_single]

    remarks = request.POST.get("remarks", "").strip()
    versioning = request.POST.get("versioning", "").strip()

    if not model_file:
        return JsonResponse({"success": False, "error": "No model file uploaded."}, status=400)
    if not model_name:
        return JsonResponse({"success": False, "error": "Model name is required."}, status=400)
    if not model_type:
        return JsonResponse({"success": False, "error": "Model type is required."}, status=400)
    if not accuracy_str:
        return JsonResponse({"success": False, "error": "Accuracy is required."}, status=400)
    if not deployment_points:
        return JsonResponse({"success": False, "error": "Deployment points are required."}, status=400)
    if not versioning:
        return JsonResponse({"success": False, "error": "Versioning is required."}, status=400)

    try:
        accuracy = float(accuracy_str)
        if accuracy < 0 or accuracy > 100:
            return JsonResponse({
                "success": False,
                "error": "Accuracy must be between 0 and 100."
            }, status=400)
    except ValueError:
        return JsonResponse({"success": False, "error": "Accuracy must be a number."}, status=400)
        
    priority = None
    if priority_str:
        try:
            priority = int(priority_str)
        except ValueError:
            return JsonResponse({"success": False, "error": "Priority must be an integer."}, status=400)

    if not (model_file.name.lower().endswith(".pt") or model_file.name.lower().endswith(".onnx")):
        return JsonResponse(
            {"success": False, "error": "Only .pt and .onnx files are supported."},
            status=400,
        )

    # ── 2. Write upload to a secure temp file (not the project root) ─────────
    from .utils import save_upload_to_temp

    try:
        with save_upload_to_temp(model_file) as tmp_path:
            # ── 3. Call the business logic service ────────────────────────────────
            try:
                from .manager import ModelUploadData
                upload_data = ModelUploadData(
                    file_path=tmp_path,
                    model_name=model_name,
                    original_filename=model_file.name,
                    file_size=model_file.size,
                    model_type=model_type,
                    architecture=architecture,
                    accuracy=accuracy,
                    priority=priority,
                    deployment_points=deployment_points,
                    remarks=remarks,
                    is_deployable=is_deployable,
                    versioning=versioning
                )
                result_data = MLManager.register_new_model(upload_data)
            except ModelRegistrationError as err:
                return JsonResponse(
                    {"success": False, "error": str(err)},
                    status=422 if "Could not load" in str(err) else 502,
                )

            # ── 4. Return success ─────────────────────────────────────────────────
            return JsonResponse(
                {
                    "success": True,
                    "message": "Model registered successfully.",
                    **result_data,
                }
            )
    except OSError as io_err:
        return JsonResponse(
            {"success": False, "error": f"Could not save uploaded file: {io_err}"},
            status=500,
        )
    except Exception as unexpected_err:
        # Safety net: guarantee JSON is always returned, never an HTML 500 page.
        return JsonResponse(
            {"success": False, "error": f"Unexpected server error: {unexpected_err}"},
            status=500,
        )


@require_http_methods(["GET"])
def list_models(request):
    """
    GET /api/models/

    Returns a JSON list of all models registered in the MLflow Model Registry.
    """
    try:
        models = MLManager.get_registry_summary()
    except ModelRegistrationError as err:
        return JsonResponse(
            {"success": False, "error": str(err)},
            status=502,
        )
    except Exception as unexpected_err:
        # Safety net: guarantee JSON is always returned, never an HTML 500 page.
        return JsonResponse(
            {"success": False, "error": f"Unexpected server error: {unexpected_err}"},
            status=500,
        )

    return JsonResponse({"success": True, "models": models})

@csrf_exempt
@require_http_methods(["GET", "POST"])
def architectures_api(request):
    from . import db_repository
    import json
    
    if request.method == "GET":
        archs = db_repository.get_all_architectures()
        return JsonResponse({"success": True, "architectures": archs})
        
    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            name = body.get("name", "").strip()
            if not name:
                return JsonResponse({"success": False, "error": "Name is required"}, status=400)
            arch = db_repository.get_or_create_architecture(name=name)
            return JsonResponse({"success": True, "architecture": {"id": arch.id, "name": arch.name}})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
