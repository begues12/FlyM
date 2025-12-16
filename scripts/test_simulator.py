#!/usr/bin/env python3
"""
Script de prueba del simulador FlyM
Permite probar todos los componentes sin hardware
"""

import sys
import time
from pathlib import Path

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Importar mocks
from simulation.mock_sdr import MockRtlSdr
from simulation.mock_gpio import MockGPIO, MockMCP3008
from simulation.mock_display import MockOLED, get_mock_device

def test_mock_sdr():
    """Prueba el mock SDR"""
    print("\n" + "="*60)
    print("🧪 Probando MockRtlSdr")
    print("="*60)
    
    sdr = MockRtlSdr()
    sdr.open()
    
    # Configurar
    sdr.set_center_freq(125_000_000)
    sdr.set_sample_rate(2_048_000)
    sdr.set_gain(30)
    
    # Leer muestras
    print("\n📊 Leyendo 1024 muestras...")
    samples = sdr.read_samples(1024)
    print(f"   Tipo: {samples.dtype}")
    print(f"   Shape: {samples.shape}")
    print(f"   Min: {abs(samples).min():.4f}")
    print(f"   Max: {abs(samples).max():.4f}")
    print(f"   Mean: {abs(samples).mean():.4f}")
    
    sdr.close()
    print("✅ MockRtlSdr funcionando correctamente\n")


def test_mock_gpio():
    """Prueba el mock GPIO"""
    print("="*60)
    print("🧪 Probando MockGPIO")
    print("="*60)
    
    gpio = MockGPIO
    
    # Configurar
    gpio.setmode(gpio.BCM)
    gpio.setup(23, gpio.OUT)
    gpio.setup(22, gpio.IN, pull_up_down=gpio.PUD_UP)
    
    # Probar salida
    print("\n💡 Probando salida (LED)...")
    for i in range(3):
        gpio.output(23, gpio.HIGH if i % 2 == 0 else gpio.LOW)
        time.sleep(0.2)
    
    # Probar entrada
    print("🔘 Probando entrada (botón)...")
    value = gpio.input(22)
    print(f"   Valor leído: {value}")
    
    gpio.cleanup()
    print("✅ MockGPIO funcionando correctamente\n")


def test_mock_adc():
    """Prueba el mock MCP3008"""
    print("="*60)
    print("🧪 Probando MockMCP3008")
    print("="*60)
    
    adc = MockMCP3008()
    
    print("\n📈 Leyendo 3 canales...")
    for channel in range(3):
        value = adc.read(channel)
        percent = adc.read_percent(channel)
        print(f"   Canal {channel}: {value:4d} ({percent:3d}%)")
    
    adc.close()
    print("✅ MockMCP3008 funcionando correctamente\n")


def test_mock_display():
    """Prueba el mock OLED"""
    print("="*60)
    print("🧪 Probando MockOLED")
    print("="*60)
    
    from PIL import Image, ImageDraw, ImageFont
    
    device = get_mock_device(width=128, height=32)
    oled = MockOLED(device=device)
    
    # Crear imagen de prueba
    image = Image.new("1", (128, 32))
    draw = ImageDraw.Draw(image)
    
    # Dibujar texto
    print("\n🖥️  Mostrando texto en display simulado...")
    draw.rectangle((0, 0, 128, 32), outline=0, fill=0)
    draw.text((10, 10), "FlyM Test", fill=1)
    
    oled.display(image)
    
    print("✅ MockOLED funcionando correctamente\n")


def test_all():
    """Ejecuta todas las pruebas"""
    print("\n🎭 INICIANDO PRUEBAS DEL SIMULADOR")
    print("="*60 + "\n")
    
    try:
        test_mock_sdr()
        test_mock_gpio()
        test_mock_adc()
        test_mock_display()
        
        print("="*60)
        print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("="*60 + "\n")
        
        print("💡 El simulador está listo para usar!")
        print("   Ejecuta: python src/main.py")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
