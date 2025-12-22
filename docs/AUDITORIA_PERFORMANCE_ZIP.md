# 📊 REPORTE DE AUDITORÍA DE PERFORMANCE
## TaleDownload - Pipeline de Generación de ZIP

**Fecha:** 21 de Diciembre, 2025  
**Versión:** 1.0.0  
**Estado:** Solo análisis (sin modificaciones)

---

## 1️⃣ RESUMEN EJECUTIVO (No Técnico)

La aplicación TaleDownload tiene un problema de rendimiento en la generación de ZIPs que se debe principalmente a un **diseño secuencial** donde cada archivo se descarga, convierte y procesa uno tras otro. Si un proyecto tiene 500 documentos, el sistema espera a que cada uno termine completamente antes de empezar con el siguiente.

**Tiempo estimado actual:**
- Cada documento: ~2-5 segundos (descarga + conversión)
- Proyecto de 500 docs: **~15-40 minutos** (solo en procesamiento)

**Factores agravantes identificados:**
- Todo el ZIP se mantiene en memoria RAM hasta terminar
- No hay límites de recursos en el contenedor Docker
- El cliente espera sin feedback real de progreso

---

## 2️⃣ FLUJO TÉCNICO DETALLADO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUJO COMPLETO DE GENERACIÓN ZIP                     │
└─────────────────────────────────────────────────────────────────────────────┘

[FRONTEND - React]
   │
   ├─ 1. Usuario hace clic en "Descargar ZIP"
   │     └─ handleDownloadProjectZip() → Home.tsx#L97
   │
   ├─ 2. Axios GET /api/download/zip/project/{code}
   │     └─ timeout: 0 (infinito) → api.ts#L247
   │     └─ responseType: 'blob' (espera TODO el contenido)
   │
   ▼
[BACKEND - FastAPI]
   │
   ├─ 3. async def download_project_zip() → routes.py#L261
   │     └─ ⚠️ ASYNC pero llama servicios SYNC bloqueantes
   │
   ├─ 4. redshift_service.get_documents() → redshift_service.py#L94
   │     ├─ Conexión via psycopg2 (sync, bloqueante)
   │     ├─ Query CTE compleja con CASE de clasificación
   │     ├─ LIMIT: 100,000 documentos máximo
   │     └─ Retorna lista completa en memoria
   │
   ├─ 5. zip_service.create_zip() → zip_service.py#L156
   │     ├─ BytesIO zip_buffer (TODO en RAM)
   │     │
   │     ├─ FOR EACH documento (SECUENCIAL):
   │     │   │
   │     │   ├─ 5a. download_service.download_file(url)
   │     │   │       ├─ requests.get() con stream=True
   │     │   │       ├─ ⚠️ PERO usa response.content (carga todo en RAM)
   │     │   │       └─ timeout: 30s por archivo
   │     │   │
   │     │   ├─ 5b. pdf_service.convert_to_pdf(content)
   │     │   │       ├─ Si ya es PDF → passthrough
   │     │   │       └─ Si es imagen → PIL + ReportLab → PDF
   │     │   │           ├─ Image.open() en memoria
   │     │   │           ├─ canvas.Canvas() en BytesIO
   │     │   │           └─ ⚠️ Doble copia en RAM
   │     │   │
   │     │   └─ 5c. zip_file.writestr(path, pdf_content)
   │     │           └─ Acumula en zip_buffer (RAM)
   │     │
   │     └─ zip_buffer.seek(0) → retorna BytesIO completo
   │
   ├─ 6. StreamingResponse(zip_buffer)
   │     └─ ⚠️ NO es streaming real: buffer ya está completo
   │
   ▼
[FRONTEND - React]
   │
   └─ 7. Recibe blob, crea URL, descarga archivo
```

---

## 3️⃣ TABLA DE TIEMPOS POR ETAPA (ESTIMADO)

| Etapa | Operación | Tiempo Unitario | Para 500 docs |
|-------|-----------|-----------------|---------------|
| T0→T1 | Query Redshift | 1-5s | 1-5s |
| T1→T2 | Descargar archivo (c/u) | 0.5-3s | 250-1500s |
| T2→T3 | Conversión PDF (c/u) | 0.1-1s (imágenes) | 50-500s |
| T3→T4 | Escritura en ZIP (c/u) | <0.01s | ~5s |
| T4→T5 | Transferencia a cliente | Variable | 10-60s |
| **TOTAL** | | | **5-35 min** |

**Nota:** No se pudo medir en vivo sin agregar instrumentación.

---

## 4️⃣ CUELLOS DE BOTELLA REALES (Ordenados por Impacto)

### 🔴 CRÍTICO #1: Descargas 100% Secuenciales

**Ubicación:** `backend/services/zip_service.py#L174-L197`

