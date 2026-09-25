# Technical Architecture Report: ML Model Management

This report provides a complete, accurate snapshot of the current implementation based on the active codebase. No files have been modified.

---

## 1. Project Structure

The project consists of a Django backend and a React frontend, along with integration configurations for MLflow and MinIO.

* **Django Backend**: `registration/` (Core application logic, APIs, DAOs, integrations)
* **React Frontend**: `mfe/` (User interface built with Vite + React + Tailwind)
* **Configuration**: `.env` (Environment variables), `registration/core/settings.py`, `mfe/vite.config.js`
* **Database Models**: `registration/registry/models.py` (PostgreSQL via Django ORM)
* **Service/Manager/DAO Layers**: `manager.py` (Service/Facade), `dao.py` (Database Access)
* **Integrations**: `minio_client.py` (MinIO storage), `manager.py` (MLflow tracking/registry)
* **IAM/Security**: `iam.py` (Mock IAM), `security.py` (Mock Encryption)
* **Tests**: `scratch/` (Previously contained comprehensive testing scripts `test_comprehensive.py`, `test_deletion.py` which are currently deleted in the working tree).

---

## 2. Backend Architecture

The backend strictly follows a layered architecture, separating presentation (views), business logic (manager), and data access (DAO).

| File | Responsibility | Important Classes/Functions | Who calls it | What it calls | Why it exists |
|---|---|---|---|---|---|
| `views.py` | HTTP layer, routing, input parsing, returning JSON. | `register_model`, `list_models`, `update_model`, `delete_model` | Django URL router | `ModelManager` | To decouple HTTP mechanics from business logic. |
| `manager.py` | Core business logic, orchestrating DB, MinIO, MLflow, and IAM. | `ModelManager` | `views.py` | `ModelDAO`, `MinioStorageService`, `mlflow`, `ModelIAMAdapter` | Acts as the central Facade orchestrator. |
| `dao.py` | Postgres database operations via Django ORM. | `ModelDAO`, `_map_to_data_object` | `ModelManager` | Django Models (`LogicalModel`, `ModelVersion`) | Isolates database queries from business logic. |
| `data_objects.py` | Pure Python DTOs representing entities. | `Model` | `views.py`, `manager.py`, `dao.py` | None | Decouples business logic from Django ORM models. |
| `models.py` | Django ORM database schema definitions. | `LogicalModel`, `ModelVersion` | `dao.py` | Django DB | Defines the persistent relational schema. |
| `iam.py` | Authorization mock layer. | `ModelIAMAdapter`, `MockIAM` | `ModelManager` | None | Future-proofing for real IAM integration. |
| `security.py` | Data encryption/decryption layer (currently mock). | `ModelEncrypt` | `ModelManager` | None | Future-proofing for at-rest encryption. |
| `model_config.py` | Environment variable management. | `ModelConfig` | `ModelManager` | `os.getenv` | Centralizes configuration fetching. |
| `settings.py` | Django framework configuration. | `DATABASES`, `INSTALLED_APPS` | Django Framework | None | Standard Django configuration. |
| `urls.py` | API route definitions. | `urlpatterns` | Django Framework | `views.py` | Maps HTTP endpoints to view functions. |

---

## 3. Data Model

The PostgreSQL schema uses a two-tier relational model.

### `LogicalModel`
Represents the top-level identity of a model (e.g., "SpeechRecognizer").
* **Fields**:
  * `id`: Primary Key (Implicit AutoField)
  * `name`: `CharField(255, unique=True)`
  * `model_type`: `CharField(100)`
  * `mlflow_name`: `CharField(255, unique=True)` (Stores the MLflow registered model name)
  * `purpose`: `CharField(255, blank=True)`
  * `created_at`, `updated_at`: Timestamps

