import os
from dotenv import load_dotenv

class ModelConfig:
    """Configuration handler for the Model Management System."""
    
    def __init__(self):
        # Ensure we load from the project-level .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        load_dotenv(env_path)
        
    @property
    def tracking_uri(self):
        # Use the MLflow Server HTTP endpoint instead of direct DB connection
        return os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        
    @property
    def minio_endpoint(self):
        return os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
        
    @property
    def minio_access_key(self):
        return os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        
    @property
    def minio_secret_key(self):
        return os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
    @property
    def minio_bucket(self):
        return os.getenv("MINIO_BUCKET", "mlflow-dev")

    @property
    def minio_secure(self):
        val = os.getenv("MINIO_SECURE", "False").lower()
        return val in ("true", "1", "yes")
