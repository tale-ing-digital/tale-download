"""
Modelos Pydantic para request/response de la API
"""
from pydantic import BaseModel
from typing import Optional, List

class DocumentModel(BaseModel):
    """Modelo de documento"""
    codigo_proforma: Optional[str] = None
    documento_cliente: Optional[str] = None
    codigo_proyecto: Optional[str] = None
    codigo_unidad: Optional[str] = None
    url: Optional[str] = None
    nombre_archivo: Optional[str] = None
    fecha_carga: Optional[str] = None
    tipo_documento: Optional[str] = None

class ProjectModel(BaseModel):
    """Modelo de proyecto (DIM)"""
    codigo_proyecto: str
    nombre_proyecto: str
    total_documentos: Optional[int] = None
    ultima_fecha_carga: Optional[str] = None

class ProjectSummaryModel(BaseModel):
    """Modelo de resumen de proyecto"""
    codigo_proyecto: str
    total_documentos: int
    ultima_actualizacion: str

class DocumentTypeModel(BaseModel):
    """Modelo de tipo de documento homologado"""
    tipo_documento: str
    descripcion: Optional[str] = None

class DocumentListResponse(BaseModel):
    """Respuesta de lista de documentos"""
    total: int
    documents: List[DocumentModel]

class ProjectListResponse(BaseModel):
    """Respuesta de lista de proyectos"""
    total: int
    projects: List[ProjectSummaryModel]

class ProjectsResponse(BaseModel):
    """Respuesta de proyectos (con nombres)"""
    total: int
    projects: List[ProjectModel]

class DocumentTypesResponse(BaseModel):
    """Respuesta de tipos de documento"""
    total: int
    types: List[DocumentTypeModel]

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