### `ModelVersion`
Represents a specific iteration of a `LogicalModel` (e.g., v1, v2).
* **Fields**:
  * `id`: Primary Key (Implicit)
  * `logical_model`: `ForeignKey(LogicalModel)` (Relationship mapping version to parent identity)
  * `version_number`: `IntegerField`
  * `architecture`: `CharField(100, blank=True)`
  * `accuracy`: `FloatField` (0.0 to 100.0)
  * `priority`: `IntegerField(null=True, blank=True)` (Optional)
  * `is_deployable`: `BooleanField(default=False)`
  * `remarks`: `TextField(blank=True)`
  * `deployment_points`: `JSONField(default=list)`
  * `original_filename`: `CharField(255)`
  * `file_format`: `CharField(20)`
  * `file_size`: `PositiveBigIntegerField`
  * `model_artifact_path`: `CharField(500, blank=True)` (MinIO bucket path)
  * `run_id`: `CharField(255)` (Link to MLflow Tracking Run)
  * `status`: `CharField(50, default="PENDING")`
* **Constraints**: Unique constraint on `['logical_model', 'version_number']`.

**Metadata split**: Identity, Type, and Purpose are Model-level. Accuracy, Architecture, Deployability, Deployment Points, and Artifacts are Version-level.

---

## 4. Complete Registration Flow

**Trigger**: User clicks "Register Model" in the React UI.
1. **React**: `ModelRegistrationForm` builds a `FormData` object containing the `.pt`/`.onnx` file and form fields.
2. **modelService.js**: Calls `POST /api/models/register/` (omitting `Content-Type` to allow the browser to set the multipart boundary).
3. **Django `urls.py` & `views.py`**: Receives the request. Extracts metadata and saves the uploaded file to a temporary `scratch/` directory. Builds the `Model` DTO and calls `ModelManager.registerModel`. Passes a hardcoded user `"authorized_user"`.
4. **ModelManager (IAM)**: Calls `iam_adapter.checkAccess`, which returns `True`.
5. **ModelManager (MLflow Prep)**: Connects to MLflow. Creates the Registered Model container if it doesn't exist. Sets `model_type` and `purpose` tags on the Registered Model.
6. **ModelManager (Version Prediction)**: Queries Postgres `MAX(version)` for the model name to predict the upcoming version number (e.g., `predicted_version = 2`).
7. **ModelManager (MinIO)**: Reads the temp file. Passes it to `ModelEncrypt.encrypt` (which currently returns raw data). Uploads it to MinIO using `upload_model` at the path: `models/{model_name}_v{predicted_version}.{file_format}`.
8. **ModelManager (MLflow Tracking)**: Starts an MLflow run. Logs tags (`framework`, `is_deployable`, `architecture`) and metrics (`accuracy`, `priority`).
9. **ModelManager (MLflow Registry)**: Calls `mlflow.register_model()` referencing the MinIO path (`s3://mlflow-dev/models/...`). Extracts the `actual_version` assigned by MLflow. Adds tags directly to the MLflow Model Version (`architecture`, `accuracy`, `priority`, `is_deployable`, `deployment_points`, `remarks`).
10. **ModelManager (DAO)**: Calls `dao.storeModel()` which creates/fetches the `LogicalModel` and inserts a new `ModelVersion` into PostgreSQL with the metadata and the `run_id`.
11. **Cleanup**: Temporary file in `scratch/` is deleted by `views.py`.

**Failure handling**: If MLflow registration fails, the MinIO artifact is deleted. If DB save fails, both the MLflow version and MinIO artifact are rolled back.

---

## 5. MLflow Implementation

MLflow serves as both a Tracking server (for runs) and a Model Registry (for versioning).

| Metadata | PostgreSQL | MLflow Location | MinIO |
|---|---|---|---|
| `name` | `LogicalModel.name` | Registered Model Name | Path prefix |
| `model_type` | `LogicalModel.model_type` | RM Tag & Run Tag | N/A |
| `purpose` | `LogicalModel.purpose` | RM Tag | N/A |
| `version` | `ModelVersion.version_number` | Model Version | Path suffix |
| `architecture` | `ModelVersion.architecture` | Run Tag & MV Tag | N/A |
| `accuracy` | `ModelVersion.accuracy` | Run Metric & MV Tag | N/A |
| `priority` | `ModelVersion.priority` | Run Metric & MV Tag | N/A |
| `is_deployable` | `ModelVersion.is_deployable` | Run Tag & MV Tag | N/A |
| `deployment_points`| `ModelVersion.deployment_points` | MV Tag (JSON string) | N/A |
| `remarks` | `ModelVersion.remarks` | MV Tag | N/A |
| `run_id` | `ModelVersion.run_id` | Run ID | N/A |
| `artifact` | Path only | `model_uri` link | Binary File |

