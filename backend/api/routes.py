"""
Endpoints FastAPI para TaleDownload
"""
import asyncio
import logging
import time
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from typing import Optional
from backend.services import job_store
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
logger = logging.getLogger(__name__)


def _remaining_time(deadline: float) -> float:
    """Returns remaining time in seconds with a 1s minimum guard."""
    return max(1.0, deadline - time.monotonic())



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
    request_id = uuid.uuid4().hex[:8]
    t_total_start = time.perf_counter()
    deadline = time.monotonic() + settings.ZIP_REQUEST_TIMEOUT_SEC

    try:
        # Parsear tipos de documento
        doc_type_list = None
        if document_types:
            # Preserve order and remove duplicates to avoid accidental query expansion
            doc_type_list = list(dict.fromkeys(t.strip() for t in document_types.split(',') if t.strip()))

        logger.info(
            "[ZIP:%s] START project=%s types=%s start_date=%s end_date=%s timeout_total=%ss",
            request_id,
            project_code,
            doc_type_list,
            start_date,
            end_date,
            settings.ZIP_REQUEST_TIMEOUT_SEC,
        )

        t_redshift_start = time.perf_counter()
        documents_data = await asyncio.wait_for(
            asyncio.to_thread(
                redshift_service.get_documents,
                project_code=project_code,
                document_types=doc_type_list,
                start_date=start_date,
                end_date=end_date,
                limit=100000,
            ),
            timeout=min(settings.ZIP_REDSHIFT_TIMEOUT_SEC, _remaining_time(deadline)),
        )
        redshift_elapsed = time.perf_counter() - t_redshift_start

        logger.info(
            "[ZIP:%s] REDSHIFT_OK docs=%s elapsed=%.2fs",
            request_id,
            len(documents_data),
            redshift_elapsed,
        )
        
        if not documents_data:
            raise HTTPException(status_code=404, detail=f"No documents found for project {project_code}")

        t_zip_start = time.perf_counter()
        zip_buffer = await asyncio.wait_for(
            asyncio.to_thread(
                zip_service.create_zip,
                documents_data,
                project_code=project_code,
                request_id=request_id,
            ),
            timeout=min(settings.ZIP_GENERATION_TIMEOUT_SEC, _remaining_time(deadline)),
        )
        zip_elapsed = time.perf_counter() - t_zip_start

        logger.info(
            "[ZIP:%s] ZIP_OK elapsed=%.2fs",
            request_id,
            zip_elapsed,
        )
        
        filename = f"{project_code}.zip"

        total_elapsed = time.perf_counter() - t_total_start
        logger.info(
            "[ZIP:%s] COMPLETE project=%s total_elapsed=%.2fs docs=%s",
            request_id,
            project_code,
            total_elapsed,
            len(documents_data),
        )
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except asyncio.TimeoutError:
        total_elapsed = time.perf_counter() - t_total_start
        logger.error(
            "[ZIP:%s] TIMEOUT project=%s total_elapsed=%.2fs",
            request_id,
            project_code,
            total_elapsed,
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "La descarga excedio el tiempo de espera del servidor. "
                "Intente con menos tipos o un rango de fechas mas corto."
            ),
        )
    except RuntimeError as e:
        logger.error("[ZIP:%s] REDSHIFT_UNAVAILABLE error=%s", request_id, str(e))
        return JSONResponse(
            status_code=503,
            content={"detail": "Redshift connection unavailable", "error": str(e)},
        )
    except HTTPException:
        raise
    except Exception as e:
        total_elapsed = time.perf_counter() - t_total_start
        logger.exception(
            "[ZIP:%s] FAILED project=%s total_elapsed=%.2fs",
            request_id,
            project_code,
            total_elapsed,
        )
        raise HTTPException(status_code=500, detail=f"Error creating project ZIP: {str(e)}")


# ============================================================================
# BACKGROUND JOB ENDPOINTS  (/api/jobs/*)
# ============================================================================
# These endpoints allow long-running ZIP builds to run in the background so
# the HTTP connection is freed immediately. The client polls /status every few
# seconds and auto-downloads when status == "done".
#
# Why this is necessary:
#   S3 (Sperant) serves files at ~17 s each. With 100+ documents a synchronous
#   request exceeds the ZIP_REQUEST_TIMEOUT_SEC limit and the proxy's idle
#   timeout, resulting in a 504. Background jobs remove that ceiling entirely.
# ============================================================================

