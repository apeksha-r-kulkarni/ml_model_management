#!/bin/bash

# Path to the project-level .env file
ENV_FILE="../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Loading configuration from $ENV_FILE..."

# Parse configuration from .env
MINIO_ENDPOINT=$(grep -E '^MINIO_ENDPOINT=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
MINIO_ACCESS_KEY=$(grep -E '^MINIO_ACCESS_KEY=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
MINIO_SECRET_KEY=$(grep -E '^MINIO_SECRET_KEY=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
MINIO_BUCKET=$(grep -E '^MINIO_BUCKET=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
MINIO_SECURE=$(grep -E '^MINIO_SECURE=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
MLFLOW_S3_IGNORE_TLS=$(grep -E '^MLFLOW_S3_IGNORE_TLS=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')

# Set protocol for the endpoint URL based on MINIO_SECURE flag
PROTOCOL="http"
if [[ "${MINIO_SECURE,,}" == "true" || "$MINIO_SECURE" == "1" ]]; then
    PROTOCOL="https"
fi

# Export AWS credentials and MLflow endpoint configuration
export AWS_ACCESS_KEY_ID="${MINIO_ACCESS_KEY}"
export AWS_SECRET_ACCESS_KEY="${MINIO_SECRET_KEY}"
export MLFLOW_S3_ENDPOINT_URL="${PROTOCOL}://${MINIO_ENDPOINT}"
export MLFLOW_S3_IGNORE_TLS="${MLFLOW_S3_IGNORE_TLS:-false}"

echo "MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT_URL}"
echo "Artifact Root: s3://${MINIO_BUCKET}"

# Automatically activate the virtual environment if present
if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
fi

# Parse PG config from .env
DB_USER=$(grep -E '^DB_USER=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
DB_PASSWORD=$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | cut -d '=' -f 2 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
DB_HOST=$(grep -E '^DB_HOST=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
DB_PORT=$(grep -E '^DB_PORT=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')
DB_NAME=$(grep -E '^DB_NAME=' "$ENV_FILE" | cut -d '=' -f 2 | tr -d ' "')

# URL encode the password in bash (simple python script inline)
ENCODED_PASSWORD=$(python -c "import urllib.parse; print(urllib.parse.quote_plus('''$DB_PASSWORD'''))")
PG_URI="postgresql://${DB_USER}:${ENCODED_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Start the MLflow Server
echo "Starting MLflow server with PostgreSQL backend..."
mlflow server \
    --backend-store-uri "${PG_URI}" \
    --default-artifact-root "s3://${MINIO_BUCKET}" \
    --serve-artifacts \
    --host 127.0.0.1 \
    --port 5000
