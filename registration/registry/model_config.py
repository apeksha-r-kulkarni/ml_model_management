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
        import urllib.parse
        db_user = os.getenv('DB_USER', 'django_user')
        db_password = os.getenv('DB_PASSWORD', 'password')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'model_management')
        encoded_password = urllib.parse.quote_plus(db_password)
        pg_uri = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        return os.getenv("MLFLOW_TRACKING_URI", pg_uri)
        
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
