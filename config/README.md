# Configuración de FlyM Aviation Receiver

Este directorio contiene todos los archivos de configuración del sistema.

## 📄 Archivos

### `config.yaml` - Configuración Principal
Archivo principal de configuración del sistema con todas las opciones personalizables.

### `memories.json` - Memorias de Frecuencias
Almacena las 10 memorias de frecuencias guardadas (generado automáticamente).

## 🎛️ Secciones de Configuración

### GPIO Pins
Configuración de todos los pines GPIO utilizados:

```yaml
gpio_pins:
  button_menu: 17      # Botón para cambiar de menú
  button_plus: 27      # Botón + (incrementar)
  button_minus: 22     # Botón - (decrementar)
  button_record: 23    # Botón de grabación
  led_record: 24       # LED indicador de grabación
```

**Numeración:** BCM (Broadcom) - no usar numeración física de pines.

### Display (Pantallas OLED)
Configuración de pantallas OLED:

```yaml
display:
  main_display:
    address: 0x3C      # Dirección I²C (usar i2cdetect para verificar)
    i2c_port: 1        # Puerto I²C (1 en Raspberry Pi)
    width: 128         # Ancho en píxeles
    height: 32         # Alto en píxeles
```

### Menús
Orden y configuración de cada menú:

```yaml
menus:
  order:               # Orden de navegación con botón MENU
    - frequency
    - autoscan
    - gain
    - volume
    - memory
    - vox
```

Cada menú tiene su propia configuración:
- `name`: Texto mostrado en pantalla
- `min`/`max`: Rango de valores
- `step`: Incremento al presionar +/-
- `default`: Valor inicial
- `format`: Formato de visualización

### SDR (RTL-SDR)
Configuración del receptor SDR:

```yaml
sdr:
  sample_rate: 2048000      # 2.048 MHz
  default_frequency: 125000000  # 125 MHz (Hz)
  default_gain: 30          # 30 dB
  buffer_size: 262144       # 256K muestras
```

### Audio (PCM5102 DAC)
Configuración de audio:

```yaml
audio:
  sample_rate: 48000        # 48 kHz
  channels: 1               # Mono
  default_volume: 50        # Volumen inicial (0-100)
  recordings_path: 'recordings'  # Carpeta de grabaciones
```

### VOX (Grabación Automática)
Configuración de VOX:

```yaml
vox:
  threshold: -60            # Umbral RSSI en dB
  delay: 2.0                # Segundos de delay antes de parar
```

## 🔧 Personalización

### Cambiar orden de menús
Edita la sección `menus.order` en `config.yaml`:

```yaml
menus:
  order:
    - frequency
    - volume      # Mover volumen antes
    - gain
    - autoscan
    - memory
    - vox
```

### Cambiar pines GPIO
Edita la sección `gpio_pins`:

```yaml
gpio_pins:
  button_menu: 18    # Cambiar a GPIO 18
  button_plus: 23
  button_minus: 24
```

### Ajustar rangos de controles
Edita cada menú individual:

```yaml
menus:
  gain:
    min: 0
    max: 40        # Limitar ganancia a 40 dB
    step: 1        # Cambiar paso a 1 dB
```

### Cambiar incremento de frecuencia
```yaml
menus:
  frequency:
    step: 0.0125   # Cambiar a 12.5 kHz (8.33 kHz para uso civil: 0.00833)
```

## ⚠️ Notas Importantes

1. **Reiniciar después de cambios**: El sistema debe reiniciarse para aplicar cambios en `config.yaml`
2. **Formato YAML**: Respetar indentación (usar espacios, no tabs)
3. **Frecuencias en MHz**: Para menús, usar MHz (125.0). El sistema convierte a Hz internamente
4. **Pines BCM**: Usar numeración BCM, no física
5. **Backup**: Hacer copia de `config.yaml` antes de modificar

## 🔍 Verificación de I²C

Para verificar la dirección de tu pantalla OLED:
```bash
sudo i2cdetect -y 1
```

Busca la dirección hexadecimal (normalmente 0x3C o 0x3D) y actualiza en `config.yaml`.

## 📝 Valores por Defecto

Si se elimina `config.yaml`, el sistema usa valores hardcoded:
- Frecuencia: 125.0 MHz
- Ganancia: 30 dB
- Volumen: 50%
- Pines: MENU=17, PLUS=27, MINUS=22
- Orden de menús: frequency, autoscan, gain, volume, memory, vox
