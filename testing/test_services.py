"""
test_services.py
================
Unit tests for MLflowService write/mutate operations:
  - register_model
  - update_model_version
  - delete_model_version
  - _ensure_registered_model

All MLflow client and mlflow.start_run calls are mocked.
Run:
    python -m pytest testing/test_services.py -v  (PYTHONPATH=registration)
"""

import json
import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Bootstrap
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
    run_mock.info.run_id = "test-run-123"
    run_mock.info.artifact_uri = "s3://mock-bucket/0/test-run-123/artifacts"

    mlflow_mod.start_run = MagicMock(return_value=run_mock)
    mlflow_mod.log_artifact = MagicMock()

    tracking_mod = types.ModuleType("mlflow.tracking")
    tracking_mod.MlflowClient = MagicMock

    sys.modules["mlflow"] = mlflow_mod
    sys.modules["mlflow.tracking"] = tracking_mod
    return mlflow_mod


MLFLOW_MOD = _stub_mlflow()

try:
    import dotenv  # noqa
except ImportError:
    dotenv_mod = types.ModuleType("dotenv")
    dotenv_mod.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv_mod

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")

from registry.services import MLflowService  # noqa: E402


def _make_mv(**kwargs):
    mv = MagicMock()
    mv.name = kwargs.get("name", "Model")
    mv.version = kwargs.get("version", "1")
    mv.tags = kwargs.get("tags", {})
    mv.source = kwargs.get("source", "runs:/abc/m.pkl")
    mv.run_id = kwargs.get("run_id", "abc")
    mv.status = kwargs.get("status", "READY")
    return mv


# ---------------------------------------------------------------------------
# Test: _ensure_registered_model
# ---------------------------------------------------------------------------