@router.post("/jobs/zip")
async def submit_zip_job(
    background_tasks: BackgroundTasks,
    project_code: str,
    document_types: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Enqueue a ZIP build job and return a job_id immediately.

    The client should then poll GET /api/jobs/{job_id}/status every few seconds
    and trigger GET /api/jobs/{job_id}/download when status == 'done'.
    """
    job_id = uuid.uuid4().hex[:12]
    job_store.put_job(job_id, project_code)
    background_tasks.add_task(
        _run_zip_job,
        job_id=job_id,
        project_code=project_code,
        document_types=document_types,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(
        "[JOB:%s] Enqueued project=%s types=%s start=%s end=%s",
        job_id, project_code, document_types, start_date, end_date,
    )
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}/status")
async def get_zip_job_status(job_id: str):
    """
    Return current progress for a ZIP job.

    Response: { job_id, status, done, total, pct, error }
      status: "queued" | "processing" | "done" | "error"
      done / total: file counts (0/0 while queued / during Redshift phase)
      pct: integer 0-100
    """
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    total = job.get("total", 0)
    done = job.get("done", 0)
    pct = int(done * 100 / total) if total > 0 else 0
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "done": done,
        "total": total,
        "pct": pct,
        "error": job.get("error"),
    }


@router.get("/jobs/{job_id}/download")
async def download_zip_job_file(job_id: str):
    """
    Stream the completed ZIP file. Only available when status == 'done'.
    The file will remain available for ~20 minutes after completion.
    """
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"ZIP is not ready yet (status={job['status']})",
        )
    zip_path = job_store.get_zip_path(job_id)
    if zip_path is None:
        raise HTTPException(status_code=410, detail="ZIP file expired or was already deleted")

    project_code = job["project_code"]
    filename = f"{project_code}.zip"

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _run_zip_job(
    job_id: str,
    project_code: str,
    document_types: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> None:
    """
    Background coroutine that executes the Redshift query + ZIP generation
    and updates the job state at each phase.
    """
    request_id = job_id[:8]
    try:
        job_store.update_job(job_id, status="processing")

        # Normalize document types
        doc_type_list = None
        if document_types:
            doc_type_list = list(
                dict.fromkeys(t.strip() for t in document_types.split(",") if t.strip())
            )

        logger.info(
            "[JOB:%s] START project=%s types=%s start=%s end=%s",
            job_id, project_code, doc_type_list, start_date, end_date,
        )

        # ── Phase 1: Redshift query ──────────────────────────────────────────
        try:
            documents_data = await asyncio.wait_for(
                asyncio.to_thread(
                    redshift_service.get_documents,
                    project_code=project_code,
                    document_types=doc_type_list,
                    start_date=start_date,
                    end_date=end_date,
                    limit=100000,
                ),
                timeout=settings.ZIP_REDSHIFT_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            job_store.set_job_error(
                job_id,
                "Timeout consultando Redshift. Intente con un rango de fechas más corto.",
            )
            logger.error("[JOB:%s] REDSHIFT_TIMEOUT", job_id)
            return
        except RuntimeError as e:
            job_store.set_job_error(job_id, f"Base de datos no disponible: {e}")
            logger.error("[JOB:%s] REDSHIFT_UNAVAILABLE error=%s", job_id, e)
            return

        if not documents_data:
            job_store.set_job_error(
                job_id,
                f"No se encontraron documentos para el proyecto {project_code} con los filtros seleccionados.",
            )
            return

        total = len(documents_data)
        job_store.update_job(job_id, total=total, done=0)
        logger.info("[JOB:%s] REDSHIFT_OK docs=%s", job_id, total)

        # ── Phase 2: ZIP generation ──────────────────────────────────────────
        # No asyncio timeout here — the job runs in background, time pressure is gone.
        def _progress(done: int, total_: int) -> None:
            job_store.update_job(job_id, done=done, total=total_)

        try:
            zip_buffer = await asyncio.to_thread(
                zip_service.create_zip,
                documents_data,
                project_code=project_code,
                request_id=request_id,
                progress_callback=_progress,
            )
        except Exception as e:
            job_store.set_job_error(job_id, f"Error generando ZIP: {e}")
            logger.exception("[JOB:%s] ZIP_FAIL", job_id)
            return

        job_store.set_job_done(job_id, zip_buffer)
        logger.info("[JOB:%s] DONE project=%s docs=%s", job_id, project_code, total)

        # Cleanup expired jobs opportunistically
        removed = job_store.cleanup_old_jobs()
        if removed:
            logger.info("[JOB] Cleaned up %s expired job(s)", removed)

    except Exception as e:
        job_store.set_job_error(job_id, f"Error inesperado: {e}")
        logger.exception("[JOB:%s] UNEXPECTED_ERROR", job_id)

