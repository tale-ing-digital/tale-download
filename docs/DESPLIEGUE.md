# 🚀 Guía de Despliegue - TALE Download

## ✅ CAMBIOS IMPLEMENTADOS (21 Dic 2025)

### 1. **Flujo Correcto de Filtros**
- ✅ Separación `pendingFilters` vs `appliedFilters`
- ✅ Botón "Filtrar" aplica filtros explícitamente
- ✅ Botón "Quitar filtros" limpia y vuelve al estado base
- ✅ NO hay queries reactivas (solo al presionar botones)
- ✅ Coherencia total entre "Ver documentos" y "Descargar ZIP"

### 2. **Clasificación Mejorada de Documentos**
- ✅ Normalización única con CTE
- ✅ Cortafuegos para bloquear falsos positivos
- ✅ Clasificación jerárquica (Minuta → Adenda → Carta → Voucher → Otro)
- ✅ Query reutilizable en toda la app

---

## 🧨 DESPLIEGUE RÁPIDO

### Opción 1: Script Automatizado (RECOMENDADO)

```powershell
# Despliegue completo con reconstrucción
.\deploy.ps1

# Solo reiniciar contenedor (sin reconstruir)
.\deploy.ps1 -SkipBuild

# Ver logs en tiempo real después de desplegar
.\deploy.ps1 -ViewLogs
```

### Opción 2: Manual (Paso a Paso)

#### **PASO 1 — Detener contenedores actuales**

```powershell
docker stop tale-download tale-backend 2>$null
docker rm tale-download tale-backend 2>$null
```

#### **PASO 2 — Limpiar caché de frontend**

```powershell
Remove-Item -Recurse -Force client/dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force client/node_modules/.vite -ErrorAction SilentlyContinue
```

#### **PASO 3 — Eliminar imágenes antiguas**

```powershell
docker rmi tale-download:latest 2>$null
docker image prune -f
```

#### **PASO 4 — Reconstruir imagen SIN CACHE**

```powershell
docker build --no-cache -f Containerfile -t tale-download:latest .
```

⚠️ **IMPORTANTE:** El flag `--no-cache` es crítico para ver los últimos cambios.

#### **PASO 5 — Levantar contenedor**

```powershell
docker run -d `
  --name tale-download `
  -p 8080:8080 `
  --env-file .env `
  tale-download:latest
```

---

## 🔍 VERIFICACIÓN

### 1. Verificar que el contenedor está corriendo

```powershell
docker ps | Select-String -Pattern "tale-download"
```

Deberías ver:
```
CONTAINER ID   IMAGE                  STATUS                   PORTS
8f28e53b327e   tale-download:latest   Up X minutes (healthy)   0.0.0.0:8080->8080/tcp
```

### 2. Verificar logs

```powershell
docker logs tale-download --tail 30
```

Deberías ver:
```
✅ Redshift connection pool initialized
================================================================================
🚀 TaleDownload Backend Starting...
================================================================================
✅ Environment variables validated
📊 Version: 1.0.0
```

### 3. Verificar API Health

```powershell
curl http://localhost:8080/api/health | ConvertFrom-Json
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redshift_connected": true
}
```

### 4. Verificar Frontend

Abre en el navegador:
```
http://localhost:8080
```

**Verifica estos cambios:**
- ✅ Panel de filtros tiene botón **"Filtrar"** y **"Quitar filtros"**
- ✅ Al marcar checkboxes NO se ejecutan queries automáticas
- ✅ Solo al presionar "Filtrar" se actualizan los documentos
- ✅ Badge de filtros activos muestra solo cuando hay filtros aplicados
- ✅ "Ver documentos" y "Descargar ZIP" usan los mismos filtros

---

## 🧪 TESTING DE CAMBIOS

### Test 1: Flujo de Filtros

1. **Abre** http://localhost:8080
2. **Marca** filtros (Voucher, Minuta, fechas)
   - ✅ NO debe ejecutar queries
   - ✅ NO debe cambiar contadores
3. **Presiona "Filtrar"**
   - ✅ Ahora SÍ ejecuta query
   - ✅ Badge muestra número de filtros activos