class TestEnsureRegisteredModel(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_does_not_create_if_model_exists(self):
        """If get_registered_model succeeds, create_registered_model should NOT be called."""
        self.svc.client.get_registered_model.return_value = MagicMock()
        self.svc._ensure_registered_model("ExistingModel", "NLP", "Classification")
        self.svc.client.create_registered_model.assert_not_called()

    def test_creates_model_if_not_exists(self):
        """If get_registered_model raises, create_registered_model should be called."""
        self.svc.client.get_registered_model.side_effect = Exception("Not found")
        self.svc.client.create_registered_model.return_value = MagicMock()
        self.svc._ensure_registered_model("NewModel", "Speech", "ASR")
        self.svc.client.create_registered_model.assert_called_once_with("NewModel")

    def test_sets_model_type_and_purpose_tags(self):
        self.svc.client.get_registered_model.return_value = MagicMock()
        self.svc._ensure_registered_model("M", "NLP", "Classification")
        self.svc.client.set_registered_model_tag.assert_any_call("M", "model_type", "NLP")
        self.svc.client.set_registered_model_tag.assert_any_call("M", "purpose", "Classification")

    def test_skips_empty_tags(self):
        """Empty model_type / purpose should NOT be written as tags."""
        self.svc.client.get_registered_model.return_value = MagicMock()
        self.svc._ensure_registered_model("M", "", "")
        self.svc.client.set_registered_model_tag.assert_not_called()

    def test_handles_concurrent_creation_gracefully(self):
        """If create_registered_model also raises (race condition), no exception bubbles up."""
        self.svc.client.get_registered_model.side_effect = Exception("Not found")
        self.svc.client.create_registered_model.side_effect = Exception("Already exists")
        # Should not raise
        try:
            self.svc._ensure_registered_model("M", "NLP", "Classification")
        except Exception:
            self.fail("_ensure_registered_model raised unexpectedly on concurrent creation")


# ---------------------------------------------------------------------------
# Test: register_model
# ---------------------------------------------------------------------------

class TestRegisterModel(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

        # Prepare a fake model version returned by create_model_version
        self.fake_mv = _make_mv(name="TestModel", version="1",
                                 source="runs:/test-run-123/model.pkl")
        self.svc.client.get_registered_model.return_value = MagicMock()
        self.svc.client.create_model_version.return_value = self.fake_mv

    def _base_metadata(self, **overrides):
        meta = {
            "model_name": "TestModel",
            "model_type": "NLP",
            "architecture": "BERT",
            "model_subtype": "",
            "language": "",
            "environment": "",
            "priority": 1,
            "is_deployable": True,
            "purpose": "Classification",
            "deployment_points": ["edge"],
            "remarks": "test",
            "accuracy": 90.0,
        }
        meta.update(overrides)
        return meta

    def test_returns_success_dict_with_expected_keys(self):
        result = self.svc.register_model(
            local_file_path="/tmp/model.pkl",
            original_filename="model.pkl",
            metadata=self._base_metadata()
        )
        self.assertTrue(result["success"])
        self.assertIn("model_name", result)
        self.assertIn("version", result)
        self.assertIn("artifact_path", result)

    def test_create_model_version_called_with_correct_name(self):
        self.svc.register_model(
            local_file_path="/tmp/model.pkl",
            original_filename="model.pkl",
            metadata=self._base_metadata(model_name="SpecificModel")
        )
        call_kwargs = self.svc.client.create_model_version.call_args
        self.assertEqual(call_kwargs.kwargs.get("name") or call_kwargs[1].get("name")
                         or call_kwargs[0][0], "SpecificModel")

    def test_deployment_points_list_serialized_to_json_tag(self):
        self.svc.register_model(
            local_file_path="/tmp/m.pkl",
            original_filename="m.pkl",
            metadata=self._base_metadata(deployment_points=["edge", "cloud"])
        )
        # Collect all set_model_version_tag calls
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if c.kwargs.get("key") == "deployment_points" or (len(c[0]) > 2 and c[0][2] == "deployment_points")]
        self.assertTrue(len(dp_calls) > 0)
        raw_value = dp_calls[0].kwargs.get("value") if "value" in dp_calls[0].kwargs else dp_calls[0][0][3]
        parsed = json.loads(raw_value)
        self.assertIn("edge", parsed)
        self.assertIn("cloud", parsed)

    def test_deployment_points_string_json_is_parsed_before_serializing(self):
        """If deployment_points arrives as a JSON string, it must be decoded before re-encoding."""
        meta = self._base_metadata(deployment_points='["mobile","server"]')
        self.svc.register_model("/tmp/m.pkl", "m.pkl", meta)
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if c.kwargs.get("key") == "deployment_points" or (len(c[0]) > 2 and c[0][2] == "deployment_points")]
        if dp_calls:
            raw = dp_calls[0].kwargs.get("value") if "value" in dp_calls[0].kwargs else dp_calls[0][0][3]
            self.assertIsInstance(json.loads(raw), list)

    def test_accuracy_tag_set_as_string(self):
        self.svc.register_model("/tmp/m.pkl", "m.pkl", self._base_metadata(accuracy=85.5))
        calls = self.svc.client.set_model_version_tag.call_args_list
        acc_calls = [c for c in calls if c.kwargs.get("key") == "accuracy" or (len(c[0]) > 2 and c[0][2] == "accuracy")]
        self.assertTrue(len(acc_calls) > 0)
        val = acc_calls[0].kwargs.get("value") if "value" in acc_calls[0].kwargs else acc_calls[0][0][3]
        self.assertIsInstance(val, str)

    def test_model_uri_uses_original_filename(self):
        self.svc.register_model("/tmp/model_v2.pkl", "model_v2.pkl", self._base_metadata())
        call_kwargs = self.svc.client.create_model_version.call_args
        source = (call_kwargs.kwargs.get("source") or call_kwargs[1].get("source") or "")
        self.assertIn("model_v2.pkl", source)


# ---------------------------------------------------------------------------
# Test: update_model_version
# ---------------------------------------------------------------------------

