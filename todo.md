# TaleDownload - TODO

## Recreación del Backend

- [x] Recrear estructura de carpetas del backend
- [x] Recrear servicios (Redshift, Download, PDF, ZIP)
- [x] Recrear endpoints FastAPI base
- [ ] Commit 1: Backend completo

## Ajustes Funcionales

- [ ] Agregar endpoints BI para obtener lista de proyectos únicos
- [ ] Agregar endpoints BI para obtener lista de tipos de documento únicos
- [ ] Implementar componente Select/Autocomplete para Código de Proyecto
- [ ] Implementar componente Select/Autocomplete para Tipo de Documento
- [ ] Cambiar comportamiento: lista de documentos solo visible tras búsqueda explícita
- [ ] Implementar paginación de resultados (25 por página)
- [ ] Implementar funcionalidad "Seleccionar todos" limitada a resultados del filtro actual
- [ ] Preparar arquitectura para filtros futuros (Unidad, Cliente)

## Mejoras Visuales Controladas

- [ ] Agregar feedback visual para estado "Procesando exportación"
- [ ] Agregar feedback visual para confirmación de descarga exitosa
- [ ] Agregar feedback visual para errores de descarga
- [ ] Agregar feedback visual para carga de resultados de búsqueda
- [ ] Validar que todas las animaciones sean sutiles (150-250ms)
- [ ] Validar que no haya animaciones decorativas o constantes