```python
for idx, doc in enumerate(folder_docs, 1):  # ← SECUENCIAL
    content = download_service.download_file(url)  # ← BLOQUEANTE
```

**Impacto:** Si hay 500 docs y cada descarga toma 2s = **16 minutos solo en descargas**

**Evidencia:** Loop `for` sin concurrencia, `requests.get()` es síncrono

---

### 🔴 CRÍTICO #2: Todo en RAM (No Streaming Real)

**Ubicación:** `backend/services/zip_service.py#L158`

```python
zip_buffer = io.BytesIO()  # ← TODO el ZIP se acumula aquí
```

**Impacto:** 
- 500 docs × ~500KB = ~250MB en RAM solo para el ZIP
- Más las copias intermedias de imágenes/PDFs
- Picos de memoria de 1GB+ para proyectos grandes

**Evidencia:** `BytesIO()` sin flush a disco, `zip_buffer.seek(0)` al final

---

### 🔴 CRÍTICO #3: Endpoint async pero Servicios sync

**Ubicación:** `backend/api/routes.py#L261`

```python
async def download_project_zip(...):
    documents_data = redshift_service.get_documents(...)  # ← SYNC
    zip_buffer = zip_service.create_zip(...)  # ← SYNC
```

**Impacto:** Bloquea el event loop de Uvicorn mientras procesa

**Evidencia:** 
- `psycopg2` no es async
- `requests.get()` no es async
- `zipfile.ZipFile` no es async

---

### 🟠 ALTO #4: stream=True pero response.content

**Ubicación:** `backend/services/download_service.py#L25-L37`

```python
response = requests.get(url, timeout=timeout, stream=True)
# ...
content = response.content  # ← Lee TODO en memoria de golpe
```

**Impacto:** `stream=True` no sirve si usas `.content`

**Evidencia:** Debería usar `iter_content()` para streaming real

---

### 🟠 ALTO #5: Query CTE Compleja sin Paginación

**Ubicación:** `backend/services/redshift_service.py#L139-L267`

**Impacto:** 
- Query de ~100 líneas ejecutada en cada request
- LIMIT 100,000 sin cursor/paginación
- Resultado completo en memoria antes de procesar

---

### 🟡 MEDIO #6: Conversión de Imagen CPU-bound

**Ubicación:** `backend/services/pdf_service.py#L32-L66`

```python
image = Image.open(io.BytesIO(image_bytes))
image = image.convert('RGB')  # ← CPU-bound
c = canvas.Canvas(pdf_buffer)  # ← CPU-bound
```

**Impacto:** Para imágenes grandes, puede tomar 0.5-1s por archivo

**Evidencia:** PIL y ReportLab son CPU-bound, ejecutados en main thread

---

### 🟡 MEDIO #7: Sin Límites de Recursos en Docker

**Ubicación:** `deploy.ps1#L89-L94`

```powershell
docker run -d --name tale-download -p 8080:8080 --env-file .env
# ← Sin --memory, --cpus
```

**Impacto:** Puede consumir toda la RAM/CPU del host

**Evidencia:** No hay flags `--memory` ni `--cpus`

---

### 🟢 BAJO #8: Uvicorn Single Worker por Defecto

**Ubicación:** `backend/main.py#L68-L72`

```python
uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=settings.DEBUG)
# ← Sin workers=N, sin configuración de threads
```

**Impacto:** Solo 1 worker = 1 request de ZIP a la vez bloquea todo

**Evidencia:** Sin parámetro `workers`

---

## 5️⃣ RIESGOS DETECTADOS

