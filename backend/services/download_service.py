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
        Descarga un archivo desde una URL con un timeout adaptativo inteligente.
        """
        try:
            # Primero, una petición HEAD para obtener el tamaño sin descargar el cuerpo.
            head_response = requests.head(url, timeout=10, allow_redirects=True)
            head_response.raise_for_status()
            content_length_str = head_response.headers.get("content-length")

            # Si no podemos obtener el tamaño, usamos el timeout fijo por defecto.
            final_timeout = timeout

            if content_length_str and content_length_str.isdigit():
                content_length = int(content_length_str)
                
                # Lógica de timeout adaptativo: 1 segundo por cada 200KB, con un mínimo de 10s y un máximo de 120s.
                # Esto asume una velocidad de descarga mínima razonable.
                adaptive_timeout = max(10, min(120, content_length // 200000))
                final_timeout = adaptive_timeout

                # Verificación de tamaño máximo permitido.
                size_mb = content_length / (1024 * 1024)
                if size_mb > settings.MAX_FILE_SIZE_MB:
                    print(f"❌ File too large: {size_mb:.2f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)")
                    return None

            # Ahora, la petición GET para descargar el contenido con el timeout calculado.
            response = requests.get(url, timeout=final_timeout, stream=True)
            response.raise_for_status()

            # Descargamos el contenido en memoria.
            content = response.content
            print(f"✅ Downloaded {len(content) / 1024:.1f} KB from {url} (timeout: {final_timeout}s)")
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
