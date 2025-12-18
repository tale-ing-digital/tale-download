"""
Servicio de descarga de archivos desde URLs públicas
"""
import requests
from typing import Optional
import io
from backend.core.config import settings

class DownloadService:
    """Servicio para descargar archivos desde URLs públicas"""
    
    @staticmethod
    def download_file(url: str, timeout: int = 30) -> Optional[bytes]:
        """
        Descarga un archivo desde una URL pública
        
        Args:
            url: URL del archivo
            timeout: Timeout en segundos
        
        Returns:
            Contenido del archivo en bytes o None si falla
        """
        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Verificar tamaño
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > settings.MAX_FILE_SIZE_MB:
                    print(f"❌ File too large: {size_mb:.2f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)")
                    return None
            
            # Descargar contenido
            content = response.content
            print(f"✅ Downloaded {len(content)} bytes from {url}")
            return content
            
        except requests.exceptions.Timeout:
            print(f"❌ Timeout downloading {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {url}: {e}")
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
            return response.headers.get('content-type')
        except:
            return None

download_service = DownloadService()
