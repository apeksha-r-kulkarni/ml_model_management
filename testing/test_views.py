"""
test_views.py
=============
Unit tests for all Django API views in registry/views.py:
  - ModelRegistrationPageView
  - ModelRegistrationAPIView
  - ModelsAPIView
  - FindModelAPIView
  - UpdateModelAPIView
  - DeleteModelAPIView
  - PurposesAPIView
  - ArchitecturesAPIView
  - LanguagesAPIView
  - EnvironmentsAPIView
  - SetDeployedVersionAPIView

Uses Django's test client with the MLflowService fully mocked so no live
MLflow server or database is required.

Run:
    python -m pytest testing/test_views.py -v          (from ml_model_management/)
    or from registration/:
    python -m pytest ../testing/test_views.py -v
"""

import json
import sys
import os
import types
from io import BytesIO
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap paths
# ---------------------------------------------------------------------------
REGISTRATION_DIR = os.path.join(
    os.path.dirname(__file__), "..", "registration"
)
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

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-views")
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")

# ---------------------------------------------------------------------------
# Django setup
# ---------------------------------------------------------------------------
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key-views",
        DEBUG=True,
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "registry",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        ROOT_URLCONF="registry.urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": False,
                "OPTIONS": {"context_processors": []},
            }
        ],
        BASE_DIR=os.path.abspath(REGISTRATION_DIR),
    )
    django.setup()

import unittest
from django.test import TestCase, RequestFactory
from django.urls import reverse

from registry import views  # noqa: E402

# ---------------------------------------------------------------------------
# Shared mock model data
# ---------------------------------------------------------------------------

FAKE_MODEL = {
    "name": "TestModel",
    "version": "1",
    "model_type": "NLP",
    "purpose": "Classification",
    "architecture": "BERT",
    "accuracy": 90.0,
    "priority": 1,
    "is_deployable": True,
    "deployment_points": ["edge"],
    "remarks": "ok",
    "artifact_path": "runs:/abc/m.pkl",
    "run_id": "abc",
    "status": "READY",
}

