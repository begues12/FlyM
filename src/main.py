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
from memory_manager import MemoryManager
from activity_logger import ActivityLogger
from vox_controller import VOXController
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
        print("🚀 Iniciando FlyM Aviation Receiver...")
        
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
        self.memory_manager = None
        self.activity_logger = None
        self.vox_controller = None
        
        # Estado del sistema
        self.state = {
            'frequency': self.config['sdr']['default_frequency'],
            'mode': 'VHF_AM',  # VHF_AM o AM
            'volume': 50,
            'gain': 30,
            'autoscan': 0,  # 0=OFF, 1=ON
            'memory': 1,  # Slot de memoria actual (0=no guardar, 1-10)
            'vox': 0,  # 0=OFF, 1=ON
            'rssi': 0,
            'recording': False,
            'vox_recording': False,  # Estado de grabación VOX
            'aircraft_data': [],
            'current_menu': 'frequency',  # Menú activo
            'memory_freq': None,  # Frecuencia de la memoria seleccionada
            'memory_name': '',  # Nombre de la memoria
            'vox_threshold': -60,  # Umbral VOX en dB
            'submenu_open': False,  # Submenú abierto
            'submenu_option': 0,  # Opción seleccionada en submenú (0-3)
            'eq_auto': 0  # Ecualizador automático 0=OFF, 1=ON
        }
        
        # Hilos de procesamiento
        self.threads = []
        
        # Referencia al GUI (si está en modo simulación)
        self.gui = None
        
    def initialize_components(self):
        """Inicializar todos los componentes del sistema"""
        try:
            # SDR Controller
            print("📻 Inicializando RTL-SDR...")
            self.sdr = SDRController(self.config['sdr'])
            
            # Audio Controller
            print("🔊 Inicializando sistema de audio...")
            self.audio = AudioController(self.config['audio'])
            
            # Display Controller
            print("🖥️  Inicializando pantallas OLED...")
            self.display = DisplayController(self.config['display'])
            
            # Controls Manager
            print("🎛️  Inicializando controles...")
            # Pasar configuración completa para que tenga acceso a menus y gpio_pins
            controls_config = {
                **self.config.get('controls', {}),
                'gpio_pins': self.config.get('gpio_pins', {}),
                'menus': self.config.get('menus', {})
            }
            self.controls = ControlsManager(
                controls_config,
                self.on_control_change
            )
            
            # ADS-B Decoder
            print("✈️  Inicializando decodificador ADS-B...")
            self.adsb = ADSBDecoder(self.config['adsb'])
            
            # Memory Manager
            print("💾 Inicializando gestor de memorias...")
            self.memory_manager = MemoryManager()
            
            # Activity Logger
            print("📝 Inicializando registro de actividad...")
            self.activity_logger = ActivityLogger()
            
            # VOX Controller
            print("🎤 Inicializando controlador VOX...")
            self.vox_controller = VOXController(
                threshold=self.config.get('vox', {}).get('threshold', -60),
                delay=self.config.get('vox', {}).get('delay', 2.0)
            )
            # Asignar callbacks después de la inicialización
            self.vox_controller.on_vox_start = self._on_vox_start
            self.vox_controller.on_vox_stop = self._on_vox_stop
            
            print("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar componentes: {e}")
            return False
    
    def on_control_change(self, control_type, value):
        """Callback para cambios en controles físicos y botones"""
        
        # Manejar toggle de submenú (HOLD en botón MENU)
        if control_type == 'submenu_toggle':
            if self.state['submenu_open']:
                self.state['submenu_open'] = False
            else:
                self.state['submenu_open'] = True
                self.state['submenu_option'] = 0
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('submenu_open', self.state['submenu_open'])
                self.gui.update_state('submenu_option', self.state['submenu_option'])
            return
        
        # Manejar cambio de valor en submenú (botones +/-)
        if control_type == 'submenu_change_value':
            if self.state.get('submenu_open', False):
                self._change_submenu_value(value)
                return True
            else:
                return False
        
        # Manejar click en menú (depende si submenú está abierto)
        if control_type == 'menu_click':
            if self.state['submenu_open']:
                # Click en submenú = NAVEGAR a siguiente opción
                self.state['submenu_option'] = (self.state['submenu_option'] + 1) % 4
                
                # Sincronizar con GUI
                if self.gui:
                    self.gui.update_state('submenu_option', self.state['submenu_option'])
            else:
                # Cambiar menú normal
                self.controls.current_menu_index = (self.controls.current_menu_index + 1) % len(self.controls.MENUS)
                menu_name = self.controls.MENUS[self.controls.current_menu_index]
                self.state['current_menu'] = menu_name
                
                # Sincronizar con GUI
                if self.gui:
                    self.gui.update_state('current_menu', menu_name)
            return
        
        # Manejar cambio de menú (legacy - por si se usa desde GUI)
        if control_type == 'menu_change':
            self.state['current_menu'] = value
            print(f"📋 Menú cambiado a: {value}")
            return
        
        # Configuración de handlers para cada control
        control_actions = {
            'volume': {
                'set': lambda: self.audio.set_volume(value),
                'log': f"🔊 Volumen ajustado a {value}%"
            },
            'gain': {
                'set': lambda: self.sdr.set_gain(value),
                'log': f"📶 Ganancia ajustada a {value} dB"
            },
            'frequency': {
                'set': lambda: self.sdr.set_frequency(value),
                'log': f"📻 Frecuencia ajustada a {value/1e6:.3f} MHz"
            },
            'autoscan': {
                'set': lambda: self._toggle_autoscan(value),
                'log': f"🔄 Auto-Scan {'activado' if value == 1 else 'desactivado'}"
            },
            'memory': {
                'set': lambda: self._on_memory_change(value),
                'log': None
            },
            'memory_save': {
                'set': lambda: self._on_memory_save(value),
                'log': None
            },
            'vox': {
                'set': lambda: self._toggle_vox(value),
                'log': f"🎤 VOX {'activado' if value == 1 else 'desactivado'}"
            },
            'record_button': {
                'set': lambda: self._toggle_recording(),
                'log': None
            },
            'recording': {
                'set': lambda: self._toggle_recording() if value != self.state.get('recording', False) else None,
                'log': None
            },
            'mode': {
                'set': lambda: self._change_mode(value),
                'log': f"📡 Modo cambiado a {value}"
            }
        }
        
        # Manejar detección de avión simulado
        if control_type == 'aircraft_detected':
            if 'aircraft_data' not in self.state:
                self.state['aircraft_data'] = []
            self.state['aircraft_data'].append(value)
            print(f"✈️ Avión detectado: {value.get('callsign', 'UNKNOWN')}")
            return
        
        # Ejecutar acción si el control existe
        if control_type in control_actions:
            action = control_actions[control_type]
            
            # Actualizar estado
            self.state[control_type] = value
            
            # Ejecutar setter
            try:
                if action['set']:
                    action['set']()
            except Exception as e:
                logger.error(f"❌ Error en {control_type}: {e}")
                return
            
            # Log si hay mensaje
            if action['log']:
                print(action['log'])
    
    def _change_mode(self, mode):
        """Cambiar modo de operación"""
        if mode == 'ADSB':
            # Cambiar a frecuencia ADS-B
            self.sdr.set_frequency(1090000000)  # 1090 MHz
            self.state['frequency'] = 1090000000
        elif mode == 'VHF_AM':
            # Volver a frecuencia VHF por defecto
            default_freq = self.config['sdr'].get('default_frequency', 125000000)
            self.sdr.set_frequency(default_freq)
            self.state['frequency'] = default_freq
        print(f"📡 Modo cambiado a {mode}")
    
    def _toggle_autoscan(self, value):
        """Activar/desactivar auto-scan"""
        self.state['autoscan'] = value
        
        if value == 1:
            print("🔄 Auto-Scan ACTIVADO - buscando señales...")
            # TODO: Implementar lógica de auto-scan en sdr_processing_loop
        else:
            print("⏸️  Auto-Scan DESACTIVADO")
    
    def _toggle_recording(self):
        """Alternar grabación de audio"""
        if self.audio.is_recording():
            self.audio.stop_recording()
            self.controls.set_record_led(False)
            self.state['recording'] = False
            print("⏹️  Grabación detenida")
        else:
            self.audio.start_recording()
            self.state['recording'] = True
            print("🔴 Grabación iniciada")
    
    def _change_submenu_value(self, direction):
        """Cambiar valor de la opción seleccionada en el submenú"""
        option = self.state['submenu_option']
        
        if option == 0:  # SAVE - Cambiar slot de memoria
            current_slot = self.state.get('memory', 1)
            new_slot = current_slot + direction
            
            if new_slot > 10:
                new_slot = 0
            elif new_slot < 0:
                new_slot = 10
            
            self.state['memory'] = new_slot
            if hasattr(self, 'controls') and hasattr(self.controls, 'values'):
                self.controls.values['memory'] = new_slot
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('memory', new_slot)
                
        elif option == 1:  # MODE - Toggle VHF ↔ AM
            current_mode = self.state.get('mode', 'VHF_AM')
            new_mode = 'AM' if current_mode == 'VHF_AM' else 'VHF_AM'
            self.state['mode'] = new_mode
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('mode', new_mode)
                
        elif option == 2:  # REC - Toggle grabación
            self._toggle_recording()
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('recording', self.state['recording'])
            
        elif option == 3:  # EQ - Toggle ecualizador automático
            current_eq = self.state.get('eq_auto', 0)
            new_eq = 1 if current_eq == 0 else 0
            self.state['eq_auto'] = new_eq
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('eq_auto', new_eq)
    
    def _execute_submenu_action(self):
        """Forzar actualización inmediata del display con el estado actual"""
        display_data = {
            'frequency': self.state['frequency'],
            'mode': self.state['mode'],
            'volume': self.state['volume'],
            'gain': self.state['gain'],
            'autoscan': self.state.get('autoscan', 0),
            'memory': self.state.get('memory', 1),
            'vox': self.state.get('vox', 0),
            'rssi': self.state.get('rssi', 0),
            'recording': self.state.get('recording', False),
            'squelch_open': self.audio.is_squelch_open() if self.audio else False,
            'aircraft_data': self.state.get('aircraft_data', []),
            'current_menu': self.state.get('current_menu', 'frequency'),
            'memory_freq': self.state.get('memory_freq'),
            'memory_name': self.state.get('memory_name', ''),
            'memory_saved': self.state.get('memory_saved', False),
            'vox_recording': self.state.get('vox_recording', False),
            'vox_threshold': self.state.get('vox_threshold', -60),
            'submenu_open': self.state.get('submenu_open', False),
            'submenu_option': self.state.get('submenu_option', 0),
            'eq_auto': self.state.get('eq_auto', 0)
        }
        # Actualizar el display (esto actualiza self.display.image)
        self.display.update_display(display_data)
        
        # Forzar refresh inmediato del canvas en la GUI 
        # Usar after(1, ...) para dar tiempo a que la imagen se actualice
        if self.gui and hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.after(1, self.gui._update_oled_display)
    
    def _execute_submenu_action(self):
        """Ejecutar acción seleccionada en el submenú (DEPRECATED - ahora se usa _change_submenu_value)"""
        option = self.state['submenu_option']
        
        # Opciones del submenú: 0=SAVE, 1=MODE, 2=REC, 3=VOX
        if option == 0:  # SAVE - Guardar memoria
            slot = self.state['memory']
            self._on_memory_save(slot)
            print(f"💾 Guardando en memoria M{slot}")
        elif option == 1:  # MODE - Cambiar VHF ↔ ADS-B
            current_mode = self.state['mode']
            new_mode = 'ADSB' if current_mode == 'VHF_AM' else 'VHF_AM'
            self._change_mode(new_mode)
            self.state['mode'] = new_mode
            print(f"📡 Modo cambiado a {new_mode}")
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('mode', new_mode)
        elif option == 2:  # REC - Toggle grabación
            self._toggle_recording()
        elif option == 3:  # VOX - Toggle VOX
            new_vox = 1 if self.state['vox'] == 0 else 0
            self._toggle_vox(new_vox)
            self.state['vox'] = new_vox
            
            # Sincronizar con GUI
            if self.gui:
                self.gui.update_state('vox', new_vox)
        
        # Cerrar submenú después de ejecutar
        self.state['submenu_open'] = False
        
        # Sincronizar cierre con GUI
        if self.gui:
            self.gui.update_state('submenu_open', False)
    
    def _on_memory_change(self, slot):
        """Callback cuando cambia el slot de memoria"""
        self.state['memory'] = slot
        
        # Obtener información de la memoria
        memory = self.memory_manager.recall_memory(int(slot))
        
        if memory:
            self.state['memory_freq'] = memory['frequency']
            self.state['memory_name'] = memory['name']
            print(f"💾 Memoria M{slot}: {memory['name']} - {memory['frequency']/1e6:.3f} MHz")
            
            # Si estamos en el menú de memoria, podríamos auto-sintonizar
            # (descomentado si quieres auto-tune al cambiar memoria)
            # self.sdr.set_frequency(memory['frequency'])
            # self.state['frequency'] = memory['frequency']
        else:
            self.state['memory_freq'] = None
            self.state['memory_name'] = ''
            print(f"💾 Memoria M{slot}: VACÍA")
    
    def _on_memory_save(self, slot):
        """Callback para guardar frecuencia actual en memoria (hold botón menu)"""
        current_freq = self.state['frequency']
        freq_mhz = current_freq / 1e6
        
        # Generar nombre automático basado en frecuencia
        name = f"{freq_mhz:.3f} MHz"
        
        # Guardar en el slot actual (orden correcto: slot, name, frequency)
        self.memory_manager.save_memory(int(slot), name, current_freq)
        
        # Actualizar estado para mostrar en display
        self.state['memory_freq'] = current_freq
        self.state['memory_name'] = name
        self.state['memory_saved'] = True  # Flag para mostrar confirmación
        
        print(f"💾 ✅ Guardado en M{slot}: {name}")
        
        # Resetear flag después de 2 segundos
        import threading
        def reset_flag():
            time.sleep(2)
            self.state['memory_saved'] = False
        threading.Thread(target=reset_flag, daemon=True).start()
    
    def _toggle_vox(self, value):
        """Activar/desactivar VOX"""
        self.state['vox'] = value
        self.vox_controller.set_enabled(value == 1)
        
        if value == 1:
            print("🎤 VOX ACTIVADO - grabación automática por actividad")
        else:
            print("🎤 VOX DESACTIVADO")
            # Detener grabación VOX si está activa
            if self.state.get('vox_recording', False):
                self.audio.stop_recording()
                self.state['vox_recording'] = False
    
    def _on_vox_start(self):
        """Callback cuando VOX detecta actividad y empieza a grabar"""
        if not self.audio.is_recording():
            self.audio.start_recording()
            self.state['vox_recording'] = True
            
            # Iniciar registro de transmisión
            freq = self.state['frequency']
            rssi = self.state.get('rssi', 0)
            self.activity_logger.start_transmission(freq, rssi)
            
            print("🔴 VOX: Grabación iniciada automáticamente")
    
    def _on_vox_stop(self):
        """Callback cuando VOX termina la grabación"""
        if self.audio.is_recording() and self.state.get('vox_recording', False):
            self.audio.stop_recording()
            self.state['vox_recording'] = False
            
            # Finalizar registro de transmisión
            rssi = self.state.get('rssi', 0)
            self.activity_logger.end_transmission(rssi)
            
            print("⏹️  VOX: Grabación detenida automáticamente")
    
    def sdr_processing_loop(self):
        """Loop de procesamiento de señal SDR"""
        print("🔄 Iniciando loop de procesamiento SDR...")
        
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
                    rssi = self.sdr.get_rssi(samples)
                    self.state['rssi'] = rssi
                    
                    # Actualizar VOX con RSSI actual
                    if self.state.get('vox', 0) == 1:
                        current_time = time.time()
                        self.vox_controller.update(rssi, current_time)
                    
                    # Actualizar log de transmisión si está grabando con VOX
                    if self.state.get('vox_recording', False):
                        self.activity_logger.update_transmission(rssi)
                    
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
        print("🖥️  Iniciando loop de actualización de display...")
        
        while not self.shutdown_event.is_set():
            try:
                # Recopilar datos del sistema
                display_data = {
                    'frequency': self.state['frequency'],
                    'mode': self.state['mode'],
                    'volume': self.state['volume'],
                    'gain': self.state['gain'],
                    'autoscan': self.state.get('autoscan', 0),
                    'memory': self.state.get('memory', 1),
                    'vox': self.state.get('vox', 0),
                    'rssi': self.state.get('rssi', 0),
                    'recording': self.state.get('recording', False),
                    'squelch_open': self.audio.is_squelch_open() if self.audio else False,
                    'aircraft_data': self.state.get('aircraft_data', []),
                    'current_menu': self.state.get('current_menu', 'frequency'),
                    'memory_freq': self.state.get('memory_freq'),
                    'memory_name': self.state.get('memory_name', ''),
                    'memory_saved': self.state.get('memory_saved', False),
                    'vox_recording': self.state.get('vox_recording', False),
                    'vox_threshold': self.state.get('vox_threshold', -60),
                    'submenu_open': self.state.get('submenu_open', False),
                    'submenu_option': self.state.get('submenu_option', 0),
                    'eq_auto': self.state.get('eq_auto', 0)
                }
                
                # Actualizar pantalla
                self.display.update_display(display_data)
                
                # Parpadear LED si está grabando
                if self.state.get('recording', False):
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
            print(f"🔄 Hilo {name} iniciado")
        
        print("✅ FlyM System está ACTIVO")
        return True
    
    def stop(self):
        """Detener el sistema de forma ordenada"""
        print("🛑 Deteniendo FlyM System...")
        
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
        
        print("✅ Sistema detenido correctamente")
    
    def run(self, use_gui=True):
        """
        Ejecutar el sistema hasta que se interrumpa
        
        Args:
            use_gui: Si True, usa interfaz gráfica en modo simulación
        """
        try:
            if self.start():
                # Verificar si hay hardware simulado
                from sdr_controller import SIMULATION_MODE
                
                if SIMULATION_MODE:
                    print("\n" + "="*60)
                    print("🎭 MODO SIMULACIÓN ACTIVO")
                    print("="*60)
                    
                    # Preguntar modo de control
                    if use_gui:
                        try:
                            from simulation.gui_controller import get_gui_controller
                            
                            print("🖥️  Abriendo interfaz gráfica...")
                            print("   Si no se abre, verifica que tkinter esté instalado")
                            print("="*60 + "\n")
                            
                            # Crear GUI con callback
                            gui = get_gui_controller(callback=self.on_control_change)
                            self.gui = gui  # Guardar referencia
                            
                            # Vincular display controller a la GUI
                            if self.display:
                                gui.set_display_controller(self.display)
                                print("📺 Display OLED vinculado a GUI")
                            
                            gui.start()
                            
                            # Mantener ejecutando mientras GUI está activa
                            while not self.shutdown_event.is_set() and gui.running:
                                time.sleep(0.5)
                            
                        except ImportError as e:
                            logger.warning(f"⚠️  No se pudo cargar GUI: {e}")
                            print("💡 Instalando tkinter: pip install tk")
                            print("   Continuando con modo consola...\n")
                            use_gui = False
                    
                    if not use_gui:
                        # Modo consola interactivo
                        print("💻 Modo consola interactivo")
                        print("Comandos disponibles:")
                        print("  v [0-100]  - Ajustar volumen")
                        print("  g [0-50]   - Ajustar ganancia")
                        print("  s [0-100]  - Ajustar squelch")
                        print("  r          - Toggle grabación")
                        print("  f [MHz]    - Cambiar frecuencia")
                        print("  q          - Salir")
                        print("="*60 + "\n")
                        
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
                                    print(f"✅ Frecuencia: {freq_mhz} MHz")
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
                    print("📡 Sistema ejecutándose con hardware real...")
                    while not self.shutdown_event.is_set():
                        time.sleep(1)
                        
        except KeyboardInterrupt:
            print("⚠️  Interrupción por teclado (Ctrl+C)")
        finally:
            self.stop()


def signal_handler(signum, frame):
    """Handler para señales del sistema"""
    print(f"📨 Señal recibida: {signum}")
    sys.exit(0)


def main():
    """Punto de entrada principal"""
    import argparse
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(description='FlyM Aviation Receiver')
    parser.add_argument('--no-gui', action='store_true',
                       help='Usar modo consola en lugar de GUI (solo simulación)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Ruta al archivo de configuración')
    
    args = parser.parse_args()
    
    # Registrar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crear y ejecutar el sistema
    system = FlyMSystem(config_path=args.config)
    system.run(use_gui=not args.no_gui)


if __name__ == "__main__":
    main()
