"""
Servicio de conversión a PDF con compresión inteligente
Optimiza el tamaño de los archivos usando JPEG con calidad controlada
"""
import io
import logging
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PDFService:
    """Servicio para conversión de archivos a PDF con compresión optimizada"""
    
    # Configuración de compresión JPEG
    JPEG_QUALITY = 85  # Rango: 0-100. 85 es un buen balance entre calidad y tamaño
    JPEG_OPTIMIZE = True  # Usar optimización JPEG
    
    @staticmethod
    def is_pdf(content: bytes) -> bool:
        """Verifica si el contenido es un PDF"""
        return content.startswith(b'%PDF')
    
    @staticmethod
    def is_image(content: bytes) -> bool:
        """Verifica si el contenido es una imagen"""
        try:
            Image.open(io.BytesIO(content))
            return True
        except Exception as e:
            logger.debug(f"[PDF] Not a valid image: {e}")
            return False
    
    @staticmethod
    def _get_optimal_format(image: Image.Image) -> Tuple[str, dict]:
        """
        Determina el formato óptimo para guardar la imagen
        
        Args:
            image: Objeto Image de Pillow
        
        Returns:
            Tupla (format, kwargs) con el formato y parámetros de guardado
        """
        # Si la imagen tiene canal alpha (transparencia), usar PNG
        if image.mode in ('RGBA', 'LA', 'P'):
            logger.debug("[PDF] Image has transparency, using PNG format")
            return ('PNG', {})
        
        # Para imágenes sin transparencia, usar JPEG (mucho más liviano)
        logger.debug(f"[PDF] Image mode is {image.mode}, using JPEG format with quality={PDFService.JPEG_QUALITY}")
        return ('JPEG', {
            'quality': PDFService.JPEG_QUALITY,
            'optimize': PDFService.JPEG_OPTIMIZE
        })
    
    @staticmethod
    def image_to_pdf(image_bytes: bytes) -> Optional[bytes]:
        """
        Convierte una imagen a PDF con compresión optimizada
        
        Args:
            image_bytes: Bytes de la imagen
        
        Returns:
            Bytes del PDF o None si falla
        """
        try:
            logger.debug(f"[PDF] Converting image to PDF, size: {len(image_bytes)} bytes")
            
            # Abrir imagen
            image = Image.open(io.BytesIO(image_bytes))
            logger.debug(f"[PDF] Image format: {image.format}, mode: {image.mode}, size: {image.size}")
            
            # Convertir a RGB si es necesario (JPEG no soporta otros modos)
            if image.mode not in ('RGB', 'L', 'RGBA', 'LA', 'P'):
                logger.debug(f"[PDF] Converting image mode from {image.mode} to RGB")
                image = image.convert('RGB')
            
            # Crear PDF en memoria
            pdf_buffer = io.BytesIO()
            
            # Calcular tamaño para ajustar a A4
            a4_width, a4_height = A4
            img_width, img_height = image.size
            
            # Calcular escala para ajustar a A4 manteniendo aspecto
            scale = min(a4_width / img_width, a4_height / img_height)
            new_width = img_width * scale
            new_height = img_height * scale
            
            # Crear PDF
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            
            # Centrar imagen en la página
            x = (a4_width - new_width) / 2
            y = (a4_height - new_height) / 2
            
            # Guardar imagen con formato optimizado
            temp_img = io.BytesIO()
            format_to_use, save_kwargs = PDFService._get_optimal_format(image)
            
            logger.debug(f"[PDF] Saving image as {format_to_use} with kwargs: {save_kwargs}")
            image.save(temp_img, format=format_to_use, **save_kwargs)
            temp_img.seek(0)
            
            temp_img_size = temp_img.getbuffer().nbytes
            reduction = 100 - (temp_img_size / len(image_bytes) * 100)
            logger.debug(f"[PDF] Compressed image size: {temp_img_size} bytes (reduction: {reduction:.1f}%)")
            
            # Dibujar imagen en PDF
            c.drawImage(temp_img, x, y, width=new_width, height=new_height)
            c.save()
            
            pdf_buffer.seek(0)
            pdf_content = pdf_buffer.read()
            logger.info(f"[PDF] ✅ Image converted to PDF successfully, size: {len(pdf_content)} bytes")
            return pdf_content
            
        except Exception as e:
            logger.error(f"[PDF] ❌ Error converting image to PDF: {type(e).__name__}: {e}")
            return None
    
    @staticmethod
    def convert_to_pdf(content: bytes) -> Optional[bytes]:
        """
        Convierte contenido a PDF (si no lo es ya)
        
        Args:
            content: Bytes del archivo
        
        Returns:
            Bytes del PDF
        """
        # Si ya es PDF, retornar directamente
        if PDFService.is_pdf(content):
            logger.debug(f"[PDF] Content is already PDF, size: {len(content)} bytes")
            return content
        
        # Si es imagen, convertir a PDF
        if PDFService.is_image(content):
            logger.debug(f"[PDF] Content is an image, converting to PDF")
            return PDFService.image_to_pdf(content)
        
        # Formato no soportado
        magic_bytes = content[:8].hex() if len(content) >= 8 else content.hex()
        logger.error(f"[PDF] ❌ Unsupported file format, magic bytes: {magic_bytes}, size: {len(content)} bytes")
        return None


pdf_service = PDFService()
