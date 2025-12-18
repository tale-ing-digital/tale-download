"""
Servicio de generación de ZIPs en memoria
"""
import io
import zipfile
from typing import List, Dict, Any
from backend.services.download_service import download_service
from backend.services.pdf_service import pdf_service
from backend.utils.file_naming import generate_filename, generate_folder_path

class ZipService:
    """Servicio para generar ZIPs en memoria con estructura de carpetas"""
    
    @staticmethod
    def create_zip(documents: List[Dict[str, Any]]) -> io.BytesIO:
        """
        Crea un ZIP en memoria con documentos organizados en carpetas
        
        Args:
            documents: Lista de documentos con metadata de BI
        
        Returns:
            BytesIO con el contenido del ZIP
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in documents:
                try:
                    # Descargar archivo
                    content = download_service.download_file(doc['url'])
                    if not content:
                        print(f"⚠️  Skipping {doc['codigo_proforma']}: download failed")
                        continue
                    
                    # Convertir a PDF
                    pdf_content = pdf_service.convert_to_pdf(content)
                    if not pdf_content:
                        print(f"⚠️  Skipping {doc['codigo_proforma']}: PDF conversion failed")
                        continue
                    
                    # Generar nombre de archivo
                    filename = generate_filename(doc)
                    
                    # Generar ruta de carpeta
                    folder_path = generate_folder_path(doc)
                    
                    # Ruta completa dentro del ZIP
                    zip_path = f"{folder_path}/{filename}"
                    
                    # Agregar al ZIP
                    zip_file.writestr(zip_path, pdf_content)
                    print(f"✅ Added to ZIP: {zip_path}")
                    
                except Exception as e:
                    print(f"❌ Error processing {doc.get('codigo_proforma', 'unknown')}: {e}")
                    continue
        
        zip_buffer.seek(0)
        return zip_buffer

zip_service = ZipService()
