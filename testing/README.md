# Testing — ML Model Management

Automated unit tests for every feature and method in the `registration/registry` Django app.

## Structure

```
testing/
├── __init__.py
├── conftest.py          # pytest path bootstrap
├── README.md            # this file
├── test_models.py       # MLflowService data-layer methods
├── test_services.py     # MLflowService write/mutate operations
└── test_views.py        # All Django API views (end-to-end via RequestFactory)
```

## Coverage

| File | Tests | What is covered |
|---|---|---|
| `test_models.py` | ~35 | `_format_model_version`, `list_models`, `find_models`, `list_architectures`, `list_purposes`, `get_model_version` |
| `test_services.py` | ~22 | `_ensure_registered_model`, `register_model`, `update_model_version`, `delete_model_version` |
| `test_views.py` | ~30 | All 11 view classes: registration, list, find, update, delete, purposes, architectures, languages, environments, set-deployed |

> No live MLflow server or PostgreSQL database is required — all external dependencies are mocked.

## How to Run

```bash
# From the project root (ml_model_management/)
python -m pytest testing/ -v

# Run a specific file
python -m pytest testing/test_views.py -v

# Show coverage (if pytest-cov is installed)
python -m pytest testing/ --cov=registration/registry --cov-report=term-missing
```

## Dependencies

Install test dependencies (in addition to `registration/requirements.txt`):

```bash
pip install pytest pytest-django
```
