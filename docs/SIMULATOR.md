# 🎭 Guía del Simulador FlyM

## 📖 Descripción

El simulador FlyM permite desarrollar y probar el sistema sin hardware real (RTL-SDR, Raspberry Pi, etc.). Es ideal para:

- ✅ **Desarrollo en Windows/Mac/Linux**
- ✅ **Pruebas de funcionalidad**
- ✅ **Aprendizaje y experimentación**
- ✅ **Demos y presentaciones**

---

## 🚀 Inicio Rápido

### 1. **Modo Automático (Detección)**
```bash
python src/main.py
```
- Detecta automáticamente si falta hardware
- Inicia en modo simulación si es necesario
- Abre interfaz gráfica por defecto

### 2. **Modo GUI (Interfaz Gráfica)**
```bash
python src/main.py
```
![Interfaz GUI](../assets/gui_preview.png)

**Ventajas:**
- 🎚️ Controles deslizantes visuales
- 📊 Estado en tiempo real
- 📻 Frecuencias preestablecidas
- 🎨 Interfaz intuitiva

### 3. **Modo Consola (Sin GUI)**
```bash
python src/main.py --no-gui
```

**Comandos disponibles:**
```
v 75      # Volumen al 75%
g 30      # Ganancia a 30 dB
s 15      # Squelch al 15%
f 125.5   # Frecuencia 125.5 MHz
r         # Toggle grabación
q         # Salir
```

---

## 🔧 Componentes Simulados

### **Mock RTL-SDR** ([mock_sdr.py](../src/simulation/mock_sdr.py))
Simula el dongle RTL-SDR con:
- ✅ Señales IQ sintéticas (tono 440 Hz)
- ✅ Modulación AM realista
- ✅ Ruido gaussiano configurable
- ✅ Control de frecuencia y ganancia

**Parámetros:**
```python
signal_frequency = 1000  # Hz (portadora)
signal_amplitude = 0.3    # Amplitud base
noise_level = 0.05        # Nivel de ruido
```

### **Mock GPIO/SPI** ([mock_gpio.py](../src/simulation/mock_gpio.py))
Simula Raspberry Pi GPIO:
- ✅ Pines de entrada/salida
- ✅ Interrupciones y callbacks
- ✅ SPI para MCP3008 (ADC)
- ✅ Valores variables de potenciómetros

**Simulación de potenciómetros:**
```python
# Valores cambian con el tiempo para simular ajustes
Canal 0 (Volumen):  50-70% (varía cada 10s)
Canal 1 (Ganancia): 30-60% (varía cada 15s)
Canal 2 (Squelch):  10-15% (varía cada 5s)
```

### **Mock OLED** ([mock_display.py](../src/simulation/mock_display.py))
Simula pantalla OLED en consola:
- ✅ Representación ASCII art
- ✅ Actualización en tiempo real
- ✅ Compatible con PIL/Pillow

**Ejemplo de salida:**
```
┌────────────────────────────────────────────────┐
│                                                │
│     FlyM System                                │
│     125.0 MHz  Vol:75%  RSSI:-45dB             │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 🎮 Interfaz Gráfica de Control

### **Secciones de la GUI:**

#### 1. **Controles** 🎚️
- **Volumen:** 0-100% (deslizador)
- **Ganancia:** 0-50 dB (deslizador)
- **Squelch:** 0-100% (deslizador)

#### 2. **Frecuencia** 📻
- Campo de entrada manual
- Botones preestablecidos:
  - `118.0 MHz` - Torre de control
  - `121.5 MHz` - Emergencia
  - `125.0 MHz` - General
  - `1090 MHz` - ADS-B

#### 3. **Grabación** 🔴
- Botón ON/OFF
- Indicador de estado
- Archivos WAV en `recordings/`

#### 4. **Modo de Operación** 📡
- **VHF AM:** Comunicaciones de aviación
- **ADS-B:** Rastreo de aeronaves

#### 5. **Estado del Sistema** 📊
- **RSSI:** Nivel de señal (dBm)
- **Squelch:** Estado abierto/cerrado
- **Modo:** Modo actual activo

#### 6. **Acciones** 🔄
- **Resetear:** Volver a valores por defecto
- **Ayuda:** Guía rápida

---

## 🧪 Casos de Prueba

### **Prueba 1: Ajuste de Controles**
```python
# En GUI: Mover sliders
# En consola:
v 50    # Volumen medio
g 25    # Ganancia media
s 20    # Squelch bajo

# Verificar:
# - Display muestra valores actualizados
# - Audio controller recibe cambios
# - Sin errores en logs
```

### **Prueba 2: Cambio de Frecuencia**
```python
# En GUI: Botón "118.0 MHz (Torre)"
# En consola:
f 118.0

# Verificar:
# - SDR cambia frecuencia
# - Display actualiza valor
# - Log muestra confirmación
```

### **Prueba 3: Grabación**
```python
# En GUI: Click "Iniciar Grabación"
# En consola:
r

# Verificar:
# - LED simulado se enciende
# - Archivo WAV se crea en recordings/
# - Indicador de grabación activo

# Detener:
r  # Segunda vez

# Verificar:
# - Archivo WAV completo y reproducible
# - Tamaño > 0 bytes
```

### **Prueba 4: Modo ADS-B**
```python
# En GUI: Seleccionar "ADS-B (1090 MHz)"
# En consola:
# (usar GUI para este modo)

