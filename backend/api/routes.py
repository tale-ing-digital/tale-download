"""
Endpoints FastAPI para TaleDownload
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check del backend"""
    redshift_connected = redshift_service.test_connection()
    return HealthResponse(
        status="healthy" if redshift_connected else "degraded",
        version=settings.VERSION,
        redshift_connected=redshift_connected
    )

@router.get("/debug/columns")
async def get_table_columns():
    """DEBUG: Obtiene las columnas de la tabla archivos"""
    try:
        columns = redshift_service.get_table_columns()
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/diagnosis")
async def diagnose_bi():
    """DEBUG: Diagnóstico completo de tablas BI disponibles"""
    try:
        diagnosis = redshift_service.diagnose_tables()
        return diagnosis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    except RuntimeError:
        return ProjectsResponse(total=0, projects=[])
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
    except RuntimeError:
        return DocumentTypesResponse(total=0, types=[])
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
    except RuntimeError:
        # No hay conexión a Redshift, devolver lista vacía
        return FilterOptionsResponse(options=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project options: {str(e)}")

@router.get("/filters/document-types", response_model=FilterOptionsResponse)
async def get_document_type_options():
    """Obtiene lista única de tipos de documento para filtro"""
    try:
        document_types = redshift_service.get_document_types()
        return FilterOptionsResponse(options=document_types)
    except RuntimeError:
        # No hay conexión a Redshift, devolver lista vacía
        return FilterOptionsResponse(options=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document type options: {str(e)}")

@router.get("/projects", response_model=ProjectListResponse)
async def get_projects():
    """Obtiene lista de proyectos con resumen"""
    try:
        projects_data = redshift_service.get_projects_summary()
        projects = [ProjectSummaryModel(**p) for p in projects_data]
        return ProjectListResponse(total=len(projects), projects=projects)
    except RuntimeError:
        # No hay conexión a Redshift, devolver lista vacía
        return ProjectListResponse(total=0, projects=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

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
    except RuntimeError:
        # No hay conexión a Redshift, devolver lista vacía
        return DocumentListResponse(total=0, documents=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

@router.get("/download/document/{codigo_proforma}")
async def download_document(codigo_proforma: str):
    """Descarga un documento individual, ya sea convertido a PDF o en su formato original."""
    try:
        doc = redshift_service.get_document_by_codigo(codigo_proforma)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        content = download_service.download_file(doc["url"])
        if not content:
            raise HTTPException(status_code=500, detail="Failed to download document from URL")

        # Extraemos el nombre original del archivo desde la URL para el fallback de extensión.
        original_filename = doc["url"].split("/")[-1].split("?")[0] # Limpia query strings

        # La función ahora devuelve un diccionario con el modo de manejo.
        result = pdf_service.convert_to_pdf(content, original_filename)
        if not result:
            raise HTTPException(status_code=500, detail=f"Failed to process document: {original_filename}")

        # --- Lógica de respuesta según el modo ---
        file_content = result["content"]
        file_extension = result["extension"]

        if result["mode"] == "pdf":
            # Modo PDF: se sirve como siempre, con el nombre de archivo generado por TALE.
            filename = generate_filename(doc)
            media_type = "application/pdf"
        
        elif result["mode"] == "passthrough":
            # Modo Passthrough: usamos el nombre de archivo TALE pero con la extensión original.
            filename_base = generate_filename(doc).rsplit(".", 1)[0]
            filename = f"{filename_base}{file_extension}"
            
            # Mapeo de Content-Type para archivos Office.
            content_type_map = {
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".doc": "application/msword",
            }
            media_type = content_type_map.get(file_extension, "application/octet-stream")
        
        else:
            raise HTTPException(status_code=500, detail="Unknown processing mode")

        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )

    except HTTPException:
        raise
    except Exception as e:
        # Captura de error más detallada para debugging.
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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
        
        zip_buffer = zip_service.create_zip(documents_data, project_code=request.project_code)
        
        filename = f"{request.project_code or 'tale_documents'}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating ZIP: {str(e)}")

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
