"""
Tests unitarios para la homologación canónica de tipo de unidad.

PRIORIDAD DE MATCH: LC > DPTO > EST > DEP > GAB > OTRO

Códigos canónicos:
- DPTO: cualquier tipo que contenga "departamento" (incluye duplex, loft, etc.)
- EST: cualquier tipo que contenga "estacionamiento" (incluye moto, doble, "con depósito", etc.)
- DEP: "depósito/deposito" SOLO cuando NO es estacionamiento
- LC: "local comercial"
- GAB: "gabinete"
- SIN_DATA: cuando tipo_unidad venga NULL o vacío
- OTRO: cualquier valor que no matchee con las reglas anteriores
"""
import pytest
import sys
import os

# Añadir el directorio raíz al path para poder importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.file_naming import homologar_tipo_unidad, extract_tipo_unidad, TIPO_UNIDAD_CODES


class TestHomologarTipoUnidad:
    """Tests para la función homologar_tipo_unidad"""
    
    # =========================================================================
    # CASOS BÁSICOS - DEPARTAMENTO (DPTO)
    # =========================================================================
    
    def test_departamento_simple(self):
        """departamento => DPTO"""
        assert homologar_tipo_unidad("departamento") == "DPTO"
    
    def test_departamento_mayusculas(self):
        """DEPARTAMENTO => DPTO"""
        assert homologar_tipo_unidad("DEPARTAMENTO") == "DPTO"
    
    def test_departamento_duplex(self):
        """departamento duplex => DPTO"""
        assert homologar_tipo_unidad("departamento duplex") == "DPTO"
    
    def test_departamento_loft(self):
        """departamento loft => DPTO"""
        assert homologar_tipo_unidad("departamento loft") == "DPTO"
    
    def test_departamento_con_espacios(self):
        """  departamento  => DPTO"""
        assert homologar_tipo_unidad("  departamento  ") == "DPTO"
    
    # =========================================================================
    # CASOS BÁSICOS - ESTACIONAMIENTO (EST)
    # =========================================================================
    
    def test_estacionamiento_simple(self):
        """estacionamiento => EST"""
        assert homologar_tipo_unidad("estacionamiento") == "EST"
    
    def test_estacionamiento_moto(self):
        """estacionamiento moto => EST"""
        assert homologar_tipo_unidad("estacionamiento moto") == "EST"
    
    def test_estacionamiento_doble(self):
        """estacionamiento doble => EST"""
        assert homologar_tipo_unidad("estacionamiento doble") == "EST"
    
    def test_estacionamiento_espacio_abierto(self):
        """estacionamiento espacio abierto => EST"""
        assert homologar_tipo_unidad("estacionamiento espacio abierto") == "EST"
    
    def test_estacionamiento_closet(self):
        """estacionamiento closet => EST"""
        assert homologar_tipo_unidad("estacionamiento closet") == "EST"
    
    # =========================================================================
    # CASO CRÍTICO: ESTACIONAMIENTO CON DEPÓSITO => EST (NO DEP)
    # =========================================================================
    
    def test_estacionamiento_con_deposito(self):
        """
        CASO CRÍTICO: estacionamiento con depósito => EST (NO DEP)
        La prioridad de EST es mayor que DEP.
        """
        assert homologar_tipo_unidad("estacionamiento con depósito") == "EST"
    
    def test_estacionamiento_con_deposito_sin_tilde(self):
        """estacionamiento con deposito => EST"""
        assert homologar_tipo_unidad("estacionamiento con deposito") == "EST"
    
    # =========================================================================
    # CASOS BÁSICOS - DEPÓSITO (DEP)
    # =========================================================================
    
    def test_deposito_simple(self):
        """depósito => DEP"""
        assert homologar_tipo_unidad("depósito") == "DEP"
    
    def test_deposito_sin_tilde(self):
        """deposito => DEP"""
        assert homologar_tipo_unidad("deposito") == "DEP"
    
    def test_deposito_mayusculas(self):
        """DEPÓSITO => DEP"""
        assert homologar_tipo_unidad("DEPÓSITO") == "DEP"
    
    # =========================================================================
    # CASOS BÁSICOS - LOCAL COMERCIAL (LC)
    # =========================================================================
    
    def test_local_comercial(self):
        """local comercial => LC"""
        assert homologar_tipo_unidad("local comercial") == "LC"
    
    def test_local_comercial_mayusculas(self):
        """LOCAL COMERCIAL => LC"""
        assert homologar_tipo_unidad("LOCAL COMERCIAL") == "LC"
    
    def test_local_comercial_mixto(self):
        """Local Comercial => LC"""
        assert homologar_tipo_unidad("Local Comercial") == "LC"
    
    # =========================================================================
    # CASOS BÁSICOS - GABINETE (GAB)
    # =========================================================================
    
    def test_gabinete_simple(self):
        """gabinete => GAB"""
        assert homologar_tipo_unidad("gabinete") == "GAB"
    
    def test_gabinete_mayusculas(self):
        """GABINETE => GAB"""
        assert homologar_tipo_unidad("GABINETE") == "GAB"
    
    # =========================================================================
    # CASOS DE SEGURIDAD - SIN_DATA
    # =========================================================================
    
    def test_null(self):
        """NULL => SIN_DATA"""
        assert homologar_tipo_unidad(None) == "SIN_DATA"
    
    def test_vacio(self):
        """'' => SIN_DATA"""
        assert homologar_tipo_unidad("") == "SIN_DATA"
    
    def test_espacios_vacios(self):
        """'   ' => SIN_DATA"""
        assert homologar_tipo_unidad("   ") == "SIN_DATA"
    
    # =========================================================================
    # CASOS DE SEGURIDAD - OTRO
    # =========================================================================
    
    def test_valor_desconocido(self):
        """cualquier otro => OTRO"""
        assert homologar_tipo_unidad("cualquier otro") == "OTRO"
    
    def test_texto_aleatorio(self):
        """xyz123 => OTRO"""
        assert homologar_tipo_unidad("xyz123") == "OTRO"
    
    def test_oficina(self):
        """oficina => OTRO (no hay regla para oficina)"""
        assert homologar_tipo_unidad("oficina") == "OTRO"
    
    # =========================================================================
    # CÓDIGOS CANÓNICOS DIRECTOS (ya homologados)
    # =========================================================================
    
    def test_codigo_dpto_directo(self):
        """DPTO => DPTO (ya es código canónico)"""
        assert homologar_tipo_unidad("DPTO") == "DPTO"
    
    def test_codigo_est_directo(self):
        """EST => EST (ya es código canónico)"""
        assert homologar_tipo_unidad("EST") == "EST"
    
    def test_codigo_dep_directo(self):
        """DEP => DEP (ya es código canónico)"""
        assert homologar_tipo_unidad("DEP") == "DEP"
    
    def test_codigo_lc_directo(self):
        """LC => LC (ya es código canónico)"""
        assert homologar_tipo_unidad("LC") == "LC"
    
    def test_codigo_gab_directo(self):
        """GAB => GAB (ya es código canónico)"""
        assert homologar_tipo_unidad("GAB") == "GAB"
    
    # =========================================================================
    # BACKWARD COMPATIBILITY - CÓDIGOS LEGACY
    # =========================================================================
    
    def test_legacy_loc_a_lc(self):
        """LOC => LC (backward compatibility)"""
        assert homologar_tipo_unidad("LOC") == "LC"
    
    def test_legacy_local_a_lc(self):
        """LOCAL => LC (backward compatibility)"""
        assert homologar_tipo_unidad("LOCAL") == "LC"
    
    def test_legacy_estac_a_est(self):
        """ESTAC => EST (backward compatibility)"""
        assert homologar_tipo_unidad("ESTAC") == "EST"
    
    def test_legacy_ofic_a_lc(self):
        """OFIC => LC (backward compatibility, aproximación)"""
        assert homologar_tipo_unidad("OFIC") == "LC"
    
    def test_legacy_tienda_a_lc(self):
        """TIENDA => LC (backward compatibility)"""
        assert homologar_tipo_unidad("TIENDA") == "LC"
    
    def test_legacy_unidad_a_otro(self):
        """UNIDAD => OTRO (backward compatibility)"""
        assert homologar_tipo_unidad("UNIDAD") == "OTRO"


