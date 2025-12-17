"""
VOX Controller - Voice Operated Transmit
Grabación automática basada en detección de actividad
"""

import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class VOXController:
    """Controlador de VOX para grabación automática"""
    
    def __init__(self, threshold: float = -60.0, delay: float = 2.0):
        """
        Inicializar VOX
        
        Args:
            threshold: Umbral de RSSI en dB para activar (-60 dB por defecto)
            delay: Tiempo en segundos para mantener grabación después de perder señal
        """
        self.threshold = threshold
        self.delay = delay
        self.enabled = False
        
        self.is_active = False
        self.last_activity_time = 0
        self.recording_active = False
        
        self.on_vox_start: Optional[Callable] = None
        self.on_vox_stop: Optional[Callable] = None
        
        print(f"🎙️  VOX inicializado (umbral: {threshold} dB, delay: {delay}s)")
    
    def set_enabled(self, enabled: bool):
        """Activar/desactivar VOX"""
        self.enabled = enabled
        if enabled:
            print("🎙️  VOX ACTIVADO")
        else:
            print("⏸️  VOX DESACTIVADO")
            if self.recording_active:
                self._stop_recording()
    
    def set_threshold(self, threshold: float):
        """Establecer umbral de activación"""
        self.threshold = threshold
        print(f"🎚️  VOX threshold: {threshold} dB")
    
    def set_delay(self, delay: float):
        """Establecer tiempo de delay"""
        self.delay = delay
        print(f"⏱️  VOX delay: {delay}s")
    
    def update(self, rssi: float, current_time: float) -> bool:
        """
        Actualizar estado VOX
        
        Args:
            rssi: Nivel de señal actual en dB
            current_time: Tiempo actual en segundos
            
        Returns:
            True si debe estar grabando
        """
        if not self.enabled:
            return False
        
        # Detectar actividad
        activity_detected = rssi > self.threshold
        
        if activity_detected:
            self.last_activity_time = current_time
            
            # Iniciar grabación si no está activa
            if not self.recording_active:
                self._start_recording()
                return True
        
        # Verificar timeout para detener grabación
        if self.recording_active:
            time_since_activity = current_time - self.last_activity_time
            
            if time_since_activity > self.delay:
                self._stop_recording()
                return False
            else:
                return True  # Seguir grabando durante delay
        
        return False
    
    def _start_recording(self):
        """Iniciar grabación VOX"""
        self.recording_active = True
        self.is_active = True
        
        if self.on_vox_start:
            self.on_vox_start()
        
        print("🔴 VOX: Grabación iniciada")
    
    def _stop_recording(self):
        """Detener grabación VOX"""
        self.recording_active = False
        self.is_active = False
        
        if self.on_vox_stop:
            self.on_vox_stop()
        
        print("⏹️  VOX: Grabación detenida")
    
    def force_stop(self):
        """Forzar detención de grabación"""
        if self.recording_active:
            self._stop_recording()
    
    def get_status(self) -> dict:
        """Obtener estado actual del VOX"""
        return {
            'enabled': self.enabled,
            'threshold': self.threshold,
            'delay': self.delay,
            'is_active': self.is_active,
            'recording': self.recording_active
        }
