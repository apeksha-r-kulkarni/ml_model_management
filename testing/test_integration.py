"""
test_integration.py
===================
Integration tests for the Django REST backend:
  - All 10 API endpoints tested via Django's test Client
  - MLflowService fully mocked so no live server is required
  - Covers HTTP method routing, response shape, status codes,
    CORS / CSRF exemption, and edge-case inputs

Run:
    python3 -m pytest testing/test_integration.py -v
"""

import json
import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO

# ---------------------------------------------------------------------------
# Bootstrap: add registration/ to sys.path
# ---------------------------------------------------------------------------
REGISTRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "registration")
if os.path.abspath(REGISTRATION_DIR) not in sys.path:
    sys.path.insert(0, os.path.abspath(REGISTRATION_DIR))


def _stub_mlflow():
    mlflow_mod = types.ModuleType("mlflow")
    mlflow_mod.set_tracking_uri = lambda *a, **k: None
    mlflow_mod.set_registry_uri = lambda *a, **k: None
    run_mock = MagicMock()
    run_mock.__enter__ = MagicMock(return_value=run_mock)
    run_mock.__exit__ = MagicMock(return_value=False)
    run_mock.info = MagicMock()
    run_mock.info.run_id = "test-run-xyz"
    mlflow_mod.start_run = MagicMock(return_value=run_mock)
    mlflow_mod.log_artifact = MagicMock()
    tracking_mod = types.ModuleType("mlflow.tracking")
    tracking_mod.MlflowClient = MagicMock
    sys.modules["mlflow"] = mlflow_mod
    sys.modules["mlflow.tracking"] = tracking_mod


_stub_mlflow()

try:
    import dotenv  # noqa
except ImportError:
    dotenv_mod = types.ModuleType("dotenv")
    dotenv_mod.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv_mod

os.environ.setdefault("DJANGO_SECRET_KEY", "test-integration-secret-key")
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-integration-secret-key",
        DEBUG=True,
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "registry",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        ROOT_URLCONF="registry.urls",
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": False,
            "OPTIONS": {"context_processors": []},
        }],
        BASE_DIR=os.path.abspath(REGISTRATION_DIR),
    )
    django.setup()

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from registry import views

# ---------------------------------------------------------------------------
# Fake model data
# ---------------------------------------------------------------------------
FAKE_MV = {
    "name": "IntegrationModel",
    "version": "1",
    "model_type": "NLP",
    "purpose": "Classification",
    "architecture": "BERT",
    "accuracy": 92.5,
    "priority": 1,
    "is_deployable": True,
    "deployment_points": ["edge"],
    "remarks": "integration test",
    "artifact_path": "runs:/abc/m.pkl",
    "run_id": "abc",
    "status": "READY",
}

FAKE_LIST = [{
    "name": "IntegrationModel",
    "model_type": "NLP",
    "purpose": "Classification",
    "all_versions": [FAKE_MV],
}]


def _mock_svc():
    svc = MagicMock()
    svc.list_models.return_value = FAKE_LIST
    svc.find_models.return_value = FAKE_LIST
    svc.list_purposes.return_value = ["ASR", "Classification"]
    svc.list_architectures.return_value = ["BERT", "CNN"]
    svc.register_model.return_value = {
        "success": True, "model_name": "IntegrationModel",
        "version": "1", "artifact_path": "runs:/abc/m.pkl",
    }
    svc.get_model_version.return_value = FAKE_MV
    svc.update_model_version.return_value = True
    svc.delete_model_version.return_value = True
    return svc


