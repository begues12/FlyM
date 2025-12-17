"""
Mock GPIO y SPI para simulación
Simula RPi.GPIO, spidev y MCP3008
"""

import logging
import time
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class MockGPIO:
    """Mock de RPi.GPIO"""
    
    # Constantes (compatibles con RPi.GPIO)
    BCM = 'BCM'
    BOARD = 'BOARD'
    IN = 'IN'
    OUT = 'OUT'
    HIGH = 1
    LOW = 0
    PUD_UP = 'PUD_UP'
    PUD_DOWN = 'PUD_DOWN'
    RISING = 'RISING'
    FALLING = 'FALLING'
    BOTH = 'BOTH'
    
    _mode = None
    _pins = {}
    _callbacks = {}
    
    @classmethod
    def setmode(cls, mode):
        """Establece modo de numeración"""
        cls._mode = mode
        logger.debug(f"🎭 GPIO mode: {mode}")
    
    @classmethod
    def setwarnings(cls, enabled: bool):
        """Habilita/deshabilita warnings"""
        pass
    
    @classmethod
    def setup(cls, pin, mode, pull_up_down=None):
        """Configura un pin"""
        cls._pins[pin] = {
            'mode': mode,
            'pull': pull_up_down,
            'value': 0 if mode == cls.OUT else 1
        }
        logger.debug(f"🎭 GPIO pin {pin} configurado como {mode}")
    
    @classmethod
    def output(cls, pin, value):
        """Establece valor de salida"""
        if pin in cls._pins:
            cls._pins[pin]['value'] = value
            logger.debug(f"🎭 GPIO pin {pin} = {value}")
    
    @classmethod
    def input(cls, pin) -> int:
        """Lee valor de entrada"""
        if pin in cls._pins:
            return cls._pins[pin]['value']
        return 1
    
    @classmethod
    def add_event_detect(cls, pin, edge, callback=None, bouncetime=None):
        """Añade detección de eventos"""
        cls._callbacks[pin] = callback
        logger.debug(f"🎭 Event detect añadido en pin {pin} ({edge})")
    
    @classmethod
    def remove_event_detect(cls, pin):
        """Elimina detección de eventos"""
        if pin in cls._callbacks:
            del cls._callbacks[pin]
    
    @classmethod
    def cleanup(cls):
        """Limpia configuración GPIO"""
        cls._pins.clear()
        cls._callbacks.clear()
        print("🎭 GPIO cleanup realizado")
    
    @classmethod
    def simulate_button_press(cls, pin: int):
        """Simula pulsación de botón (para testing)"""
        if pin in cls._callbacks and cls._callbacks[pin]:
            print(f"🎭 Simulando botón en pin {pin}")
            cls._callbacks[pin](pin)


class MockSpiDev:
    """Mock de spidev"""
    
    def __init__(self):
        self.bus = None
        self.device = None
        self.max_speed_hz = 1_000_000
        self.mode = 0
        logger.debug("🎭 MockSpiDev creado")
    
    def open(self, bus: int, device: int):
        """Abre conexión SPI"""
        self.bus = bus
        self.device = device
        print(f"🎭 SPI abierto: bus={bus}, device={device}")
    
    def close(self):
        """Cierra conexión SPI"""
        print("🎭 SPI cerrado")
    
    def xfer2(self, data: list) -> list:
        """
        Transfiere datos SPI
        Simula respuesta del MCP3008
        """
        # MCP3008: envía 3 bytes, recibe valor de 10 bits
        if len(data) == 3:
            # Extraer canal del comando
            channel = (data[1] >> 4) & 0x07
            
            # Generar valor simulado según canal
            values = self._get_simulated_values()
            raw_value = values.get(channel, 512)
            
            # Formato de respuesta MCP3008
            return [0, (raw_value >> 8) & 0x03, raw_value & 0xFF]
        
        return [0] * len(data)
    
    def _get_simulated_values(self) -> dict:
        """
        Genera valores simulados para cada canal
        Los valores se mantienen relativamente estables pero varían ligeramente
        para simular ruido del ADC real
        """
        t = time.time()
        
        # Valores base para cada potenciómetro
        # Canal 0: Volumen (50% = 512)
        # Canal 1: Ganancia (60% = 614)  
        # Canal 2: Squelch (20% = 205)
        
        base_values = {
            0: 512,   # Volumen medio (50%)
            1: 614,   # Ganancia media-alta (60%)
            2: 205,   # Squelch bajo (20%)
        }
        
        # Agregar ruido pequeño para simular variación del ADC
        import random
        noise = random.randint(-5, 5)
        
        return {
            channel: max(0, min(1023, value + noise))
            for channel, value in base_values.items()
        }


class MockMCP3008:
    """
    Mock del MCP3008 ADC
    Simula lectura de 8 canales analógicos
    """
    
    MAX_VALUE = 1023
    NUM_CHANNELS = 8
    
    def __init__(self, bus=0, device=0, max_speed_hz=1_350_000):
        self.spi = MockSpiDev()
        self.spi.max_speed_hz = max_speed_hz
        self.spi.open(bus, device)
        print("🎭 MockMCP3008 inicializado")
    
    def read(self, channel: int) -> int:
        """
        Lee valor de un canal (0-7)
        Retorna valor 0-1023 (10 bits)
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Canal debe estar entre 0 y {self.NUM_CHANNELS - 1}")
        
        # Comando MCP3008: start bit + single-ended + channel
        cmd = [1, (8 + channel) << 4, 0]
        
        # Transferencia SPI
        response = self.spi.xfer2(cmd)
        
        # Extraer valor de 10 bits
        value = ((response[1] & 3) << 8) + response[2]
        
        logger.debug(f"🎭 ADC canal {channel} = {value}")
        return value
    
    def read_percent(self, channel: int) -> int:
        """Lee canal como porcentaje (0-100)"""
        value = self.read(channel)
        return int((value / self.MAX_VALUE) * 100)
    
    def close(self):
        """Cierra conexión SPI"""
        self.spi.close()
        print("🎭 MockMCP3008 cerrado")


# Instancia global para simulación
mock_gpio = MockGPIO()