---

## 6. MinIO

* **Why**: Provides S3-compatible object storage for the large binary model weights (.pt, .onnx), keeping massive blobs out of PostgreSQL.
* **Storage**: Stores the raw (mock encrypted) model files.
* **Path Determination**: `models/{model_name}_v{predicted_version}.{file_format}` in the `mlflow-dev` bucket.
* **MLflow Linkage**: MLflow `model_uri` is set to the MinIO `s3://` path.
* **PostgreSQL Storage**: Only stores the relative path (`models/...`), not the binary.
* **Deletion**: When a version is deleted, the file is physically removed from MinIO via `delete_model()`.

---

## 7. PostgreSQL (Dual-Storage Architecture)

PostgreSQL stores a complete relational map of the metadata.
* **Why it exists**: MLflow's querying capabilities are limited, and MLflow hides soft-deleted models from search queries, breaking version prediction. PostgreSQL allows fast relational filtering, custom business logic (like deployment points), and ensures referential integrity for the custom MFE.
* **Architecture**: It is a dual-storage system where data is duplicated into both MLflow tags and Postgres rows during Registration.

---

## 8. Current APIs

| Operation | HTTP | Endpoint | Request | Response | Backend Flow |
|---|---|---|---|---|---|
| Register | POST | `/api/models/register/` | FormData (file + metadata) | `{success, model_id, artifact_path}` | View -> Manager -> IAM -> MinIO -> MLflow -> PG |
| List | GET | `/api/models/` | None | `{success, models: [...]}` | View -> Manager -> DAO -> PG |
| Find | GET | `/api/models/find/?purpose={val}` | Query param | `{success, models: [...]}` | View -> Manager -> DAO -> PG |
| Purposes | GET | `/api/models/purposes/` | None | `{success, purposes: [...]}` | View -> Manager -> DAO -> PG |
| Architectures | GET | `/api/models/architectures/` | None | `{success, architectures: [...]}` | View -> Manager -> DAO -> PG |
| Update | PUT | `/api/models/update/` | JSON `{id, accuracy, ...}` | `{success, model: {...}}` | View -> Manager -> IAM -> PG |
| Delete | DELETE| `/api/models/<name>/version/<ver>/` | JSON `{db_id}` (unused in backend) | `{success}` | View -> Manager -> IAM -> MLflow -> MinIO -> PG |

---

## 9. Register Model Fields

* **Model Name**: Required. Used as MLflow Identity. Stored in PG and MLflow.
* **Model Type**: Required. Stored in PG, MLflow RM Tag, Run Tag.
* **Purpose**: Optional. Stored in PG, MLflow RM Tag.
* **Architecture**: Optional. Stored in PG, MLflow Run Tag, MV Tag.
* **Accuracy**: Required (0-100). Backend validates bounds. Stored in PG, MLflow Run Metric, MV Tag.
* **Priority**: Optional (Integer). Stored in PG, MLflow Run Metric, MV Tag.
* **Deployment Points**: Optional Array. Stored in PG (JSONField) and MLflow MV Tag (JSON string).
* **Remarks**: Optional string. Stored in PG and MLflow MV Tag.
* **Is Deployable**: Boolean. Stored in PG, MLflow Run Tag, MV Tag.
* **Model Artifact**: Required file upload (.pt or .onnx). Uploaded to MinIO.

---

## 10. Versioning

