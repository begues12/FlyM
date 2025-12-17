"""
FlyM Aviation Receiver - Display Controller
==========================================
Controlador para pantalla OLED única con vistas dinámicas
"""

import logging
import time
from threading import Lock
from typing import Dict, Any, Optional

try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    from PIL import Image, ImageDraw, ImageFont
    DISPLAY_AVAILABLE = True
except ImportError:
    i2c = None
    canvas = None
    ssd1306 = None
    Image = None
    ImageFont = None
    DISPLAY_AVAILABLE = False

logger = logging.getLogger(__name__)


class DisplayController:
    """Controlador para pantalla OLED única con vistas dinámicas"""
    
    # Constantes
    DISPLAY_WIDTH = 128
    DISPLAY_HEIGHT = 32
    DEFAULT_VIEW_TIMEOUT = 3
    VALID_VIEWS = {'main', 'volume', 'gain', 'squelch', 'adsb', 'memory', 'vox', 'autoscan'}
    SPLASH_DURATION = 2
    
    def __init__(self, config):
        """
        Inicializar controlador de pantalla
        
        Args:
            config: Diccionario con configuración de pantalla
        """
        self.config = config
        
        # Configuración I²C
        self.display_addr = config.get('display_address', 0x3C)
        self.i2c_port = config.get('i2c_port', 1)
        self.view_timeout = config.get('view_timeout', 3)
        
        # Dispositivo OLED
        self.display = None
        
        # Lock para acceso thread-safe
        self.lock = Lock()
        
        # Fuentes
        self.fonts = {}
        
        # Estado de la pantalla
        self.current_view = 'main'  # main, volume, gain, adsb
        self.last_update = time.time()
        self.last_control_time = 0
        
        self._initialize_displays()
        self._load_fonts()
    
    def _initialize_displays(self):
        """Inicializar pantalla OLED o simulador"""
        global canvas
        try:
            if not DISPLAY_AVAILABLE:
                # Modo simulación
                from simulation.mock_display import MockOLED, get_mock_device, canvas as mock_canvas
                canvas = mock_canvas  # Usar el canvas mock
                device = get_mock_device(width=128, height=32)
                self.display = MockOLED(device=device)
                print("🎭 Usando MockOLED (modo simulación)")
            else:
                # Modo real
                try:
                    print(f"🖥️  Inicializando Display real (I²C: 0x{self.display_addr:02X})...")
                    serial = i2c(port=self.i2c_port, address=self.display_addr)
                    self.display = ssd1306(serial, width=128, height=32)
                    print("✅ Display real inicializado")
                except Exception as e:
                    logger.error(f"❌ Error al inicializar display: {e}")
                    # Fallback a mock
                    from simulation.mock_display import MockOLED, get_mock_device, canvas as mock_canvas
                    canvas = mock_canvas  # Usar el canvas mock
                    device = get_mock_device(width=128, height=32)
                    self.display = MockOLED(device=device)
                    logger.warning("⚠️  Usando mock display como fallback")
            
            # Mostrar splash screen
            self._show_splash()
            
        except Exception as e:
            logger.error(f"❌ Error crítico al inicializar pantalla: {e}")
            raise
    
    def _load_fonts(self):
        """Cargar fuentes para las pantallas"""
        if not DISPLAY_AVAILABLE or ImageFont is None:
            # En modo simulación, usar fuentes por defecto
            try:
                from PIL import ImageFont as PilFont
                self.fonts = {
                    'small': PilFont.load_default(),
                    'medium': PilFont.load_default(),
                    'large': PilFont.load_default()
                }
            except:
                self.fonts = {
                    'small': None,
                    'medium': None,
                    'large': None
                }
            print("📝 Usando fuentes por defecto (modo simulación)")
            return
        
        try:
            # Intentar cargar fuentes TrueType
            self.fonts = {
                'small': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10),
                'medium': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12),
                'large': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            }
            print("📝 Fuentes personalizadas cargadas")
        except Exception as e:
            logger.warning(f"⚠️  No se pudieron cargar fuentes personalizadas: {e}")
            # Usar fuente por defecto
            try:
                self.fonts = {
                    'small': ImageFont.load_default(),
                    'medium': ImageFont.load_default(),
                    'large': ImageFont.load_default()
                }
            except:
                self.fonts = {
                    'small': None,
                    'medium': None,
                    'large': None
                }
    
    def _show_splash(self):
        """Mostrar pantalla de inicio"""
        try:
            print("🎉 Mostrando splash screen...")
            with canvas(self.display) as draw:
                draw.text((15, 0), "FlyM System", fill="white", font=self.fonts.get('large'))
                draw.text((10, 18), "Aviation RX", fill="white", font=self.fonts.get('medium'))
            print("✅ Splash screen mostrado")
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Error mostrando splash: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_display(self, data: Dict[str, Any]):
        """
        Actualizar pantalla con vista dinámica basada en menú activo
        
        Args:
            data: Dict con todos los datos del sistema
        """
        with self.lock:
            try:
                # Obtener menú activo y modo del data
                current_menu = data.get('current_menu', 'frequency')
                submenu_open = data.get('submenu_open', False)
                mode = data.get('mode', 'VHF_AM')
        
                
                # Mapear menú a vista
                # Si el submenú está abierto, mostrar vista de submenú
                if submenu_open:
                    self._draw_submenu_view(data)
                else:
                    # Si estamos en modo ADS-B, mostrar vista de aviones
                    if mode == 'ADSB':
                        self.current_view = 'adsb'
                    else:
                        menu_to_view = {
                            'frequency': 'main',
                            'adsb': 'adsb',
                            'autoscan': 'autoscan',
                            'gain': 'gain',
                            'volume': 'volume',
                            'memory': 'memory',
                            'vox': 'vox'
                        }
                        
                        self.current_view = menu_to_view.get(current_menu, 'main')
                    
                    # Mapa de vistas a métodos
                    view_handlers = {
                        'volume': self._draw_volume_view,
                        'gain': self._draw_gain_view,
                        'autoscan': self._draw_autoscan_view,
                        'adsb': self._draw_adsb_view,
                        'memory': self._draw_memory_view,
                        'vox': self._draw_vox_view,
                        'main': self._draw_main_view
                    }
                    
                    # Renderizar vista (default a main)
                    handler = view_handlers.get(self.current_view, self._draw_main_view)
                    handler(data)
                
                self.last_update = time.time()
                
            except Exception as e:
                logger.error(f"Error al actualizar Display: {e}")
    
    def _check_view_timeout(self):
        """Verificar timeout y volver a vista principal si es necesario"""
        control_views = {'volume', 'gain', 'squelch'}
        elapsed = time.time() - self.last_control_time
        
        if self.current_view in control_views and elapsed > self.view_timeout:
            self.current_view = 'main'
    
    def set_view(self, view_name: str):
        """
        Cambiar vista manualmente
        
        Args:
            view_name: 'main', 'volume', 'gain', 'squelch', 'adsb'
        """
        if view_name not in self.VALID_VIEWS:
            logger.warning(f"⚠️  Vista inválida: {view_name}, usando 'main'")
            view_name = 'main'
        
        self.current_view = view_name
        self.last_control_time = time.time()
    
    def _draw_main_view(self, data):
        """Vista principal: Frecuencia y RSSI"""
        try:
            with canvas(self.display) as draw:
                # Indicador de menú
                
                # Línea 1: Frecuencia
                freq_mhz = data.get('frequency', 0) / 1e6
                freq_text = f"{freq_mhz:.3f}"
                draw.text((5, 2), freq_text, fill="white", font=self.fonts['large'])
                draw.text((45, 2), "MHz", fill="white", font=self.fonts['small'])
                
                # Indicador de grabación (esquina superior derecha)
                if data.get('recording', False) or data.get('vox_recording', False):
                    draw.ellipse((115, 0, 127, 12), fill="white")
                    draw.text((119, 1), "R", fill="black", font=self.fonts['small'])
                
                # Línea 2: Modo y señal
                mode_text = data.get('mode', 'VHF').replace('_', ' ')
                draw.text((5, 18), mode_text, fill="white", font=self.fonts['small'])
                
                # Barra de señal
                rssi = data.get('rssi', 0)
                self._draw_signal_bars(draw, 65, 18, rssi)
            logger.debug(f"📺 Main view dibujada: {freq_text} MHz")
        except Exception as e:
            logger.error(f"Error dibujando main view: {e}")
    
    def _draw_volume_view(self, data):
        """Vista de volumen con escala"""
        with canvas(self.display) as draw:
            vol = data.get('volume', 0)
            
            # Indicador + Título
            draw.text((0, 0), ">VOL", fill="white", font=self.fonts['medium'])
            
            # Valor numérico grande
            draw.text((45, 14), f"{vol}%", fill="white", font=self.fonts['large'])
            
            # Barra horizontal
            bar_width = int((vol / 100) * 110)
            draw.rectangle((8, 28, 8 + bar_width, 31), fill="white")
            draw.rectangle((8, 28, 118, 31), outline="white")
    
    def _draw_gain_view(self, data):
        """Vista de ganancia/tono con escala"""
        with canvas(self.display) as draw:
            gain = data.get('gain', 0)
            
            # Indicador + Título
            draw.text((0, 0), ">GAIN", fill="white", font=self.fonts['medium'])
            
            # Valor numérico
            draw.text((40, 14), f"{gain}dB", fill="white", font=self.fonts['large'])
            
            # Barra horizontal
            bar_width = int((gain / 50) * 110)
            draw.rectangle((8, 28, 8 + bar_width, 31), fill="white")
            draw.rectangle((8, 28, 118, 31), outline="white")
    
    def _draw_squelch_view(self, data):
        """Vista de squelch (umbral de silenciamiento)"""
        with canvas(self.display) as draw:
            squelch = data.get('squelch', 0)
            
            # Indicador + Título
            draw.text((0, 0), ">SQ", fill="white", font=self.fonts['medium'])
            
            # Valor numérico grande
            draw.text((45, 14), f"{squelch}%", fill="white", font=self.fonts['large'])
            
            # Barra horizontal
            bar_width = int((squelch / 100) * 110)
            draw.rectangle((8, 28, 8 + bar_width, 31), fill="white")
            draw.rectangle((8, 28, 118, 31), outline="white")
    
    def _draw_autoscan_view(self, data):
        """Vista de auto-scan con frecuencia siendo escaneada"""
        with canvas(self.display) as draw:
            autoscan = data.get('autoscan', 0)
            
            # Indicador + Título
            draw.text((0, 0), ">SCAN", fill="white", font=self.fonts['medium'])
            
            if autoscan == 1:
                # Mostrar frecuencia actual siendo escaneada
                scan_freq = data.get('scan_frequency')
                if scan_freq:
                    freq_mhz = scan_freq / 1e6
                    draw.text((5, 14), f"{freq_mhz:.3f}", fill="white", font=self.fonts['medium'])
                    draw.text((70, 16), "MHz", fill="white", font=self.fonts['small'])
                else:
                    draw.text((30, 14), "SCAN", fill="white", font=self.fonts['large'])
                
                # Dibujar animación de scanning (círculos concéntricos)
                import time
                phase = int(time.time() * 3) % 3  # Más rápido: 0, 1, 2
                center_x, center_y = 110, 20
                for i in range(3):
                    if i == phase:
                        radius = 3 + i * 2
                        draw.ellipse((center_x - radius, center_y - radius,
                                    center_x + radius, center_y + radius),
                                   outline="white")
            else:
                # Estado OFF grande
                draw.text((30, 14), "OFF", fill="white", font=self.fonts['large'])
    
    def _draw_squelch_view(self, data):
        """DEPRECATED - Vista de squelch ya no se usa"""
        # Redirigir a vista principal
        self._draw_main_view(data)
    
    def _draw_adsb_view(self, data):
        """Vista de datos ADS-B - muestra un avión individual con todos sus datos"""
        with canvas(self.display) as draw:
            aircraft_list = data.get('aircraft_data', [])
            
            if not aircraft_list:
                # Sin aviones detectados
                draw.text((5, 0), "ADS-B SCAN", fill="white", font=self.fonts['small'])
                draw.text((20, 14), "No aircraft", fill="white", font=self.fonts['small'])
                return
            
            # Obtener índice del avión seleccionado
            selected_idx = data.get('selected_aircraft_index', 0)
            
            # Asegurar que el índice sea válido
            if selected_idx >= len(aircraft_list):
                selected_idx = 0
            
            aircraft = aircraft_list[selected_idx]
            
            # Verificar si el avión está sin señal
            signal_lost = aircraft.get('signal_lost', False)
            
            # Línea 1: ICAO y contador (con indicador de señal perdida)
            icao = aircraft.get('icao', '------')[:6]
            if signal_lost:
                draw.text((2, 0), f"!{icao}", fill="white", font=self.fonts['medium'])
            else:
                draw.text((2, 0), icao, fill="white", font=self.fonts['medium'])
            draw.text((95, 1), f"{selected_idx + 1}/{len(aircraft_list)}", fill="white", font=self.fonts['small'])
            
            # Línea 2: Callsign
            callsign = aircraft.get('callsign', '-')
            if callsign:
                draw.text((2, 11), callsign[:10], fill="white", font=self.fonts['medium'])
            else:
                draw.text((2, 11), "NO CALL", fill="white", font=self.fonts['small'])
            
            # Línea 3: Altitud y velocidad
            altitude = aircraft.get('altitude')
            speed = aircraft.get('speed')
            
            alt_text = f"{int(altitude):05d}ft" if altitude is not None else "-----ft"
            spd_text = f"{int(speed):03d}kt" if speed is not None else "---kt"
            
            draw.text((2, 22), alt_text, fill="white", font=self.fonts['small'])
            draw.text((80, 22), spd_text, fill="white", font=self.fonts['small'])
    
    def _draw_signal_bars(self, draw, x, y, signal_level):
        """Dibujar barras de señal"""
        bar_count = 5
        bar_width = 3
        bar_spacing = 2
        filled_bars = int((signal_level / 100) * bar_count)
        
        for i in range(bar_count):
            bar_height = 4 + (i * 2)
            bar_x = x + i * (bar_width + bar_spacing)
            bar_y = y + 12 - bar_height
            
            if i < filled_bars:
                draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), fill="white")
            else:
                draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), outline="white")
    
    def _draw_memory_view(self, data):
        """Dibujar vista de memorias"""
        with canvas(self.display) as draw:
            # Verificar si se acaba de guardar (mostrar confirmación)
            if data.get('memory_saved', False):
                # Pantalla de confirmación
                draw.text((0, 0), "SAVED!", fill="white", font=self.fonts['large'])
                memory_slot = data.get('memory', 1)
                draw.text((0, 18), f"Memory M{int(memory_slot)}", fill="white", font=self.fonts['small'])
                return
            
            # Vista normal de memoria
            # Título
            draw.text((0, 0), "MEMORY", fill="white", font=self.fonts['small'])
            
            # Slot actual
            memory_slot = data.get('memory', 1)
            draw.text((70, 0), f"M{int(memory_slot)}", fill="white", font=self.fonts['small'])
            
            # Instrucción en esquina
            draw.text((95, 0), "[HOLD]", fill="white", font=self.fonts['small'])
            
            # Frecuencia guardada en memoria (si existe)
            memory_freq = data.get('memory_freq')
            memory_name = data.get('memory_name', '')
            
            if memory_freq:
                freq_mhz = memory_freq / 1e6
                draw.text((0, 12), f"{freq_mhz:.3f} MHz", fill="white", font=self.fonts['medium'])
                
                # Nombre de la memoria
                if memory_name:
                    draw.text((0, 24), memory_name[:16], fill="white", font=self.fonts['small'])
            else:
                draw.text((0, 16), "EMPTY", fill="white", font=self.fonts['large'])
                draw.text((0, 24), "Hold MENU to save", fill="white", font=self.fonts['small'])
    
    def _draw_vox_view(self, data):
        """Dibujar vista de VOX"""
        with canvas(self.display) as draw:
            # Título y estado en línea superior
            vox_enabled = data.get('vox', 0) == 1
            status_text = "ON" if vox_enabled else "OFF"
            draw.text((0, 0), f"VOX: {status_text}", fill="white", font=self.fonts['small'])
            
            if vox_enabled:
                # Estado de grabación en esquina superior derecha
                vox_recording = data.get('vox_recording', False)
                if vox_recording:
                    draw.ellipse((110, 2, 126, 10), fill="white")
                    draw.text((113, 1), "REC", fill="black", font=self.fonts['small'])
                
                # Umbral y RSSI en línea inferior
                vox_threshold = data.get('vox_threshold', -60)
                rssi = data.get('rssi', -100)
                draw.text((0, 16), f"Th:{vox_threshold:+.0f}", fill="white", font=self.fonts['small'])
                draw.text((60, 16), f"RS:{rssi:+.0f}", fill="white", font=self.fonts['small'])
            else:
                draw.text((0, 16), "OFF", fill="white", font=self.fonts['large'])
    
    def _draw_submenu_view(self, data):
        """Vista de submenú con 3 opciones: SAVE, REC, EQ
        
        Nota: Aviación usa exclusivamente AM (Amplitude Modulation).
        AM permite que dos transmisiones simultáneas se escuchen mezcladas,
        mientras que en FM una señal "captura" a la otra perdiendo información.
        En aviación es crítico oír interferencia antes que perder comunicación.
        """
        try:
            
            with canvas(self.display) as draw:
                selected = data.get('submenu_option', 0)
                
                # Opciones del submenú (solo 3 ahora)
                memory_slot = data.get('memory', 1)
                if memory_slot == 0:
                    save_text = "-"
                else:
                    save_text = f"M{memory_slot}"
                
                rec_text = "ON" if data.get('recording', False) else "OFF"
                eq_text = "ON" if data.get('eq_auto', 0) == 1 else "OFF"
                
                # Log solo cuando hay cambio de valor
                current_values = (save_text, rec_text, eq_text)
                if not hasattr(self, '_last_submenu_values') or self._last_submenu_values != current_values:
                    print(f"📺 Submenú actualizado: SAV:{save_text} REC:{rec_text} EQ:{eq_text}")
                    self._last_submenu_values = current_values
                
                options = [
                    ("SAV", save_text),  # Guardar en memoria (- o M1-M10)
                    ("REC", rec_text),   # Grabar
                    ("EQ", eq_text)      # Ecualizador automático
                ]
                                
                # Layout: 3 opciones horizontales centradas
                positions = [
                    (5, 10),    # SAVE izquierda
                    (48, 10),   # REC centro
                    (91, 10)    # EQ derecha
                ]
                
                for i, ((label, value), (x, y)) in enumerate(zip(options, positions)):
                    # Resaltar opción seleccionada
                    if i == selected:
                        # Fondo blanco, texto negro
                        draw.rectangle((x-2, y-2, x+32, y+12), fill="white")
                        text_color = "black"
                    else:
                        text_color = "white"
                    
                    # Dibujar label y valor en la misma línea
                    text = f"{label}:{value}"
                    draw.text((x, y), text, fill=text_color, font=self.fonts['small'])
                    
        except Exception as e:
            logger.error(f"❌ Error dibujando submenú: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def clear(self):
        """Limpiar pantalla"""
        if self.display:
            self.display.clear()
    
    def shutdown(self):
        """Apagar pantalla limpiamente"""
        print("🔌 Apagando display...")
        if self.display:
            self.display.clear()
            self.display.hide()