4. **Presiona "Ver documentos"**
   - ✅ Muestra solo documentos filtrados
5. **Presiona "Descargar ZIP"**
   - ✅ ZIP contiene los MISMOS documentos
6. **Presiona "Quitar filtros"**
   - ✅ Vuelve al estado sin filtros
   - ✅ Badge desaparece

### Test 2: Clasificación de Documentos

1. **Expande un proyecto** (ej: PAINO)
2. **Verifica tipos de documento:**
   - ✅ Voucher solo debe contener transferencias/pagos
   - ✅ Minuta solo debe contener minutas
   - ✅ NO debe haber "Contrato de Separación" en Voucher
   - ✅ NO debe haber "Cronograma de Pagos" en Voucher

---

## 🛠️ COMANDOS ÚTILES

### Ver logs en tiempo real

```powershell
docker logs -f tale-download
```

### Reiniciar contenedor

```powershell
docker restart tale-download
```

### Detener contenedor

```powershell
docker stop tale-download
```

### Eliminar todo y empezar de cero

```powershell
docker stop tale-download
docker rm tale-download
docker rmi tale-download:latest
.\deploy.ps1
```

### Entrar al contenedor (debugging)

```powershell
docker exec -it tale-download /bin/bash
```

---

## 🐛 TROUBLESHOOTING

### El contenedor no arranca

```powershell
# Ver logs de error
docker logs tale-download

# Verificar que .env existe y tiene las variables correctas
cat .env
```

### No veo los últimos cambios

```powershell
# SOLUCIÓN: Reconstruir SIN CACHE
docker stop tale-download
docker rm tale-download
docker rmi tale-download:latest
docker build --no-cache -f Containerfile -t tale-download:latest .
docker run -d --name tale-download -p 8080:8080 --env-file .env tale-download:latest
```

### Puerto 8080 ya está en uso

```powershell
# Verificar qué está usando el puerto
netstat -ano | findstr :8080

# Detener el proceso o usar otro puerto
docker run -d --name tale-download -p 8081:8080 --env-file .env tale-download:latest
```

### Redshift no conecta

```powershell
# Verificar variables de entorno
docker exec tale-download env | findstr REDSHIFT

# Verificar logs de conexión
docker logs tale-download | findstr Redshift
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
tale-download/
├── deploy.ps1                              ← Script de despliegue automático
├── DESPLIEGUE.md                          ← Esta guía
├── IMPLEMENTACION_FILTROS_Y_CLASIFICACION.md  ← Documentación técnica
├── .env                                   ← Variables de entorno (no commitear)
├── Containerfile                          ← Dockerfile
├── backend/
│   ├── services/
│   │   └── redshift_service.py           ← Query SQL mejorado
│   └── api/
│       └── routes.py                      ← Endpoints actualizados
└── client/
    └── src/
        ├── pages/
        │   └── Home.tsx                   ← Lógica de filtros implementada
        └── lib/
            └── api.ts                     ← API client actualizado
```

---

## 🌐 URLs

- **Frontend:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs
- **Health Check:** http://localhost:8080/api/health
- **Proyectos:** http://localhost:8080/api/projects/all

---

## 📝 NOTAS IMPORTANTES

1. **SIEMPRE usar `--no-cache`** al reconstruir para ver cambios de código
2. **NO commitear `.env`** con credenciales de producción
3. **Verificar health check** antes de usar la app
4. **Limpiar caché de frontend** (`dist/` y `.vite/`) antes de rebuild

---

## ✅ CHECKLIST DE DESPLIEGUE

- [ ] Detener contenedores antiguos
- [ ] Limpiar caché de frontend
- [ ] Eliminar imágenes antiguas
- [ ] Reconstruir con `--no-cache`
- [ ] Levantar contenedor nuevo
- [ ] Verificar logs (sin errores)
- [ ] Verificar health check
- [ ] Verificar frontend en navegador
- [ ] Probar flujo de filtros
- [ ] Probar clasificación de documentos

---

**¡TALE Download listo para producción! 🚀**