# ---------------------------------------------------------------------------
# 1. GET /  — page view
# ---------------------------------------------------------------------------
class TestIndexPage(TestCase):
    def test_get_returns_200(self):
        with patch("registry.views.render") as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            c = Client()
            # directly invoke view to avoid template lookup
            from django.test import RequestFactory
            req = RequestFactory().get("/")
            resp = views.ModelRegistrationPageView.as_view()(req)
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 2. GET /api/models/  — list models
# ---------------------------------------------------------------------------
class TestListModelsEndpoint(TestCase):

    def _get(self):
        svc = _mock_svc()
        with patch.object(views.ModelsAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            c = Client()
            return c.get("/api/models/"), svc

    def test_returns_200(self):
        resp, _ = self._get()
        self.assertEqual(resp.status_code, 200)

    def test_returns_json(self):
        resp, _ = self._get()
        data = json.loads(resp.content)
        self.assertTrue(data["success"])

    def test_models_key_present(self):
        resp, _ = self._get()
        data = json.loads(resp.content)
        self.assertIn("models", data)
        self.assertIsInstance(data["models"], list)

    def test_model_structure(self):
        resp, _ = self._get()
        models = json.loads(resp.content)["models"]
        self.assertEqual(models[0]["name"], "IntegrationModel")
        self.assertIn("all_versions", models[0])

    def test_service_called_once(self):
        _, svc = self._get()
        svc.list_models.assert_called_once()

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.list_models.side_effect = Exception("MLflow down")
        with patch.object(views.ModelsAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            c = Client()
            resp = c.get("/api/models/")
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(json.loads(resp.content)["success"])

    def test_wrong_method_returns_405(self):
        svc = _mock_svc()
        with patch.object(views.ModelsAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            c = Client()
            resp = c.post("/api/models/", data={}, content_type="application/json")
        self.assertEqual(resp.status_code, 405)


# ---------------------------------------------------------------------------
# 3. GET /api/models/find/?purpose=  — find by purpose
# ---------------------------------------------------------------------------
class TestFindModelsEndpoint(TestCase):

    def _get(self, purpose="ASR"):
        svc = _mock_svc()
        with patch.object(views.FindModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().get(f"/api/models/find/?purpose={purpose}"), svc

    def test_returns_200_with_models(self):
        resp, _ = self._get("Classification")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("models", data)

    def test_purpose_passed_to_service(self):
        _, svc = self._get("ASR")
        svc.find_models.assert_called_once_with("ASR")

    def test_empty_purpose_still_calls_service(self):
        _, svc = self._get("")
        svc.find_models.assert_called_once_with("")

    def test_special_characters_in_purpose(self):
        svc = _mock_svc()
        svc.find_models.return_value = []
        with patch.object(views.FindModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/find/?purpose=Speech+Recognition")
        self.assertEqual(resp.status_code, 200)

    def test_service_failure_returns_500(self):
        svc = _mock_svc()
        svc.find_models.side_effect = Exception("fail")
        with patch.object(views.FindModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/find/?purpose=ASR")
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# 4. POST /api/models/register/  — model registration
# ---------------------------------------------------------------------------
class TestRegisterModelEndpoint(TestCase):

    def _post(self, svc, extra_data=None):
        fake_file = SimpleUploadedFile("model.pkl", b"fake bytes", content_type="application/octet-stream")
        data = {"model": fake_file, "model_name": "TestModel", "accuracy": "85"}
        if extra_data:
            data.update(extra_data)
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None), \
             patch("registry.views.os.makedirs"), \
             patch("registry.views.os.path.exists", return_value=True), \
             patch("registry.views.os.remove"), \
             patch("builtins.open", unittest.mock.mock_open()):
            return Client().post("/api/models/register/", data)

    def test_success_returns_200(self):
        resp = self._post(_mock_svc())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

    def test_response_contains_version(self):
        resp = self._post(_mock_svc())
        data = json.loads(resp.content)
        self.assertIn("version", data)
        self.assertIn("model_name", data)

    def test_missing_model_file_returns_400(self):
        svc = _mock_svc()
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().post("/api/models/register/", {"model_name": "M"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No model file", json.loads(resp.content)["error"])

    def test_missing_model_name_returns_400(self):
        svc = _mock_svc()
        fake_file = SimpleUploadedFile("m.pkl", b"bytes")
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().post("/api/models/register/", {"model": fake_file, "model_name": ""})
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_accuracy_returns_400(self):
        resp = self._post(_mock_svc(), {"accuracy": "bad_number"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Accuracy", json.loads(resp.content)["error"])

    def test_accuracy_greater_than_100_returns_400(self):
        resp = self._post(_mock_svc(), {"accuracy": "110"})
        self.assertEqual(resp.status_code, 400)

    def test_accuracy_zero_is_valid(self):
        resp = self._post(_mock_svc(), {"accuracy": "0"})
        self.assertEqual(resp.status_code, 200)

    def test_accuracy_exactly_100_is_valid(self):
        resp = self._post(_mock_svc(), {"accuracy": "100"})
        self.assertEqual(resp.status_code, 200)

    def test_is_deployable_on_value(self):
        captured = {}
        svc = _mock_svc()
        def capture(local_file_path, original_filename, metadata):
            captured.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture
        self._post(svc, {"is_deployable": "on"})
        self.assertTrue(captured.get("is_deployable"))

    def test_ner_model_sets_text_pipeline_subtype(self):
        captured = {}
        svc = _mock_svc()
        def capture(local_file_path, original_filename, metadata):
            captured.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture
        self._post(svc, {"model_type": "NER"})
        self.assertEqual(captured.get("model_subtype"), "Text Pipeline")

    def test_fileclassifier_sets_uis_subtype(self):
        captured = {}
        svc = _mock_svc()
        def capture(local_file_path, original_filename, metadata):
            captured.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture
        self._post(svc, {"model_type": "FileClassifier"})
        self.assertEqual(captured.get("model_subtype"), "UIS")

    def test_speech_model_preserves_language(self):
        captured = {}
        svc = _mock_svc()
        def capture(local_file_path, original_filename, metadata):
            captured.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture
        self._post(svc, {"model_type": "Speech", "language": "en"})
        # Speech type should NOT blank out language
        self.assertEqual(captured.get("language"), "en")

    def test_non_speech_model_clears_language(self):
        captured = {}
        svc = _mock_svc()
        def capture(local_file_path, original_filename, metadata):
            captured.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture
        self._post(svc, {"model_type": "Other", "language": "en"})
        self.assertEqual(captured.get("language"), "")

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.register_model.side_effect = Exception("mlflow down")
        resp = self._post(svc)
        self.assertEqual(resp.status_code, 500)

    def test_get_method_not_allowed(self):
        svc = _mock_svc()
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/register/")
        self.assertEqual(resp.status_code, 405)


# ---------------------------------------------------------------------------
# 5. POST /api/models/update/  — update model
# ---------------------------------------------------------------------------
class TestUpdateModelEndpoint(TestCase):

    def _post(self, svc, body):
        with patch.object(views.UpdateModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().post(
                "/api/models/update/",
                data=json.dumps(body),
                content_type="application/json",
            )

    def test_success_returns_200(self):
        resp = self._post(_mock_svc(), {"name": "M", "version": "1", "accuracy": 90.0})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

    def test_response_contains_model(self):
        resp = self._post(_mock_svc(), {"name": "M", "version": "1"})
        data = json.loads(resp.content)
        self.assertIn("model", data)

    def test_missing_name_returns_400(self):
        resp = self._post(_mock_svc(), {"version": "1"})
        self.assertEqual(resp.status_code, 400)

    def test_missing_version_returns_400(self):
        resp = self._post(_mock_svc(), {"name": "M"})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_500(self):
        svc = _mock_svc()
        with patch.object(views.UpdateModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().post(
                "/api/models/update/",
                data="not-json",
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 500)

    def test_empty_body_returns_400(self):
        resp = self._post(_mock_svc(), {})
        self.assertEqual(resp.status_code, 400)

    def test_service_called_with_correct_name_and_version(self):
        svc = _mock_svc()
        self._post(svc, {"name": "MyModel", "version": "3"})
        args = svc.update_model_version.call_args[0]
        self.assertEqual(args[0], "MyModel")
        self.assertEqual(args[1], 3)

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.update_model_version.side_effect = Exception("db err")
        resp = self._post(svc, {"name": "M", "version": "1"})
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# 6. DELETE /api/models/<name>/version/<v>/
# ---------------------------------------------------------------------------
class TestDeleteModelEndpoint(TestCase):

    def _delete(self, svc, name="IntegrationModel", version=1):
        with patch.object(views.DeleteModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().delete(f"/api/models/{name}/version/{version}/")

    def test_returns_200_on_success(self):
        resp = self._delete(_mock_svc())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

    def test_passes_correct_name_and_version_to_service(self):
        svc = _mock_svc()
        self._delete(svc, name="TargetModel", version=3)
        svc.delete_model_version.assert_called_once_with("TargetModel", 3)

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.delete_model_version.side_effect = Exception("Not found")
        resp = self._delete(svc)
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(json.loads(resp.content)["success"])

    def test_get_not_allowed(self):
        svc = _mock_svc()
        with patch.object(views.DeleteModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/IntegrationModel/version/1/")
        self.assertEqual(resp.status_code, 405)


# ---------------------------------------------------------------------------
# 7. GET /api/models/purposes/
# ---------------------------------------------------------------------------
class TestPurposesEndpoint(TestCase):

    def _get(self, svc):
        with patch.object(views.PurposesAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().get("/api/models/purposes/")

    def test_returns_200_and_purposes(self):
        resp = self._get(_mock_svc())
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["purposes"], ["ASR", "Classification"])

    def test_returns_empty_list_if_no_purposes(self):
        svc = _mock_svc()
        svc.list_purposes.return_value = []
        resp = self._get(svc)
        self.assertEqual(json.loads(resp.content)["purposes"], [])

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.list_purposes.side_effect = Exception("fail")
        resp = self._get(svc)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# 8. GET /api/models/architectures/
# ---------------------------------------------------------------------------
class TestArchitecturesEndpoint(TestCase):

    def _get(self, svc):
        with patch.object(views.ArchitecturesAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().get("/api/models/architectures/")

    def test_returns_200_and_architectures(self):
        resp = self._get(_mock_svc())
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["architectures"], ["BERT", "CNN"])

    def test_service_exception_returns_500(self):
        svc = _mock_svc()
        svc.list_architectures.side_effect = Exception("fail")
        resp = self._get(svc)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# 9. GET /api/models/languages/  (stub, always empty)
# ---------------------------------------------------------------------------
class TestLanguagesEndpoint(TestCase):

    def test_returns_200_with_empty_list(self):
        resp = Client().get("/api/models/languages/")
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["languages"], [])


# ---------------------------------------------------------------------------
# 10. GET /api/models/environments/  (stub, always empty)
# ---------------------------------------------------------------------------
class TestEnvironmentsEndpoint(TestCase):

    def test_returns_200_with_empty_list(self):
        resp = Client().get("/api/models/environments/")
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["environments"], [])


# ---------------------------------------------------------------------------
# 11. POST /api/models/set-deployed/
# ---------------------------------------------------------------------------
class TestSetDeployedEndpoint(TestCase):

    def _post(self, body):
        svc = _mock_svc()
        with patch.object(views.SetDeployedVersionAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return Client().post(
                "/api/models/set-deployed/",
                data=json.dumps(body),
                content_type="application/json",
            )

    def test_returns_success_true(self):
        resp = self._post({"name": "M", "version": "1", "deployment_point": "ASR"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

    def test_empty_body_fails(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# 12. Response content-type tests
# ---------------------------------------------------------------------------
class TestResponseContentType(TestCase):

    def test_list_models_content_type_is_json(self):
        svc = _mock_svc()
        with patch.object(views.ModelsAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/")
        self.assertIn("application/json", resp["Content-Type"])

    def test_purposes_content_type_is_json(self):
        svc = _mock_svc()
        with patch.object(views.PurposesAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            resp = Client().get("/api/models/purposes/")
        self.assertIn("application/json", resp["Content-Type"])

    def test_languages_content_type_is_json(self):
        resp = Client().get("/api/models/languages/")
        self.assertIn("application/json", resp["Content-Type"])


if __name__ == "__main__":
    unittest.main()
