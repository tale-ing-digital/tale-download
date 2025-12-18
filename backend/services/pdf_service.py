"""
Servicio de conversión a PDF
"""
import io
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import Optional

class PDFService:
    """Servicio para conversión de archivos a PDF"""
    
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
        except:
            return False
    
    @staticmethod
    def image_to_pdf(image_bytes: bytes) -> Optional[bytes]:
        """
        Convierte una imagen a PDF
        
        Args:
            image_bytes: Bytes de la imagen
        
        Returns:
            Bytes del PDF o None si falla
        """
        try:
            # Abrir imagen
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
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
            
            # Guardar imagen temporalmente
            temp_img = io.BytesIO()
            image.save(temp_img, format='PNG')
            temp_img.seek(0)
            
            # Dibujar imagen en PDF
            c.drawImage(temp_img, x, y, width=new_width, height=new_height)
            c.save()
            
            pdf_buffer.seek(0)
            return pdf_buffer.read()
            
        except Exception as e:
            print(f"❌ Error converting image to PDF: {e}")
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
            return content
        
        # Si es imagen, convertir a PDF
        if PDFService.is_image(content):
            return PDFService.image_to_pdf(content)
        
        # Formato no soportado
        print("❌ Unsupported file format for PDF conversion")
        return None

pdf_service = PDFService()
