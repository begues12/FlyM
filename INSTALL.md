# 🚀 Guía de Instalación FlyM

## 📋 Requisitos Previos

### Hardware Necesario
- **Raspberry Pi 4** (recomendado) o superior
- **RTL-SDR** (USB dongle para recepción radio)
- **PCM5102 DAC** (salida audio I2S)
- **OLED SSD1306** (128x64 o 128x32, I2C)
- **MCP3008** (ADC 10-bit SPI, para potenciómetros)
- **3 Potenciómetros** (10kΩ)
- **1 Botón pulsador** + **1 LED**

### Software Necesario
- **Sistema Operativo:** Raspberry Pi OS (32 o 64-bit)
- **Python:** 3.7 o superior
- **Git:** Para clonar el repositorio

---

## 🔧 Instalación en Raspberry Pi (Producción)

### 1. Actualizar Sistema
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Instalar Dependencias del Sistema
```bash
# Librerías RTL-SDR
sudo apt install -y rtl-sdr librtlsdr-dev

# Librerías de audio
sudo apt install -y python3-dev python3-pip \
    libportaudio2 libsndfile1

# Herramientas de compilación (para spidev)
sudo apt install -y build-essential python3-dev

# I2C y SPI (para OLED y MCP3008)
sudo apt install -y i2c-tools python3-smbus
```

### 3. Habilitar I2C y SPI
```bash
sudo raspi-config
# Ir a: Interface Options → I2C → Enable
# Ir a: Interface Options → SPI → Enable
# Reiniciar
```

### 4. Clonar Repositorio
```bash
cd ~
git clone https://github.com/tu-usuario/FlyM.git
cd FlyM
```

### 5. Crear Entorno Virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. Instalar Dependencias Python
```bash
# Actualizar pip
pip install --upgrade pip

# Dependencias base
pip install -r requirements.txt

# Dependencias específicas de Raspberry Pi
pip install -r requirements-rpi.txt
```

### 7. Configurar
```bash
# Copiar configuración de ejemplo
cp config.example.yaml config.yaml

# Editar según tu hardware
nano config.yaml
```

### 8. Probar
```bash
# Test de hardware
python3 scripts/test_hardware.py

# Ejecutar
python3 src/main.py
```

---

## 💻 Instalación en Windows/Mac (Desarrollo)

### 1. Instalar Python
- **Windows:** [python.org](https://www.python.org/downloads/)
- **Mac:** `brew install python3`

### 2. Clonar Repositorio
```bash
git clone https://github.com/tu-usuario/FlyM.git
cd FlyM
```

### 3. Crear Entorno Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar Dependencias Base
```bash
# Actualizar pip
python -m pip install --upgrade pip

# Solo dependencias base (sin GPIO)
pip install -r requirements.txt
```

**⚠️ IMPORTANTE:** En Windows/Mac **NO instalar** `requirements-rpi.txt` (GPIO no funciona).

### 5. Desarrollo con Mocks
Para desarrollo sin hardware:
```python
# En tu código de desarrollo, usar mocks:
try:
    import RPi.GPIO as GPIO
    import spidev
except ImportError:
    # Mock para desarrollo en Windows/Mac
    import unittest.mock as mock
    GPIO = mock.MagicMock()
    spidev = mock.MagicMock()
```

---

## 🧪 Instalación para Desarrollo Completo

```bash
# Instalar herramientas de desarrollo
pip install -r requirements-dev.txt

# Configurar pre-commit hooks
pip install pre-commit
pre-commit install

# Ejecutar tests
pytest tests/

# Formatear código
black src/

# Linting
flake8 src/
```

---

## 📦 Estructura de Dependencias

```
requirements.txt          → Base (Windows/Linux/Mac compatible)
requirements-rpi.txt      → Solo Raspberry Pi (GPIO/SPI)
requirements-dev.txt      → Desarrollo (testing, linting)
```

### Instalación Según Plataforma

| Plataforma | Comando |
|------------|---------|
| **Raspberry Pi (producción)** | `pip install -r requirements.txt -r requirements-rpi.txt` |
| **Windows/Mac (desarrollo)** | `pip install -r requirements.txt` |
| **Desarrollo completo** | `pip install -r requirements-dev.txt` |

---

## 🐛 Solución de Problemas

### Error: "Microsoft Visual C++ 14.0 required" (Windows)
```bash
# NO instalar requirements-rpi.txt en Windows
# Solo usar requirements.txt
```

### Error: "No module named 'RPi.GPIO'"
```bash
# En Raspberry Pi:
pip install RPi.GPIO spidev

# En Windows/Mac:
# Normal, usar mocks para desarrollo
```

### Error: "Could not find RTL-SDR device"
```bash
# Verificar conexión USB
lsusb | grep RTL

# Verificar drivers
rtl_test
```

### Error: "I2C device not found"
```bash
# Verificar I2C habilitado
sudo i2cdetect -y 1

# Debe mostrar dispositivos (ej: 0x3C para OLED)
```

### Error: "Permission denied /dev/spidev0.0"
```bash
# Agregar usuario a grupo spi
sudo usermod -a -G spi $USER

# Reiniciar sesión
```

---

## 🚀 Inicio Automático (Raspberry Pi)

### Crear Servicio Systemd
```bash
sudo nano /etc/systemd/system/flym.service
```

```ini
[Unit]
Description=FlyM Aviation Receiver
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/FlyM
Environment="PATH=/home/pi/FlyM/venv/bin"
ExecStart=/home/pi/FlyM/venv/bin/python3 /home/pi/FlyM/src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar servicio
sudo systemctl enable flym
sudo systemctl start flym

# Ver logs
sudo journalctl -u flym -f
```

---

## ✅ Verificación de Instalación

```bash
# Test rápido
python3 -c "import numpy, scipy, yaml, rtlsdr; print('✅ Dependencias OK')"

# Test completo
python3 scripts/test_hardware.py
```

---

## 📚 Recursos Adicionales

- [RTL-SDR Setup](https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/)
- [Raspberry Pi GPIO](https://www.raspberrypi.com/documentation/computers/os.html#gpio-and-the-40-pin-header)
- [I2C Configuration](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c)

---

**🎉 ¡Listo!** Tu receptor FlyM está instalado y funcionando.
