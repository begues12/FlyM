#!/usr/bin/env python3
"""
Gestor de Controles Físicos
Maneja potenciómetros, botón de grabación y LED
"""

import time
import logging
from threading import Thread

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO no disponible. Usando modo simulación.")

try:
    import spidev
    SPI_AVAILABLE = True
except ImportError:
    spidev = None
    SPI_AVAILABLE = False
    logging.warning("spidev no disponible. Usando modo simulación.")

logger = logging.getLogger(__name__)


class ControlsManager:
    """Gestor de todos los controles físicos"""
    
    def __init__(self, config, callback):
        """
        Inicializar gestor de controles
        
        Args:
            config: Configuración de controles
            callback: Función de callback para cambios
        """
        self.config = config
        self.callback = callback
        
        # ADC para potenciómetros
        self.adc = None
        self.volume_channel = config.get('volume_pot_channel', 0)
        self.gain_channel = config.get('gain_pot_channel', 1)
        self.squelch_channel = config.get('squelch_pot_channel', 2)
        
        # Botón de grabación y LED
        self.record_button = config.get('record_button_pin', 22)
        self.record_led = config.get('record_led_pin', 23)
        
        # Cache de valores para evitar callbacks innecesarios
        self.last_volume = 0
        self.last_gain = 0
        self.last_squelch = 0
        
        self._initialize_gpio()
        self._initialize_adc()
    
    def _initialize_gpio(self):
        """Inicializar GPIO para botón y LED o simulador"""
        if not GPIO_AVAILABLE:
            # Modo simulación
            from simulation.mock_gpio import MockGPIO
            global GPIO
            GPIO = MockGPIO
            logger.info("🎭 Usando MockGPIO (modo simulación)")
        
        try:
            # Configurar GPIO (funciona igual en real y mock)
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Botón de grabación y LED
            GPIO.setup(self.record_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.record_led, GPIO.OUT)
            GPIO.output(self.record_led, GPIO.LOW)  # LED apagado inicialmente
            
            # Configurar interrupción del botón
            GPIO.add_event_detect(
                self.record_button,
                GPIO.FALLING,
                callback=self._record_button_callback,
                bouncetime=300
            )
            
            mode_text = "🎭 simulado" if not GPIO_AVAILABLE else "📡 real"
            logger.info(f"✅ GPIO {mode_text} inicializado")
            logger.info(f"   Botón grabación: GPIO{self.record_button}")
            logger.info(f"   LED: GPIO{self.record_led}")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar GPIO: {e}")
    
    def _initialize_adc(self):
        """Inicializar ADC MCP3008 para potenciómetros o simulador"""
        if not SPI_AVAILABLE:
            # Modo simulación
            from simulation.mock_gpio import MockMCP3008
            self.adc = MockMCP3008()
            logger.info("🎭 Usando MockMCP3008 (modo simulación)")
        else:
            try:
                self.adc = MCP3008()
                logger.info("📡 ADC MCP3008 real inicializado")
            except Exception as e:
                logger.error(f"❌ Error al inicializar ADC: {e}")
                return
        
        logger.info(f"✅ ADC configurado:")
        logger.info(f"   Volumen: Canal {self.volume_channel}")
        logger.info(f"   Ganancia: Canal {self.gain_channel}")
        logger.info(f"   Squelch: Canal {self.squelch_channel}")
    
    def _record_button_callback(self, channel):
        """Callback para botón de grabación"""
        try:
            logger.info("🔴 Botón de grabación presionado")
            if self.callback:
                self.callback('record_button', True)
        except Exception as e:
            logger.error(f"Error en callback de botón: {e}")
    
    def read_potentiometers(self):
        """Leer valores de los tres potenciómetros"""
        if self.adc is None:
            return None, None, None
        
        try:
            # Mapeo de canales a rangos (channel, max_value)
            pots = {
                'volume': (self.volume_channel, 100),
                'gain': (self.gain_channel, 50),
                'squelch': (self.squelch_channel, 100)
            }
            
            # Leer todos los valores
            values = {}
            for name, (channel, max_val) in pots.items():
                raw = self.adc.read(channel)
                values[name] = int((raw / 1023) * max_val)
            
            return values['volume'], values['gain'], values['squelch']
            
        except Exception as e:
            logger.error(f"Error al leer potenciómetros: {e}")
            return None, None, None
    
    def monitor_loop(self, shutdown_event):
        """Loop de monitoreo de potenciómetros"""
        logger.info("🎛️  Iniciando monitoreo de potenciómetros...")
        
        # Umbral de cambio para cada control
        thresholds = {'volume': 2, 'gain': 1, 'squelch': 2}
        last_values = {'volume': self.last_volume, 'gain': self.last_gain, 'squelch': self.last_squelch}
        
        while not shutdown_event.is_set():
            try:
                volume, gain, squelch = self.read_potentiometers()
                
                if all(v is not None for v in [volume, gain, squelch]):
                    current = {'volume': volume, 'gain': gain, 'squelch': squelch}
                    
                    # Verificar cambios significativos
                    for control, value in current.items():
                        if abs(value - last_values[control]) > thresholds[control]:
                            last_values[control] = value
                            if self.callback:
                                self.callback(control, value)
                
                time.sleep(0.1)  # Leer cada 100ms
                
            except Exception as e:
                logger.error(f"Error en monitor loop: {e}")
                time.sleep(1)
        
        logger.info("🛑 Monitor de potenciómetros detenido")
    
    def set_record_led(self, state):
        """Controlar LED de grabación"""
        if GPIO:
            try:
                GPIO.output(self.record_led, GPIO.HIGH if state else GPIO.LOW)
            except Exception as e:
                logger.error(f"Error al controlar LED: {e}")
    
    def blink_record_led(self):
        """Alternar estado del LED (para parpadeo)"""
        if GPIO:
            try:
                current = GPIO.input(self.record_led)
                GPIO.output(self.record_led, not current)
            except Exception as e:
                logger.error(f"Error al parpadear LED: {e}")
    
    def cleanup(self):
        """Limpiar recursos GPIO y SPI"""
        if GPIO:
            try:
                # Apagar LED antes de limpiar
                self.set_record_led(False)
                GPIO.cleanup()
                logger.info("✅ GPIO limpiado")
            except Exception as e:
                logger.error(f"Error al limpiar GPIO: {e}")
        
        if self.adc:
            try:
                self.adc.close()
                logger.info("✅ ADC cerrado")
            except Exception as e:
                logger.error(f"Error al cerrar ADC: {e}")


