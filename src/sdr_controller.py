#!/usr/bin/env python3
"""
Controlador para RTL-SDR
Maneja la recepción de señales RF, demodulación AM y control del dispositivo
"""

import numpy as np
from scipy import signal
import logging
from typing import Optional

try:
    from rtlsdr import RtlSdr
    SIMULATION_MODE = False
except ImportError:
    RtlSdr = None
    SIMULATION_MODE = True
    logging.warning("pyrtlsdr no está instalado. Usando modo simulación.")

logger = logging.getLogger(__name__)


class SDRController:
    """Controlador del dispositivo RTL-SDR"""
    
    # Constantes
    MIN_GAIN = 0
    MAX_GAIN = 50
    DEFAULT_FILTER_TAPS = 101
    AVIATION_BANDWIDTH = 10_000  # 10 kHz
    
    def __init__(self, config):
        """
        Inicializar el controlador SDR
        
        Args:
            config: Diccionario con configuración del SDR
        """
        self.config = config
        self.sdr = None
        self.sample_rate = config.get('sample_rate', 2.048e6)
        self.center_freq = config.get('default_frequency', 125.0e6)
        self.gain = config.get('default_gain', 30)
        self.buffer_size = config.get('buffer_size', 256 * 1024)
        
        # Filtros y procesamiento
        self.audio_rate = config.get('audio_rate', 48000)
        self.decimation = int(self.sample_rate / self.audio_rate)
        
        # Buffer para procesamiento
        self.last_samples = None
        
        self._initialize_sdr()
        self._setup_filters()
    
    def _initialize_sdr(self):
        """Inicializar dispositivo RTL-SDR o simulador"""
        if SIMULATION_MODE:
            # Modo simulación
            from simulation.mock_sdr import MockRtlSdr
            self.sdr = MockRtlSdr()
            self.sdr.open()  # ✅ Abrir el mock SDR
            logger.info("🎭 Usando MockRtlSdr (modo simulación)")
        else:
            # Modo real
            if RtlSdr is None:
                logger.error("❌ pyrtlsdr no disponible")
                raise ImportError("pyrtlsdr es necesario para el funcionamiento del SDR")
            
            try:
                self.sdr = RtlSdr()
                logger.info("📡 RTL-SDR real inicializado")
            except Exception as e:
                logger.error(f"❌ Error al inicializar RTL-SDR: {e}")
                raise
        
        # Configurar parámetros (funciona igual en real y mock)
        self.sdr.sample_rate = self.sample_rate
        self.sdr.center_freq = self.center_freq
        self.sdr.gain = self.gain
        
        logger.info(f"✅ SDR configurado:")
        logger.info(f"   Sample Rate: {self.sample_rate/1e6:.3f} MHz")
        logger.info(f"   Center Freq: {self.center_freq/1e6:.3f} MHz")
        logger.info(f"   Gain: {self.gain} dB")
    
    def _setup_filters(self):
        """Configurar filtros para procesamiento de señal"""
        # Filtro paso-bajo para demodulación AM
        # Ancho de banda de canal de aviación: ~8.33 kHz o 25 kHz
        nyquist = self.sample_rate / 2
        normalized_cutoff = self.AVIATION_BANDWIDTH / nyquist
        
        # Diseñar filtro FIR Hamming
        self.lpf_taps = signal.firwin(
            numtaps=self.DEFAULT_FILTER_TAPS,
            cutoff=normalized_cutoff,
            window='hamming'
        )
        
        logger.info(f"📊 Filtro paso-bajo: {self.AVIATION_BANDWIDTH/1000} kHz")
    
    def read_samples(self, num_samples=None):
        """
        Leer muestras del SDR
        
        Args:
            num_samples: Número de muestras a leer (default: buffer_size)
            
        Returns:
            Array de muestras complejas
        """
        if num_samples is None:
            num_samples = self.buffer_size
        
        try:
            samples = self.sdr.read_samples(num_samples)
            self.last_samples = samples
            return samples
        except Exception as e:
            logger.error(f"Error al leer muestras del SDR: {e}")
            return None
    
    def demodulate_am(self, samples):
        """
        Demodular señal AM (Amplitude Modulation)
        
        Args:
            samples: Array de muestras IQ complejas
            
        Returns:
            Array de audio demodulado
        """
        if samples is None or len(samples) == 0:
            return np.array([])
        
        # 1. Calcular magnitud (envelope detection)
        magnitude = np.abs(samples)
        
        # 2. Eliminar DC offset
        magnitude = magnitude - np.mean(magnitude)
        
        # 3. Aplicar filtro paso-bajo
        filtered = signal.lfilter(self.lpf_taps, 1.0, magnitude)
        
        # 4. Decimación para reducir a tasa de audio
        audio = signal.decimate(filtered, self.decimation, zero_phase=True)
        
        # 5. Normalizar
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio))
        
        # 6. Aplicar AGC suave (Automatic Gain Control)
        audio = self._apply_agc(audio)
        
        return audio
    
    def _apply_agc(self, audio, target_level=0.5):
        """
        Aplicar control automático de ganancia
        
        Args:
            audio: Señal de audio
            target_level: Nivel objetivo (0-1)
            
        Returns:
            Audio con AGC aplicado
        """
        # Calcular RMS
        rms = np.sqrt(np.mean(audio**2))
        
        if rms > 0:
            gain = target_level / rms
            # Limitar ganancia para evitar sobre-amplificación
            gain = min(gain, 10.0)
            audio = audio * gain
        
        # Clip para evitar saturación
        audio = np.clip(audio, -1.0, 1.0)
        
        return audio
    
    def get_rssi(self, samples=None):
        """
        Calcular RSSI (Received Signal Strength Indicator)
        
        Args:
            samples: Muestras IQ (usa last_samples si es None)
            
        Returns:
            RSSI en dB (normalizado 0-100)
        """
        if samples is None:
            samples = self.last_samples
        
        if samples is None or len(samples) == 0:
            return 0
        
        # Calcular potencia
        power = np.mean(np.abs(samples)**2)
        
        # Convertir a dB
        if power > 0:
            power_db = 10 * np.log10(power)
        else:
            power_db = -100
        
        # Normalizar a escala 0-100
        # Asumiendo rango de -80 dB a -20 dB
        rssi = (power_db + 80) * (100 / 60)
        rssi = max(0, min(100, rssi))
        
        return int(rssi)
    
    def set_frequency(self, freq):
        """
        Cambiar frecuencia de sintonización
        
        Args:
            freq: Frecuencia en Hz
        """
        try:
            self.sdr.center_freq = freq
            self.center_freq = freq
            logger.info(f"📻 Frecuencia ajustada a {freq/1e6:.3f} MHz")
        except Exception as e:
            logger.error(f"Error al cambiar frecuencia: {e}")
    
    def set_gain(self, gain):
        """
        Ajustar ganancia del SDR
        
        Args:
            gain: Ganancia en dB (0-50)
        """
        try:
            # Limitar rango
            gain = max(0, min(50, gain))
            
            # Usar modo manual
            self.sdr.gain = gain
            self.gain = gain
            logger.debug(f"📶 Ganancia ajustada a {gain} dB")
        except Exception as e:
            logger.error(f"Error al ajustar ganancia: {e}")
    
    def set_automatic_gain(self, enabled=True):
        """
        Habilitar/deshabilitar ganancia automática
        
        Args:
            enabled: True para AGC automático
        """
        try:
            if enabled:
                self.sdr.gain = 'auto'
                logger.info("🔄 AGC automático activado")
            else:
                self.sdr.gain = self.gain
                logger.info("🔧 Ganancia manual activada")
        except Exception as e:
            logger.error(f"Error al configurar AGC: {e}")
    
    def get_valid_gains(self):
        """
        Obtener lista de ganancias válidas para el dispositivo
        
        Returns:
            Lista de ganancias en dB
        """
        try:
            return self.sdr.valid_gains_db
        except:
            return list(range(0, 50, 3))
    
    def tune_to_airband(self, channel=None):
        """
        Sintonizar a frecuencia de aviación
        
        Args:
            channel: Frecuencia específica en MHz, o None para default
        """
        if channel is None:
            # Frecuencia común de torre de control
            channel = 125.7
        
        # Las frecuencias de aviación están en el rango 118-137 MHz
        if 118 <= channel <= 137:
            freq = channel * 1e6
            self.set_frequency(freq)
        else:
            logger.warning(f"⚠️  Frecuencia {channel} MHz fuera del rango de aviación (118-137 MHz)")
    
    def tune_to_adsb(self):
        """Sintonizar a frecuencia ADS-B (1090 MHz)"""
        self.set_frequency(1090e6)
        logger.info("✈️  Sintonizado a ADS-B (1090 MHz)")
    
    def close(self):
        """Cerrar y limpiar el dispositivo SDR"""
        if self.sdr:
            try:
                self.sdr.close()
                logger.info("✅ RTL-SDR cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar SDR: {e}")


# Frecuencias comunes de aviación
AIRBAND_FREQUENCIES = {
    'tower': [118.1, 118.3, 118.7, 119.1, 119.3, 119.7, 120.9, 121.7, 121.9],
    'approach': [119.0, 119.2, 119.5, 120.4, 125.0, 125.2, 125.8, 127.0],
    'departure': [118.2, 120.5, 121.2, 124.2, 126.2],
    'ground': [121.6, 121.7, 121.8, 121.9],
    'emergency': [121.5],  # Frecuencia internacional de emergencia
    'atis': [126.0, 127.0, 128.0]  # Información aeroportuaria
}


def get_frequency_info(freq_mhz):
    """
    Obtener información sobre una frecuencia
    
    Args:
        freq_mhz: Frecuencia en MHz
        
    Returns:
        String con tipo de frecuencia
    """
    for freq_type, frequencies in AIRBAND_FREQUENCIES.items():
        if freq_mhz in frequencies:
            return freq_type.upper()
    
    if 118.0 <= freq_mhz <= 137.0:
        return "AIRBAND"
    elif freq_mhz == 1090.0:
        return "ADS-B"
    else:
        return "UNKNOWN"
