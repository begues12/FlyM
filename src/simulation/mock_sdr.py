"""
Mock RTL-SDR para simulación
Genera señales sintéticas de radio AM
"""

import numpy as np
import logging
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class MockRtlSdr:
    """Mock del RTL-SDR que genera señales sintéticas"""
    
    def __init__(self):
        self.sample_rate = 2_048_000  # 2.048 MHz
        self.center_freq = 125_000_000  # 125 MHz
        self.gain = 20
        self.is_open = False
        self.is_streaming = False
        
        # Parámetros de simulación
        self.signal_frequency = 1000  # Tono de 1 kHz
        self.signal_amplitude = 0.3
        self.noise_level = 0.05
        self.time_offset = 0.0
        
        logger.info("🎭 MockRtlSdr inicializado (modo simulación)")
    
    def open(self):
        """Simula apertura del dispositivo"""
        self.is_open = True
        logger.info("🎭 Mock SDR abierto")
        return self
    
    def close(self):
        """Simula cierre del dispositivo"""
        if self.is_streaming:
            self.cancel_read_async()
        self.is_open = False
        logger.info("🎭 Mock SDR cerrado")
    
    def set_center_freq(self, freq: int):
        """Establece frecuencia central"""
        self.center_freq = freq
        logger.debug(f"🎭 Frecuencia simulada: {freq/1e6:.3f} MHz")
    
    def get_center_freq(self) -> int:
        """Obtiene frecuencia central"""
        return self.center_freq
    
    def set_sample_rate(self, rate: int):
        """Establece tasa de muestreo"""
        self.sample_rate = rate
        logger.debug(f"🎭 Sample rate simulado: {rate/1e6:.3f} MHz")
    
    def get_sample_rate(self) -> int:
        """Obtiene tasa de muestreo"""
        return self.sample_rate
    
    def set_gain(self, gain: int):
        """Establece ganancia"""
        self.gain = gain
        # Ajustar amplitud según ganancia
        self.signal_amplitude = 0.1 + (gain / 50.0) * 0.5
        logger.debug(f"🎭 Ganancia simulada: {gain} dB")
    
    def get_gain(self) -> int:
        """Obtiene ganancia"""
        return self.gain
    
    def read_samples(self, num_samples: int) -> np.ndarray:
        """
        Genera muestras IQ sintéticas
        Simula señal AM con tono + ruido
        """
        if not self.is_open:
            raise RuntimeError("Mock SDR no está abierto")
        
        # Generar eje de tiempo
        t = np.arange(num_samples) / self.sample_rate + self.time_offset
        self.time_offset += num_samples / self.sample_rate
        
        # Señal portadora (AM)
        carrier = np.exp(2j * np.pi * self.signal_frequency * t)
        
        # Modulación (tono de audio)
        audio_freq = 440  # La (A4)
        modulation = 1.0 + 0.5 * np.sin(2 * np.pi * audio_freq * t)
        
        # Señal AM
        signal = self.signal_amplitude * modulation * carrier
        
        # Ruido
        noise_i = np.random.normal(0, self.noise_level, num_samples)
        noise_q = np.random.normal(0, self.noise_level, num_samples)
        noise = noise_i + 1j * noise_q
        
        # Señal completa
        samples = signal + noise
        
        # Convertir a formato esperado (I/Q entrelazado)
        return samples.astype(np.complex64)
    
    def read_samples_async(self, callback: Callable, num_samples: int = 262144):
        """
        Lectura asíncrona simulada
        Llama al callback con bloques de datos
        """
        self.is_streaming = True
        self._async_callback = callback
        self._async_num_samples = num_samples
        logger.info(f"🎭 Streaming simulado iniciado ({num_samples} samples/bloque)")
    
    def cancel_read_async(self):
        """Cancela lectura asíncrona"""
        self.is_streaming = False
        self._async_callback = None
        logger.info("🎭 Streaming simulado detenido")
    
    def __enter__(self):
        """Context manager"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager"""
        self.close()
        return False


def get_mock_sdr():
    """Factory function para obtener instancia mock"""
    return MockRtlSdr()
