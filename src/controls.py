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
        
        # Obtener configuración de pines GPIO (soporta ambos formatos)
        gpio_pins = config.get('gpio_pins', {})
        self.button_menu = gpio_pins.get('button_menu') or config.get('button_menu_pin', 17)
        self.button_plus = gpio_pins.get('button_plus') or config.get('button_plus_pin', 27)
        self.button_minus = gpio_pins.get('button_minus') or config.get('button_minus_pin', 22)
        self.record_button = gpio_pins.get('button_record') or config.get('record_button_pin', 23)
        self.record_led = gpio_pins.get('led_record') or config.get('record_led_pin', 24)
        
        # Obtener configuración de menús
        menus_config = config.get('menus', {})
        self.MENUS = menus_config.get('order', ['frequency', 'autoscan', 'gain', 'volume', 'memory', 'vox'])
        
        # Estado del menú
        self.current_menu_index = 0
        
        # Cargar configuración de cada menú para valores por defecto, pasos y rangos
        self.values = {}
        self.steps = {}
        self.ranges = {}
        
        for menu_name in self.MENUS:
            menu_cfg = menus_config.get(menu_name, {})
            
            # Valores por defecto
            if menu_name == 'frequency':
                default_val = menu_cfg.get('default', 125.0) * 1e6  # Convertir MHz a Hz
                self.values[menu_name] = default_val
                self.steps[menu_name] = int(menu_cfg.get('step', 0.025) * 1e6)  # MHz a Hz
                min_hz = menu_cfg.get('min', 108.0) * 1e6
                max_hz = menu_cfg.get('max', 137.0) * 1e6
                self.ranges[menu_name] = (min_hz, max_hz)
            else:
                self.values[menu_name] = menu_cfg.get('default', 0)
                self.steps[menu_name] = menu_cfg.get('step', 1)
                self.ranges[menu_name] = (menu_cfg.get('min', 0), menu_cfg.get('max', 100))
        
        # Variables para detectar hold del botón menu
        self.menu_button_press_time = None
        self.menu_button_hold_threshold = 1.0  # 1 segundo para hold
        
        # Variables para aceleración en hold de +/-
        self.button_hold_active = None  # 'plus' o 'minus'
        self.button_hold_count = 0
        self.button_hold_timer = None
        
        self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Inicializar GPIO para botones y LED o simulador"""
        if not GPIO_AVAILABLE:
            # Modo simulación
            from simulation.mock_gpio import MockGPIO
            global GPIO
            GPIO = MockGPIO
            print("🎭 Usando MockGPIO (modo simulación)")
        
        try:
            # Configurar GPIO (funciona igual en real y mock)
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Botones de control
            GPIO.setup(self.button_menu, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.button_plus, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.button_minus, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Botón de grabación y LED
            GPIO.setup(self.record_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.record_led, GPIO.OUT)
            GPIO.output(self.record_led, GPIO.LOW)  # LED apagado inicialmente
            
            # Configurar interrupciones de botones
            # Botón menú con detección de press y release
            GPIO.add_event_detect(
                self.button_menu,
                GPIO.BOTH,  # Detectar tanto press como release
                callback=self._menu_button_callback,
                bouncetime=50
            )
            # Botones + y - con detección de press y release para aceleración
            GPIO.add_event_detect(
                self.button_plus,
                GPIO.BOTH,
                callback=self._plus_button_callback,
                bouncetime=50
            )
            GPIO.add_event_detect(
                self.button_minus,
                GPIO.BOTH,
                callback=self._minus_button_callback,
                bouncetime=50
            )
            GPIO.add_event_detect(
                self.record_button,
                GPIO.FALLING,
                callback=self._record_button_callback,
                bouncetime=300
            )
            
            mode_text = "🎭 simulado" if not GPIO_AVAILABLE else "📡 real"
            print(f"✅ GPIO {mode_text} inicializado")
            print(f"   Botón Menú: GPIO{self.button_menu}")
            print(f"   Botón +: GPIO{self.button_plus}")
            print(f"   Botón -: GPIO{self.button_minus}")
            print(f"   Botón grabación: GPIO{self.record_button}")
            print(f"   LED: GPIO{self.record_led}")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar GPIO: {e}")
    
    def _menu_button_callback(self, channel):
        """Callback para botón de menú - cambiar entre pantallas (click) o abrir submenú (hold)"""
        try:
            button_state = GPIO.input(self.button_menu)
            current_time = time.time()
            
            if button_state == GPIO.LOW:  # Botón presionado
                self.menu_button_press_time = current_time
                
            else:  # Botón liberado
                if self.menu_button_press_time is None:
                    return
                
                hold_duration = current_time - self.menu_button_press_time
                self.menu_button_press_time = None
                
                # HOLD detectado - abrir/cerrar submenú
                if hold_duration >= self.menu_button_hold_threshold:
                    print(f"⚙️ HOLD detectado - abriendo submenú...")
                    if self.callback:
                        self.callback('submenu_toggle', None)
                    return
                
                # Click normal - cambiar de menú o confirmar en submenú
                if hold_duration < self.menu_button_hold_threshold:
                    if self.callback:
                        self.callback('menu_click', None)
                        
        except Exception as e:
            logger.error(f"Error en callback de botón menú: {e}")
    
    def _plus_button_callback(self, channel):
        """Callback para botón + - incrementar valor actual con aceleración en hold"""
        try:
            button_state = GPIO.input(self.button_plus)
            
            if button_state == GPIO.LOW:  # Botón presionado
                # Primer cambio inmediato
                self._increment_value()
                
                # Iniciar hold con aceleración
                self.button_hold_active = 'plus'
                self.button_hold_count = 0
                self._schedule_hold_repeat()
                
            else:  # Botón liberado
                # Detener hold
                self.button_hold_active = None
                if self.button_hold_timer:
                    try:
                        self.button_hold_timer.cancel()
                    except:
                        pass
                    self.button_hold_timer = None
                    
        except Exception as e:
            logger.error(f"Error en callback de botón +: {e}")
    
    def _increment_value(self):
        """Incrementar valor del control actual o cambiar valor en submenú"""
        try:
            # Si el callback existe y retorna True, significa que manejó el submenú
            if self.callback and self.callback('submenu_change_value', 1):
                return
            
            menu_name = self.MENUS[self.current_menu_index]
            current = self.values[menu_name]
            step = self.steps[menu_name]
            min_val, max_val = self.ranges[menu_name]
            
            # Multiplicador de step para frecuencia (acelera aún más en hold largo)
            if menu_name == 'frequency':
                if self.button_hold_count < 5:
                    multiplier = 1  # 25 kHz
                elif self.button_hold_count < 10:
                    multiplier = 4  # 100 kHz
                else:
                    multiplier = 10  # 250 kHz - máximo
                step = step * multiplier
            
            # Incrementar valor
            new_value = min(current + step, max_val)
            
            if new_value != current:
                self.values[menu_name] = new_value
                
                # Log solo si no es repetición rápida
                if self.button_hold_count < 3:
                    print(f"➕ {menu_name}: {new_value}")
                
                if self.callback:
                    self.callback(menu_name, new_value)
        except Exception as e:
            logger.error(f"Error al incrementar valor: {e}")
    
    def _minus_button_callback(self, channel):
        """Callback para botón - - decrementar valor actual con aceleración en hold"""
        try:
            button_state = GPIO.input(self.button_minus)
            
            if button_state == GPIO.LOW:  # Botón presionado
                # Primer cambio inmediato
                self._decrement_value()
                
                # Iniciar hold con aceleración
                self.button_hold_active = 'minus'
                self.button_hold_count = 0
                self._schedule_hold_repeat()
                
            else:  # Botón liberado
                # Detener hold
                self.button_hold_active = None
                if self.button_hold_timer:
                    try:
                        self.button_hold_timer.cancel()
                    except:
                        pass
                    self.button_hold_timer = None
                    
        except Exception as e:
            logger.error(f"Error en callback de botón -: {e}")
    
    def _decrement_value(self):
        """Decrementar valor del control actual o cambiar valor en submenú"""
        try:
            # Si el callback existe y retorna True, significa que manejó el submenú
            if self.callback and self.callback('submenu_change_value', -1):
                return
            
            menu_name = self.MENUS[self.current_menu_index]
            current = self.values[menu_name]
            step = self.steps[menu_name]
            min_val, max_val = self.ranges[menu_name]
            
            # Multiplicador de step para frecuencia (acelera aún más en hold largo)
            if menu_name == 'frequency':
                if self.button_hold_count < 5:
                    multiplier = 1  # 25 kHz
                elif self.button_hold_count < 10:
                    multiplier = 4  # 100 kHz
                else:
                    multiplier = 10  # 250 kHz - máximo
                step = step * multiplier
            
            # Decrementar valor
            new_value = max(current - step, min_val)
            
            if new_value != current:
                self.values[menu_name] = new_value
                
                # Log solo si no es repetición rápida
                if self.button_hold_count < 3:
                    print(f"➖ {menu_name}: {new_value}")
                
                if self.callback:
                    self.callback(menu_name, new_value)
        except Exception as e:
            logger.error(f"Error al decrementar valor: {e}")
    
    def _schedule_hold_repeat(self):
        """Programar siguiente repetición con aceleración progresiva"""
        if self.button_hold_active is None:
            return
        
        # Aceleración progresiva
        if self.button_hold_count < 3:
            delay = 0.4  # Lento al inicio (400ms)
        elif self.button_hold_count < 6:
            delay = 0.2  # Medio (200ms)
        elif self.button_hold_count < 10:
            delay = 0.1  # Rápido (100ms)
        else:
            delay = 0.05  # Muy rápido (50ms)
        
        # Programar siguiente ejecución
        from threading import Timer
        self.button_hold_timer = Timer(delay, self._execute_hold_repeat)
        self.button_hold_timer.daemon = True
        self.button_hold_timer.start()
    
    def _execute_hold_repeat(self):
        """Ejecutar repetición durante hold"""
        if self.button_hold_active is None:
            return
        
        self.button_hold_count += 1
        
        # Ejecutar cambio según dirección
        if self.button_hold_active == 'plus':
            self._increment_value()
        elif self.button_hold_active == 'minus':
            self._decrement_value()
        
        # Programar siguiente repetición
        self._schedule_hold_repeat()
    
    def _record_button_callback(self, channel):
        """Callback para botón de grabación"""
        try:
            print("🔴 Botón de grabación presionado")
            if self.callback:
                self.callback('record_button', True)
        except Exception as e:
            logger.error(f"Error en callback de botón: {e}")
    
    def get_current_menu(self):
        """Obtener el menú actual"""
        return self.MENUS[self.current_menu_index]
    
    def set_value(self, control, value):
        """Establecer valor de un control externamente (para GUI)"""
        if control in self.values:
            min_val, max_val = self.ranges[control]
            self.values[control] = max(min_val, min(value, max_val))
    
    def get_value(self, control):
        """Obtener valor actual de un control"""
        return self.values.get(control, 0)
    
    def read_potentiometers(self):
        """DEPRECATED - Ya no se usan potenciómetros"""
        return None, None, None
    
    def monitor_loop(self, shutdown_event):
        """Loop de monitoreo - ya no es necesario con botones"""
        print("🎛️  Sistema de botones activo (no requiere polling)")
        
        # Mantener el thread vivo
        while not shutdown_event.is_set():
            time.sleep(1)
        
        print("🛑 Monitor de controles detenido")
    
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
        """Limpiar recursos GPIO"""
        if GPIO:
            try:
                # Apagar LED antes de limpiar
                self.set_record_led(False)
                GPIO.cleanup()
                print("✅ GPIO limpiado")
            except Exception as e:
                logger.error(f"Error al limpiar GPIO: {e}")


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
        
        print("⌨️  Controles por teclado activados:")
        print("   [W/S] - Frecuencia")
        print("   [A/D] - Volumen")
        print("   [Q/E] - Ganancia")
        print("   [M] - Cambiar modo")
    
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
