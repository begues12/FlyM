# ⚡ Conexiones Rápidas FlyM

## 📟 OLED Display (SSD1306 128x32)

| OLED | → | Raspberry Pi |
|------|---|--------------|
| VCC  | → | Pin 1 (3.3V) |
| GND  | → | Pin 6 (GND)  |
| SDA  | → | Pin 3 (GPIO2) |
| SCL  | → | Pin 5 (GPIO3) |

**Dirección I²C:** 0x3C

---

## 🎵 DAC PCM5102 (Audio)

| PCM5102 | → | Raspberry Pi |
|---------|---|--------------|
| VIN     | → | Pin 1 (3.3V) |
| GND     | → | Pin 6 (GND)  |
| BCK     | → | Pin 12 (GPIO18) |
| DIN     | → | Pin 40 (GPIO21) |
| LCK     | → | Pin 35 (GPIO19) |
| SCK     | → | GND |
| FLT     | → | 3.3V |
| XSMT    | → | 3.3V |

---


## 🔢 MCP3008 ADC (SPI)

| MCP3008 Pin | Nombre | → | Raspberry Pi |
|-------------|--------|---|--------------|
| 16 | VDD    | → | Pin 1 (3.3V) |
| 15 | VREF   | → | Pin 1 (3.3V) |
| 14 | AGND   | → | Pin 6 (GND) |
| 9  | DGND   | → | Pin 6 (GND) |
| 13 | CLK    | → | Pin 23 (GPIO11) |
| 12 | DOUT   | → | Pin 21 (GPIO9) |
| 11 | DIN    | → | Pin 19 (GPIO10) |
| 10 | CS     | → | Pin 24 (GPIO8) |

---

## 🎛️ Potenciómetros → MCP3008

### Potenciómetro 1 (Volumen)
| Pot 1 | → | Conexión |
|-------|---|----------|
| Pin 1 | → | GND |
| Pin 2 | → | MCP3008 CH0 (pin 1) |
| Pin 3 | → | 3.3V |

### Potenciómetro 2 (Ganancia)
| Pot 2 | → | Conexión |
|-------|---|----------|
| Pin 1 | → | GND |
| Pin 2 | → | MCP3008 CH1 (pin 2) |
| Pin 3 | → | 3.3V |

### Potenciómetro 3 (Squelch)
| Pot 3 | → | Conexión |
|-------|---|----------|
| Pin 1 | → | GND |
| Pin 2 | → | MCP3008 CH2 (pin 3) |
| Pin 3 | → | 3.3V |

---

## 📻 RTL-SDR

| RTL-SDR | → | Raspberry Pi |
|---------|---|--------------|
| USB     | → | Puerto USB   |

**Antena VHF:** 118-137 MHz  
**Antena ADS-B:** 1090 MHz

---

## 🔊 Altavoz

| Salida | → | Altavoz |
|--------|---|---------|
| PCM5102 OUT | → | Altavoz 8Ω |

---

## 📋 Resumen Alimentación

**3.3V (Pin 1):**
- OLED VCC
- MCP3008 VDD + VREF
- Potenciómetros (todos Pin 3)
- PCM5102 VIN

**GND (Pin 6):**
- OLED GND
- MCP3008 AGND + DGND
- Potenciómetros (todos Pin 1)
- PCM5102 GND
- Botón grabación (Pin 2)
- LED cátodo (vía resistencia 220Ω)

---

## ✅ Verificación

```bash
# I²C (OLED)
sudo i2cdetect -y 1
# Debe mostrar: 0x3C

# SPI (MCP3008)
ls /dev/spi*
# Debe mostrar: /dev/spidev0.0

# GPIO
gpio readall
```
