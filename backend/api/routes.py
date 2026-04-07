"""
Endpoints FastAPI para TaleDownload
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
from backend.api.models import (
    DocumentListResponse,
    ProjectListResponse,
    ProjectsResponse,
    DocumentTypesResponse,
    HealthResponse,
    FilterOptionsResponse,
    DownloadZipRequest,
    DocumentModel,
    ProjectSummaryModel,
    ProjectModel,
    DocumentTypeModel,
    TipoUnidadModel,
    TipoUnidadResponse,
    TipoUnidadHomologado,
    TIPO_UNIDAD_LABELS,
)
from backend.services.redshift_service import redshift_service
from backend.services.download_service import download_service
from backend.services.pdf_service import pdf_service
from backend.services.zip_service import zip_service
from backend.utils.file_naming import generate_filename
from backend.core.config import settings

router = APIRouter(prefix="/api", tags=["TaleDownload"])



@router.get("/projects/all", response_model=ProjectsResponse)
async def get_all_projects():
    """Obtiene lista de proyectos con nombres (DIM)"""
    try:
        projects = redshift_service.get_projects_with_names()
        return ProjectsResponse(total=len(projects), projects=[
            ProjectModel(
                codigo_proyecto=p['codigo_proyecto'],
                nombre_proyecto=p['nombre_proyecto'],
                total_documentos=p.get('total_documentos'),
                ultima_fecha_carga=str(p.get('ultima_fecha_carga')) if p.get('ultima_fecha_carga') else None
            ) for p in projects
        ])
    except RuntimeError as e:
        return JSONResponse(
            status_code=503,
            content={"detail": "Redshift connection unavailable", "error": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@router.get("/document-types/all", response_model=DocumentTypesResponse)
async def get_all_document_types():
    """Obtiene lista de tipos de documento homologados"""
    try:
        doc_types = redshift_service.get_document_types_homologated()
        return DocumentTypesResponse(total=len(doc_types), types=[
            DocumentTypeModel(tipo_documento=t['tipo_documento']) for t in doc_types
        ])
    except RuntimeError as e:
        return JSONResponse(
            status_code=503,
            content={"detail": "Redshift connection unavailable", "error": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document types: {str(e)}")


@router.get("/unit-types/all", response_model=TipoUnidadResponse)
async def get_all_unit_types():
    """
    Obtiene lista de tipos de unidad homologados (códigos canónicos).
    
    Códigos disponibles:
    - DPTO: Departamento (incluye duplex, loft, etc.)
    - EST: Estacionamiento (incluye moto, doble, con depósito, etc.)
    - DEP: Depósito
    - LC: Local Comercial
    - GAB: Gabinete
    
    Nota: SIN_DATA y OTRO son solo para robustez, normalmente no aparecen.
    """
    # Solo exponer los tipos principales (excluir SIN_DATA y OTRO)
    main_types = [
        TipoUnidadHomologado.DPTO,
        TipoUnidadHomologado.EST,
        TipoUnidadHomologado.DEP,
        TipoUnidadHomologado.LC,
        TipoUnidadHomologado.GAB,
    ]
    
    tipos = [
        TipoUnidadModel(codigo=t.value, label=TIPO_UNIDAD_LABELS[t])
        for t in main_types
    ]
    
    return TipoUnidadResponse(total=len(tipos), tipos=tipos)


@router.get("/filters/projects", response_model=FilterOptionsResponse)
async def get_project_options(q: Optional[str] = None, limit: int = 50):
    """Obtiene lista única de códigos de proyecto para filtro con búsqueda opcional"""
    try:
        project_codes = redshift_service.get_project_codes(search_query=q, limit=limit)
        return FilterOptionsResponse(options=project_codes)
    except RuntimeError as e:
        return JSONResponse(
            status_code=503,
            content={"detail": "Redshift connection unavailable", "error": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project options: {str(e)}")



@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    project_code: Optional[str] = None,
    document_types: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 25,
    offset: int = 0
):
    """Obtiene lista de documentos con filtros opcionales y paginación"""
    try:
        # Convertir CSV a lista
        doc_type_list = None
        if document_types:
            doc_type_list = [t.strip() for t in document_types.split(',') if t.strip()]
        
        documents_data = redshift_service.get_documents(
            project_code=project_code,
            document_types=doc_type_list,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        documents = [DocumentModel(**d) for d in documents_data]
        return DocumentListResponse(total=len(documents), documents=documents)
    except RuntimeError as e:
        return JSONResponse(
            status_code=503,
            content={"detail": "Redshift connection unavailable", "error": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")


@router.get("/download/zip/project/{project_code}")
async def download_project_zip(
    project_code: str,
    document_types: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Descarga ZIP de todos los documentos de un proyecto con filtros opcionales
    
    Args:
        project_code: Código del proyecto
        document_types: Tipos de documento separados por coma (Voucher,Minuta,Adenda...)
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)
    """
    try:
        # Parsear tipos de documento
        doc_type_list = None
        if document_types:
            doc_type_list = [t.strip() for t in document_types.split(',') if t.strip()]
        
        documents_data = redshift_service.get_documents(
            project_code=project_code,
            document_types=doc_type_list,
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        if not documents_data:
            raise HTTPException(status_code=404, detail=f"No documents found for project {project_code}")
        
        zip_buffer = zip_service.create_zip(documents_data, project_code=project_code)
        
        filename = f"{project_code}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project ZIP: {str(e)}")