FAKE_MODELS_LIST = [
    {
        "name": "TestModel",
        "model_type": "NLP",
        "purpose": "Classification",
        "all_versions": [FAKE_MODEL],
    }
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mock_service():
    """Return a MagicMock that mimics MLflowService."""
    svc = MagicMock()
    svc.list_models.return_value = FAKE_MODELS_LIST
    svc.find_models.return_value = FAKE_MODELS_LIST
    svc.list_purposes.return_value = ["ASR", "Classification"]
    svc.list_architectures.return_value = ["BERT", "CNN"]
    svc.register_model.return_value = {
        "success": True,
        "model_name": "TestModel",
        "version": "1",
        "artifact_path": "runs:/abc/m.pkl",
    }
    svc.get_model_version.return_value = FAKE_MODEL
    svc.update_model_version.return_value = True
    svc.delete_model_version.return_value = True
    return svc


# ---------------------------------------------------------------------------
# Test: ModelRegistrationPageView
# ---------------------------------------------------------------------------

class TestModelRegistrationPageView(TestCase):

    def test_get_returns_200(self):
        """GET / should render the index page successfully."""
        factory = RequestFactory()
        req = factory.get("/")

        # Patch render so template resolution is skipped
        with patch("registry.views.render") as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            view = views.ModelRegistrationPageView.as_view()
            response = view(req)
        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once()


# ---------------------------------------------------------------------------
# Test: ModelRegistrationAPIView  (POST /api/models/register/)
# ---------------------------------------------------------------------------

class TestModelRegistrationAPIView(TestCase):

    def _post(self, data, files=None):
        factory = RequestFactory()
        post_data = dict(data)
        if files:
            post_data.update(files)
        req = factory.post("/api/models/register/", post_data)
        return req

    def test_missing_model_file_returns_400(self):
        req = self._post({"model_name": "M"})
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            view = views.ModelRegistrationAPIView.as_view()
            response = view(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data["success"])
        self.assertIn("No model file", data["error"])

    def test_missing_model_name_returns_400(self):
        factory = RequestFactory()
        file_content = BytesIO(b"fake model bytes")
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("model.pkl", b"fake bytes")
        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": ""},
                           format="multipart")
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            view = views.ModelRegistrationAPIView.as_view()
            response = view(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data["success"])
        self.assertIn("required", data["error"])

    def test_invalid_accuracy_returns_400(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("model.pkl", b"bytes")
        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "accuracy": "not-a-number"},
                           format="multipart")
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            view = views.ModelRegistrationAPIView.as_view()
            response = view(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Accuracy", data["error"])

    def test_accuracy_above_100_returns_400(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("model.pkl", b"bytes")
        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "accuracy": "105"},
                           format="multipart")
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            view = views.ModelRegistrationAPIView.as_view()
            response = view(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn("100", data["error"])

    def test_accuracy_below_0_returns_400(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("model.pkl", b"bytes")
        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "accuracy": "-5"},
                           format="multipart")
        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            view = views.ModelRegistrationAPIView.as_view()
            response = view(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)

    def test_ner_type_overrides_subtype_language_environment(self):
        """For NER model type, subtype must be 'Text Pipeline' and language/env must be empty."""
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("ner.pkl", b"bytes")

        captured_metadata = {}
        svc = _mock_service()

        def capture_register(local_file_path, original_filename, metadata):
            captured_metadata.update(metadata)
            return {"success": True, "model_name": "NERModel", "version": "1", "artifact_path": "x"}

        svc.register_model.side_effect = capture_register

        req = factory.post("/api/models/register/",
                           {
                               "model": fake_file,
                               "model_name": "NERModel",
                               "model_type": "NER",
                               "model_subtype": "SomethingElse",
                               "language": "en",
                               "environment": "prod",
                               "accuracy": "85",
                           },
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            with patch("registry.views.os.makedirs"), \
                 patch("registry.views.os.path.exists", return_value=True), \
                 patch("registry.views.os.remove"), \
                 patch("builtins.open", unittest.mock.mock_open()):
                view = views.ModelRegistrationAPIView.as_view()
                view(req)

        self.assertEqual(captured_metadata.get("model_subtype"), "Text Pipeline")
        self.assertEqual(captured_metadata.get("language"), "")
        self.assertEqual(captured_metadata.get("environment"), "")

    def test_fileclassifier_type_sets_uis_subtype(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("fc.pkl", b"bytes")

        captured_metadata = {}
        svc = _mock_service()

        def capture_register(local_file_path, original_filename, metadata):
            captured_metadata.update(metadata)
            return {"success": True, "model_name": "FC", "version": "1", "artifact_path": "x"}

        svc.register_model.side_effect = capture_register

        req = factory.post("/api/models/register/",
                           {
                               "model": fake_file,
                               "model_name": "FC",
                               "model_type": "FileClassifier",
                               "accuracy": "70",
                           },
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            with patch("registry.views.os.makedirs"), \
                 patch("registry.views.os.path.exists", return_value=True), \
                 patch("registry.views.os.remove"), \
                 patch("builtins.open", unittest.mock.mock_open()):
                view = views.ModelRegistrationAPIView.as_view()
                view(req)

        self.assertEqual(captured_metadata.get("model_subtype"), "UIS")

    def test_is_deployable_true_string_parsed(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("m.pkl", b"bytes")

        captured_metadata = {}
        svc = _mock_service()

        def capture_register(local_file_path, original_filename, metadata):
            captured_metadata.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}

        svc.register_model.side_effect = capture_register

        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M",
                            "is_deployable": "true", "accuracy": "80"},
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            with patch("registry.views.os.makedirs"), \
                 patch("registry.views.os.path.exists", return_value=True), \
                 patch("registry.views.os.remove"), \
                 patch("builtins.open", unittest.mock.mock_open()):
                view = views.ModelRegistrationAPIView.as_view()
                view(req)

        self.assertTrue(captured_metadata.get("is_deployable"))

    def test_service_exception_returns_500(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("m.pkl", b"bytes")

        svc = _mock_service()
        svc.register_model.side_effect = Exception("mlflow down")

        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "accuracy": "80"},
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            with patch("registry.views.os.makedirs"), \
                 patch("registry.views.os.path.exists", return_value=True), \
                 patch("registry.views.os.remove"), \
                 patch("builtins.open", unittest.mock.mock_open()):
                view = views.ModelRegistrationAPIView.as_view()
                response = view(req)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_empty_accuracy_defaults_to_zero(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("m.pkl", b"bytes")

        captured_metadata = {}
        svc = _mock_service()
        def capture_register(local_file_path, original_filename, metadata):
            captured_metadata.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture_register

        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "accuracy": ""},
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None), \
             patch("registry.views.os.makedirs"), \
             patch("registry.views.os.path.exists", return_value=True), \
             patch("registry.views.os.remove"), \
             patch("builtins.open", unittest.mock.mock_open()):
            views.ModelRegistrationAPIView.as_view()(req)

        self.assertEqual(captured_metadata.get("accuracy"), 0.0)

    def test_invalid_priority_ignored(self):
        factory = RequestFactory()
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("m.pkl", b"bytes")

        captured_metadata = {}
        svc = _mock_service()
        def capture_register(local_file_path, original_filename, metadata):
            captured_metadata.update(metadata)
            return {"success": True, "model_name": "M", "version": "1", "artifact_path": "x"}
        svc.register_model.side_effect = capture_register

        req = factory.post("/api/models/register/",
                           {"model": fake_file, "model_name": "M", "priority": "high"},
                           format="multipart")

        with patch.object(views.ModelRegistrationAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None), \
             patch("registry.views.os.makedirs"), \
             patch("registry.views.os.path.exists", return_value=True), \
             patch("registry.views.os.remove"), \
             patch("builtins.open", unittest.mock.mock_open()):
            views.ModelRegistrationAPIView.as_view()(req)

        self.assertIsNone(captured_metadata.get("priority"))


# ---------------------------------------------------------------------------
# Test: ModelsAPIView  (GET /api/models/)
# ---------------------------------------------------------------------------

class TestModelsAPIView(TestCase):

    def _get_response(self, svc):
        factory = RequestFactory()
        req = factory.get("/api/models/")
        with patch.object(views.ModelsAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.ModelsAPIView.as_view()(req)

    def test_get_returns_200_and_success_true(self):
        resp = self._get_response(_mock_service())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])

    def test_get_returns_models_list(self):
        resp = self._get_response(_mock_service())
        data = json.loads(resp.content)
        self.assertIn("models", data)
        self.assertIsInstance(data["models"], list)

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.list_models.side_effect = Exception("DB error")
        resp = self._get_response(svc)
        self.assertEqual(resp.status_code, 500)
        data = json.loads(resp.content)
        self.assertFalse(data["success"])
        self.assertIn("error", data)


