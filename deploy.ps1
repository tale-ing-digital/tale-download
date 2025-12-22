# ============================================================================
# SCRIPT DE DESPLIEGUE TALE DOWNLOAD
# ============================================================================
# Limpia caché, reconstruye imagen y lanza contenedor con últimos cambios
# ============================================================================

param(
    [switch]$SkipBuild = $false,
    [switch]$ViewLogs = $false
)

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  🚀 TALE DOWNLOAD - DESPLIEGUE LIMPIO" -ForegroundColor White
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Función para verificar si Docker está corriendo
function Test-DockerRunning {
    try {
        docker ps > $null 2>&1
        return $true
    }
    catch {
        return $false
    }
}

# Verificar Docker
if (-not (Test-DockerRunning)) {
    Write-Host "❌ Docker no está corriendo. Por favor, inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

# PASO 1: Detener y eliminar contenedores
Write-Host "🟦 PASO 1 - Deteniendo y eliminando contenedores antiguos..." -ForegroundColor Cyan
docker stop tale-download tale-backend 2>$null | Out-Null
docker rm tale-download tale-backend tale-v1 tale-prod tale-bi tale-diagnose tale-app tale-download-final tale-download-latest tale-download-prod 2>$null | Out-Null
Write-Host "   ✓ Contenedores eliminados" -ForegroundColor Green
Write-Host ""

if (-not $SkipBuild) {
    # PASO 2: Limpiar caché de frontend
    Write-Host "🟦 PASO 2 - Limpiando caché de frontend..." -ForegroundColor Cyan
    
    if (Test-Path "client/dist") {
        Remove-Item -Recurse -Force "client/dist"
        Write-Host "   ✓ dist/ eliminado" -ForegroundColor Green
    }
    
    if (Test-Path "client/node_modules/.vite") {
        Remove-Item -Recurse -Force "client/node_modules/.vite"
        Write-Host "   ✓ .vite/ eliminado" -ForegroundColor Green
    }
    
    Write-Host ""

    # PASO 3: Eliminar imágenes antiguas
    Write-Host "🟦 PASO 3 - Eliminando imágenes Docker antiguas..." -ForegroundColor Cyan
    docker rmi tale-download:latest 2>$null | Out-Null
    docker image prune -f | Out-Null
    Write-Host "   ✓ Imágenes antiguas eliminadas" -ForegroundColor Green
    Write-Host ""

    # PASO 4: Reconstruir imagen SIN CACHE
    Write-Host "🟦 PASO 4 - Reconstruyendo imagen SIN CACHE..." -ForegroundColor Cyan
    Write-Host "   ⚠️  Este paso puede tomar 2-3 minutos..." -ForegroundColor Yellow
    Write-Host ""
    
    $buildResult = docker build --no-cache -f Containerfile -t tale-download:latest . 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Imagen reconstruida exitosamente" -ForegroundColor Green
    }
    else {
        Write-Host "   ❌ Error al reconstruir imagen" -ForegroundColor Red
        Write-Host $buildResult
        exit 1
    }
    Write-Host ""
}

# PASO 5: Levantar contenedor
Write-Host "🟦 PASO 5 - Levantando contenedor nuevo..." -ForegroundColor Cyan

# Verificar que existe .env
if (-not (Test-Path ".env")) {
    Write-Host "   ❌ Archivo .env no encontrado" -ForegroundColor Red
    Write-Host "   Crea un archivo .env con las credenciales de Redshift" -ForegroundColor Yellow
    exit 1
}

docker run -d `
    --name tale-download `
    -p 8080:8080 `
    --env-file .env `
    tale-download:latest | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Contenedor levantado en puerto 8080" -ForegroundColor Green
}
else {
    Write-Host "   ❌ Error al levantar contenedor" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Esperar a que el contenedor esté listo
Write-Host "⏳ Esperando que el contenedor esté listo..." -ForegroundColor Yellow
Start-Sleep 4

# Verificar estado del contenedor
$containerStatus = docker inspect -f '{{.State.Status}}' tale-download 2>$null

if ($containerStatus -eq "running") {
    Write-Host "✅ Contenedor corriendo correctamente" -ForegroundColor Green
}
else {
    Write-Host "❌ Contenedor no está corriendo. Estado: $containerStatus" -ForegroundColor Red
    Write-Host ""
    Write-Host "Logs del contenedor:" -ForegroundColor Yellow
    docker logs tale-download --tail 50
    exit 1
}

Write-Host ""

# Verificar health check
Write-Host "🔍 Verificando health check..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/api/health" -Method Get
    
    if ($health.status -eq "healthy") {
        Write-Host "   ✓ API responde correctamente" -ForegroundColor Green
        Write-Host "   ✓ Redshift conectado: $($health.redshift_connected)" -ForegroundColor Green
        Write-Host "   ✓ Versión: $($health.version)" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  API responde pero estado: $($health.status)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "   ⚠️  No se pudo verificar health check (el contenedor puede estar iniciando)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  ✅ DESPLIEGUE COMPLETADO" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🌐 Frontend: http://localhost:8080" -ForegroundColor White
Write-Host "  📡 API:      http://localhost:8080/api" -ForegroundColor White
Write-Host "  📄 Docs:     http://localhost:8080/docs" -ForegroundColor White
Write-Host ""
Write-Host "  📋 Ver logs:    docker logs -f tale-download" -ForegroundColor Gray
Write-Host "  🛑 Detener:     docker stop tale-download" -ForegroundColor Gray
Write-Host "  🔄 Reiniciar:   docker restart tale-download" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Si se solicitó ver logs
if ($ViewLogs) {
    Write-Host "📋 Mostrando logs en tiempo real (Ctrl+C para salir)..." -ForegroundColor Yellow
    Write-Host ""
    docker logs -f tale-download
}
