# Project Requirements & Architecture Summary

## Overall Architecture (Pure-MLflow)
This project implements a "Pure-MLflow" model management backend architecture. The objective is to establish MLflow as the absolute Single Source of Truth for model metadata, versioning, and artifact storage.

**Crucial Distinction:** 
Django does **not** use its own PostgreSQL model registry or database tables for storing model metadata. **MLflow uses PostgreSQL as its backend store**, and **MinIO stores the actual model artifacts**. Django communicates strictly via the MLflow HTTP API and does **not** directly access MinIO or PostgreSQL. PostgreSQL has not been removed from the project; rather, its usage has been strictly limited to serving as MLflow's internal tracking registry.

### Role Breakdown
*   **Django (API Layer):** Acts purely as an API proxy/UI backend. It contains zero ORM models, zero database migrations for model metadata, and zero MinIO/S3 credentials. 
*   **MLflow (Single Source of Truth):** Handles all model registry operations, versioning, and metadata tagging. It runs alongside a proxy server that securely streams artifacts to MinIO.
*   **PostgreSQL:** Operates exclusively as MLflow's backend store (`--backend-store-uri`), maintaining MLflow's internal relational structure.
*   **MinIO (Artifact Store):** The S3-compatible blob storage where actual `.pt` and `.onnx` model files reside, securely managed through MLflow's `--serve-artifacts` configuration.

## Features & Implementation

### Model Registration & Artifacts
*   **Registration:** Models are registered via the Django API, which utilizes `mlflow.start_run()` and `mlflow.log_artifact()` to stream uploads.
*   **Supported Artifacts:** The system handles arbitrary model artifact formats, including `.pt` (PyTorch) and `.onnx`.
*   **Artifact URI Handling:** Artifact paths are dynamically retrieved from MLflow's `ModelVersion.source` field (e.g., `runs:/<run_id>/<file>`). Django never attempts to build or predict S3 URIs.

### Metadata & Versioning
*   **MLflow Versioning:** All model version iterations are natively managed by the MLflow Model Registry.
*   **Model Metadata:** Custom attributes (architecture, purpose, model type, accuracy, priority, deployable status, etc.) are stored purely as MLflow **Tags** on the Registered Model (RM) and Model Version (MV). 

### Operations
*   **List Models:** Fetches a grouped list of all models and their associated versions from MLflow.
*   **Find by Purpose:** Queries the registry for models matching a specific `purpose` tag.
*   **Architecture Listing:** Extracts and deduplicates unique architecture strings from all model version tags.
*   **Update Metadata:** Modifies MLflow tags for a specific model version.
*   **Delete Versions/Models:** Deletes a specific model version from MLflow. If a Registered Model becomes empty, it is automatically removed.

## Frontend (MFE) Requirements
*   A React-based Micro-Frontend (MFE) handles the UI (Models Inventory).
*   Expects the Django API to provide model data already grouped by model identity.
*   Reads all attributes (accuracy, architecture, language, etc.) dynamically from the MLflow-provided tags.

## API Endpoints (Django)
*   `POST /api/models/register/`: Upload a new model file and metadata.
*   `GET /api/models/`: List all registered models and versions.
*   `GET /api/models/find/?purpose={val}`: Find models by purpose tag.
*   `GET /api/models/architectures/`: List all distinct architectures.
*   `GET /api/models/purposes/`: List all distinct purposes.
*   `PUT /api/models/update/`: Update tags for a model version.
*   `DELETE /api/models/{name}/version/{version}/`: Delete a model version.

## Environment & Configuration Requirements
The `.env` file must configure MLflow to securely proxy artifacts and use PostgreSQL:
*   `MINIO_ACCESS_KEY` & `MINIO_SECRET_KEY` (Exclusively used by MLflow)
*   `MINIO_BUCKET` & `MINIO_ENDPOINT`
*   `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` (For MLflow's PostgreSQL store)
*   `MLFLOW_TRACKING_URI=http://127.0.0.1:5000`

## Startup Instructions
1.  **PostgreSQL & MinIO:** Ensure system services (or containers) for PostgreSQL and MinIO are actively running.
2.  **MLflow Server:** Run `registration/start_mlflow.sh`. This spins up the MLflow tracker on port 5000, configured with `--serve-artifacts` and `--artifacts-destination`.
3.  **Django API:** Run `python manage.py runserver` to start the backend proxy on port 8000.
4.  **Frontend (MFE):** Run `npm run dev` in the `mfe/` directory to start the React interface.

## Testing Performed
End-to-End API verification was performed confirming:
1.  Successful multi-version model uploads (.pt dummy models) via the proxy layer.
2.  Data mapping consistency (tags properly applied to MLflow).
3.  Successful listing, updating, and deletion cascades.
4.  Total absence of Django ORM PostgreSQL footprint for model metadata.

## Current Limitations
*   **Deployment Status Not Tracked:** Because we removed the Django database, the legacy "Currently Deployed Version" column is gone. MLflow aliases/stages are not yet integrated into the `set-deployed` API. As a result, deployment status is not currently tracked, and the frontend UI explicitly displays **N/A (Not Tracked)** to avoid falsely implying a model is deployed.
