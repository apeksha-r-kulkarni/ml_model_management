"""
test_models.py
==============
Unit tests for MLflowService data-layer methods:
  - _format_model_version
  - list_models
  - find_models
  - list_architectures
  - list_purposes
  - get_model_version

All MLflow client calls are mocked so no live MLflow server is needed.
Run from the `registration/` directory:
    python -m pytest ../testing/test_models.py -v
Or from the project root:
    python -m pytest testing/test_models.py -v  (with PYTHONPATH=registration)
"""

import json
import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap: make `registration/` importable
# ---------------------------------------------------------------------------
REGISTRATION_DIR = os.path.join(
    os.path.dirname(__file__), "..", "registration"
)
if os.path.abspath(REGISTRATION_DIR) not in sys.path:
    sys.path.insert(0, os.path.abspath(REGISTRATION_DIR))


def _stub_mlflow():
    """Provide minimal mlflow stubs so imports work without a real install."""
    mlflow_mod = types.ModuleType("mlflow")
    mlflow_mod.set_tracking_uri = lambda *a, **k: None
    mlflow_mod.set_registry_uri = lambda *a, **k: None
    mlflow_mod.start_run = MagicMock()
    mlflow_mod.log_artifact = lambda *a, **k: None

    tracking_mod = types.ModuleType("mlflow.tracking")
    tracking_mod.MlflowClient = MagicMock

    sys.modules.setdefault("mlflow", mlflow_mod)
    sys.modules.setdefault("mlflow.tracking", tracking_mod)


_stub_mlflow()

try:
    import dotenv  # noqa
except ImportError:
    dotenv_mod = types.ModuleType("dotenv")
    dotenv_mod.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv_mod

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")

from registry.services import MLflowService  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mv(name="TestModel", version="1", tags=None,
             source="runs:/abc/model.pkl", run_id="abc123", status="READY"):
    mv = MagicMock()
    mv.name = name
    mv.version = version
    mv.tags = tags or {}
    mv.source = source
    mv.run_id = run_id
    mv.status = status
    return mv


def _make_rm(name="TestModel", tags=None):
    rm = MagicMock()
    rm.name = name
    rm.tags = tags or {}
    return rm


# ---------------------------------------------------------------------------
# Test: _format_model_version
# ---------------------------------------------------------------------------

