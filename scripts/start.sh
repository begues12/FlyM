#!/bin/bash

##############################################################################
# FlyM Aviation Receiver - Script de Inicio
# Inicia el sistema con configuración adecuada
##############################################################################

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================"
echo "  🛫 FlyM Aviation Receiver"
echo "================================"
echo ""

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Verificar que existe main.py
if [ ! -f "$PROJECT_DIR/src/main.py" ]; then
    echo -e "${RED}Error: main.py no encontrado${NC}"
    exit 1
fi

# Cambiar al directorio src
cd "$PROJECT_DIR/src"

# Verificar RTL-SDR
echo "Verificando RTL-SDR..."
if lsusb | grep -q "Realtek"; then
    echo -e "${GREEN}✓ RTL-SDR detectado${NC}"
else
    echo -e "${RED}✗ RTL-SDR no detectado${NC}"
    echo "Conecta el dispositivo RTL-SDR y vuelve a intentar"
    exit 1
fi

# Verificar I²C
echo "Verificando pantallas OLED..."
if i2cdetect -y 1 2>&1 | grep -qE "3c|3d"; then
    echo -e "${GREEN}✓ Pantallas OLED detectadas${NC}"
else
    echo -e "${RED}✗ Pantallas OLED no detectadas${NC}"
    echo "Verifica las conexiones I²C"
fi

echo ""
echo "Iniciando FlyM Aviation Receiver..."
echo "Presiona Ctrl+C para detener"
echo ""

# Ejecutar programa principal
python3 main.py

# Si el programa termina
echo ""
echo "FlyM detenido"