* **Who assigns it**: MLflow is the authoritative source for the version number via `mlflow.register_model()`.
* **How it's predicted**: To name the MinIO artifact before MLflow registers it, the backend runs `SELECT MAX(version)` in Postgres.
* **Deletion behavior**: If v3 is deleted, it is permanently deleted from MLflow, MinIO, and Postgres.
* **Reusing numbers**: If v3 is deleted, MLflow will NEVER reuse v3 (the next will be v4). However, Postgres `MAX(version)` might predict v3 again.
* **The MinIO path discrepancy**: If v3 is deleted, PG predicts the next is v3. MinIO artifact is named `_v3`. But MLflow will assign `v4`. The system handles this because it captures the `actual_version` from MLflow and stores `v4` in PostgreSQL, while the MinIO path string simply retains `_v3` in its text path. The database mapping remains intact.

---

## 11. CRUD Operations (Source of Truth)

* **Register**: Writes to MLflow, MinIO, and PostgreSQL.
* **List**: Reads strictly from **PostgreSQL**.
* **Find**: Reads strictly from **PostgreSQL**.
* **Update**: Writes strictly to **PostgreSQL**. (Does NOT update MLflow tags).
* **Delete**: Deletes from MLflow, MinIO, and PostgreSQL.

---

## 12. React MFE

* **Architecture**: It is a standalone React SPA built with Vite. It is **NOT** a federated module (No Module Federation plugins are present in `vite.config.js`). 
* **Structure**:
  * `App.jsx`: Maintains `currentView` state for navigation.
  * `components/layout/AppLayout.jsx`: Persistent Sidebar.
  * `pages/Models.jsx`: Groups flat API data into nested structures based on Purpose.
* **Styling**: Tailwind CSS integration is present and used extensively.

---

## 13. React → Django Communication

* **Flow**: Browser -> React (`fetch('/api/...')`) -> Vite Dev Server Proxy (`vite.config.js`) -> Django (`127.0.0.1:8000`).
* **Why**: The Vite proxy intercepts `/api` requests and forwards them to Django, avoiding CORS issues during local development.

---

## 14. IAM & Security

* **IAM**: `ModelIAMAdapter` uses a `MockIAM` class. It hardcodes a check: if `user == "unauthorized_user"`, access is denied. Otherwise, access is granted. The views currently hardcode `user = "authorized_user"`.
* **Security**:
  * **Encryption**: `ModelEncrypt` class exists but is a mock (returns raw bytes).
  * **CSRF**: Disabled on API views using `@csrf_exempt`.
  * **Authentication**: None implemented.

---

## 15. Configuration

`ModelConfig` class orchestrates config by loading the root `.env` file.
* **Postgres**: Derived from `DB_USER`, `DB_PASSWORD`, etc., in `.env`.
* **MLflow**: Defaults to using the Postgres URI for tracking if `MLFLOW_TRACKING_URI` is absent.
* **MinIO**: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, etc., loaded from `.env`.

---

## 16. Git State & Tests

* **Git State**: Extensive UI modifications have been made to `mfe/` components (`App.jsx`, `Models.jsx`, `ModelCard.jsx`) to introduce the Purpose-grouped layout and state-based routing.
* **Tests**: Test scripts (`test_comprehensive.py`, `test_deletion.py`, `test_model.py`) in the `scratch/` directory have been removed in the working tree.

---

## 17. Identified Uncertainties & Flaws

1. **Update API Divergence**: The `/api/models/update/` endpoint successfully updates Postgres, but it completely fails to update the MLflow tags. This causes the dual-storage systems to diverge the moment a model is edited.
2. **MinIO Pathing Issue**: Because MLflow doesn't reuse versions but Postgres `MAX(version)` prediction does, the MinIO path (`_v3`) will diverge from the actual MLflow version (`v4`) after deletions. The code anticipates this but leaves a messy bucket naming convention.
3. **Security Mocks**: Encryption and IAM are explicitly mocked. 
4. **No Real MFE**: The frontend directory is named `mfe`, but it lacks Webpack/Vite Module Federation configurations, making it a standard monolith React app.
5. **No Authentication**: The APIs are fully open with CSRF disabled and a hardcoded "authorized_user" string.
