#!/bin/bash

##############################################################################
# FlyM Aviation Receiver - Script de Instalación
# Instala todas las dependencias y configura el sistema
##############################################################################

set -e  # Salir si hay error

echo "================================"
echo "  FlyM Aviation Receiver"
echo "  Instalación Automática"
echo "================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que se ejecuta en Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    print_error "Este script debe ejecutarse en Raspberry Pi"
    exit 1
fi

print_info "Detectado: $(cat /proc/device-tree/model)"
echo ""

# Actualizar sistema
print_info "Actualizando sistema..."
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependencias del sistema
print_info "Instalando dependencias del sistema..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-numpy \
    python3-scipy \
    git \
    cmake \
    build-essential \
    libusb-1.0-0-dev \
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    i2c-tools \
    python3-smbus \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenjp2-7 \
    libtiff5

# Instalar RTL-SDR
print_info "Instalando RTL-SDR..."
if [ ! -d "$HOME/rtl-sdr" ]; then
    cd $HOME
    git clone https://github.com/osmocom/rtl-sdr.git
    cd rtl-sdr
    mkdir -p build
    cd build
    cmake ../ -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON
    make
    sudo make install
    sudo ldconfig
    
    # Agregar reglas udev
    sudo bash -c 'echo "SUBSYSTEM==\"usb\", ATTRS{idVendor}==\"0bda\", ATTRS{idProduct}==\"2838\", MODE=\"0666\"" > /etc/udev/rules.d/rtl-sdr.rules'
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    
    print_info "RTL-SDR instalado correctamente"
else
    print_warning "RTL-SDR ya está instalado"
fi

# Blacklist drivers DVB-T (interfieren con RTL-SDR)
print_info "Configurando blacklist de drivers DVB-T..."
sudo bash -c 'cat > /etc/modprobe.d/rtl-sdr-blacklist.conf << EOF
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist rtl2830
EOF'

# Habilitar I²C
print_info "Habilitando I²C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    sudo bash -c 'echo "dtparam=i2c_arm=on" >> /boot/config.txt'
fi

# Habilitar SPI
print_info "Habilitando SPI..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    sudo bash -c 'echo "dtparam=spi=on" >> /boot/config.txt'
fi

# Configurar I²S para PCM5102
print_info "Configurando I²S para DAC PCM5102..."
if ! grep -q "^dtparam=i2s=on" /boot/config.txt; then
    sudo bash -c 'echo "dtparam=i2s=on" >> /boot/config.txt'
fi

if ! grep -q "^dtoverlay=hifiberry-dac" /boot/config.txt; then
    sudo bash -c 'echo "dtoverlay=hifiberry-dac" >> /boot/config.txt'
fi

# Agregar usuario a grupos necesarios
print_info "Agregando usuario a grupos gpio, i2c, spi, audio..."
sudo usermod -a -G gpio,i2c,spi,audio $USER

# Instalar dependencias Python
print_info "Instalando dependencias Python..."
cd "$(dirname "$0")/.."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Crear directorio de logs
print_info "Creando directorio de logs..."
mkdir -p logs

# Verificar instalaciones
print_info "Verificando instalaciones..."

echo ""
echo "=== Verificación de Hardware ==="

# Verificar RTL-SDR
if command -v rtl_test &> /dev/null; then
    print_info "✓ RTL-SDR instalado"
else
    print_error "✗ RTL-SDR no encontrado"
fi

# Verificar I²C
if [ -c /dev/i2c-1 ]; then
    print_info "✓ I²C habilitado"
    i2cdetect -y 1 || true
else
    print_warning "✗ I²C no disponible (reiniciar requerido)"
fi

# Verificar SPI
if [ -c /dev/spidev0.0 ]; then
    print_info "✓ SPI habilitado"
else
    print_warning "✗ SPI no disponible (reiniciar requerido)"
fi

# Verificar Python packages
echo ""
echo "=== Paquetes Python ==="
pip3 list | grep -E "numpy|scipy|pyrtlsdr|sounddevice|luma|RPi.GPIO|spidev" || true

echo ""
echo "================================"
echo "  Instalación Completada"
echo "================================"
echo ""
print_info "Pasos siguientes:"
echo "  1. Conectar el hardware según docs/wiring.md"
echo "  2. Reiniciar: sudo reboot"
echo "  3. Ejecutar: cd ~/FlyM/src && python3 main.py"
echo ""
print_warning "IMPORTANTE: Se requiere reiniciar para aplicar cambios de I²C/SPI/I²S"
echo ""

read -p "¿Deseas reiniciar ahora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[SsYy]$ ]]; then
    print_info "Reiniciando..."
    sudo reboot
fi
