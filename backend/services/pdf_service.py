"""
Servicio de conversión a PDF
"""
import io
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import Optional

# Constantes para detectar extensiones de Office
WORD_EXTENSIONS = {".doc", ".docx"}
PASSTHROUGH_EXTENSIONS = {".xlsx", ".pptx"}

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
    def get_file_extension_from_content(content: bytes) -> str:
        """Detecta la extensión del archivo por sus magic bytes para mayor fiabilidad."""
        if content.startswith(b'%PDF'):
            return '.pdf'
        
        # Formatos de Office basados en ZIP (OOXML)
        if content.startswith(b'PK\x03\x04'):
            # El contenido de los archivos OOXML es un ZIP. Buscamos directorios específicos.
            if b'word/' in content[:2000]:
                return '.docx'
            if b'xl/' in content[:2000]:
                return '.xlsx'
            if b'ppt/' in content[:2000]:
                return '.pptx'
        
        # Formatos de Office antiguos (OLE CF)
        if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            # Estos son más difíciles de diferenciar, pero podemos buscar strings comunes.
            if b'WordDocument' in content[:2000]:
                return '.doc'
            # Nota: .xls y .ppt antiguos son más ambiguos y los omitimos por ahora para seguridad.

        # Formatos de imagen
        try:
            with Image.open(io.BytesIO(content)) as img:
                if img.format and img.format.lower() in ['jpeg', 'jpg']:
                    return '.jpg'
                if img.format and img.format.lower() == 'png':
                    return '.png'
        except IOError:
            pass # No es una imagen que PIL pueda abrir

        return '' # Extensión desconocida
    
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
    def convert_to_pdf(content: bytes, original_filename: str = None) -> Optional[dict]:
        """
        Convierte contenido a PDF o indica que debe pasar sin cambios (passthrough).

        Args:
            content: Bytes del archivo.
            original_filename: Nombre original del archivo para usar como fallback.

        Returns:
            Un diccionario con {"mode", "content", "extension"} o None si falla.
        """
        # Primero, intentamos detectar la extensión por el contenido (magic bytes).
        ext = PDFService.get_file_extension_from_content(content)

        # Si no se detecta, usamos el nombre del archivo como segunda opción.
        if not ext and original_filename:
            file_parts = original_filename.lower().split(".")
            if len(file_parts) > 1:
                ext = f".{file_parts[-1]}"

        # --- Lógica de decisión ---

        # 1. Si ya es un PDF, es un passthrough de tipo PDF.
        if ext == ".pdf":
            return {"mode": "pdf", "content": content, "extension": ".pdf"}

        # 2. Si es una extensión de Office que no convertimos, es passthrough.
        if ext in PASSTHROUGH_EXTENSIONS:
            return {"mode": "passthrough", "content": content, "extension": ext}

        # 3. Si es Word, por ahora también es passthrough. En el futuro se convertirá.
        if ext in WORD_EXTENSIONS:
            return {"mode": "passthrough", "content": content, "extension": ext}

        # 4. Si es una imagen, la convertimos a PDF.
        if ext in [".jpg", ".png"]:
            pdf_content = PDFService.image_to_pdf(content)
            if pdf_content:
                return {"mode": "pdf", "content": pdf_content, "extension": ".pdf"}

        # 5. Si no es nada de lo anterior, es un formato no soportado.
        print(f"❌ Formato de archivo no soportado con extensión detectada: '{ext}'")
        return None

pdf_service = PDFService()
