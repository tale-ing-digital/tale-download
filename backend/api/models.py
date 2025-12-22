"""
Modelos Pydantic para request/response de la API
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from enum import Enum


class TipoUnidadHomologado(str, Enum):
    """
    Códigos canónicos de tipo de unidad.
    Prioridad de match: LC > DPTO > EST > DEP > GAB > OTRO
    """
    DPTO = "DPTO"           # Departamento (incluye duplex, loft, etc.)
    EST = "EST"             # Estacionamiento (incluye moto, doble, con depósito, etc.)
    DEP = "DEP"             # Depósito (solo cuando NO es estacionamiento)
    LC = "LC"               # Local Comercial
    GAB = "GAB"             # Gabinete
    SIN_DATA = "SIN_DATA"   # NULL o vacío
    OTRO = "OTRO"           # Cualquier otro valor


# Labels amigables para UI
TIPO_UNIDAD_LABELS = {
    TipoUnidadHomologado.DPTO: "Departamento",
    TipoUnidadHomologado.EST: "Estacionamiento",
    TipoUnidadHomologado.DEP: "Depósito",
    TipoUnidadHomologado.LC: "Local Comercial",
    TipoUnidadHomologado.GAB: "Gabinete",
    TipoUnidadHomologado.SIN_DATA: "Sin Datos",
    TipoUnidadHomologado.OTRO: "Otro",
}

# Backward compatibility: mapeo de códigos antiguos a canónicos
TIPO_UNIDAD_LEGACY_MAP = {
    "LOC": TipoUnidadHomologado.LC,
    "LOCAL": TipoUnidadHomologado.LC,
    "ESTAC": TipoUnidadHomologado.EST,
    "OFIC": TipoUnidadHomologado.LC,
    "TIENDA": TipoUnidadHomologado.LC,
    "UNIDAD": TipoUnidadHomologado.OTRO,
}


def normalize_tipo_unidad(value: str) -> str:
    """
    Normaliza un tipo de unidad a su código canónico.
    Soporta backward compatibility con códigos legacy (LOC → LC, ESTAC → EST, etc.)
    """
    if not value:
        return TipoUnidadHomologado.SIN_DATA.value
    
    value_upper = value.upper().strip()
    
    # Verificar si ya es canónico
    if value_upper in [e.value for e in TipoUnidadHomologado]:
        return value_upper
    
    # Backward compatibility
    if value_upper in TIPO_UNIDAD_LEGACY_MAP:
        return TIPO_UNIDAD_LEGACY_MAP[value_upper].value
    
    return value_upper


class DocumentModel(BaseModel):
    """Modelo de documento"""
    codigo_proforma: Optional[str] = None
    documento_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    codigo_proyecto: Optional[str] = None
    codigo_unidad: Optional[str] = None
    tipo_unidad: Optional[str] = None  # Código homologado: DPTO, EST, DEP, LC, GAB, SIN_DATA, OTRO
    url: Optional[str] = None
    nombre_archivo: Optional[str] = None
    fecha_carga: Optional[str] = None
    tipo_documento: Optional[str] = None
    
    @field_validator('tipo_unidad', mode='before')
    @classmethod
    def normalize_tipo_unidad_field(cls, v):
        """Normaliza tipo_unidad a código canónico"""
        return normalize_tipo_unidad(v) if v else None

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


class TipoUnidadModel(BaseModel):
    """Modelo de tipo de unidad homologado"""
    codigo: str  # Código canónico: DPTO, EST, DEP, LC, GAB
    label: str   # Label amigable para UI


class TipoUnidadResponse(BaseModel):
    """Respuesta de tipos de unidad homologados"""
    total: int
    tipos: List[TipoUnidadModel]


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