class TestExtractTipoUnidad:
    """Tests para la función extract_tipo_unidad"""
    
    def test_prefiere_tipo_unidad_db(self):
        """Debe preferir tipo_unidad_db sobre código de unidad"""
        result = extract_tipo_unidad("PAINO-E123", "departamento loft")
        assert result == "DPTO"
    
    def test_fallback_a_codigo_unidad(self):
        """Si no hay tipo_unidad_db, debe usar el código de unidad"""
        result = extract_tipo_unidad("PAINO-E123", None)
        assert result == "EST"  # E = Estacionamiento
    
    def test_codigo_numerico_es_dpto(self):
        """Si el código es numérico, asume DPTO"""
        result = extract_tipo_unidad("PAINO-305", None)
        assert result == "DPTO"
    
    def test_sin_codigo_unidad(self):
        """Si no hay codigo_unidad, devuelve SIN_DATA"""
        result = extract_tipo_unidad(None, None)
        assert result == "SIN_DATA"


class TestTipoUnidadCodes:
    """Tests para validar que TIPO_UNIDAD_CODES contiene todos los códigos"""
    
    def test_contiene_dpto(self):
        assert "DPTO" in TIPO_UNIDAD_CODES
    
    def test_contiene_est(self):
        assert "EST" in TIPO_UNIDAD_CODES
    
    def test_contiene_dep(self):
        assert "DEP" in TIPO_UNIDAD_CODES
    
    def test_contiene_lc(self):
        assert "LC" in TIPO_UNIDAD_CODES
    
    def test_contiene_gab(self):
        assert "GAB" in TIPO_UNIDAD_CODES
    
    def test_contiene_sin_data(self):
        assert "SIN_DATA" in TIPO_UNIDAD_CODES
    
    def test_contiene_otro(self):
        assert "OTRO" in TIPO_UNIDAD_CODES
    
    def test_labels_son_strings(self):
        """Todos los labels deben ser strings no vacíos"""
        for code, label in TIPO_UNIDAD_CODES.items():
            assert isinstance(label, str)
            assert len(label) > 0


