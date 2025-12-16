#!/bin/bash

##############################################################################
# FlyM Aviation Receiver - Script de Test de Hardware
# Verifica que todos los componentes estén correctamente conectados
##############################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_test() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
}

echo "========================================"
echo "  FlyM Hardware Test"
echo "========================================"

# Test 1: RTL-SDR
print_test "Test 1: RTL-SDR USB"
if lsusb | grep -q "Realtek"; then
    print_ok "RTL-SDR detectado"
    DEVICE=$(lsusb | grep "Realtek")
    echo "   $DEVICE"
    
    # Test de lectura
    echo "   Ejecutando rtl_test (5 segundos)..."
    timeout 5 rtl_test > /tmp/rtl_test.log 2>&1
    if [ $? -eq 124 ]; then
        print_ok "RTL-SDR funciona correctamente"
    else
        print_fail "Error al leer RTL-SDR"
        cat /tmp/rtl_test.log
    fi
else
    print_fail "RTL-SDR no detectado"
    echo "   Verifica la conexión USB"
fi

# Test 2: I²C (Pantallas OLED)
print_test "Test 2: Pantallas OLED (I²C)"
if [ -c /dev/i2c-1 ]; then
    print_ok "I²C habilitado"
    
    echo "   Escaneando dispositivos I²C..."
    I2C_DEVICES=$(i2cdetect -y 1 | grep -oE "[0-9a-f]{2}" | grep -vE "^(00|01|02|03|04|05|06|07)$")
    
    if echo "$I2C_DEVICES" | grep -q "3c"; then
        print_ok "Pantalla OLED en 0x3C detectada"
    else
        print_fail "No se detectó pantalla en 0x3C"
    fi
    
    if echo "$I2C_DEVICES" | grep -q "3d"; then
        print_ok "Pantalla OLED en 0x3D detectada"
    else
        print_fail "No se detectó pantalla en 0x3D"
    fi
    
    echo ""
    echo "   Mapa completo I²C:"
    i2cdetect -y 1
else
    print_fail "I²C no habilitado"
    echo "   Ejecuta: sudo raspi-config"
    echo "   Interface Options → I²C → Enable"
fi

# Test 3: SPI (MCP3008 ADC)
print_test "Test 3: ADC MCP3008 (SPI)"
if [ -c /dev/spidev0.0 ]; then
    print_ok "SPI habilitado"
    
    # Test Python de SPI
    python3 << 'EOF'
try:
    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1350000
    
    # Leer canal 0
    cmd = [1, (8 + 0) << 4, 0]
    result = spi.xfer2(cmd)
    value = ((result[1] & 3) << 8) + result[2]
    
    print(f"   Canal 0 (Volumen): {value}")
    
    # Leer canal 1
    cmd = [1, (8 + 1) << 4, 0]
    result = spi.xfer2(cmd)
    value = ((result[1] & 3) << 8) + result[2]
    
    print(f"   Canal 1 (Ganancia): {value}")
    
    spi.close()
    print("   ✓ MCP3008 responde correctamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
EOF
else
    print_fail "SPI no habilitado"
    echo "   Ejecuta: sudo raspi-config"
    echo "   Interface Options → SPI → Enable"
fi

# Test 4: GPIO (Botón + LED)
print_test "Test 4: Botón de Grabación + LED (GPIO)"
python3 << 'EOF'
try:
    import RPi.GPIO as GPIO
    import time
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Configurar pines
    GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Botón
    GPIO.setup(23, GPIO.OUT)  # LED
    
    # Leer estados
    button = GPIO.input(22)
    print(f"   Botón (GPIO22): {'Presionado' if button == 0 else 'No presionado'}")
    
    # Probar LED
    GPIO.output(23, GPIO.HIGH)
    print("   LED (GPIO23): ON")
    time.sleep(0.5)
    GPIO.output(23, GPIO.LOW)
    print("   LED (GPIO23): OFF")
    
    GPIO.cleanup()
    print("   ✓ GPIO funciona correctamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
EOF

# Test 5: Audio (I²S)
print_test "Test 5: Audio DAC (I²S)"
if aplay -l 2>/dev/null | grep -q "hifiberry"; then
    print_ok "HiFiBerry DAC detectado"
    aplay -l | grep -A 2 "hifiberry"
else
    print_fail "DAC no detectado"
    echo "   Verifica /boot/config.txt:"
    echo "   dtparam=i2s=on"
    echo "   dtoverlay=hifiberry-dac"
fi

# Test 6: Paquetes Python
print_test "Test 6: Paquetes Python"

check_package() {
    if pip3 list 2>/dev/null | grep -q "^$1 "; then
        VERSION=$(pip3 list 2>/dev/null | grep "^$1 " | awk '{print $2}')
        print_ok "$1 ($VERSION)"
    else
        print_fail "$1 no instalado"
    fi
}

check_package "numpy"
check_package "scipy"
check_package "pyrtlsdr"
check_package "sounddevice"
check_package "luma.oled"
check_package "RPi.GPIO"
check_package "spidev"
check_package "PyYAML"

# Resumen final
echo ""
echo "========================================"
echo "  Test Completado"
echo "========================================"
echo ""
echo "Si todos los tests pasaron, el hardware está listo."
echo "Ejecuta: ./scripts/start.sh para iniciar FlyM"
echo ""
