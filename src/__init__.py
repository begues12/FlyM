"""
FlyM Aviation Receiver
Sistema de recepción de comunicaciones de aviación y ADS-B

Módulos disponibles:
- main: Programa principal
- sdr_controller: Control del RTL-SDR
- audio_controller: Gestión de audio
- display_controller: Control de pantallas OLED
- controls: Controles físicos (potenciómetros, botón, LED)
- adsb_decoder: Decodificador ADS-B
- config_loader: Carga de configuración
"""

__version__ = "1.0.0"
__author__ = "FlyM Project"
__license__ = "MIT"

# Imports principales para facilitar uso
from .sdr_controller import SDRController
from .audio_controller import AudioController
from .display_controller import DisplayController
from .controls import ControlsManager
from .adsb_decoder import ADSBDecoder
from .config_loader import load_config

__all__ = [
    'SDRController',
    'AudioController',
    'DisplayController',
    'ControlsManager',
    'ADSBDecoder',
    'load_config'
]
