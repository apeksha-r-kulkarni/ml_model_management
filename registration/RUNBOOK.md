# RUNBOOK

## Prerequisites
- Python 3.9+
- PostgreSQL
- MinIO
- MLflow Server

## Setup Commands

### 1. Database (PostgreSQL)
```bash
sudo -u postgres psql
CREATE DATABASE ml_model_management;
CREATE USER django_user WITH PASSWORD 'password';
ALTER ROLE django_user SET client_encoding TO 'utf8';
ALTER ROLE django_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE django_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ml_model_management TO django_user;
```

### 2. Environment Variables (.env)
Create `.env` in `registration/core`:
```env
DB_NAME=ml_model_management
DB_USER=django_user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
BUCKET_NAME=mlflow-dev
```

### 3. Migrations
```bash
cd registration
python manage.py makemigrations registry
python manage.py migrate
```

### 4. Running Backend
```bash
python manage.py runserver
```

## API Testing

**Register Model:**
```bash
curl -X POST -F "model=@dummy.pt" \
     -F "model_name=TestModel" \
     -F "model_type=Classification" \
     -F "purpose=Testing" \
     -F "accuracy=95.5" \
     http://localhost:8000/api/models/register/
```

**List Models:**
```bash
curl -X GET http://localhost:8000/api/models/
```

**Find by Use Case:**
```bash
curl -X GET http://localhost:8000/api/models/find/?purpose=Testing
```

## Infrastructure Details

### Shared PostgreSQL Database
Django and MLflow use the exact same PostgreSQL database (`model_management`). Their tables coexist safely without colliding because MLflow scopes its tables distinctly (e.g., `experiments`, `runs`, `model_versions`) while Django's native ORM tables use the `registry_` prefix.

### MLflow Backend Configuration
The MLflow server's PostgreSQL backend URI is dynamically constructed in `start_mlflow.sh` by parsing `.env`. It reads the database credentials (`DB_USER`, `DB_PASSWORD`, etc.) and automatically URL-encodes them to form the required `postgresql://user:pass@host:port/dbname` connection string.

### MinIO/AWS Environment Mapping
To enable S3-compatible storage via MinIO, the `start_mlflow.sh` script maps local MinIO `.env` variables directly to standard AWS environment variables required by MLflow's boto3 client:
- `MINIO_ACCESS_KEY` -> `AWS_ACCESS_KEY_ID`
- `MINIO_SECRET_KEY` -> `AWS_SECRET_ACCESS_KEY`
- `MINIO_ENDPOINT` -> `MLFLOW_S3_ENDPOINT_URL` (with `http` or `https` protocol inferred via `MINIO_SECURE`)
