"""
Servicio de generación de ZIPs en streaming con estructura TALE
Incluye logging estructurado para diagnóstico de errores
"""
import io
import zipfile
import logging
import time
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
from backend.services.download_service import download_service
from backend.services.pdf_service import pdf_service
from backend.utils.file_naming import generate_filename, generate_folder_path

logger = logging.getLogger(__name__)

# Orden de prioridad de tipos de documento
DOCUMENT_TYPE_ORDER = {
    'Voucher': 1,
    'Minuta': 2,
    'Adenda': 3,
    'Carta de Aprobación': 4,
    'CartaAprobacion': 4,  # Alias
    'Otro': 5,
}

class ZipService:
    """
    Servicio para generar ZIPs en streaming con estructura TALE oficial
    
    Estructura del ZIP:
    {CODIGO_PROYECTO}.zip
    ├── _00_INFO_TALE/
    │   ├── logo_tale.png
    │   └── README.pdf
    ├── {TIPO_UNIDAD}-{CODIGO_UNIDAD} - {NOMBRE_CLIENTE}/
    │   ├── {PROYECTO}_{PROFORMA}_{CLIENTE}_{TIPO_DOC}_{TIPO_UNIDAD}-{CODIGO_UNIDAD}.pdf
    │   └── ...
    └── FAILED_FILES.txt (solo si hubo errores)
    """
    
    @staticmethod
    def _get_doc_sort_key(doc: Dict[str, Any]) -> Tuple:
        """
        Genera clave de ordenamiento para documentos
        
        Orden TALE OFICIAL:
        1. Por tipo de documento (Voucher, Minuta, Adenda, Carta de Aprobación, Otro)
        2. Por fecha de carga DESCENDENTE (más reciente primero dentro del mismo tipo)
        
        Args:
            doc: Documento con metadata
        
        Returns:
            Tupla para ordenamiento (priority ASC, fecha DESC)
        """
        tipo = doc.get('tipo_documento', 'Otro')
        fecha = doc.get('fecha_carga', '1900-01-01')
        
        # Normalizar tipo
        tipo_normalized = tipo.replace(' ', '')
        
        # Obtener prioridad
        priority = DOCUMENT_TYPE_ORDER.get(tipo, DOCUMENT_TYPE_ORDER.get(tipo_normalized, 99))
        
        # Invertir fecha para orden descendente (usar negación o reverse)
        # Como fecha es string YYYY-MM-DD, invertir alfabéticamente funciona
        return (priority, fecha[::-1])  # Invertir string para DESC
    
    @staticmethod
    def _group_documents_by_folder(documents: List[Dict[str, Any]], project_code: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa documentos por carpeta (unidad + cliente)
        
        Args:
            documents: Lista de documentos
            project_code: Código del proyecto
        
        Returns:
            Diccionario {folder_path: [documentos]}
        """
        grouped = defaultdict(list)
        
        for doc in documents:
            folder_path = generate_folder_path(doc, project_code)
            grouped[folder_path].append(doc)
        
        # Ordenar documentos dentro de cada carpeta
        for folder in grouped:
            grouped[folder].sort(key=ZipService._get_doc_sort_key)
        
        return dict(grouped)
    
    @staticmethod
    def _add_info_folder(zip_file: zipfile.ZipFile) -> None:
        """
        Agrega carpeta _00_INFO_TALE con archivos informativos
        
        Args:
            zip_file: ZipFile donde agregar
        """
        # README.txt con información del ZIP
        fecha_generacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        readme_content = f"""
╔════════════════════════════════════════════════════════════════╗
║                    TALE INMOBILIARIA                           ║
║                  Exportación Documental                        ║
╚════════════════════════════════════════════════════════════════╝

Fecha de generación: {fecha_generacion}

ESTRUCTURA DEL ZIP:
-------------------
Cada carpeta representa una unidad vendida:
  {{TIPO_UNIDAD}}-{{CODIGO_UNIDAD}} - {{NOMBRE_CLIENTE}}/

ARCHIVOS:
---------
Los archivos siguen el formato:
  {{PROYECTO}}_{{PROFORMA}}_{{DNI_CLIENTE}}_{{TIPO_DOCUMENTO}}_{{UNIDAD}}.pdf

TIPOS DE DOCUMENTO:
------------------
• Voucher: Comprobantes de pago
• Minuta: Acuerdos contractuales
• Adenda: Modificaciones contractuales
• Carta de Aprobación: Aprobaciones oficiales
• Otro: Documentación adicional

Para más información: www.taleinmobiliaria.com
Soporte: soporte@taleinmobiliaria.com
""".encode('utf-8')
        
        zip_file.writestr("_00_INFO_TALE/README.txt", readme_content)
        
        logger.info("[ZIP] Added _00_INFO_TALE folder")
    
    @staticmethod
    def create_zip(documents: List[Dict[str, Any]], project_code: str = None) -> io.BytesIO:
        """
        Crea un ZIP en streaming con documentos organizados según estructura TALE
        
        Args:
            documents: Lista de documentos con metadata de BI
            project_code: Código del proyecto (para logs y contexto)
        
        Returns:
            BytesIO con el contenido del ZIP listo para streaming
        """
        zip_buffer = io.BytesIO()
        failed_files = []
        processed_count = 0
        total_docs = len(documents)
        
        start_time = time.time()
        logger.info(f"[ZIP] Starting ZIP generation: Project={project_code or 'UNKNOWN'}, Total Docs={total_docs}")
        
        # Agrupar documentos por carpeta
        grouped_docs = ZipService._group_documents_by_folder(documents, project_code or 'PROJECT')
        logger.info(f"[ZIP] Grouped into {len(grouped_docs)} folders")
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Agregar carpeta de información
            ZipService._add_info_folder(zip_file)
            
            # 2. Procesar cada carpeta (ordenadas alfabéticamente)
            for folder_path in sorted(grouped_docs.keys()):
                folder_docs = grouped_docs[folder_path]
                logger.info(f"[ZIP] Processing folder: {folder_path} ({len(folder_docs)} docs)")
                
                # Procesar cada documento en la carpeta
                for idx, doc in enumerate(folder_docs, 1):
                    processed_count += 1
                    codigo_proforma = doc.get('codigo_proforma', 'UNKNOWN')
                    tipo_doc = doc.get('tipo_documento', 'Otro')
                    
                    try:
                        # Descargar archivo
                        url = doc.get('url', '')
                        if not url:
                            raise ValueError("Missing URL")
                        
                        content = download_service.download_file(url)
                        if not content:
                            raise ValueError("Download failed")
                        
                        # Convertir a PDF
                        pdf_content = pdf_service.convert_to_pdf(content)
                        if not pdf_content:
                            raise ValueError("PDF conversion failed")
                        
                        # Generar nombre de archivo
                        filename = generate_filename(doc)
                        
                        # Ruta completa dentro del ZIP
                        zip_path = f"{folder_path}/{filename}"
                        
                        # Agregar al ZIP
                        zip_file.writestr(zip_path, pdf_content)
                        
                        logger.info(f"[ZIP] ✓ {processed_count}/{total_docs} | {tipo_doc} | {folder_path}/{filename}")
                        
                    except Exception as e:
                        error_msg = f"{codigo_proforma} | {tipo_doc} | {str(e)}"
                        failed_files.append(error_msg)
                        logger.warning(f"[ZIP] ✗ {processed_count}/{total_docs} | FAILED: {error_msg}")
                        continue
            
            # 3. Agregar FAILED_FILES.txt si hubo errores
            if failed_files:
                failed_content = "╔════════════════════════════════════════════════════════════════╗\n"
                failed_content += "║                    ARCHIVOS NO PROCESADOS                      ║\n"
                failed_content += "╚════════════════════════════════════════════════════════════════╝\n\n"
                failed_content += f"Total de errores: {len(failed_files)}\n"
                failed_content += f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                failed_content += "PROFORMA | TIPO | ERROR\n"
                failed_content += "-" * 80 + "\n"
                for fail in failed_files:
                    failed_content += f"{fail}\n"
                
                zip_file.writestr("FAILED_FILES.txt", failed_content.encode('utf-8'))
                logger.warning(f"[ZIP] Added FAILED_FILES.txt ({len(failed_files)} errors)")
        
        zip_buffer.seek(0)
        
        success_count = total_docs - len(failed_files)
        elapsed_time = time.time() - start_time
        logger.info(f"[ZIP] Completed: {success_count}/{total_docs} successful, {len(failed_files)} failed in {elapsed_time:.2f}s")
        
        return zip_buffer

zip_service = ZipService()
