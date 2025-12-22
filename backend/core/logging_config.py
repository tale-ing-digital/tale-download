"""
Configuración centralizada de logging para TaleDownload
Proporciona logging estructurado con timestamps, niveles de severidad y rotación de archivos
"""
import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configura logging estructurado con timestamps y niveles de severidad
    
    Args:
        debug: Si True, usa nivel DEBUG; si False, usa INFO
    
    Returns:
        Logger configurado para TaleDownload
    """
    # Crear directorio de logs si no existe
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logger raíz
    logger = logging.getLogger("taledownload")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Limpiar handlers existentes para evitar duplicados
    logger.handlers.clear()
    
    # Formato con timestamps, nivel, módulo y mensaje
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo (rotativo)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "taledownload.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Logger global para TaleDownload
logger = setup_logging()
