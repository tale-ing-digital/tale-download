"""
Script de prueba para validar la conversión de imágenes a PDF
y verificar que el bug fue correctamente solucionado.
"""

import sys
import os
from io import BytesIO
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.pdf_service import PDFService
from utils.file_naming import generate_folder_path, sanitize_filename


def test_image_to_pdf_conversion():
    """Prueba la conversión de imágenes a PDF con BytesIO"""
    print("\n" + "="*70)
    print("TEST 1: Conversión de Imágenes a PDF")
    print("="*70)
    
    try:
        # Crear una imagen simple en memoria (PNG)
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_bytes = img_buffer.read()
        
        print(f"✓ Imagen creada: {len(image_bytes)} bytes")
        
        # Intentar convertir a PDF
        result = PDFService.image_to_pdf(image_bytes)
        
        if result:
            print(f"✓ Conversión exitosa: {len(result)} bytes de PDF")
            print("✓ TEST PASSED: image_to_pdf funciona correctamente")
            return True
        else:
            print("✗ TEST FAILED: Conversión retornó None")
            return False
            
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_extension_detection():
    """Prueba la detección de extensiones de archivo"""
    print("\n" + "="*70)
    print("TEST 2: Detección de Extensiones de Archivo")
    print("="*70)
    
    try:
        # Crear imágenes de prueba
        from PIL import Image
        
        test_cases = [
            ('PNG', 'PNG'),
            ('JPEG', 'JPEG'),
        ]
        
        all_passed = True
        
        for format_name, pil_format in test_cases:
            img = Image.new('RGB', (50, 50), color='blue')
            img_buffer = BytesIO()
            img.save(img_buffer, format=pil_format)
            img_buffer.seek(0)
            image_bytes = img_buffer.read()
            
            detected_ext = PDFService.get_file_extension_from_content(image_bytes)
            expected_ext = '.jpg' if format_name == 'JPEG' else '.png'
            
            if detected_ext == expected_ext:
                print(f"✓ {format_name}: detectado como {detected_ext}")
            else:
                print(f"✗ {format_name}: detectado como {detected_ext}, esperado {expected_ext}")
                all_passed = False
        
        if all_passed:
            print("✓ TEST PASSED: Detección de extensiones correcta")
        else:
            print("✗ TEST FAILED: Algunos formatos no detectados correctamente")
        
        return all_passed
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convert_to_pdf():
    """Prueba el método convert_to_pdf con imágenes"""
    print("\n" + "="*70)
    print("TEST 3: Método convert_to_pdf() con Imágenes")
    print("="*70)
    
    try:
        from PIL import Image
        
        img = Image.new('RGB', (200, 200), color='green')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_bytes = img_buffer.read()
        
        result = PDFService.convert_to_pdf(image_bytes, "test_image.png")
        
        if result and result.get("mode") == "pdf" and result.get("content"):
            print(f"✓ Conversión completa exitosa")
            print(f"  - Modo: {result['mode']}")
            print(f"  - Tamaño: {len(result['content'])} bytes")
            print(f"  - Extensión: {result['extension']}")
            print("✓ TEST PASSED: convert_to_pdf funciona correctamente")
            return True
        else:
            print(f"✗ TEST FAILED: Resultado incompleto: {result}")
            return False
            
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_folder_name_uppercase():
    """Prueba que los nombres de carpeta están en mayúsculas"""
    print("\n" + "="*70)
    print("TEST 4: Nombres de Carpeta en MAYÚSCULAS")
    print("="*70)
    
    try:
        test_doc = {
            'codigo_unidad': 'PAINO-305',
            'documento_cliente': '12345678',
            'nombre_cliente': 'juan perez gutierrez',
            'tipo_unidad': 'DPTO'
        }
        
        folder_path = generate_folder_path(test_doc)
        print(f"Carpeta generada: {folder_path}")
        
        # Verificar que el nombre del cliente está en mayúsculas
        if "JUAN PEREZ GUTIERREZ" in folder_path:
            print("✓ Nombre del cliente en MAYÚSCULAS")
            print("✓ TEST PASSED: Homologación a mayúsculas correcta")
            return True
        else:
            print("✗ Nombre del cliente NO está en mayúsculas")
            print(f"  Valor encontrado: {folder_path}")
            print("✗ TEST FAILED: Homologación a mayúsculas no aplicada")
            return False
            
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  SUITE DE VALIDACIÓN - TaleDownload Bug Fix".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        test_image_to_pdf_conversion,
        test_file_extension_detection,
        test_convert_to_pdf,
        test_folder_name_uppercase,
    ]
    
    results = []
    for test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"\n✗ Error inesperado en {test_func.__name__}: {e}")
            results.append(False)
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\n✓ Tests pasados: {passed}/{total} ({percentage:.1f}%)")
    
    if all(results):
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("\nEl proyecto está listo para desplegar. Los siguientes bugs fueron corregidos:")
        print("  1. ✓ Conversión de imágenes a PDF (BytesIO handling)")
        print("  2. ✓ Detección de extensiones de archivo")
        print("  3. ✓ Pipeline completo convert_to_pdf")
        print("  4. ✓ Nombres de carpeta en mayúsculas")
        return 0
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        for i, result in enumerate(results, 1):
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  Test {i}: {status}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
