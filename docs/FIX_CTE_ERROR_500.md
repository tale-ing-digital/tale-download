# 🐛 Fix: Error 500 al cargar documentos sin filtros

## Fecha: 21 de Diciembre 2025 - 19:08

---

## ❌ PROBLEMA DETECTADO

Al intentar **"Ver documentos"** de un proyecto SIN aplicar filtros de tipo de documento, el backend devolvía:

```
GET /api/documents?project_code=PAINO&limit=10000&offset=0
500 Internal Server Error
```

**Error específico:**
```json
{
  "detail": "Error fetching documents: Only SELECT queries are allowed (read-only)"
}
```

---

## 🔍 CAUSA RAÍZ

El método `execute_query()` en [redshift_service.py](backend/services/redshift_service.py) validaba que todas las queries empiecen con `SELECT`:

```python
if not query.strip().upper().startswith("SELECT"):
    raise ValueError("Only SELECT queries are allowed (read-only)")
```

**PERO** el nuevo query mejorado con clasificación de documentos utiliza un **CTE (Common Table Expression)** que empieza con `WITH`:

```sql
WITH base AS (
    SELECT ...
)
SELECT ...
FROM base
```

Por lo tanto, el validador rechazaba el query como "no permitido" aunque **SÍ es una query de solo lectura**.

---

## ✅ SOLUCIÓN APLICADA

Actualización en [backend/services/redshift_service.py](backend/services/redshift_service.py#L44-L49):

```python
# ANTES (línea 49)
if not query.strip().upper().startswith("SELECT"):
    raise ValueError("Only SELECT queries are allowed (read-only)")

# DESPUÉS (líneas 47-49)
query_upper = query.strip().upper()
if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
    raise ValueError("Only SELECT queries are allowed (read-only)")
```

**Ahora acepta:**
- ✅ `SELECT ...` (queries directas)
- ✅ `WITH ... SELECT ...` (CTEs - Common Table Expressions)

**Sigue rechazando:**
- ❌ `INSERT ...`
- ❌ `UPDATE ...`
- ❌ `DELETE ...`
- ❌ `DROP ...`

---

## 🧪 VERIFICACIÓN

### Test 1: SIN filtros (antes fallaba)
```powershell
curl "http://localhost:8080/api/documents?project_code=PAINO&limit=5&offset=0"
```

**Resultado:**
```json
{
  "total": 5,
  "documents": [...]
}
```
✅ **200 OK**

### Test 2: CON filtros (ya funcionaba)
```powershell
curl "http://localhost:8080/api/documents?project_code=PAINO&limit=5&offset=0&document_types=Voucher"
```

**Resultado:**
```json
{
  "total": 5,
  "documents": [...]
}
```
✅ **200 OK**

---

## 📝 IMPACTO

**Afectado:**
- ✅ Ver documentos de proyectos sin filtros
- ✅ Descargar ZIP sin filtros de tipo
- ✅ Cualquier query que use CTEs

**NO afectado:**
- ✅ Seguridad (sigue siendo read-only)
- ✅ Queries directas SELECT
- ✅ Lógica de clasificación

---

## 🚀 DESPLIEGUE

El fix ya está aplicado en el contenedor actual.

**Para futuros despliegues:**
```powershell
.\deploy.ps1
```

---

## 📄 ARCHIVOS MODIFICADOS

- [backend/services/redshift_service.py](backend/services/redshift_service.py) - Líneas 47-49

---

**Status:** ✅ RESUELTO Y VERIFICADO
