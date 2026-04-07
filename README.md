# TaleDownload - Sistema de Exportación Documental

Sistema de exportación documental desde Business Intelligence (AWS Redshift) para TALE Inmobiliaria.

> **🎉 v2.0.0 - 2025-12-23**: Release Production Ready con fix de conversión de imágenes, normalización a mayúsculas y puerto configurable. [Ver cambios →](./CHANGELOG.md)

## 📋 Descripción

TaleDownload es un sistema **stateless** que permite consultar y descargar documentos almacenados en AWS Redshift, con las siguientes capacidades:

- ✅ Consulta read-only a BI (sin base de datos propia)
- ✅ Descarga de documentos individuales (convertidos a PDF)
- ✅ Generación de ZIPs organizados por proyecto/filtros
- ✅ Conversión automática de imágenes a PDF
- ✅ Renombrado según convención TALE
- ✅ 100% stateless (sin persistencia)

## 🏗️ Arquitectura

- **Frontend**: React 19 + Vite + Tailwind CSS 4
- **Backend**: FastAPI (Python 3.11)
- **Base de Datos**: AWS Redshift (read-only)
- **Despliegue**: Podman (Rocky Linux)

## 📦 Estructura del Proyecto

```
tale-download/
├── backend/                   # Backend FastAPI
│   ├── api/                   # Endpoints y modelos
│   ├── core/                  # Configuración
│   ├── services/              # Lógica de negocio
│   └── utils/                 # Utilidades
├── client/                    # Frontend React
│   ├── public/                # Assets estáticos
│   └── src/                   # Código fuente
├── requirements.txt           # Dependencias Python
├── env.example.txt            # Variables de entorno (ejemplo)
├── Containerfile              # Imagen Docker/Podman
├── BACKEND_DOCUMENTATION.md   # Documentación técnica del backend
└── README.md                  # Este archivo
```

## 🚀 Despliegue en Producción (Rocky Linux + Podman)

### Flujo de Trabajo Obligatorio

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd tale-download

# 2. Configurar variables de entorno
cp env.example.txt .env
nano .env  # Editar con credenciales reales

# 3. Construir imagen
podman build --no-cache -t tale-download .

# 4. Detener contenedor anterior (si existe)
podman stop tale-download || true
podman rm tale-download || true

# 5. Ejecutar contenedor
podman run -d \
  --name tale-download \
  -p 8010:8010 \
  --env-file .env \
  tale-download

# 6. Verificar
podman logs -f tale-download
curl http://localhost:8010/api/health
```

### Variables de Entorno Requeridas

Crear archivo `.env` en la raíz del proyecto:

```env
# Redshift (REQUERIDO)
REDSHIFT_HOST=your-cluster.region.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=your_database
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password

# Configuración (OPCIONAL)
DEBUG=False
MAX_FILE_SIZE_MB=500
```

### Verificación del Despliegue

```bash
# Health check
curl http://localhost:8010/api/health

# Listar proyectos
curl http://localhost:8010/api/projects

# Interfaz web
open http://localhost:8010
```

## 💻 Desarrollo Local

### Prerrequisitos

- Python 3.11+
- Node.js 22+
- pnpm
- Credenciales de AWS Redshift

### 1. Backend (FastAPI)

```bash
# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example.txt .env
nano .env

# Ejecutar backend
python -m backend.main
```

El backend estará disponible en:
- API: `http://localhost:8010/api`
- Swagger UI: `http://localhost:8010/api/docs`

### 2. Frontend (React)

```bash
# Instalar dependencias
pnpm install

# Ejecutar frontend
pnpm dev
```

El frontend estará disponible en: `http://localhost:3000`

## 📚 Documentación

### API y Arquitectura
- **Swagger UI**: `http://localhost:8010/api/docs` (cuando el backend esté ejecutándose)
- **ReDoc**: `http://localhost:8010/api/redoc`

### Documentación Técnica
Toda la documentación técnica está organizada en la carpeta [`docs/`](./docs/):

- 🏗️ **[Arquitectura Backend](./docs/ARCHITECTURE.md)** - Documentación completa de arquitectura, filtros, clasificación y estructura del ZIP
- 📖 **[Changelog](./docs/CHANGELOG.md)** - Historial de versiones y cambios notables
- 🚀 **[Quick Reference](./docs/QUICK_REFERENCE.md)** - Guía rápida de operación y comandos útiles
- 🔧 **[Systemd Autostart](./docs/SYSTEMD_AUTOSTART.md)** - Configuración de auto-inicio con systemd
- 💡 **[Ideas](./docs/ideas.md)** - Ideas para futuras mejoras

## 🔌 Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/projects` | GET | Listar proyectos |
| `/api/documents` | GET | Listar documentos (con filtros) |
| `/api/download/document/{id}` | GET | Descargar documento individual (PDF) |
| `/api/download/zip` | POST | Descargar ZIP (filtros avanzados) |
| `/api/download/zip/project/{code}` | GET | Descargar ZIP de proyecto |

## 🧪 Pruebas con curl

