#!/usr/bin/env python3
"""
Cargador de configuración con validación y valores por defecto
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Constantes de configuración
class ConfigDefaults:
    """Valores por defecto de configuración"""
    
    # SDR
    SDR_SAMPLE_RATE = 2_048_000
    SDR_DEFAULT_FREQ = 125_000_000
    SDR_DEFAULT_GAIN = 30
    SDR_BUFFER_SIZE = 262_144
    SDR_AUDIO_RATE = 48_000
    
    # Audio
    AUDIO_SAMPLE_RATE = 48_000
    AUDIO_CHANNELS = 1
    AUDIO_DTYPE = 'float32'
    AUDIO_VOLUME = 50
    AUDIO_BUFFER_SIZE = 2048
    AUDIO_SQUELCH_THRESHOLD = 0.01
    
    # Display
    DISPLAY_ADDRESS = 0x3C
    DISPLAY_I2C_PORT = 1
    DISPLAY_VIEW_TIMEOUT = 3
    
    # Controls
    POT_VOLUME_CHANNEL = 0
    POT_GAIN_CHANNEL = 1
    POT_SQUELCH_CHANNEL = 2
    BUTTON_RECORD_PIN = 22
    LED_RECORD_PIN = 23
    
    # ADS-B
    ADSB_THRESHOLD = 0.5
    ADSB_TIMEOUT = 60


def load_config(config_path: str = 'config/config.yaml') -> Dict[str, Any]:
    """
    Cargar configuración desde archivo YAML con fallback a valores por defecto
    
    Args:
        config_path: Ruta al archivo de configuración
        
    Returns:
        Diccionario con configuración validada
    """
    config_file = Path(config_path)
    
    # Si no existe, usar defaults
    if not config_file.exists():
        logger.warning(f"⚠️  Archivo no encontrado: {config_path}")
        print("📋 Usando configuración por defecto")
        return get_default_config()
    
    # Cargar y validar
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Validar estructura
        config = _validate_config(config)
        
        print(f"✅ Configuración cargada: {config_path}")
        return config
        
    except yaml.YAMLError as e:
        logger.error(f"❌ Error YAML: {e}")
    except Exception as e:
        logger.error(f"❌ Error al cargar configuración: {e}")
    
    print("📋 Usando configuración por defecto")
    return get_default_config()


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validar y completar configuración con valores por defecto
    
    Args:
        config: Configuración cargada del archivo
        
    Returns:
        Configuración validada y completada
    """
    defaults = get_default_config()
    
    # Fusionar con defaults (prioridad a config cargada)
    for section, values in defaults.items():
        if section not in config:
            config[section] = values
        else:
            for key, default_value in values.items():
                if key not in config[section]:
                    config[section][key] = default_value
    
    return config


def get_default_config() -> Dict[str, Any]:
    """
    Obtener configuración por defecto desde constantes
    
    Returns:
        Diccionario con configuración por defecto
    """
    D = ConfigDefaults
    
    return {
        'sdr': {
            'sample_rate': D.SDR_SAMPLE_RATE,
            'default_frequency': D.SDR_DEFAULT_FREQ,
            'default_gain': D.SDR_DEFAULT_GAIN,
            'buffer_size': D.SDR_BUFFER_SIZE,
            'audio_rate': D.SDR_AUDIO_RATE
        },
        'audio': {
            'sample_rate': D.AUDIO_SAMPLE_RATE,
            'channels': D.AUDIO_CHANNELS,
            'dtype': D.AUDIO_DTYPE,
            'device': None,
            'default_volume': D.AUDIO_VOLUME,
            'buffer_size': D.AUDIO_BUFFER_SIZE,
            'squelch': True,
            'squelch_threshold': D.AUDIO_SQUELCH_THRESHOLD,
            'recordings_path': '/home/pi/flym/recordings',
            'recording_format': 'wav'
        },
        'display': {
            'display_address': D.DISPLAY_ADDRESS,
            'i2c_port': D.DISPLAY_I2C_PORT,
            'view_timeout': D.DISPLAY_VIEW_TIMEOUT
        },
        'controls': {
            'volume_pot_channel': D.POT_VOLUME_CHANNEL,
            'gain_pot_channel': D.POT_GAIN_CHANNEL,
            'squelch_pot_channel': D.POT_SQUELCH_CHANNEL,
            'record_button_pin': D.BUTTON_RECORD_PIN,
            'record_led_pin': D.LED_RECORD_PIN
        },
        'adsb': {
            'threshold': D.ADSB_THRESHOLD,
            'aircraft_timeout': D.ADSB_TIMEOUT
        }
    }


def save_config(config: Dict[str, Any], config_path: str = 'config/config.yaml') -> bool:
    """
    Guardar configuración a archivo YAML
    
    Args:
        config: Diccionario con configuración
        config_path: Ruta donde guardar
        
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                config, 
                f, 
                default_flow_style=False, 
                allow_unicode=True,
                sort_keys=False
            )
        
        print(f"✅ Configuración guardada: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al guardar configuración: {e}")
        return False
