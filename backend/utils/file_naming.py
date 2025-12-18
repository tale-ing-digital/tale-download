"""
Utilidad de renombrado de archivos según convención TALE
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
    # Remover caracteres no válidos
    name = re.sub(r'[<>:"/\|?*]', '', name)
    # Reemplazar espacios por guiones bajos
    name = name.replace(' ', '_')
    # Remover múltiples guiones bajos consecutivos
    name = re.sub(r'_+', '_', name)
    return name

def generate_filename(doc: Dict[str, Any]) -> str:
    """
    Genera nombre de archivo según convención TALE
    
    Formato: {codigo_proyecto}_{codigo_proforma}_{documento_cliente}_{tipo_documento}_{codigo_unidad}.pdf
    
    Args:
        doc: Diccionario con metadata del documento
    
    Returns:
        Nombre de archivo sanitizado
    """
    parts = [
        doc.get('codigo_proyecto', 'UNKNOWN'),
        doc.get('codigo_proforma', 'UNKNOWN'),
        doc.get('documento_cliente', 'UNKNOWN'),
        doc.get('tipo_documento', 'UNKNOWN'),
        doc.get('codigo_unidad', 'UNKNOWN'),
    ]
    
    # Sanitizar cada parte
    parts = [sanitize_filename(str(part)) for part in parts]
    
    # Unir con guiones bajos
    filename = '_'.join(parts) + '.pdf'
    
    return filename

def generate_folder_path(doc: Dict[str, Any]) -> str:
    """
    Genera ruta de carpetas según convención TALE
    
    Formato: {codigo_proyecto}/{codigo_proforma}/{codigo_unidad}/{tipo_documento}
    
    Args:
        doc: Diccionario con metadata del documento
    
    Returns:
        Ruta de carpetas sanitizada
    """
    parts = [
        doc.get('codigo_proyecto', 'UNKNOWN'),
        doc.get('codigo_proforma', 'UNKNOWN'),
        doc.get('codigo_unidad', 'UNKNOWN'),
        doc.get('tipo_documento', 'UNKNOWN'),
    ]
    
    # Sanitizar cada parte
    parts = [sanitize_filename(str(part)) for part in parts]
    
    # Unir con barras
    folder_path = '/'.join(parts)
    
    return folder_path
