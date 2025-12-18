"""
Endpoints FastAPI para TaleDownload
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from backend.api.models import (
    DocumentListResponse,
    ProjectListResponse,
    HealthResponse,
    FilterOptionsResponse,
    DownloadZipRequest,
    DocumentModel,
    ProjectSummaryModel
)
from backend.services.redshift_service import redshift_service
from backend.services.download_service import download_service
from backend.services.pdf_service import pdf_service
from backend.services.zip_service import zip_service
from backend.utils.file_naming import generate_filename
from backend.core.config import settings

router = APIRouter(prefix="/api", tags=["TaleDownload"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check del backend"""
    redshift_connected = redshift_service.test_connection()
    return HealthResponse(
        status="healthy" if redshift_connected else "degraded",
        version=settings.VERSION,
        redshift_connected=redshift_connected
    )

@router.get("/filters/projects", response_model=FilterOptionsResponse)
async def get_project_options():
    """Obtiene lista única de códigos de proyecto para filtro"""
    try:
        project_codes = redshift_service.get_project_codes()
        return FilterOptionsResponse(options=project_codes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project options: {str(e)}")

@router.get("/filters/document-types", response_model=FilterOptionsResponse)
async def get_document_type_options():
    """Obtiene lista única de tipos de documento para filtro"""
    try:
        document_types = redshift_service.get_document_types()
        return FilterOptionsResponse(options=document_types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document type options: {str(e)}")

@router.get("/projects", response_model=ProjectListResponse)
async def get_projects():
    """Obtiene lista de proyectos con resumen"""
    try:
        projects_data = redshift_service.get_projects_summary()
        projects = [ProjectSummaryModel(**p) for p in projects_data]
        return ProjectListResponse(total=len(projects), projects=projects)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    project_code: Optional[str] = None,
    document_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 25,
    offset: int = 0
):
    """Obtiene lista de documentos con filtros opcionales y paginación"""
    try:
        documents_data = redshift_service.get_documents(
            project_code=project_code,
            document_type=document_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        documents = [DocumentModel(**d) for d in documents_data]
        return DocumentListResponse(total=len(documents), documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

@router.get("/download/document/{codigo_proforma}")
async def download_document(codigo_proforma: str):
    """Descarga un documento individual como PDF"""
    try:
        doc = redshift_service.get_document_by_codigo(codigo_proforma)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = download_service.download_file(doc['url'])
        if not content:
            raise HTTPException(status_code=500, detail="Failed to download document")
        
        pdf_content = pdf_service.convert_to_pdf(content)
        if not pdf_content:
            raise HTTPException(status_code=500, detail="Failed to convert to PDF")
        
        filename = generate_filename(doc)
        
        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading document: {str(e)}")

@router.post("/download/zip")
async def download_zip(request: DownloadZipRequest):
    """Descarga ZIP con documentos filtrados"""
    try:
        if request.document_ids:
            documents_data = [
                redshift_service.get_document_by_codigo(doc_id)
                for doc_id in request.document_ids
            ]
            documents_data = [d for d in documents_data if d is not None]
        else:
            if not any([request.project_code, request.document_type, request.start_date, request.end_date]):
                raise HTTPException(status_code=400, detail="At least one filter is required")
            
            documents_data = redshift_service.get_documents(
                project_code=request.project_code,
                document_type=request.document_type,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=1000
            )
        
        if not documents_data:
            raise HTTPException(status_code=404, detail="No documents found matching filters")
        
        zip_buffer = zip_service.create_zip(documents_data)
        
        filename = f"{request.project_code or 'tale_documents'}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.read()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating ZIP: {str(e)}")

@router.get("/download/zip/project/{project_code}")
async def download_project_zip(project_code: str):
    """Descarga ZIP de todos los documentos de un proyecto"""
    try:
        documents_data = redshift_service.get_documents(
            project_code=project_code,
            limit=1000
        )
        
        if not documents_data:
            raise HTTPException(status_code=404, detail=f"No documents found for project {project_code}")
        
        zip_buffer = zip_service.create_zip(documents_data)
        
        filename = f"{project_code}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.read()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project ZIP: {str(e)}")
