# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [2.0.0] - 2025-12-23

### 🎉 Lanzamiento Mayor - TaleDownload Production Ready

**Fecha**: 23 de diciembre de 2025, 14:48 UTC-5  
**Commits**: 4 commits principales  
**Build**: Limpio (sin cache)

### ✨ Nuevas Características

- **Soporte completo de conversión de imágenes a PDF**
  - ImageReader de reportlab para manejo correcto de BytesIO
  - Soporta JPG, JPEG, PNG con optimización automática
  - Resuelve 348 archivos previamente marcados como "Unsupported file type"

- **Normalización de nombres a MAYÚSCULAS**
  - Nombres de clientes en estructura de carpetas convertidos a MAYÚSCULAS
  - Formato: `{TIPO_UNIDAD}-{CODIGO} - {NOMBRE_CLIENTE_EN_MAYÚSCULAS}`
  - Cumple requisito de homologación TALE

- **Puerto configurable parametrizado**
  - Puerto ahora es parametrizable vía variable de entorno `PORT`
  - Default: 8010 (evita conflicto con PGAdmin en 8080)
  - Actualizado en Containerfile, backend y documentación

### 🔧 Mejoras Técnicas

- **Deploy Script mejorado** (`deploy.sh`)
  - Validación completa del entorno
  - Gestión automática de contenedores
  - Health check integrado
  - Soporte para `--no-cache` y `--force`

- **Suite de validación completa**
  - 4 tests de validación automatizados
  - Cobertura: conversión de PDF, detección de extensiones, normalización de nombres
  - 100% pasando (4/4)

- **Optimización de recursos**
  - Limpieza de 98.72 GB de espacio (imágenes antiguas)
  - Build sin cache para garantizar consistencia
  - Logs limpios en Cockpit

### 🐛 Bugs Corregidos

- **Conversión de imágenes JPG/PNG a PDF**
  - Problema: `TypeError: expected str, bytes or os.PathLike object, not BytesIO`
  - Solución: Implementación de `ImageReader` de reportlab.lib.utils
  - Resultado: 348 archivos se procesan correctamente

- **Conflicto de puertos (8080 vs 8010)**
  - Problema: TaleDownload en 8080 conflictaba con PGAdmin
  - Solución: Migración a puerto 8010 con configuración parametrizada
  - Resultado: Sin conflictos de puertos

- **Nombres de carpetas no normalizados**
  - Problema: Nombres de clientes en minúsculas
  - Solución: Aplicación de `.upper()` en `generate_folder_path()`
  - Resultado: Homologación TALE cumplida

### 📚 Cambios en Documentación

- Actualización completa de README.md con referencias al puerto 8010
- Documentación de variables de entorno (PORT)
- Ejemplos de curl actualizados
- Guía de despliegue mejorada

### 🔄 Cambios en Dependencias

- No hay cambios en dependencias principales
- Todas las versiones se mantienen estables
- Python 3.11, FastAPI 0.115.5, React 19.2.1

### 📊 Estadísticas del Release

- **Archivos modificados**: 7
- **Archivos nuevos**: 2 (test_reprocess.py, deploy.sh)
- **Líneas agregadas**: 567
- **Líneas eliminadas**: 58
- **Commits en este release**: 4

### 🚀 Instrucciones de Deploy

```bash
# 1. Actualizar código
git pull origin main

# 2. Crear archivo .env con variables necesarias
cp env.example.txt .env
# Editar con credenciales de Redshift

# 3. Ejecutar deploy limpio
./deploy.sh --no-cache

# 4. Verificar salud
curl http://localhost:8010/api/health
```

### ✅ Validación Completada

- ✓ 4/4 tests de validación pasando
- ✓ Frontend cargando correctamente
- ✓ API respondiendo en puerto 8010
- ✓ No hay conflictos con otros servicios
- ✓ Logs del sistema limpios
- ✓ Conversión de imágenes funcionando

### 🔗 URLs de Acceso

- **Frontend**: http://localhost:8010
- **API Health**: http://localhost:8010/api/health
- **Swagger UI**: http://localhost:8010/api/docs
- **ReDoc**: http://localhost:8010/api/redoc

### 📝 Commits Incluidos

```
e5bba1e - fix: Configurar puerto 8010 como default
3e82823 - chore: Agregar deploy.sh a repositorio
af5b3de - fix: Aplicar normalización a MAYÚSCULAS en nombres de carpeta
5307f76 - fix: Corregir conversión imágenes JPG/PNG a PDF con ImageReader
```

### 🎯 Próximas Mejoras (Planeadas)

- Implementar sistema de caché para descargas frecuentes
- Dashboard de monitoreo en tiempo real
- API de webhook para notificaciones de descargas completadas
- Soporte para más formatos de conversión (DOCX → PDF)

### 📞 Soporte

Para reportar bugs o sugerir mejoras, contactar al equipo de desarrollo de TALE.

---

**Creado por**: GitHub Copilot / TALE Development Team  
**Fecha**: 2025-12-23 14:48 UTC-5  
**Verificado**: ✅ Todos los tests pasando
