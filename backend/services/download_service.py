"""
Servicio de descarga de archivos desde URLs públicas
Incluye reintentos automáticos y logging estructurado
"""
import requests
import time
import logging
from typing import Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class DownloadService:
    """Servicio para descargar archivos desde URLs públicas con reintentos automáticos"""
    
    # Configuración de reintentos
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 1s, 2s, 4s
    
    @staticmethod
    def download_file(url: str, timeout: int = 30, max_retries: int = None) -> Optional[bytes]:
        """
        Descarga un archivo desde una URL pública con reintentos automáticos
        
        Args:
            url: URL del archivo
            timeout: Timeout en segundos (0 = sin límite)
            max_retries: Número máximo de intentos (usa MAX_RETRIES si es None)
        
        Returns:
            Contenido del archivo en bytes o None si falla
        """
        if max_retries is None:
            max_retries = DownloadService.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"[DOWNLOAD] Attempt {attempt + 1}/{max_retries} for {url}")
                
                response = requests.get(url, timeout=timeout if timeout > 0 else None, stream=True)
                response.raise_for_status()
                
                # Verificar tamaño
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > settings.MAX_FILE_SIZE_MB:
                        logger.warning(f"[DOWNLOAD] File too large: {size_mb:.2f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)")
                        return None
                
                # Descargar contenido
                content = response.content
                logger.info(f"[DOWNLOAD] ✅ Downloaded {len(content)} bytes from {url}")
                return content
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"[DOWNLOAD] Timeout on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = DownloadService.RETRY_BACKOFF_FACTOR ** attempt
                    logger.info(f"[DOWNLOAD] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[DOWNLOAD] ❌ Failed after {max_retries} attempts (timeout)")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[DOWNLOAD] Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = DownloadService.RETRY_BACKOFF_FACTOR ** attempt
                    logger.info(f"[DOWNLOAD] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[DOWNLOAD] ❌ Failed after {max_retries} attempts: {e}")
                    return None
    
    @staticmethod
    def get_content_type(url: str) -> Optional[str]:
        """
        Obtiene el Content-Type de una URL sin descargar el archivo completo
        
        Args:
            url: URL del archivo
        
        Returns:
            Content-Type o None
        """
        try:
            response = requests.head(url, timeout=10)
            content_type = response.headers.get('content-type')
            logger.debug(f"[DOWNLOAD] Content-Type for {url}: {content_type}")
            return content_type
        except Exception as e:
            logger.warning(f"[DOWNLOAD] Error getting content-type: {e}")
            return None


download_service = DownloadService()
