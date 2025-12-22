# 🔍 Análisis de Discrepancias en Conteo de Documentos - MUM 363

## Resumen Ejecutivo

**La interfaz muestra 194 documentos para MUM, pero la BD contiene 3,059 documentos.** 

Esta discrepancia es causada por **2 JOINs incorrectos** en el backend que relacionan la tabla `archivos` con `proforma_unidad`.

---

## Hallazgos

### 1. Datos Reales en la BD

```sql
-- Consulta correcta:
SELECT COUNT(*) as total_documentos
FROM tale.archivos a
INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
WHERE pu.codigo_proyecto = 'MUM'
-- Resultado: 3,059 documentos ✅
```

**Desglose de documentos MUM por tipo:**
- `proceso adquisicion`: 2,515 documentos
- `contrato`: 544 documentos
- **Total**: 3,059 documentos

Todos son clasificados como tipo "Otro" porque los montajes reales no coinciden con los patrones buscados:
- Se busca: `voucher`, `minuta`, `adenda`, `agenda`, `notificacion`, `cotizacion`, `presupuesto`
- Se encuentra: `proceso adquisicion`, `contrato`

---

### 2. Lo que Muestra la Interfaz Incorrectamente

```
194 Documentos (INCORRECTO ❌)
├─ Otro: 194
├─ Voucher: 0
├─ Minuta: 0
├─ Adenda: 0
├─ Presupuesto: 0
└─ Notificación: 0
```

---

### 3. Root Cause: JOINs Incorrectos en Backend

El backend usa `a.entidad_id = pu.id` que filtra por entidades de tipo "Unidad" (galerías, imágenes), no por documentos de proformas.

```sql
-- JOIN ACTUAL (INCORRECTO):
INNER JOIN tale.archivos a ON pu.id = a.entidad_id
-- Resultado: 194 documentos ❌ (solo galerías de unidades)

-- JOIN CORRECTO:
INNER JOIN tale.archivos a ON pu.codigo_proforma = a.codigo_proforma
-- Resultado: 3,059 documentos ✅ (todos los documentos)
```

---

### 4. Tablas Implicadas

| Tabla | Propósito | Campos Clave |
|-------|-----------|--------------|
| `tale.archivos` | Almacena todos los archivos/documentos | `codigo_proforma`, `entidad_id`, `montaje`, `fecha_carga` |
| `tale.proforma_unidad` | Proformas de unidades por proyecto | `id`, `codigo_proforma`, `codigo_proyecto`, `nombre_proyecto` |

---

### 5. Códigos Afectados en Backend

**Archivo:** `backend/services/redshift_service.py`

#### ❌ Problema 1 - Línea 253 (función `get_projects_with_names`):

```python
def get_projects_with_names(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
    SELECT 
        pu.codigo_proyecto,
        pu.nombre_proyecto,
        COUNT(DISTINCT a.codigo_proforma) as total_documentos,
        MAX(a.fecha_carga) as ultima_fecha_carga
    FROM tale.proforma_unidad pu
    INNER JOIN tale.archivos a ON pu.id = a.entidad_id  -- ❌ INCORRECTO
    WHERE pu.codigo_proyecto IS NOT NULL 
      AND pu.nombre_proyecto IS NOT NULL
    GROUP BY pu.codigo_proyecto, pu.nombre_proyecto
    ORDER BY pu.codigo_proyecto
    """
```

**Debe ser:**
```python
INNER JOIN tale.archivos a ON pu.codigo_proforma = a.codigo_proforma  -- ✅ CORRECTO
```

#### ❌ Problema 2 - Línea 80 (función `get_projects_summary`):

```python
def get_projects_summary(self) -> List[Dict[str, Any]]:
    query = """
    SELECT 
        CAST(entidad_id AS VARCHAR) as codigo_proyecto,  -- ❌ INCORRECTO
        COUNT(*) as total_documentos,
        TO_CHAR(MAX(fecha_carga), 'YYYY-MM-DD HH24:MI:SS') as ultima_actualizacion
    FROM tale.archivos
    WHERE entidad_id IS NOT NULL
    GROUP BY entidad_id
    ORDER BY entidad_id
    """
```

**El problema:** Está usando `entidad_id` directamente en lugar de unirse con `proforma_unidad` para obtener `codigo_proyecto`.

**Debe ser:**
```python
SELECT 
    pu.codigo_proyecto,
    COUNT(*) as total_documentos,
    TO_CHAR(MAX(a.fecha_carga), 'YYYY-MM-DD HH24:MI:SS') as ultima_actualizacion
FROM tale.archivos a
LEFT JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
WHERE pu.codigo_proyecto IS NOT NULL
GROUP BY pu.codigo_proyecto
ORDER BY pu.codigo_proyecto
```

#### ❌ Problema 3 - Línea 172 (función `get_documents`):

Misma issue - JOIN incorrecto:
```python
INNER JOIN tale.proforma_unidad pu ON a.entidad_id = pu.id  -- ❌ INCORRECTO
```

**Debe ser:**
```python
INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma  -- ✅ CORRECTO
```

---

## Impacto

| Componente | Impacto |
|-----------|---------|
| `/api/projects/all` | Devuelve 194 documentos en lugar de 3,059 |
| `/api/projects` | Muestra conteo incorrecto |
| `/api/documents` | Filtra documentos incorrectamente |
| Frontend (Home.tsx) | Muestra 194 documentos para MUM en lugar de 3,059 |

---

## Solución

Cambiar todos los JOINs en `redshift_service.py` de:
```sql
a.entidad_id = pu.id
```

A:
```sql
a.codigo_proforma = pu.codigo_proforma
```

Y en `get_projects_summary`, cambiar la lógica para usar `proforma_unidad` en lugar de `entidad_id` directamente.