# =========================================================================
# TESTS DE INTEGRACIÓN: EVIDENCIA DE 8 ENTRADAS
# =========================================================================

class TestEvidencia8Entradas:
    """
    Tests que demuestran la homologación con 8 entradas representativas.
    Esto sirve como evidencia para validación.
    """
    
    def test_evidencia_completa(self):
        """Tabla de evidencia: raw tipo_unidad -> homologado nuevo"""
        casos = [
            ("departamento", "DPTO"),
            ("departamento duplex", "DPTO"),
            ("departamento loft", "DPTO"),
            ("estacionamiento con depósito", "EST"),  # CASO CRÍTICO
            ("depósito", "DEP"),
            ("local comercial", "LC"),
            ("gabinete", "GAB"),
            (None, "SIN_DATA"),
            ("", "SIN_DATA"),
            ("cualquier otro", "OTRO"),
        ]
        
        print("\n" + "=" * 70)
        print("EVIDENCIA DE HOMOLOGACIÓN DE TIPO DE UNIDAD")
        print("=" * 70)
        print(f"{'Raw tipo_unidad':<35} | {'Homologado':<10}")
        print("-" * 70)
        
        for raw, expected in casos:
            result = homologar_tipo_unidad(raw)
            display_raw = f'"{raw}"' if raw else str(raw)
            print(f"{display_raw:<35} | {result:<10}")
            assert result == expected, f"Falló: {raw} debería ser {expected}, pero fue {result}"
        
        print("=" * 70)
        print("✓ Todos los casos pasaron correctamente")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
