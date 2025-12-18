"""
Aplicación principal FastAPI para TaleDownload
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.core.config import settings

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

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("=" * 80)
    print("🚀 TaleDownload Backend Starting...")
    print("=" * 80)
    
    try:
        settings.validate()
        print("✅ Environment variables validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("⚠️  Backend will start but may not function correctly")
    
    print(f"📊 Version: {settings.VERSION}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"📁 Max file size: {settings.MAX_FILE_SIZE_MB}MB")
    print("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    print("=" * 80)
    print("🛑 TaleDownload Backend Shutting Down...")
    print("=" * 80)
    
    from backend.services.redshift_service import redshift_service
    redshift_service.close()

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG
    )
