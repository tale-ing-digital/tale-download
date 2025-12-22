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