# ---------------------------------------------------------------------------
# Test: FindModelAPIView  (GET /api/models/find/?purpose=...)
# ---------------------------------------------------------------------------

class TestFindModelAPIView(TestCase):

    def _get_response(self, svc, purpose="ASR"):
        factory = RequestFactory()
        req = factory.get("/api/models/find/", {"purpose": purpose})
        with patch.object(views.FindModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.FindModelAPIView.as_view()(req)

    def test_returns_200_with_models(self):
        resp = self._get_response(_mock_service())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("models", data)

    def test_purpose_forwarded_to_service(self):
        svc = _mock_service()
        self._get_response(svc, purpose="NER")
        svc.find_models.assert_called_once_with("NER")

    def test_empty_purpose_handled(self):
        self._get_response(_mock_service(), purpose="")

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.find_models.side_effect = Exception("oops")
        resp = self._get_response(svc)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# Test: UpdateModelAPIView  (POST /api/models/update/)
# ---------------------------------------------------------------------------

class TestUpdateModelAPIView(TestCase):

    def _post(self, svc, body):
        factory = RequestFactory()
        req = factory.post(
            "/api/models/update/",
            data=json.dumps(body),
            content_type="application/json",
        )
        with patch.object(views.UpdateModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.UpdateModelAPIView.as_view()(req)

    def test_missing_name_returns_400(self):
        resp = self._post(_mock_service(), {"version": "1"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(json.loads(resp.content)["success"])

    def test_missing_version_returns_400(self):
        resp = self._post(_mock_service(), {"name": "M"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(json.loads(resp.content)["success"])

    def test_successful_update_returns_200(self):
        resp = self._post(_mock_service(), {"name": "M", "version": "1", "accuracy": 95.0})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("model", data)

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.update_model_version.side_effect = Exception("fail")
        resp = self._post(svc, {"name": "M", "version": "1"})
        self.assertEqual(resp.status_code, 500)

    def test_update_delegates_to_service_with_correct_args(self):
        svc = _mock_service()
        self._post(svc, {"name": "M", "version": "2", "accuracy": 88.0})
        svc.update_model_version.assert_called_once()
        call_args = svc.update_model_version.call_args[0]
        self.assertEqual(call_args[0], "M")
        self.assertEqual(call_args[1], 2)

    def test_invalid_json_body_returns_500(self):
        factory = RequestFactory()
        req = factory.post(
            "/api/models/update/",
            data="not-a-json",
            content_type="application/json",
        )
        with patch.object(views.UpdateModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            resp = views.UpdateModelAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(json.loads(resp.content)["success"])


# ---------------------------------------------------------------------------
# Test: DeleteModelAPIView  (DELETE /api/models/<name>/version/<v>/)
# ---------------------------------------------------------------------------

class TestDeleteModelAPIView(TestCase):

    def _delete(self, svc, name="TestModel", version=1):
        factory = RequestFactory()
        req = factory.delete(f"/api/models/{name}/version/{version}/")
        with patch.object(views.DeleteModelAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.DeleteModelAPIView.as_view()(req, mlflow_name=name, version=version)

    def test_successful_delete_returns_200(self):
        resp = self._delete(_mock_service())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

    def test_delete_passes_correct_args_to_service(self):
        svc = _mock_service()
        self._delete(svc, name="MyModel", version=3)
        svc.delete_model_version.assert_called_once_with("MyModel", 3)

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.delete_model_version.side_effect = Exception("not found")
        resp = self._delete(svc)
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(json.loads(resp.content)["success"])


# ---------------------------------------------------------------------------
# Test: PurposesAPIView  (GET /api/models/purposes/)
# ---------------------------------------------------------------------------

class TestPurposesAPIView(TestCase):

    def _get(self, svc):
        factory = RequestFactory()
        req = factory.get("/api/models/purposes/")
        with patch.object(views.PurposesAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.PurposesAPIView.as_view()(req)

    def test_returns_200_and_purposes_list(self):
        resp = self._get(_mock_service())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["purposes"], ["ASR", "Classification"])

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.list_purposes.side_effect = Exception("fail")
        resp = self._get(svc)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# Test: ArchitecturesAPIView  (GET /api/models/architectures/)
# ---------------------------------------------------------------------------

class TestArchitecturesAPIView(TestCase):

    def _get(self, svc):
        factory = RequestFactory()
        req = factory.get("/api/models/architectures/")
        with patch.object(views.ArchitecturesAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", svc) or None):
            return views.ArchitecturesAPIView.as_view()(req)

    def test_returns_200_and_architectures_list(self):
        resp = self._get(_mock_service())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["architectures"], ["BERT", "CNN"])

    def test_service_exception_returns_500(self):
        svc = _mock_service()
        svc.list_architectures.side_effect = Exception("fail")
        resp = self._get(svc)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# Test: LanguagesAPIView  (GET /api/models/languages/)
# ---------------------------------------------------------------------------

class TestLanguagesAPIView(TestCase):

    def test_returns_200_and_empty_languages(self):
        factory = RequestFactory()
        req = factory.get("/api/models/languages/")
        resp = views.LanguagesAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["languages"], [])


# ---------------------------------------------------------------------------
# Test: EnvironmentsAPIView  (GET /api/models/environments/)
# ---------------------------------------------------------------------------

class TestEnvironmentsAPIView(TestCase):

    def test_returns_200_and_empty_environments(self):
        factory = RequestFactory()
        req = factory.get("/api/models/environments/")
        resp = views.EnvironmentsAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["environments"], [])


# ---------------------------------------------------------------------------
# Test: SetDeployedVersionAPIView  (POST /api/models/set-deployed/)
# ---------------------------------------------------------------------------

class TestSetDeployedVersionAPIView(TestCase):

    def test_post_returns_success_true(self):
        factory = RequestFactory()
        req = factory.post(
            "/api/models/set-deployed/",
            data=json.dumps({"name": "M", "version": "1", "deployment_point": "ASR"}),
            content_type="application/json",
        )
        with patch.object(views.SetDeployedVersionAPIView, "__init__",
                          lambda self, **kw: setattr(self, "service", _mock_service()) or None):
            resp = views.SetDeployedVersionAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])


if __name__ == "__main__":
    unittest.main()
