#!/bin/bash

################################################################################
# TALE DOWNLOAD - DEPLOYMENT SCRIPT
# 
# Descripción: Script de despliegue completo para TaleDownload
# - Build de imagen Podman
# - Gestión de contenedores existentes
# - Inicialización segura del servicio
# - Validación de salud
#
# Uso: ./deploy.sh [OPTIONS]
# Opciones:
#   --no-cache          Build sin usar caché
#   --force             Fuerza reconstrucción y eliminación de recursos
#   --port PORT         Puerto personalizado (default: 8010)
#   --help              Muestra esta ayuda
################################################################################

set -e

# Colors para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración por defecto
PROJECT_NAME="tale-download"
PORT=8010
BUILD_CACHE="--no-cache"
FORCE_DEPLOY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

################################################################################
# FUNCIONES AUXILIARES
################################################################################

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

show_help() {
    head -20 "$0" | tail -15
    exit 0
}

################################################################################
# VALIDACIONES PREVIAS
################################################################################

validate_environment() {
    print_header "Validando entorno"
    
    # Verificar podman
    if ! command -v podman &> /dev/null; then
        print_error "Podman no está instalado. Por favor instala Podman."
        exit 1
    fi
    print_success "Podman encontrado: $(podman --version)"
    
    # Verificar que estamos en el directorio correcto
    if [[ ! -f "$SCRIPT_DIR/Containerfile" ]]; then
        print_error "Containerfile no encontrado en $SCRIPT_DIR"
        exit 1
    fi
    print_success "Directorio del proyecto correcto"
    
    # Validar puerto
    if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
        print_error "Puerto inválido: $PORT (debe estar entre 1024 y 65535)"
        exit 1
    fi
    print_success "Puerto válido: $PORT"
}

################################################################################
# LIMPIEZA DE RECURSOS EXISTENTES
################################################################################

cleanup_existing() {
    print_header "Limpiando recursos existentes"
    
    # Detener contenedor si está corriendo
    if podman ps -a | grep -q "$PROJECT_NAME"; then
        print_info "Deteniendo contenedor $PROJECT_NAME..."
        podman stop "$PROJECT_NAME" 2>/dev/null || true
        sleep 2
        print_success "Contenedor detenido"
    else
        print_info "Contenedor $PROJECT_NAME no encontrado (es normal en primer despliegue)"
    fi
    
    # Eliminar contenedor si existe
    if podman container exists "$PROJECT_NAME" 2>/dev/null; then
        print_info "Removiendo contenedor antiguo..."
        podman rm "$PROJECT_NAME" 2>/dev/null || true
        print_success "Contenedor removido"
    fi
    
    # Si --force, eliminar imagen anterior
    if [ "$FORCE_DEPLOY" = true ]; then
        if podman images | grep -q "$PROJECT_NAME"; then
            print_warning "Eliminando imagen antigua por --force..."
            podman rmi "$PROJECT_NAME:latest" 2>/dev/null || true
            print_success "Imagen removida"
        fi
    fi
}

################################################################################
# BUILD DE IMAGEN
################################################################################

build_image() {
    print_header "Construyendo imagen Podman"
    
    print_info "Build parameters:"
    print_info "  - Imagen: $PROJECT_NAME:latest"
    print_info "  - Directorio: $SCRIPT_DIR"
    print_info "  - Cache: $([ "$BUILD_CACHE" = "--no-cache" ] && echo 'DESHABILITADO' || echo 'HABILITADO')"
    echo ""
    
    if podman build $BUILD_CACHE -t "$PROJECT_NAME:latest" "$SCRIPT_DIR"; then
        print_success "Imagen construida exitosamente"
        print_info "ID de imagen: $(podman images --format '{{.ID}}' "$PROJECT_NAME:latest" | head -c 12)"
    else
        print_error "Error durante la construcción de la imagen"
        exit 1
    fi
}

################################################################################
# INICIALIZACIÓN DEL CONTENEDOR
################################################################################

start_container() {
    print_header "Iniciando contenedor"
    
    print_info "Parámetros del contenedor:"
    print_info "  - Nombre: $PROJECT_NAME"
    print_info "  - Puerto: $PORT (interno: 8010)"
    print_info "  - Imagen: $PROJECT_NAME:latest"
    echo ""
    
    if podman run -d \
        --name "$PROJECT_NAME" \
        -p "$PORT:8010" \
        --restart=unless-stopped \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=10s \
        --env-file .env \
        "$PROJECT_NAME:latest"; then
        
        print_success "Contenedor iniciado con ID: $(podman ps --format '{{.ID}}' -f name="$PROJECT_NAME" | head -c 12)"
    else
        print_error "Error al iniciar el contenedor"
        exit 1
    fi
}

################################################################################
# VALIDACIÓN DE SALUD
################################################################################

validate_health() {
    print_header "Validando salud del servicio"
    
    print_info "Esperando a que el servicio esté listo..."
    local max_attempts=30
    local attempt=1
    local health_url="http://localhost:$PORT/api/health"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$health_url" > /dev/null 2>&1; then
            local response=$(curl -s "$health_url")
            print_success "Servicio está saludable"
            print_info "Respuesta: $response"
            return 0
        fi
        
        echo -ne "\r  Intento $attempt/$max_attempts..."
        attempt=$((attempt + 1))
        sleep 1
    done
    
    print_error "Servicio no respondió después de $max_attempts intentos"
    print_error "Revisa los logs:"
    print_info "  podman logs $PROJECT_NAME"
    exit 1
}

################################################################################
# INFORMACIÓN FINAL
################################################################################

print_summary() {
    print_header "Despliegue completado exitosamente"
    
    echo ""
    print_success "Servicio TaleDownload está corriendo"
    echo ""
    
    print_info "URLs de acceso:"
    echo "  🌐 Frontend:    http://localhost:$PORT"
    echo "  📚 Swagger:     http://localhost:$PORT/api/docs"
    echo "  📖 ReDoc:       http://localhost:$PORT/api/redoc"
    echo "  🏥 Health:      http://localhost:$PORT/api/health"
    echo ""
    
    print_info "Comandos útiles:"
    echo "  Ver logs:       podman logs -f $PROJECT_NAME"
    echo "  Estado:         podman ps -f name=$PROJECT_NAME"
    echo "  Estadísticas:   podman stats $PROJECT_NAME"
    echo "  Detener:        podman stop $PROJECT_NAME"
    echo "  Reiniciar:      podman restart $PROJECT_NAME"
    echo "  Eliminar:       podman stop $PROJECT_NAME && podman rm $PROJECT_NAME"
    echo ""
}

################################################################################
# PARSEO DE ARGUMENTOS
################################################################################

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cache)
                BUILD_CACHE="--no-cache"
                shift
                ;;
            --with-cache)
                BUILD_CACHE=""
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --help)
                show_help
                ;;
            *)
                print_error "Argumento desconocido: $1"
                show_help
                ;;
        esac
    done
}

################################################################################
# MAIN
################################################################################

main() {
    parse_arguments "$@"
    
    # Bienvenida
    clear
    echo ""
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════════╗
    ║                     TALE DOWNLOAD                              ║
    ║                  Deployment Script v1.0                        ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo ""
    
    # Ejecución
    validate_environment
    echo ""
    cleanup_existing
    echo ""
    build_image
    echo ""
    start_container
    echo ""
    validate_health
    echo ""
    print_summary
}

# Ejecutar main
main "$@"
