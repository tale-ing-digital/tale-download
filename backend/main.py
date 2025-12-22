"""
Aplicación principal FastAPI para TaleDownload
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from backend.api.routes import router
from backend.core.config import settings
from backend.core.logging_config import setup_logging

# Configurar logging
logger = setup_logging(debug=settings.DEBUG)

app = FastAPI(
    title="TaleDownload API",
    description="Sistema de exportación documental desde BI (AWS Redshift)",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Servir archivos estáticos del frontend
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="static")

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    logger.info("=" * 80)
    logger.info("🚀 TaleDownload Backend Starting...")
    logger.info("=" * 80)
    
    try:
        settings.validate()
        logger.info("✅ Environment variables validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.warning("⚠️  Backend will start but may not function correctly")
    
    logger.info(f"📊 Version: {settings.VERSION}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"📁 Max file size: {settings.MAX_FILE_SIZE_MB}MB")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    logger.info("=" * 80)
    logger.info("🛑 TaleDownload Backend Shutting Down...")
    logger.info("=" * 80)
    
    from backend.services.redshift_service import redshift_service
    redshift_service.close()

if __name__ == "__main__":
    # Determinar número de workers basado en modo debug
    # En debug: 1 worker (para desarrollo)
    # En producción: 4 workers (para concurrencia)
    workers = 1 if settings.DEBUG else 4
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        workers=workers,
        reload=settings.DEBUG
    )
