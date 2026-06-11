"""
Configuración de entorno para TaleDownload Backend
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configuración de la aplicación"""
    
    # Redshift (AWS)
    REDSHIFT_HOST: str = os.getenv("REDSHIFT_HOST", "")
    REDSHIFT_PORT: int = int(os.getenv("REDSHIFT_PORT", "5439"))
    REDSHIFT_DATABASE: str = os.getenv("REDSHIFT_DATABASE", "")
    REDSHIFT_USER: str = os.getenv("REDSHIFT_USER", "")
    REDSHIFT_PASSWORD: str = os.getenv("REDSHIFT_PASSWORD", "")
    
    # Redshift pool / resilience
    REDSHIFT_POOL_MIN: int = int(os.getenv("REDSHIFT_POOL_MIN", "1"))
    REDSHIFT_POOL_MAX: int = int(os.getenv("REDSHIFT_POOL_MAX", "10"))
    REDSHIFT_KEEPALIVE_IDLE: int = int(os.getenv("REDSHIFT_KEEPALIVE_IDLE", "30"))
    REDSHIFT_QUERY_TIMEOUT: int = int(os.getenv("REDSHIFT_QUERY_TIMEOUT", "30000"))
    REDSHIFT_RETRY_ATTEMPTS: int = int(os.getenv("REDSHIFT_RETRY_ATTEMPTS", "2"))
    REDSHIFT_SLOW_QUERY_MS: int = int(os.getenv("REDSHIFT_SLOW_QUERY_MS", "5000"))
    REDSHIFT_SLOW_POOL_WAIT_MS: int = int(os.getenv("REDSHIFT_SLOW_POOL_WAIT_MS", "500"))

    # ZIP request guards (seconds)
    ZIP_REQUEST_TIMEOUT_SEC: int = int(os.getenv("ZIP_REQUEST_TIMEOUT_SEC", "240"))
    ZIP_REDSHIFT_TIMEOUT_SEC: int = int(os.getenv("ZIP_REDSHIFT_TIMEOUT_SEC", "45"))
    ZIP_GENERATION_TIMEOUT_SEC: int = int(os.getenv("ZIP_GENERATION_TIMEOUT_SEC", "210"))
    ZIP_SLOW_FILE_SEC: float = float(os.getenv("ZIP_SLOW_FILE_SEC", "10"))
    
    # Configuración general
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
    
    # Versión
    VERSION: str = "1.0.0"
    
    @classmethod
    def validate(cls) -> None:
        """Valida que las variables requeridas estén configuradas"""
        required_vars = [
            ("REDSHIFT_HOST", cls.REDSHIFT_HOST),
            ("REDSHIFT_DATABASE", cls.REDSHIFT_DATABASE),
            ("REDSHIFT_USER", cls.REDSHIFT_USER),
            ("REDSHIFT_PASSWORD", cls.REDSHIFT_PASSWORD),
        ]
        
        missing = [var for var, value in required_vars if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

settings = Settings()