class MCP3008:
    """Interfaz para ADC MCP3008 via SPI"""
    
    # Constantes
    MAX_VALUE = 1023
    NUM_CHANNELS = 8
    DEFAULT_SPEED = 1350000  # 1.35 MHz
    
    def __init__(self, bus=0, device=0):
        """Inicializar MCP3008"""
        if spidev is None:
            raise ImportError("spidev es necesario para MCP3008")
        
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = self.DEFAULT_SPEED
        self.spi.mode = 0
    
    def read(self, channel):
        """Leer valor de un canal ADC (0-1023)"""
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Canal debe estar entre 0 y {self.NUM_CHANNELS-1}")
        
        # Comando SPI: start bit, single-ended, channel
        cmd = [1, (8 + channel) << 4, 0]
        result = self.spi.xfer2(cmd)
        
        # Extraer valor de 10 bits
        return ((result[1] & 3) << 8) + result[2]
    
    def read_voltage(self, channel, vref=3.3):
        """Leer voltaje de un canal (0-vref V)"""
        value = self.read(channel)
        return (value / self.MAX_VALUE) * vref
    
    def read_percent(self, channel):
        """Leer valor como porcentaje (0-100%)"""
        value = self.read(channel)
        return int((value / self.MAX_VALUE) * 100)
    
    def close(self):
        """Cerrar interfaz SPI"""
        if self.spi:
            self.spi.close()


# Simuladores para desarrollo removidos (no se necesita EncoderSimulator)


class KeyboardControls:
    """Controles por teclado para pruebas sin hardware"""
    
    def __init__(self, callback):
        """
        Inicializar controles por teclado
        
        Args:
            callback: Función de callback para cambios
        """
        self.callback = callback
        self.frequency = 125.0e6
        self.volume = 50
        self.gain = 30
        
        logger.info("⌨️  Controles por teclado activados:")
        logger.info("   [W/S] - Frecuencia")
        logger.info("   [A/D] - Volumen")
        logger.info("   [Q/E] - Ganancia")
        logger.info("   [M] - Cambiar modo")
    
    def process_key(self, key):
        """
        Procesar tecla presionada
        
        Args:
            key: Tecla presionada
        """
        key = key.lower()
        
        if key == 'w':
            # Aumentar frecuencia
            self.frequency += 25000
            self.callback('frequency', self.frequency)
        elif key == 's':
            # Disminuir frecuencia
            self.frequency -= 25000
            self.callback('frequency', self.frequency)
        elif key == 'a':
            # Disminuir volumen
            self.volume = max(0, self.volume - 5)
            self.callback('volume', self.volume)
        elif key == 'd':
            # Aumentar volumen
            self.volume = min(100, self.volume + 5)
            self.callback('volume', self.volume)
        elif key == 'q':
            # Disminuir ganancia
            self.gain = max(0, self.gain - 5)
            self.callback('gain', self.gain)
        elif key == 'e':
            # Aumentar ganancia
            self.gain = min(50, self.gain + 5)
            self.callback('gain', self.gain)
        elif key == 'm':
            # Cambiar modo
            self.callback('mode_button', True)
