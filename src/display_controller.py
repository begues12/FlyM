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
    VALID_VIEWS = {'main', 'volume', 'gain', 'squelch', 'adsb'}
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
                logger.info("🎭 Usando MockOLED (modo simulación)")
            else:
                # Modo real
                try:
                    logger.info(f"🖥️  Inicializando Display real (I²C: 0x{self.display_addr:02X})...")
                    serial = i2c(port=self.i2c_port, address=self.display_addr)
                    self.display = ssd1306(serial, width=128, height=32)
                    logger.info("✅ Display real inicializado")
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
            logger.info("📝 Usando fuentes por defecto (modo simulación)")
            return
        
        try:
            # Intentar cargar fuentes TrueType
            self.fonts = {
                'small': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10),
                'medium': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12),
                'large': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            }
            logger.info("📝 Fuentes personalizadas cargadas")
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
            logger.info("🎉 Mostrando splash screen...")
            with canvas(self.display) as draw:
                draw.text((15, 0), "FlyM System", fill="white", font=self.fonts.get('large'))
                draw.text((10, 18), "Aviation RX", fill="white", font=self.fonts.get('medium'))
            logger.info("✅ Splash screen mostrado")
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Error mostrando splash: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_display(self, data: Dict[str, Any]):
        """
        Actualizar pantalla con vista dinámica
        
        Args:
            data: Dict con todos los datos del sistema
        """
        with self.lock:
            try:
                # Verificar timeout para volver a vista principal
                self._check_view_timeout()
                
                # Mapa de vistas a métodos
                view_handlers = {
                    'volume': self._draw_volume_view,
                    'gain': self._draw_gain_view,
                    'squelch': self._draw_squelch_view,
                    'adsb': self._draw_adsb_view,
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
                # Línea 1: Frecuencia
                freq_mhz = data.get('frequency', 0) / 1e6
                freq_text = f"{freq_mhz:.3f}"
                draw.text((0, 0), freq_text, fill="white", font=self.fonts['large'])
                draw.text((90, 2), "MHz", fill="white", font=self.fonts['small'])
                
                # Línea 2: Modo y RSSI
                mode_text = data.get('mode', 'VHF').replace('_', ' ')
                draw.text((0, 18), mode_text, fill="white", font=self.fonts['small'])
                
                # Barra de señal
                rssi = data.get('rssi', 0)
                self._draw_signal_bars(draw, 70, 18, rssi)
            logger.debug(f"📺 Main view dibujada: {freq_text} MHz")
        except Exception as e:
            logger.error(f"Error dibujando main view: {e}")
    
    def _draw_volume_view(self, data):
        """Vista de volumen con escala"""
        with canvas(self.display) as draw:
            vol = data.get('volume', 0)
            
            # Título
            draw.text((30, 0), "VOLUMEN", fill="white", font=self.fonts['medium'])
            
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
            
            # Título
            draw.text((25, 0), "GANANCIA", fill="white", font=self.fonts['medium'])
            
            # Valor numérico
            draw.text((40, 14), f"{gain} dB", fill="white", font=self.fonts['large'])
            
            # Barra horizontal
            bar_width = int((gain / 50) * 110)
            draw.rectangle((8, 28, 8 + bar_width, 31), fill="white")
            draw.rectangle((8, 28, 118, 31), outline="white")
    
    def _draw_squelch_view(self, data):
        """Vista de squelch (umbral de silenciamiento)"""
        with canvas(self.display) as draw:
            squelch = data.get('squelch', 0)
            
            # Título
            draw.text((28, 0), "SQUELCH", fill="white", font=self.fonts['medium'])
            
            # Valor numérico grande
            draw.text((45, 14), f"{squelch}%", fill="white", font=self.fonts['large'])
            
            # Barra horizontal
            bar_width = int((squelch / 100) * 110)
            draw.rectangle((8, 28, 8 + bar_width, 31), fill="white")
            draw.rectangle((8, 28, 118, 31), outline="white")
    
    def _draw_adsb_view(self, data):
        """Vista de datos ADS-B"""
        with canvas(self.display) as draw:
            aircraft_list = data.get('aircraft_data', [])
            
            if not aircraft_list:
                draw.text((20, 10), "No aircraft", fill="white", font=self.fonts['medium'])
                return
            
            # Mostrar primer avión
            ac = aircraft_list[0]
            
            # Línea 1: Callsign
            callsign = ac.get('callsign', ac.get('icao', 'UNKNOWN'))
            draw.text((0, 0), callsign[:10], fill="white", font=self.fonts['large'])
            
            # Línea 2: Altitud y velocidad
            altitude = ac.get('altitude', 0)
            speed = ac.get('speed', 0)
            draw.text((0, 18), f"ALT:{altitude}ft", fill="white", font=self.fonts['small'])
            draw.text((75, 18), f"{speed}kt", fill="white", font=self.fonts['small'])
    
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
    
    def clear(self):
        """Limpiar pantalla"""
        if self.display:
            self.display.clear()
    
    def shutdown(self):
        """Apagar pantalla limpiamente"""
        logger.info("🔌 Apagando display...")
        if self.display:
            self.display.clear()
            self.display.hide()
