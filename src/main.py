#!/usr/bin/env python3
"""
FlyM - Sistema de Recepción de Aviación + ADS-B
Orquestador principal del sistema
"""

import sys
import time
import signal
import logging
from threading import Thread, Event
from pathlib import Path

# Importar módulos del proyecto
from sdr_controller import SDRController
from audio_controller import AudioController
from display_controller import DisplayController
from controls import ControlsManager
from adsb_decoder import ADSBDecoder
from config_loader import load_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flym.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FlyMSystem:
    """Sistema principal de recepción de aviación"""
    
    def __init__(self, config_path='config/config.yaml'):
        """Inicializar el sistema"""
        logger.info("🚀 Iniciando FlyM Aviation Receiver...")
        
        # Cargar configuración
        self.config = load_config(config_path)
        
        # Event para control de shutdown
        self.shutdown_event = Event()
        
        # Inicializar componentes
        self.sdr = None
        self.audio = None
        self.display = None
        self.controls = None
        self.adsb = None
        
        # Estado del sistema
        self.state = {
            'frequency': self.config['sdr']['default_frequency'],
            'mode': 'VHF_AM',  # VHF_AM o ADSB
            'volume': 50,
            'gain': 30,
            'rssi': 0,
            'aircraft_data': []
        }
        
        # Hilos de procesamiento
        self.threads = []
        
    def initialize_components(self):
        """Inicializar todos los componentes del sistema"""
        try:
            # SDR Controller
            logger.info("📻 Inicializando RTL-SDR...")
            self.sdr = SDRController(self.config['sdr'])
            
            # Audio Controller
            logger.info("🔊 Inicializando sistema de audio...")
            self.audio = AudioController(self.config['audio'])
            
            # Display Controller
            logger.info("🖥️  Inicializando pantallas OLED...")
            self.display = DisplayController(self.config['display'])
            
            # Controls Manager
            logger.info("🎛️  Inicializando controles...")
            self.controls = ControlsManager(
                self.config['controls'],
                self.on_control_change
            )
            
            # ADS-B Decoder
            logger.info("✈️  Inicializando decodificador ADS-B...")
            self.adsb = ADSBDecoder(self.config['adsb'])
            
            logger.info("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar componentes: {e}")
            return False
    
    def on_control_change(self, control_type, value):
        """Callback para cambios en controles físicos"""
        
        # Configuración de handlers para cada control
        control_actions = {
            'volume': {
                'set': lambda: self.audio.set_volume(value),
                'view': 'volume',
                'log': f"🔊 Volumen ajustado a {value}%"
            },
            'gain': {
                'set': lambda: self.sdr.set_gain(value),
                'view': 'gain',
                'log': f"📶 Ganancia ajustada a {value} dB"
            },
            'squelch': {
                'set': lambda: self.audio.set_squelch_threshold(value / 100.0),
                'view': 'squelch',
                'log': f"🔇 Squelch ajustado a {value}% (umbral: {value/100:.2f})"
            },
            'record_button': {
                'set': lambda: self._toggle_recording(),
                'view': None,
                'log': None
            }
        }
        
        # Ejecutar acción si el control existe
        if control_type in control_actions:
            action = control_actions[control_type]
            
            # Actualizar estado
            self.state[control_type] = value
            
            # Ejecutar setter
            try:
                action['set']()
            except Exception as e:
                logger.error(f"❌ Error en {control_type}: {e}")
                return
            
            # Cambiar vista si corresponde
            if action['view']:
                self.display.set_view(action['view'])
            
            # Log si hay mensaje
            if action['log']:
                logger.debug(action['log'])
    
    def _toggle_recording(self):
        """Alternar grabación de audio"""
        if self.audio.is_recording():
            self.audio.stop_recording()
            self.controls.set_record_led(False)
            self.state['recording'] = False
            logger.info("⏹️  Grabación detenida")
        else:
            self.audio.start_recording()
            self.state['recording'] = True
            logger.info("🔴 Grabación iniciada")
    
    def sdr_processing_loop(self):
        """Loop de procesamiento de señal SDR"""
        logger.info("🔄 Iniciando loop de procesamiento SDR...")
        
        while not self.shutdown_event.is_set():
            try:
                # Leer muestras del SDR
                samples = self.sdr.read_samples()
                
                if self.state['mode'] == 'VHF_AM':
                    # Demodular AM para audio de aviación
                    audio_data = self.sdr.demodulate_am(samples)
                    
                    # Enviar audio al DAC
                    self.audio.play_audio(audio_data)
                    
                    # Actualizar nivel de señal
                    self.state['rssi'] = self.sdr.get_rssi(samples)
                    
                elif self.state['mode'] == 'ADSB':
                    # Decodificar mensajes ADS-B
                    messages = self.adsb.decode(samples)
                    
                    if messages:
                        self.state['aircraft_data'] = self.adsb.get_aircraft_list()
                        logger.debug(f"✈️  {len(messages)} mensajes ADS-B decodificados")
                
            except Exception as e:
                logger.error(f"Error en loop SDR: {e}")
                time.sleep(0.1)
    
    def display_update_loop(self):
        """Loop para actualizar pantalla"""
        logger.info("🖥️  Iniciando loop de actualización de display...")
        
        while not self.shutdown_event.is_set():
            try:
                # Recopilar datos del sistema
                display_data = {
                    'frequency': self.state['frequency'],
                    'mode': self.state['mode'],
                    'volume': self.state['volume'],
                    'gain': self.state['gain'],
                    'squelch': self.state.get('squelch', 50),
                    'rssi': self.state.get('rssi', 0),
                    'squelch_open': self.audio.is_squelch_open() if self.audio else False,
                    'aircraft_data': self.state.get('aircraft_data', [])
                }
                
                # Si hay datos de aviones y no estamos en vista de control, mostrar ADS-B
                if display_data['aircraft_data'] and self.display.current_view == 'main':
                    self.display.set_view('adsb')
                elif not display_data['aircraft_data'] and self.display.current_view == 'adsb':
                    self.display.set_view('main')
                
                # Actualizar pantalla
                self.display.update_display(display_data)
                
                # Parpadear LED si está grabando
                if self.state['recording']:
                    self.controls.blink_record_led()
                
                # Esperar un poco
                time.sleep(0.1)  # 10 Hz refresh rate
                
            except Exception as e:
                logger.error(f"Error en display_update_loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Iniciar el sistema completo"""
        if not self.initialize_components():
            logger.error("❌ No se pudieron inicializar los componentes")
            return False
        
        # Definir hilos de procesamiento
        thread_configs = [
            (self.sdr_processing_loop, "SDR"),
            (self.display_update_loop, "Display"),
            (self.controls.monitor_loop, "Controls", (self.shutdown_event,))
        ]
        
        # Crear e iniciar hilos
        for config in thread_configs:
            target = config[0]
            name = config[1]
            args = config[2] if len(config) > 2 else ()
            
            thread = Thread(target=target, args=args, name=name, daemon=True)
            thread.start()
            self.threads.append(thread)
            logger.info(f"🔄 Hilo {name} iniciado")
        
        logger.info("✅ FlyM System está ACTIVO")
        return True
    
    def stop(self):
        """Detener el sistema de forma ordenada"""
        logger.info("🛑 Deteniendo FlyM System...")
        
        # Señalar shutdown
        self.shutdown_event.set()
        
        # Esperar hilos con timeout
        for thread in self.threads:
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning(f"⚠️  Hilo {thread.name} no terminó a tiempo")
        
        # Limpiar componentes en orden
        components = [
            ('SDR', self.sdr),
            ('Audio', self.audio),
            ('Display', self.display),
            ('Controls', self.controls)
        ]
        
        for name, component in components:
            if component:
                try:
                    if hasattr(component, 'close'):
                        component.close()
                    elif hasattr(component, 'cleanup'):
                        component.cleanup()
                    logger.debug(f"✅ {name} limpiado")
                except Exception as e:
                    logger.error(f"❌ Error limpiando {name}: {e}")
        
        logger.info("✅ Sistema detenido correctamente")
    
    def run(self):
        """Ejecutar el sistema hasta que se interrumpa"""
        try:
            if self.start():
                # Verificar si hay hardware simulado
                from sdr_controller import SIMULATION_MODE
                
                if SIMULATION_MODE:
                    # Modo simulación interactivo
                    logger.info("\n" + "="*60)
                    logger.info("🎭 MODO SIMULACIÓN ACTIVO")
                    logger.info("="*60)
                    logger.info("Comandos disponibles:")
                    logger.info("  v [0-100]  - Ajustar volumen")
                    logger.info("  g [0-50]   - Ajustar ganancia")
                    logger.info("  s [0-100]  - Ajustar squelch")
                    logger.info("  r          - Toggle grabación")
                    logger.info("  f [MHz]    - Cambiar frecuencia")
                    logger.info("  q          - Salir")
                    logger.info("="*60 + "\n")
                    
                    # Loop interactivo
                    while not self.shutdown_event.is_set():
                        try:
                            cmd = input("🎮 > ").strip().lower().split()
                            if not cmd:
                                continue
                            
                            if cmd[0] == 'v' and len(cmd) > 1:
                                value = max(0, min(100, int(cmd[1])))
                                self.on_control_change('volume', value)
                            elif cmd[0] == 'g' and len(cmd) > 1:
                                value = max(0, min(50, int(cmd[1])))
                                self.on_control_change('gain', value)
                            elif cmd[0] == 's' and len(cmd) > 1:
                                value = max(0, min(100, int(cmd[1])))
                                self.on_control_change('squelch', value)
                            elif cmd[0] == 'r':
                                self._toggle_recording()
                            elif cmd[0] == 'f' and len(cmd) > 1:
                                freq_mhz = float(cmd[1])
                                freq_hz = int(freq_mhz * 1e6)
                                self.state['frequency'] = freq_hz
                                self.sdr.set_frequency(freq_hz)
                                logger.info(f"✅ Frecuencia: {freq_mhz} MHz")
                            elif cmd[0] == 'q':
                                break
                            else:
                                print("❌ Comando desconocido (escribe comandos como: v 75, g 30, etc.)")
                        except (ValueError, IndexError):
                            print("❌ Formato inválido")
                        except EOFError:
                            break
                else:
                    # Modo hardware real
                    logger.info("📡 Sistema ejecutándose con hardware real...")
                    while not self.shutdown_event.is_set():
                        time.sleep(1)
                        
        except KeyboardInterrupt:
            logger.info("⚠️  Interrupción por teclado (Ctrl+C)")
        finally:
            self.stop()


def signal_handler(signum, frame):
    """Handler para señales del sistema"""
    logger.info(f"📨 Señal recibida: {signum}")
    sys.exit(0)


def main():
    """Punto de entrada principal"""
    # Registrar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crear y ejecutar el sistema
    system = FlyMSystem()
    system.run()


if __name__ == "__main__":
    main()
