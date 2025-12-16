#!/usr/bin/env python3
"""
Controlador de Audio para PCM5102 DAC
Maneja la reproducción de audio a través del DAC I²S y grabación
"""

import numpy as np
import logging
import wave
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    sd = None
    AUDIO_AVAILABLE = False
    logging.warning("sounddevice no está instalado. Usando modo simulación audio.")

logger = logging.getLogger(__name__)


class AudioController:
    """Controlador para reproducción de audio a través de PCM5102 DAC"""
    
    # Constantes
    MIN_VOLUME = 0
    MAX_VOLUME = 100
    DEFAULT_SQUELCH_THRESHOLD = 0.01
    RECORDING_SAMPLE_WIDTH = 2  # 16-bit
    BUFFER_MULTIPLIER = 10
    
    def __init__(self, config):
        """Inicializar controlador de audio"""
        self.config = config
        self.simulation_mode = not AUDIO_AVAILABLE
        
        # Parámetros de audio
        self.sample_rate = config.get('sample_rate', 48000)
        self.channels = config.get('channels', 1)
        self.dtype = config.get('dtype', 'float32')
        self.device_name = config.get('device', None)
        self.buffer_size = config.get('buffer_size', 2048)
        
        # Control de volumen
        volume_pct = config.get('default_volume', 50)
        self.volume = np.clip(volume_pct / 100.0, 0.0, 1.0)
        self.muted = False
        
        # Buffer de audio
        max_buffer = self.buffer_size * self.BUFFER_MULTIPLIER
        self.audio_buffer = deque(maxlen=max_buffer)
        
        # Squelch
        self.enable_squelch = config.get('squelch', True)
        self.squelch_threshold = config.get('squelch_threshold', self.DEFAULT_SQUELCH_THRESHOLD)
        self.squelch_open = False
        
        # Grabación
        self.recording = False
        self.recording_buffer = []
        self.recordings_path = Path(config.get('recordings_path', '/home/pi/flym/recordings'))
        self.recording_format = config.get('recording_format', 'wav')
        self.current_recording_file = None
        
        # Stream
        self.stream = None
        
        if not self.simulation_mode:
            self._initialize_audio()
        else:
            logger.info("🎵 AudioController en modo simulación (sin sounddevice)")
    
    def _initialize_audio(self):
        """Inicializar sistema de audio"""
        if sd is None:
            logger.warning("⚠️ sounddevice no disponible, usando modo simulación")
            return
        
        try:
            # Listar dispositivos disponibles
            devices = sd.query_devices()
            logger.info(f"🔊 Dispositivos de audio disponibles:")
            for i, dev in enumerate(devices):
                logger.info(f"   [{i}] {dev['name']}")
            
            # Seleccionar dispositivo
            device_id = self._select_device()
            
            # Configurar stream de salida
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                device=device_id,
                callback=self._audio_callback,
                blocksize=self.buffer_size
            )
            
            logger.info(f"✅ Audio inicializado:")
            logger.info(f"   Sample Rate: {self.sample_rate} Hz")
            logger.info(f"   Channels: {self.channels}")
            logger.info(f"   Device: {device_id}")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar audio: {e}")
            raise
    
    def _select_device(self):
        """
        Seleccionar dispositivo de audio
        
        Returns:
            ID del dispositivo o None para default
        """
        if self.device_name:
            # Buscar dispositivo por nombre
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if self.device_name.lower() in dev['name'].lower():
                    logger.info(f"📻 Dispositivo seleccionado: {dev['name']}")
                    return i
            
            logger.warning(f"⚠️  Dispositivo '{self.device_name}' no encontrado, usando default")
        
        # Usar dispositivo por defecto
        default_device = sd.query_devices(kind='output')
        logger.info(f"📻 Usando dispositivo default: {default_device['name']}")
        return None
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Callback para el stream de audio
        
        Args:
            outdata: Buffer de salida
            frames: Número de frames
            time_info: Información de tiempo
            status: Estado del stream
        """
        if status:
            logger.warning(f"⚠️  Audio callback status: {status}")
        
        # Obtener datos del buffer
        if len(self.audio_buffer) >= frames:
            # Extraer frames del buffer
            data = np.array([self.audio_buffer.popleft() for _ in range(frames)])
        else:
            # No hay suficientes datos, generar silencio
            data = np.zeros(frames)
        
        # Aplicar volumen
        data = data * self.volume
        
        # Mute si está activado
        if self.muted:
            data = np.zeros_like(data)
        
        # Si está grabando, guardar en buffer
        if self.recording:
            self.recording_buffer.append(data.copy())
        
        # Escribir a salida
        if self.channels == 1:
            outdata[:, 0] = data
        else:
            # Duplicar para estéreo
            outdata[:, 0] = data
            outdata[:, 1] = data
    
    def play_audio(self, audio_data):
        """
        Reproducir datos de audio
        
        Args:
            audio_data: Array numpy con datos de audio
        """
        if audio_data is None or len(audio_data) == 0:
            return
        
        # Aplicar squelch (silenciar ruido de fondo)
        if self.enable_squelch:
            audio_data = self._apply_squelch(audio_data)
        
        # Agregar al buffer
        for sample in audio_data:
            self.audio_buffer.append(sample)
    
    def _apply_squelch(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Aplicar squelch (silenciar cuando señal es débil)
        
        Args:
            audio_data: Datos de audio
            
        Returns:
            Audio con squelch aplicado
        """
        # Calcular nivel RMS de la señal
        rms = np.sqrt(np.mean(audio_data**2))
        
        # Actualizar estado del squelch
        self.squelch_open = rms >= self.squelch_threshold
        
        # Silenciar si está por debajo del umbral
        if not self.squelch_open:
            return np.zeros_like(audio_data)
        
        return audio_data
    
    def set_volume(self, volume_percent: int):
        """
        Ajustar volumen
        
        Args:
            volume_percent: Volumen en porcentaje (0-100)
        """
        volume_percent = np.clip(volume_percent, self.MIN_VOLUME, self.MAX_VOLUME)
        self.volume = volume_percent / 100.0
        logger.debug(f"🔊 Volumen: {volume_percent}% ({self.volume:.2f})")
    
    def get_volume(self):
        """
        Obtener volumen actual
        
        Returns:
            Volumen en porcentaje (0-100)
        """
        return int(self.volume * 100)
    
    def mute(self):
        """Silenciar audio"""
        self.muted = True
        logger.info("🔇 Audio silenciado")
    
    def unmute(self):
        """Activar audio"""
        self.muted = False
        logger.info("🔊 Audio activado")
    
    def toggle_mute(self):
        """Alternar mute"""
        if self.muted:
            self.unmute()
        else:
            self.mute()
    
    def set_squelch(self, enabled, threshold=None):
        """
        Configurar squelch
        
        Args:
            enabled: Habilitar/deshabilitar squelch
            threshold: Umbral de squelch (0.0-1.0)
        """
        self.enable_squelch = enabled
        if threshold is not None:
            self.squelch_threshold = threshold
        
        status = "activado" if enabled else "desactivado"
        logger.info(f"🔇 Squelch {status} (umbral: {self.squelch_threshold:.3f})")
    
    def set_squelch_threshold(self, threshold_percent: int):
        """
        Ajustar umbral de squelch
        
        Args:
            threshold_percent: Umbral en porcentaje (0-100)
        """
        # Convertir porcentaje a valor 0.0-1.0
        threshold = threshold_percent / 100.0
        self.squelch_threshold = np.clip(threshold, 0.0, 1.0)
        logger.debug(f"🔇 Squelch threshold: {threshold_percent}% ({self.squelch_threshold:.3f})")
    
    def is_squelch_open(self) -> bool:
        """
        Verificar si el squelch está abierto (señal fuerte)
        
        Returns:
            True si squelch está abierto (hay señal), False si está cerrado (ruido)
        """
        return self.squelch_open
    
    def start_recording(self):
        """Iniciar grabación"""
        import os
        from datetime import datetime
        
        if not self.recording:
            self.recording = True
            self.recording_buffer = []
            
            # Crear directorio si no existe
            os.makedirs(self.recordings_path, exist_ok=True)
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.current_recording_file = os.path.join(
                self.recordings_path, 
                f'flym_recording_{timestamp}.{self.recording_format}'
            )
            
            logger.info(f"🔴 Grabación iniciada: {self.current_recording_file}")
    
    def stop_recording(self):
        """Detener grabación y guardar archivo"""
        if self.recording:
            self.recording = False
            
            if len(self.recording_buffer) > 0:
                self._save_recording()
                logger.info(f"⏹️  Grabación guardada: {self.current_recording_file}")
            else:
                logger.warning("⚠️  No hay datos para grabar")
            
            self.recording_buffer = []
    
    def is_recording(self):
        """Verificar si está grabando"""
        return self.recording
    
    def _save_recording(self):
        """Guardar buffer de grabación a archivo WAV"""
        try:
            import wave
            
            # Concatenar todo el buffer
            audio_data = np.concatenate(self.recording_buffer)
            
            # Convertir float32 a int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Guardar como WAV
            with wave.open(self.current_recording_file, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16 bits = 2 bytes
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            
            logger.info(f"💾 Archivo guardado: {len(audio_data)} muestras")
            
        except Exception as e:
            logger.error(f"Error al guardar grabación: {e}")
    
    def start(self):
        """Iniciar stream de audio"""
        if self.simulation_mode:
            logger.info("▶️  Stream de audio iniciado (simulación)")
            return
        
        if self.stream and not self.stream.active:
            self.stream.start()
            logger.info("▶️  Stream de audio iniciado")
    
    def stop(self):
        """Detener stream de audio"""
        if self.simulation_mode:
            logger.info("⏹️  Stream de audio detenido (simulación)")
            return
        
        if self.stream and self.stream.active:
            self.stream.stop()
            logger.info("⏹️  Stream de audio detenido")
    
    def close(self):
        """Cerrar y limpiar recursos de audio"""
        # Si está grabando, detener y guardar
        if self.recording:
            self.stop_recording()
        
        if self.simulation_mode:
            logger.info("✅ Sistema de audio cerrado (simulación)")
            return
        
        if self.stream:
            try:
                if self.stream.active:
                    self.stream.stop()
                self.stream.close()
                logger.info("✅ Sistema de audio cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar audio: {e}")
    
    def get_buffer_status(self):
        """
        Obtener estado del buffer de audio
        
        Returns:
            Diccionario con información del buffer
        """
        buffer_fill = len(self.audio_buffer) / self.audio_buffer.maxlen * 100
        
        return {
            'size': len(self.audio_buffer),
            'capacity': self.audio_buffer.maxlen,
            'fill_percent': buffer_fill,
            'underrun': buffer_fill < 10  # Warning si está casi vacío
        }


class AudioProcessor:
    """Procesador adicional de audio para efectos y filtros"""
    
    def __init__(self, sample_rate=48000):
        """
        Inicializar procesador
        
        Args:
            sample_rate: Tasa de muestreo en Hz
        """
        self.sample_rate = sample_rate
    
    def apply_deemphasis(self, audio, tau=75e-6):
        """
        Aplicar filtro de de-énfasis (común en FM)
        
        Args:
            audio: Señal de audio
            tau: Constante de tiempo (75µs para USA, 50µs para Europa)
            
        Returns:
            Audio con de-énfasis aplicado
        """
        # Calcular coeficiente del filtro
        dt = 1.0 / self.sample_rate
        alpha = dt / (tau + dt)
        
        # Aplicar filtro IIR de primer orden
        output = np.zeros_like(audio)
        output[0] = audio[0]
        
        for i in range(1, len(audio)):
            output[i] = output[i-1] + alpha * (audio[i] - output[i-1])
        
        return output
    
    def apply_highpass(self, audio, cutoff=300):
        """
        Aplicar filtro paso-alto para eliminar componentes DC
        
        Args:
            audio: Señal de audio
            cutoff: Frecuencia de corte en Hz
            
        Returns:
            Audio filtrado
        """
        from scipy import signal as sp_signal
        
        # Diseñar filtro Butterworth
        nyquist = self.sample_rate / 2
        normal_cutoff = cutoff / nyquist
        b, a = sp_signal.butter(2, normal_cutoff, btype='high')
        
        # Aplicar filtro
        filtered = sp_signal.filtfilt(b, a, audio)
        
        return filtered
    
    def apply_noise_reduction(self, audio, noise_threshold=0.02):
        """
        Reducción básica de ruido mediante gating
        
        Args:
            audio: Señal de audio
            noise_threshold: Umbral de ruido
            
        Returns:
            Audio con reducción de ruido
        """
        # Calcular envolvente
        envelope = np.abs(audio)
        
        # Crear gate
        gate = envelope > noise_threshold
        
        # Aplicar con suavizado para evitar clicks
        smoothed_gate = np.convolve(gate.astype(float), 
                                     np.ones(100)/100, 
                                     mode='same')
        
        # Aplicar gate al audio
        return audio * smoothed_gate
