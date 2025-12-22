# TaleDownload - TODO

## Recreación del Backend

- [x] Recrear estructura de carpetas del backend
- [x] Recrear servicios (Redshift, Download, PDF, ZIP)
- [x] Recrear endpoints FastAPI base
- [ ] Commit 1: Backend completo

## Ajustes Funcionales

- [x] Agregar endpoints BI para obtener lista de proyectos únicos
- [x] Agregar endpoints BI para obtener lista de tipos de documento únicos
- [x] Implementar Select/Autocomplete en frontend para Proyecto y Tipo
- [x] Implementar paginación (25 por página)
- [x] Lista de documentos solo visible tras búsqueda explícita
- [x] Selección múltiple de documentos
- [x] "Seleccionar todos" limitado a resultados del filtro actual
- [x] Commit 2: Ajustes funcionales

## Mejoras Visuales Controladas

- [x] Toast loading para estado "Procesando exportación"
- [x] Toast success para confirmación de descarga
- [x] Toast error para errores de descarga
- [x] Skeleton para carga de resultados de búsqueda
- [x] Animación fadeIn sutil (200ms) en cards
- [x] Hover con sombra en cards (transición 200ms)
- [x] Ring visual en documentos seleccionados
- [ ] Commit 3: Mejoras visuales
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