class TestFormatModelVersion(unittest.TestCase):
    """Tests for MLflowService._format_model_version (pure data mapping)."""

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_returns_all_expected_keys(self):
        mv = _make_mv(tags={"architecture": "CNN", "accuracy": "92.5",
                             "priority": "1", "is_deployable": "true",
                             "deployment_points": '["edge","cloud"]',
                             "remarks": "stable"})
        rm = _make_rm(tags={"model_type": "Speech", "purpose": "ASR"})
        result = self.svc._format_model_version(mv, rm)
        expected_keys = {
            "name", "version", "model_type", "purpose", "architecture",
            "accuracy", "priority", "is_deployable", "deployment_points",
            "remarks", "artifact_path", "run_id", "status"
        }
        self.assertEqual(expected_keys, set(result.keys()))

    def test_accuracy_converted_to_float(self):
        mv = _make_mv(tags={"accuracy": "87.3"})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertIsInstance(result["accuracy"], float)
        self.assertAlmostEqual(result["accuracy"], 87.3)

    def test_accuracy_defaults_to_zero_when_missing(self):
        mv = _make_mv(tags={})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["accuracy"], 0.0)

    def test_is_deployable_true(self):
        mv = _make_mv(tags={"is_deployable": "true"})
        self.assertTrue(self.svc._format_model_version(mv, _make_rm())["is_deployable"])

    def test_is_deployable_false(self):
        mv = _make_mv(tags={"is_deployable": "False"})
        self.assertFalse(self.svc._format_model_version(mv, _make_rm())["is_deployable"])

    def test_is_deployable_missing_defaults_false(self):
        mv = _make_mv(tags={})
        self.assertFalse(self.svc._format_model_version(mv, _make_rm())["is_deployable"])

    def test_priority_parsed_as_int(self):
        mv = _make_mv(tags={"priority": "3"})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["priority"], 3)
        self.assertIsInstance(result["priority"], int)

    def test_priority_non_digit_returns_none(self):
        mv = _make_mv(tags={"priority": "high"})
        self.assertIsNone(self.svc._format_model_version(mv, _make_rm())["priority"])

    def test_priority_empty_string_returns_none(self):
        mv = _make_mv(tags={"priority": ""})
        self.assertIsNone(self.svc._format_model_version(mv, _make_rm())["priority"])

    def test_deployment_points_parsed_from_json(self):
        mv = _make_mv(tags={"deployment_points": '["edge","cloud"]'})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["deployment_points"], ["edge", "cloud"])

    def test_deployment_points_invalid_json_returns_empty_list(self):
        mv = _make_mv(tags={"deployment_points": "not-json"})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["deployment_points"], [])

    def test_deployment_points_missing_returns_empty_list(self):
        mv = _make_mv(tags={})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["deployment_points"], [])

    def test_model_type_comes_from_rm_tags(self):
        rm = _make_rm(tags={"model_type": "NLP"})
        result = self.svc._format_model_version(_make_mv(), rm)
        self.assertEqual(result["model_type"], "NLP")

    def test_purpose_comes_from_rm_tags(self):
        rm = _make_rm(tags={"purpose": "Classification"})
        result = self.svc._format_model_version(_make_mv(), rm)
        self.assertEqual(result["purpose"], "Classification")

    def test_artifact_path_run_id_status_pass_through(self):
        mv = _make_mv(source="runs:/xyz/m.pkl", run_id="xyz", status="PENDING_REGISTRATION")
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["artifact_path"], "runs:/xyz/m.pkl")
        self.assertEqual(result["run_id"], "xyz")
        self.assertEqual(result["status"], "PENDING_REGISTRATION")

    def test_none_rm_does_not_crash(self):
        """When rm is None, model_type and purpose should be empty strings."""
        result = self.svc._format_model_version(_make_mv(), None)
        self.assertEqual(result["model_type"], "")
        self.assertEqual(result["purpose"], "")

    def test_accuracy_invalid_string_raises_valueerror(self):
        mv = _make_mv(tags={"accuracy": "invalid_float"})
        with self.assertRaises(ValueError):
            self.svc._format_model_version(mv, _make_rm())
            
    def test_priority_float_string_returns_none(self):
        mv = _make_mv(tags={"priority": "3.5"})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertIsNone(result["priority"])
        
    def test_deployment_points_dict_parsed(self):
        # Even though normally a list, if someone sets a dict, it gets parsed
        mv = _make_mv(tags={"deployment_points": '{"env": "prod"}'})
        result = self.svc._format_model_version(mv, _make_rm())
        self.assertEqual(result["deployment_points"], {"env": "prod"})


# ---------------------------------------------------------------------------
# Test: list_models
# ---------------------------------------------------------------------------

