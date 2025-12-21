"""
Utilidad de renombrado de archivos según convención TALE
ESTRUCTURA CONGELADA - NO MODIFICAR SIN APROBACIÓN
"""
import re
from typing import Dict, Any

def sanitize_filename(name: str) -> str:
    """
    Sanitiza un nombre de archivo removiendo caracteres no válidos
    
    Args:
        name: Nombre original
    
    Returns:
        Nombre sanitizado
    """
    # Remover caracteres no válidos para filesystem
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Reemplazar espacios por guiones bajos
    name = name.replace(' ', '_')
    # Remover múltiples guiones bajos consecutivos
    name = re.sub(r'_+', '_', name)
    return name

def sanitize_folder_name(name: str) -> str:
    """
    Sanitiza nombre de carpeta (permite espacios y guiones)
    
    Args:
        name: Nombre original
    
    Returns:
        Nombre sanitizado
    """
    # Remover solo caracteres verdaderamente inválidos
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Normalizar espacios múltiples
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_tipo_unidad(codigo_unidad: str, tipo_unidad_db: str = None) -> str:
    """
    Extrae el tipo de unidad del código de unidad o usa el de la BD
    
    Ejemplos:
        DPTO-305 → DPTO
        PAINO-E121 → E (Estacionamiento)
        PAINO-1912 → DPTO (por defecto si no tiene prefijo claro)
    
    Args:
        codigo_unidad: Código de unidad completo
        tipo_unidad_db: Tipo de unidad desde la base de datos (preferido)
    
    Returns:
        Tipo de unidad homologado
    """
    # Priorizar tipo de unidad de la BD si existe
    if tipo_unidad_db and tipo_unidad_db.strip():
        return sanitize_filename(tipo_unidad_db.strip())
    
    if not codigo_unidad:
        return "UNIDAD"
    
    # Extraer parte antes del guión
    parts = codigo_unidad.split('-')
    if len(parts) < 2:
        return "DPTO"  # Default
    
    prefix = parts[1][:1].upper()  # Primer carácter del sufijo
    
    # Mapeo de tipos comunes
    tipo_map = {
        'E': 'ESTAC',
        'D': 'DPTO',
        'O': 'OFIC',
        'T': 'TIENDA',
        'L': 'LOCAL',
    }
    
    # Si es número, es departamento
    if prefix.isdigit():
        return "DPTO"
    
    return tipo_map.get(prefix, "DPTO")

def generate_filename(doc: Dict[str, Any]) -> str:
    """
    Genera nombre de archivo según convención TALE OFICIAL
    
    Formato CONGELADO:
    {codigo_proyecto}_{codigo_proforma}_{documento_cliente}_{tipo_documento}_{TIPO_UNIDAD}-{CODIGO_UNIDAD}.pdf
    
    Ejemplo:
    PAINO_2025-01061_70349193_Voucher_DPTO-305.pdf
    
    Args:
        doc: Diccionario con metadata del documento
    
    Returns:
        Nombre de archivo sanitizado
    """
    codigo_proyecto = doc.get('codigo_proyecto', 'UNKNOWN')
    codigo_proforma = doc.get('codigo_proforma', 'UNKNOWN')
    documento_cliente = doc.get('documento_cliente', 'UNKNOWN')
    tipo_documento = doc.get('tipo_documento', 'Otro')
    codigo_unidad = doc.get('codigo_unidad', 'UNKNOWN')
    tipo_unidad_db = doc.get('tipo_unidad')
    
    # Normalizar tipo de documento (remover espacios)
    tipo_documento = tipo_documento.replace(' ', '')
    
    # Extraer tipo de unidad (preferir el de BD)
    tipo_unidad = extract_tipo_unidad(codigo_unidad, tipo_unidad_db)
    
    # Construir filename
    parts = [
        sanitize_filename(codigo_proyecto),
        sanitize_filename(codigo_proforma),
        sanitize_filename(documento_cliente),
        sanitize_filename(tipo_documento),
        f"{tipo_unidad}-{sanitize_filename(codigo_unidad.split('-')[-1])}"
    ]
    
    filename = '_'.join(parts) + '.pdf'
    
    return filename

def generate_folder_path(doc: Dict[str, Any], project_code: str = None) -> str:
    """
    Genera ruta de carpetas según convención TALE OFICIAL
    
    Formato CONGELADO:
    {TIPO_UNIDAD}-{CODIGO_UNIDAD} - {NOMBRE_CLIENTE}
    
    Ejemplo:
    DPTO-305 - Lijhoan Machaca Camarena
    
    Args:
        doc: Diccionario con metadata del documento
        project_code: Código del proyecto (opcional, para contexto)
    
    Returns:
        Ruta de carpeta sanitizada
    """
    codigo_unidad = doc.get('codigo_unidad', 'UNKNOWN')
    documento_cliente = doc.get('documento_cliente', 'UNKNOWN')
    nombre_cliente = doc.get('nombre_cliente', '')
    tipo_unidad_db = doc.get('tipo_unidad')
    
    # Extraer tipo de unidad (preferir el de BD)
    tipo_unidad = extract_tipo_unidad(codigo_unidad, tipo_unidad_db)
    
    # Limpiar código de unidad (quitar prefijo de proyecto si existe)
    unidad_limpia = codigo_unidad.split('-')[-1] if '-' in codigo_unidad else codigo_unidad
    
    # Construir identificador de unidad
    unidad_id = f"{tipo_unidad}-{unidad_limpia}"
    
    # Si no hay nombre de cliente, usar documento como fallback
    if not nombre_cliente or nombre_cliente.strip() == '':
        nombre_display = f"DNI {documento_cliente}"
    else:
        nombre_display = sanitize_folder_name(nombre_cliente)
    
    # Formato final: {TIPO_UNIDAD}-{CODIGO_UNIDAD} - {NOMBRE_CLIENTE}
    folder_name = f"{unidad_id} - {nombre_display}"
    
    return folder_name
