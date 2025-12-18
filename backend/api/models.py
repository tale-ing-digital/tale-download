"""
Modelos Pydantic para request/response de la API
"""
from pydantic import BaseModel
from typing import Optional, List

class DocumentModel(BaseModel):
    """Modelo de documento"""
    codigo_proforma: str
    documento_cliente: str
    codigo_proyecto: str
    codigo_unidad: str
    url: str
    nombre_archivo: str
    fecha_carga: str
    tipo_documento: str

class ProjectSummaryModel(BaseModel):
    """Modelo de resumen de proyecto"""
    codigo_proyecto: str
    total_documentos: int
    ultima_actualizacion: str

class DocumentListResponse(BaseModel):
    """Respuesta de lista de documentos"""
    total: int
    documents: List[DocumentModel]

class ProjectListResponse(BaseModel):
    """Respuesta de lista de proyectos"""
    total: int
    projects: List[ProjectSummaryModel]

class HealthResponse(BaseModel):
    """Respuesta de health check"""
    status: str
    version: str
    redshift_connected: bool

class FilterOptionsResponse(BaseModel):
    """Respuesta de opciones de filtros"""
    options: List[str]

class DownloadZipRequest(BaseModel):
    """Request para descarga de ZIP con filtros"""
    project_code: Optional[str] = None
    document_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    document_ids: Optional[List[str]] = None