class TestListModels(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_returns_list_type(self):
        self.svc.client.search_registered_models.return_value = []
        self.assertIsInstance(self.svc.list_models(), list)

    def test_empty_registry_returns_empty_list(self):
        self.svc.client.search_registered_models.return_value = []
        self.assertEqual(self.svc.list_models(), [])

    def test_single_model_structure(self):
        rm = _make_rm(name="ModelA", tags={"model_type": "NLP", "purpose": "Classification"})
        mv = _make_mv(name="ModelA", version="1")
        self.svc.client.search_registered_models.return_value = [rm]
        self.svc.client.search_model_versions.return_value = [mv]

        result = self.svc.list_models()
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertEqual(entry["name"], "ModelA")
        self.assertEqual(entry["model_type"], "NLP")
        self.assertEqual(entry["purpose"], "Classification")
        self.assertIn("all_versions", entry)

    def test_versions_sorted_descending_by_version(self):
        rm = _make_rm(name="M")
        mv1 = _make_mv(name="M", version="1")
        mv2 = _make_mv(name="M", version="2")
        mv3 = _make_mv(name="M", version="3")
        self.svc.client.search_registered_models.return_value = [rm]
        self.svc.client.search_model_versions.return_value = [mv1, mv3, mv2]

        result = self.svc.list_models()
        versions = [v["version"] for v in result[0]["all_versions"]]
        self.assertEqual(versions, sorted(versions, reverse=True))

    def test_multiple_models_returned(self):
        self.svc.client.search_registered_models.return_value = [_make_rm("A"), _make_rm("B")]
        self.svc.client.search_model_versions.return_value = []
        self.assertEqual(len(self.svc.list_models()), 2)

    def test_model_with_no_versions(self):
        rm = _make_rm(name="Empty")
        self.svc.client.search_registered_models.return_value = [rm]
        self.svc.client.search_model_versions.return_value = []
        result = self.svc.list_models()
        self.assertEqual(result[0]["all_versions"], [])


# ---------------------------------------------------------------------------
# Test: find_models
# ---------------------------------------------------------------------------

class TestFindModels(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_correct_filter_string_passed_to_client(self):
        self.svc.client.search_registered_models.return_value = []
        self.svc.find_models("ASR")
        self.svc.client.search_registered_models.assert_called_once_with(
            filter_string="tags.purpose = 'ASR'"
        )

    def test_returns_matching_models(self):
        rm = _make_rm(name="SpeechModel", tags={"purpose": "ASR", "model_type": "Speech"})
        mv = _make_mv(name="SpeechModel", version="1")
        self.svc.client.search_registered_models.return_value = [rm]
        self.svc.client.search_model_versions.return_value = [mv]

        result = self.svc.find_models("ASR")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "SpeechModel")

    def test_empty_purpose_returns_empty_list(self):
        self.svc.client.search_registered_models.return_value = []
        self.assertEqual(self.svc.find_models(""), [])

    def test_no_matching_purpose_returns_empty(self):
        self.svc.client.search_registered_models.return_value = []
        self.assertEqual(self.svc.find_models("unknown_purpose"), [])


# ---------------------------------------------------------------------------
# Test: list_architectures
# ---------------------------------------------------------------------------

class TestListArchitectures(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_returns_sorted_unique_architectures(self):
        mvs = [
            _make_mv(tags={"architecture": "CNN"}),
            _make_mv(tags={"architecture": "LSTM"}),
            _make_mv(tags={"architecture": "CNN"}),  # duplicate
        ]
        self.svc.client.search_model_versions.return_value = mvs
        self.assertEqual(self.svc.list_architectures(), ["CNN", "LSTM"])

    def test_skips_empty_architecture_tag(self):
        mvs = [_make_mv(tags={"architecture": ""}), _make_mv(tags={})]
        self.svc.client.search_model_versions.return_value = mvs
        self.assertEqual(self.svc.list_architectures(), [])

    def test_empty_model_versions_returns_empty(self):
        self.svc.client.search_model_versions.return_value = []
        self.assertEqual(self.svc.list_architectures(), [])


# ---------------------------------------------------------------------------
# Test: list_purposes
# ---------------------------------------------------------------------------

class TestListPurposes(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_returns_sorted_unique_purposes(self):
        rms = [
            _make_rm(tags={"purpose": "NER"}),
            _make_rm(tags={"purpose": "ASR"}),
            _make_rm(tags={"purpose": "NER"}),  # duplicate
        ]
        self.svc.client.search_registered_models.return_value = rms
        self.assertEqual(self.svc.list_purposes(), ["ASR", "NER"])

    def test_skips_empty_purpose_tag(self):
        self.svc.client.search_registered_models.return_value = [_make_rm(tags={"purpose": ""})]
        self.assertEqual(self.svc.list_purposes(), [])

    def test_empty_registry_returns_empty(self):
        self.svc.client.search_registered_models.return_value = []
        self.assertEqual(self.svc.list_purposes(), [])


# ---------------------------------------------------------------------------
# Test: get_model_version
# ---------------------------------------------------------------------------

class TestGetModelVersion(unittest.TestCase):

    def setUp(self):
        with patch("registry.services.MlflowClient"):
            self.svc = MLflowService()

    def test_returns_formatted_version(self):
        rm = _make_rm(name="M", tags={"model_type": "NLP"})
        mv = _make_mv(name="M", version="2")
        self.svc.client.get_registered_model.return_value = rm
        self.svc.client.get_model_version.return_value = mv

        result = self.svc.get_model_version("M", 2)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "M")

    def test_version_int_converted_to_str_for_client(self):
        self.svc.client.get_registered_model.return_value = _make_rm()
        self.svc.client.get_model_version.return_value = _make_mv()
        self.svc.get_model_version("M", 5)
        self.svc.client.get_model_version.assert_called_once_with("M", "5")

    def test_returns_none_when_exception_raised(self):
        self.svc.client.get_registered_model.side_effect = Exception("Not found")
        result = self.svc.get_model_version("NonExistent", 1)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