class TestUpdateModelVersion(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_updates_model_type_rm_tag(self):
        self.svc.update_model_version("M", 1, {"model_type": "Speech"})
        self.svc.client.set_registered_model_tag.assert_any_call("M", "model_type", "Speech")

    def test_updates_purpose_rm_tag(self):
        self.svc.update_model_version("M", 1, {"purpose": "ASR"})
        self.svc.client.set_registered_model_tag.assert_any_call("M", "purpose", "ASR")

    def test_updates_accuracy_mv_tag(self):
        self.svc.update_model_version("M", 1, {"accuracy": 92.5})
        self.svc.client.set_model_version_tag.assert_any_call("M", "1", "accuracy", "92.5")

    def test_updates_priority_mv_tag(self):
        self.svc.update_model_version("M", 2, {"priority": 3})
        self.svc.client.set_model_version_tag.assert_any_call("M", "2", "priority", "3")

    def test_updates_is_deployable_mv_tag(self):
        self.svc.update_model_version("M", 1, {"is_deployable": True})
        self.svc.client.set_model_version_tag.assert_any_call("M", "1", "is_deployable", "True")

    def test_updates_architecture_mv_tag(self):
        self.svc.update_model_version("M", 1, {"architecture": "ResNet"})
        self.svc.client.set_model_version_tag.assert_any_call("M", "1", "architecture", "ResNet")

    def test_updates_remarks_mv_tag(self):
        self.svc.update_model_version("M", 1, {"remarks": "Updated"})
        self.svc.client.set_model_version_tag.assert_any_call("M", "1", "remarks", "Updated")

    def test_deployment_points_list_serialized_to_json(self):
        self.svc.update_model_version("M", 1, {"deployment_points": ["edge", "cloud"]})
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if "deployment_points" in c[0]]
        self.assertTrue(len(dp_calls) > 0)
        raw = dp_calls[0][0][3]
        self.assertEqual(json.loads(raw), ["edge", "cloud"])

    def test_deployment_points_json_string_decoded_then_reencoded(self):
        self.svc.update_model_version("M", 1, {"deployment_points": '["mobile"]'})
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if "deployment_points" in c[0]]
        if dp_calls:
            raw = dp_calls[0][0][3]
            self.assertEqual(json.loads(raw), ["mobile"])

    def test_unrelated_keys_ignored(self):
        """Keys not in the update list should not trigger any client calls."""
        self.svc.client.reset_mock()
        self.svc.update_model_version("M", 1, {"unknown_field": "value"})
        self.svc.client.set_registered_model_tag.assert_not_called()
        self.svc.client.set_model_version_tag.assert_not_called()

    def test_returns_true_on_success(self):
        result = self.svc.update_model_version("M", 1, {"accuracy": 80.0})
        self.assertTrue(result)

    def test_deployment_points_invalid_json_string_wrapped_in_list(self):
        self.svc.update_model_version("M", 1, {"deployment_points": "not-json"})
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if c.kwargs.get("key") == "deployment_points" or (len(c[0]) > 2 and c[0][2] == "deployment_points")]
        raw = dp_calls[0].kwargs.get("value") if "value" in dp_calls[0].kwargs else dp_calls[0][0][3]
        self.assertEqual(json.loads(raw), ["not-json"])
        
    def test_deployment_points_non_string_wrapped_in_list(self):
        self.svc.update_model_version("M", 1, {"deployment_points": 123})
        calls = self.svc.client.set_model_version_tag.call_args_list
        dp_calls = [c for c in calls if c.kwargs.get("key") == "deployment_points" or (len(c[0]) > 2 and c[0][2] == "deployment_points")]
        raw = dp_calls[0].kwargs.get("value") if "value" in dp_calls[0].kwargs else dp_calls[0][0][3]
        self.assertEqual(json.loads(raw), 123)
        
    def test_empty_update_data_no_calls(self):
        self.svc.client.reset_mock()
        self.svc.update_model_version("M", 1, {})
        self.svc.client.set_registered_model_tag.assert_not_called()
        self.svc.client.set_model_version_tag.assert_not_called()


# ---------------------------------------------------------------------------
# Test: delete_model_version
# ---------------------------------------------------------------------------

class TestDeleteModelVersion(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def _setup_mv_mock(self, run_id="abc123"):
        mv = _make_mv(run_id=run_id)
        self.svc.client.get_model_version.return_value = mv
        return mv

    def test_calls_delete_model_version_with_str_version(self):
        self._setup_mv_mock()
        self.svc.client.search_model_versions.return_value = [_make_mv()]  # still has others
        self.svc.delete_model_version("M", 1)
        self.svc.client.delete_model_version.assert_called_once_with("M", "1")

    def test_deletes_registered_model_when_no_versions_remain(self):
        self._setup_mv_mock()
        self.svc.client.search_model_versions.return_value = []  # no versions left
        self.svc.delete_model_version("M", 1)
        self.svc.client.delete_registered_model.assert_called_once_with("M")

    def test_does_not_delete_registered_model_when_versions_remain(self):
        self._setup_mv_mock()
        self.svc.client.search_model_versions.return_value = [_make_mv()]  # one remaining
        self.svc.delete_model_version("M", 1)
        self.svc.client.delete_registered_model.assert_not_called()

    def test_returns_true_on_success(self):
        self._setup_mv_mock()
        self.svc.client.search_model_versions.return_value = []
        result = self.svc.delete_model_version("M", 1)
        self.assertTrue(result)

    def test_raises_exception_on_client_failure(self):
        self.svc.client.get_registered_model.side_effect = Exception("not found")
        with self.assertRaises(Exception) as ctx:
            self.svc.delete_model_version("M", 99)
        self.assertIn("Failed to delete MLflow model version", str(ctx.exception))

    def test_raises_exception_if_search_model_versions_fails(self):
        self._setup_mv_mock()
        self.svc.client.search_model_versions.side_effect = Exception("search failed")
        with self.assertRaises(Exception) as ctx:
            self.svc.delete_model_version("M", 1)
        self.assertIn("Failed to delete MLflow model version", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
