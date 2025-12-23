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
    Sanitiza nombre de carpeta (permite espacios y guiones) y convierte a mayúsculas
    
    Args:
        name: Nombre original
    
    Returns:
        Nombre sanitizado en mayúsculas
    """
    # Remover solo caracteres verdaderamente inválidos
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Normalizar espacios múltiples
    name = re.sub(r'\s+', ' ', name).strip()
    # Convertir a mayúsculas
    name = name.upper()
    return name

"""
HOMOLOGACIÓN CANÓNICA DE TIPO DE UNIDAD
=======================================
Códigos oficiales con prioridad de match: LC > DPTO > EST > DEP > GAB > OTRO

- DPTO: cualquier tipo que contenga "departamento" (incluye duplex, loft, etc.)
- EST: cualquier tipo que contenga "estacionamiento" (incluye moto, doble, "con depósito", etc.)
- DEP: "depósito/deposito" SOLO cuando NO es estacionamiento
- LC: "local comercial"
- GAB: "gabinete"
- SIN_DATA: cuando tipo_unidad venga NULL o vacío
- OTRO: cualquier valor que no matchee con las reglas anteriores
"""

# Códigos canónicos de tipo de unidad
TIPO_UNIDAD_CODES = {
    'DPTO': 'Departamento',
    'EST': 'Estacionamiento',
    'DEP': 'Depósito',
    'LC': 'Local Comercial',
    'GAB': 'Gabinete',
    'SIN_DATA': 'Sin Datos',
    'OTRO': 'Otro',
}

# Backward compatibility: mapeo de códigos antiguos a canónicos
TIPO_UNIDAD_LEGACY_MAP = {
    'LOC': 'LC',        # LOC → LC (Local Comercial)
    'LOCAL': 'LC',      # LOCAL → LC
    'ESTAC': 'EST',     # ESTAC → EST
    'OFIC': 'LC',       # Oficina → Local Comercial (aproximación)
    'TIENDA': 'LC',     # Tienda → Local Comercial
    'UNIDAD': 'OTRO',   # Genérico → Otro
}


def homologar_tipo_unidad(tipo_unidad_raw: str) -> str:
    """
    Homologa un tipo de unidad raw al código canónico.
    
    PRIORIDAD DE MATCH: LC > DPTO > EST > DEP > GAB > OTRO
    
    Ejemplo crítico:
        "estacionamiento con depósito" => EST (NO DEP)
    
    Args:
        tipo_unidad_raw: Valor raw desde la BD o código ya homologado
    
    Returns:
        Código canónico (DPTO, EST, DEP, LC, GAB, SIN_DATA, OTRO)
    """
    if not tipo_unidad_raw or not tipo_unidad_raw.strip():
        return 'SIN_DATA'
    
    tipo_lower = tipo_unidad_raw.lower().strip()
    
    # Si ya es un código canónico, devolverlo normalizado
    tipo_upper = tipo_unidad_raw.upper().strip()
    if tipo_upper in TIPO_UNIDAD_CODES:
        return tipo_upper
    
    # Backward compatibility: códigos legacy
    if tipo_upper in TIPO_UNIDAD_LEGACY_MAP:
        return TIPO_UNIDAD_LEGACY_MAP[tipo_upper]
    
    # Aplicar reglas de homologación con PRIORIDAD: LC > DPTO > EST > DEP > GAB > OTRO
    if 'local comercial' in tipo_lower:
        return 'LC'
    if 'departamento' in tipo_lower:
        return 'DPTO'
    if 'estacionamiento' in tipo_lower:
        return 'EST'
    if 'depósito' in tipo_lower or 'deposito' in tipo_lower:
        return 'DEP'
    if 'gabinete' in tipo_lower:
        return 'GAB'
    
    return 'OTRO'


def extract_tipo_unidad(codigo_unidad: str, tipo_unidad_db: str = None) -> str:
    """
    Extrae y homologa el tipo de unidad del código de unidad o usa el de la BD.
    
    Ejemplos:
        "departamento" → DPTO
        "departamento duplex" → DPTO
        "estacionamiento con depósito" → EST (prioridad EST sobre DEP)
        "local comercial" → LC
        "gabinete" → GAB
        NULL / '' → SIN_DATA
    
    Args:
        codigo_unidad: Código de unidad completo
        tipo_unidad_db: Tipo de unidad desde la base de datos (preferido)
    
    Returns:
        Tipo de unidad homologado (código canónico)
    """
    # Priorizar tipo de unidad de la BD si existe
    if tipo_unidad_db and tipo_unidad_db.strip():
        return homologar_tipo_unidad(tipo_unidad_db)
    
    if not codigo_unidad:
        return "SIN_DATA"
    
    # Fallback: extraer del código de unidad
    parts = codigo_unidad.split('-')
    if len(parts) < 2:
        return "DPTO"  # Default para códigos simples
    
    prefix = parts[1][:1].upper()  # Primer carácter del sufijo
    
    # Mapeo de prefijos comunes a códigos canónicos
    prefix_map = {
        'E': 'EST',     # E = Estacionamiento
        'D': 'DPTO',    # D = Departamento
        'L': 'LC',      # L = Local Comercial
        'G': 'GAB',     # G = Gabinete
        'P': 'DEP',     # P = depósito (a veces usan P)
    }
    
    # Si es número, es departamento
    if prefix.isdigit():
        return "DPTO"
    
    return prefix_map.get(prefix, "DPTO")

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
        nombre_display = f"DNI {documento_cliente}".upper()
    else:
        nombre_display = sanitize_folder_name(nombre_cliente).upper()
    
    # Formato final: {TIPO_UNIDAD}-{CODIGO_UNIDAD} - {NOMBRE_CLIENTE}
    folder_name = f"{unidad_id} - {nombre_display}"
    
    return folder_name