```bash
# Health check
curl http://localhost:8010/api/health

# Listar proyectos
curl http://localhost:8010/api/projects

# Listar documentos de un proyecto
curl "http://localhost:8010/api/documents?project_code=PAINO"

# Descargar documento individual
curl "http://localhost:8010/api/download/document/2025-01061" --output documento.pdf

# Descargar ZIP de proyecto
curl "http://localhost:8010/api/download/zip/project/PAINO" --output PAINO.zip
```

## ⚙️ Configuración

### Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `REDSHIFT_HOST` | Host del cluster Redshift | (requerido) |
| `REDSHIFT_PORT` | Puerto de Redshift | `5439` |
| `REDSHIFT_DATABASE` | Nombre de la base de datos | (requerido) |
| `REDSHIFT_USER` | Usuario de Redshift | (requerido) |
| `REDSHIFT_PASSWORD` | Contraseña de Redshift | (requerido) |
| `DEBUG` | Modo debug | `False` |
| `MAX_FILE_SIZE_MB` | Tamaño máximo de archivo | `500` |

## 🔒 Seguridad

- Las credenciales de Redshift deben estar en `.env` (nunca commitear)
- El archivo `.env` debe estar en `.gitignore`
- Usar usuario de Redshift con permisos **read-only**
- El contenedor ejecuta con usuario no-root (`appuser`)

## 📝 Convención de Nombres

### Archivos
```
{codigo_proyecto}_{codigo_proforma}_{documento_cliente}_{tipo_documento}_{codigo_unidad}.pdf
```

**Ejemplo:**
```
PAINO_2025-01061_LijhoanMachaca_Voucher_DPTO-205.pdf
```

### Estructura de Carpetas en ZIP
```
{codigo_proyecto}/{codigo_proforma}/{codigo_unidad}/{tipo_documento}/
```

**Ejemplo:**
```
PAINO/
└── 2025-01061/
    └── DPTO-205/
        └── Voucher/
            └── PAINO_2025-01061_LijhoanMachaca_Voucher_DPTO-205.pdf
```

## 🛠️ Desarrollo

### Estructura del Backend

```
backend/
├── main.py                    # Aplicación FastAPI principal
├── api/
│   ├── models.py              # Modelos Pydantic
│   └── routes.py              # Endpoints
├── core/
│   └── config.py              # Configuración
├── services/
│   ├── redshift_service.py    # Conexión a Redshift
│   ├── download_service.py    # Descarga de archivos
│   ├── pdf_service.py         # Conversión a PDF
│   └── zip_service.py         # Generación de ZIPs
└── utils/
    └── file_naming.py         # Renombrado de archivos
```

### Tecnologías del Backend

- **FastAPI**: Framework web
- **psycopg2**: Conexión a Redshift (PostgreSQL compatible)
- **Pillow**: Procesamiento de imágenes
- **ReportLab**: Generación de PDFs
- **requests**: Descarga de archivos
- **uvicorn**: Servidor ASGI

### Tecnologías del Frontend

- **React 19**: Framework UI
- **Vite**: Build tool
- **Tailwind CSS 4**: Estilos
- **Axios**: Cliente HTTP
- **Lucide React**: Iconos
- **Sonner**: Notificaciones toast

## 🐛 Troubleshooting

### Backend no se conecta a Redshift

```bash
# Verificar credenciales en .env
cat .env

# Probar conexión manualmente
psql -h $REDSHIFT_HOST -p $REDSHIFT_PORT -U $REDSHIFT_USER -d $REDSHIFT_DATABASE
```

### Error de permisos en Podman

```bash
# Ejecutar con sudo si es necesario
sudo podman build -t tale-download .
sudo podman run -d --name tale-download -p 8080:8080 --env-file .env tale-download
```

### Puerto 8080 ya en uso

```bash
# Cambiar puerto en el comando de ejecución
podman run -d --name tale-download -p 9000:8080 --env-file .env tale-download
```

### Frontend muestra "Error de conexión"

```bash
# Verificar que el backend esté corriendo
curl http://localhost:8080/api/health

# Verificar logs del contenedor
podman logs -f tale-download
```

### Build de imagen falla

```bash
# Limpiar cache de Podman
podman system prune -a

# Reconstruir sin cache
podman build --no-cache -t tale-download .
```

## 📊 Monitoreo

### Logs del Contenedor

```bash
# Ver logs en tiempo real
podman logs -f tale-download

# Ver últimas 100 líneas
podman logs --tail 100 tale-download
```

### Health Check

```bash
# Verificar estado del contenedor
podman ps

# Health check manual
curl http://localhost:8080/api/health
```

## 🔄 Actualización del Sistema

```bash
# 1. Pull de cambios
git pull

# 2. Reconstruir imagen
podman build --no-cache -t tale-download .

# 3. Detener contenedor actual
podman stop tale-download
podman rm tale-download

# 4. Ejecutar nueva versión
podman run -d \
  --name tale-download \
  -p 8080:8080 \
  --env-file .env \
  tale-download
```

## 📄 Licencia

Propiedad de TALE Inmobiliaria. Todos los derechos reservados.

## 👥 Contacto

Para soporte técnico, contactar al equipo de desarrollo de TALE Inmobiliaria.
