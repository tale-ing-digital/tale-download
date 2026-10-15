"""
Servicio de generación de ZIPs en streaming con estructura TALE
IMPLEMENTACIÓN CONGELADA - NO MODIFICAR SIN APROBACIÓN
"""
import io
import zipfile
import logging
import time
from typing import Callable, List, Dict, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import concurrent.futures
from backend.services.download_service import download_service
from backend.services.pdf_service import pdf_service
from backend.utils.file_naming import generate_filename, generate_folder_path, TIPO_UNIDAD_CODES
from backend.core.config import settings

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

CÓDIGOS DE TIPO DE UNIDAD (Homologación Canónica):
--------------------------------------------------
• DPTO: Departamento (incluye duplex, loft, etc.)
• EST:  Estacionamiento (incluye moto, doble, etc.)
• DEP:  Depósito
• LC:   Local Comercial
• GAB:  Gabinete

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
    def _download_and_process_file(
        doc: Dict[str, Any],
        project_code: str,
        request_id: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[bytes], Optional[str], float, int]:
        """
        Función de trabajo para un solo archivo: descarga, procesa y retorna el resultado.
        Diseñada para ser ejecutada en un thread pool.
        Retorna (zip_path, content, error_message).
        """
        codigo_proforma = doc.get("codigo_proforma", "UNKNOWN")
        tipo_doc = doc.get("tipo_documento", "Otro")
        t_file_start = time.perf_counter()
        
        try:
            url = doc.get("url", "")
            if not url:
                raise ValueError("Missing document URL")

            content = download_service.download_file(url)
            if not content:
                raise ValueError("Download failed or file is empty")

            original_filename = url.split("/")[-1].split("?")[0]
            result = pdf_service.convert_to_pdf(content, original_filename)
            if not result:
                raise ValueError(f"Unsupported file type for {original_filename}")

            file_content = result["content"]
            file_extension = result["extension"]
            folder_path = generate_folder_path(doc, project_code or "PROJECT")

            if result["mode"] == "pdf":
                filename = generate_filename(doc)
            else: # passthrough
                filename_base = generate_filename(doc).rsplit(".", 1)[0]
                filename = f"{filename_base}{file_extension}"
            
            zip_path = f"{folder_path}/{filename}"
            elapsed_sec = time.perf_counter() - t_file_start
            file_size = len(file_content)
            if elapsed_sec >= settings.ZIP_SLOW_FILE_SEC:
                logger.warning(
                    "[ZIP:%s] SLOW_FILE proforma=%s tipo=%s elapsed=%.2fs size=%sB",
                    request_id or "N/A",
                    codigo_proforma,
                    tipo_doc,
                    elapsed_sec,
                    file_size,
                )
            return (zip_path, file_content, None, elapsed_sec, file_size)

        except Exception as e:
            error_msg = f"{codigo_proforma} | {tipo_doc} | {str(e)}"
            elapsed_sec = time.perf_counter() - t_file_start
            logger.warning(
                "[ZIP:%s] FILE_FAIL proforma=%s tipo=%s elapsed=%.2fs error=%s",
                request_id or "N/A",
                codigo_proforma,
                tipo_doc,
                elapsed_sec,
                str(e),
            )
            return (None, None, error_msg, elapsed_sec, 0)
    
    @staticmethod
    def create_zip(
        documents: List[Dict[str, Any]],
        project_code: str = None,
        request_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> io.BytesIO:
        """Crea un ZIP en streaming con descarga y procesamiento paralelo."""
        zip_buffer = io.BytesIO()
        failed_files = []
        total_docs = len(documents)
        total_file_elapsed = 0.0
        total_file_bytes = 0
        
        # Usar máximo 20 workers para descargas S3 paralelas (I/O bound, seguro aumentar)
        MAX_WORKERS = min(20, total_docs) if total_docs > 0 else 1

        logger.info(
            "[ZIP:%s] Starting parallel ZIP generation: Project=%s, Total Docs=%s, Workers=%s",
            request_id or "N/A",
            project_code or 'UNKNOWN',
            total_docs,
            MAX_WORKERS,
        )
        
        # Agrupar documentos por carpeta
        grouped_docs = ZipService._group_documents_by_folder(documents, project_code or 'PROJECT')
        logger.info("[ZIP:%s] Grouped into %s folders", request_id or "N/A", len(grouped_docs))
        
        # Procesar todos los documentos en paralelo
        processed_results = []
        processed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Crear lista de futures
            futures = {
                executor.submit(
                    ZipService._download_and_process_file,
                    doc,
                    project_code or 'PROJECT',
                    request_id,
                ): doc
                for doc in documents
            }
            
            # Procesar resultados conforme van terminando
            for future in concurrent.futures.as_completed(futures):
                processed_count += 1
                doc = futures[future]
                tipo_doc = doc.get("tipo_documento", "Otro")
                
                try:
                    zip_path, content, error_msg, elapsed_sec, file_size = future.result()
                    total_file_elapsed += elapsed_sec
                    total_file_bytes += file_size
                    
                    if error_msg:
                        failed_files.append(error_msg)
                        logger.warning(
                            "[ZIP:%s] ✗ %s/%s | FAILED: %s",
                            request_id or "N/A",
                            processed_count,
                            total_docs,
                            error_msg,
                        )
                    else:
                        processed_results.append((zip_path, content))
                        logger.info(
                            "[ZIP:%s] ✓ %s/%s | %s | %s | elapsed=%.2fs size=%sB",
                            request_id or "N/A",
                            processed_count,
                            total_docs,
                            tipo_doc,
                            zip_path,
                            elapsed_sec,
                            file_size,
                        )
                
                except Exception as e:
                    error_msg = f"{doc.get('codigo_proforma', 'UNKNOWN')} | {tipo_doc} | {str(e)}"
                    failed_files.append(error_msg)
                    logger.warning(
                        "[ZIP:%s] ✗ %s/%s | FAILED: %s",
                        request_id or "N/A",
                        processed_count,
                        total_docs,
                        error_msg,
                    )

                if progress_callback:
                    try:
                        progress_callback(processed_count, total_docs)
                    except Exception:
                        pass
        
        # Ahora agregar todos los resultados al ZIP (ya procesados)
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Agregar carpeta de información
            ZipService._add_info_folder(zip_file)
            
            # 2. Agregar archivos procesados (deduplicar paths para evitar sobreescritura)
            seen_paths: set = set()
            for zip_path, content in processed_results:
                if zip_path in seen_paths:
                    base, ext = zip_path.rsplit('.', 1) if '.' in zip_path.split('/')[-1] else (zip_path, '')
                    counter = 2
                    while True:
                        candidate = f"{base}_{counter}.{ext}" if ext else f"{base}_{counter}"
                        if candidate not in seen_paths:
                            zip_path = candidate
                            break
                        counter += 1
                seen_paths.add(zip_path)
                zip_file.writestr(zip_path, content)
            
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
                logger.warning("[ZIP:%s] Added FAILED_FILES.txt (%s errors)", request_id or "N/A", len(failed_files))
        
        zip_buffer.seek(0)
        
        success_count = total_docs - len(failed_files)
        avg_file_sec = (total_file_elapsed / total_docs) if total_docs > 0 else 0.0
        logger.info(
            "[ZIP:%s] Completed: %s/%s successful, %s failed, total_file_elapsed=%.2fs avg_file_elapsed=%.2fs total_bytes=%sB",
            request_id or "N/A",
            success_count,
            total_docs,
            len(failed_files),
            total_file_elapsed,
            avg_file_sec,
            total_file_bytes,
        )
        
        return zip_buffer

zip_service = ZipService()