# Verificar:
# - Frecuencia cambia a 1090 MHz
# - Display muestra modo ADSB
# - Decoder ADS-B se activa
```

---

## 🐛 Troubleshooting

### **Error: "No module named 'tkinter'"**
```bash
# Windows
pip install tk

# Linux (Ubuntu/Debian)
sudo apt-get install python3-tk

# macOS
# Ya viene incluido con Python
```

### **Error: "Mock SDR no está abierto"**
**Solución:** ✅ Ya corregido en versión actual
- El mock ahora se abre automáticamente en `_initialize_sdr()`

### **GUI no se abre**
```bash
# Verificar instalación de tkinter
python -c "import tkinter; print('OK')"

# Si falla, usar modo consola
python src/main.py --no-gui
```

### **Display no se actualiza**
- Verificar que el thread de display esté corriendo
- Revisar logs: `tail -f flym.log`
- Asegurar que `update_display()` se llama cada 0.1s

---

## 📊 Comparación Modos

| Característica | Hardware Real | Simulador |
|----------------|---------------|-----------|
| **Señal RF** | RTL-SDR real | Señal sintética |
| **Audio** | PCM5102 DAC | sounddevice |
| **Display** | OLED I2C | ASCII consola |
| **Controles** | Pots + Botón | GUI / Comandos |
| **GPIO** | Raspberry Pi | Mock |
| **ADS-B** | 1090 MHz real | Datos simulados |
| **Desarrollo** | Solo en RPi | Windows/Mac/Linux |

---

## 🎓 Casos de Uso

### **1. Desarrollo de Nuevas Funciones**
```python
# Ejemplo: Añadir filtro de paso banda
def add_bandpass_filter(self, low_freq, high_freq):
    # Desarrollar en simulador
    # Probar con señales sintéticas
    # Verificar sin hardware
    pass
```

### **2. Testing Automatizado**
```bash
# scripts/test_simulator.py ya incluye tests
pytest tests/ --simulator-mode
```

### **3. Demos y Presentaciones**
- Mostrar funcionalidad sin hardware caro
- Presentaciones en laptops
- Capacitación de usuarios

### **4. Debug de Problemas**
```python
# Reproducir bug en simulador
# Añadir logs detallados
# Iterar rápidamente sin hardware
```

---

## 🔬 Personalización

### **Modificar Señal Simulada**
Editar `src/simulation/mock_sdr.py`:

```python
class MockRtlSdr:
    def __init__(self):
        # Cambiar parámetros
        self.signal_frequency = 2000  # 2 kHz en lugar de 1 kHz
        self.signal_amplitude = 0.5   # Más fuerte
        self.noise_level = 0.02       # Menos ruido
```

### **Añadir Frecuencias Preestablecidas**
Editar `src/simulation/gui_controller.py`:

```python
presets = [
    ("118.0 MHz (Torre)", 118.0),
    ("121.5 MHz (Emergencia)", 121.5),
    ("135.5 MHz (Mi frecuencia)", 135.5),  # ← Añadir aquí
    ("1090 MHz (ADS-B)", 1090.0)
]
```

### **Simular Fallas**
```python
# En mock_sdr.py, simular desconexión
def read_samples(self, num_samples):
    if random.random() < 0.01:  # 1% probabilidad
        raise RuntimeError("Simulación de falla")
    # ... código normal
```

---

## 📚 API del Simulador

### **SimulatorGUI**
```python
from simulation.gui_controller import get_gui_controller

# Obtener instancia
gui = get_gui_controller(callback=my_callback)

# Iniciar
gui.start()

# Actualizar estado externo
gui.update_state({'rssi': -45, 'squelch_open': True})

# Detener
gui.stop()
```

### **MockRtlSdr**
```python
from simulation.mock_sdr import MockRtlSdr

sdr = MockRtlSdr()
sdr.open()
sdr.set_center_freq(125_000_000)
samples = sdr.read_samples(1024)
sdr.close()
```

### **MockMCP3008**
```python
from simulation.mock_gpio import MockMCP3008

adc = MockMCP3008()
value = adc.read(channel=0)  # 0-1023
percent = adc.read_percent(channel=0)  # 0-100
adc.close()
```

---

## 🚀 Próximas Mejoras

- [ ] **Grabación de escenarios** (replay de señales)
- [ ] **Simulación de múltiples aviones** (ADS-B)
- [ ] **Gráficas de espectro** en tiempo real
- [ ] **Editor de configuración** en GUI
- [ ] **Modo headless** para CI/CD
- [ ] **API REST** para control remoto

---

## 📞 Soporte

**Problemas con el simulador:**
- 📧 Abrir issue en GitHub
- 📖 Consultar logs: `flym.log`
- 🔍 Ejecutar tests: `python scripts/test_simulator.py`

**Contribuir:**
```bash
git clone https://github.com/tu-usuario/FlyM.git
cd FlyM
# Hacer cambios en src/simulation/
python scripts/test_simulator.py  # Verificar
git commit -m "Mejora simulador: ..."
```

---

**🎉 ¡Disfruta del simulador FlyM!**

*Desarrolla sin límites, sin hardware real requerido.*