| Riesgo | Severidad | Descripción |
|--------|-----------|-------------|
| **OOM Kill** | 🔴 CRÍTICA | Proyectos grandes pueden agotar RAM del contenedor |
| **Timeout de Red** | 🟠 ALTA | Requests HTTP de minutos pueden cerrarse por proxies intermedios |
| **Bloqueo de Otros Usuarios** | 🟠 ALTA | Un ZIP grande bloquea el único worker |
| **Sin Reintentos** | 🟡 MEDIA | Si falla una descarga, no hay retry automático |
| **Sin Progress Real** | 🟡 MEDIA | `onDownloadProgress` solo funciona cuando hay Content-Length conocido |

---

## 6️⃣ RECOMENDACIONES TÉCNICAS (SIN IMPLEMENTAR)

### QUICK WINS (Bajo esfuerzo, Alto impacto)

| # | Recomendación | Esfuerzo | Impacto |
|---|---------------|----------|---------|
| 1 | Agregar workers a Uvicorn: `workers=4` | 🟢 Bajo | 🔴 Alto |
| 2 | Límites de Docker: `--memory=2g --cpus=2` | 🟢 Bajo | 🟠 Medio |
| 3 | Timeout más corto por archivo: 15s en vez de 30s | 🟢 Bajo | 🟡 Bajo |
| 4 | Logging de tiempos: timestamps en cada etapa | 🟢 Bajo | 🟡 Diagnóstico |

### CAMBIOS ESTRUCTURALES (Mayor esfuerzo)

| # | Recomendación | Esfuerzo | Impacto |
|---|---------------|----------|---------|
| 1 | Descargas Paralelas: `asyncio.gather()` con `aiohttp` | 🟠 Medio | 🔴 Alto |
| 2 | Streaming Real: ZIP a disco + streamear | 🟠 Medio | 🔴 Alto |
| 3 | Async DB: Cambiar `psycopg2` por `asyncpg` | 🟠 Medio | 🟠 Medio |
| 4 | Background Job: Generar ZIP en tarea async | 🔴 Alto | 🔴 Alto |
| 5 | Chunked Encoding: Enviar ZIP mientras se genera | 🔴 Alto | 🔴 Alto |

---

## 7️⃣ COMPARATIVO: ¿Qué Pudo Cambiar?

| Factor | Antes | Ahora | Impacto |
|--------|-------|-------|---------|
| Cantidad de docs/proyecto | ~100 | ~500+ | ↑ 5x tiempo |
| Tamaño promedio de archivos | ~200KB | ~500KB+ | ↑ 2.5x RAM |
| Homologación tipo_unidad | 4 tipos | 7 tipos | Más carpetas en ZIP |
| Query de clasificación | Simple | CTE compleja | +1-2s por query |
| Cardinalidad | Baja | Alta | Más filas procesadas |

---

## 8️⃣ CHECKLIST PARA SIGUIENTE FASE

Cuando se decida proceder con fixes, priorizar:

- [ ] Instrumentar logging con timestamps (t0-t5)
- [ ] Medir proyecto real (cuántos docs, cuánto tiempo)
- [ ] Agregar workers a Uvicorn (quick win)
- [ ] Agregar límites de Docker (quick win)
- [ ] Evaluar si conviene descargas paralelas
- [ ] Evaluar si conviene background job + notificación

---

## 9️⃣ ARCHIVOS ANALIZADOS

| Archivo | Rol en el Pipeline |
|---------|-------------------|
| `client/src/pages/Home.tsx` | Trigger del download |
| `client/src/lib/api.ts` | Axios config + blob handling |
| `backend/api/routes.py` | Endpoints FastAPI |
| `backend/services/zip_service.py` | Armado del ZIP |
| `backend/services/download_service.py` | Descarga de URLs |
| `backend/services/pdf_service.py` | Conversión a PDF |
| `backend/services/redshift_service.py` | Queries a Redshift |
| `backend/main.py` | Config de Uvicorn |
| `backend/core/config.py` | Settings |
| `Containerfile` | Imagen Docker |
| `deploy.ps1` | Script de deploy |

---

## 🔒 RESTRICCIONES APLICADAS

Durante esta auditoría:
- ✅ Solo lectura y análisis de código
- ✅ Sin modificaciones a lógica de negocio
- ✅ Sin cambios de arquitectura
- ✅ Sin optimizaciones aplicadas
- ✅ Sin cache agregado
- ✅ Sin paralelización implementada

---

**FIN DEL REPORTE DE AUDITORÍA**

*Documento generado el 21 de Diciembre, 2025*
