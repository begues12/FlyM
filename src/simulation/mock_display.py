"""
Mock OLED Display para simulación
Simula pantalla SSD1306 mostrando en consola
"""

import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

logger = logging.getLogger(__name__)


class MockDevice:
    """Mock del device I2C"""
    
    def __init__(self, width=128, height=32):
        self.width = width
        self.height = height
        self.mode = "1"  # 1-bit color
        self.size = (width, height)
        logger.debug(f"🎭 MockDevice: {width}x{height}")


class MockOLED:
    """
    Mock de luma.oled para simulación
    Imprime el contenido en consola (ASCII art)
    """
    
    def __init__(self, device=None, width=128, height=32):
        self.device = device or MockDevice(width, height)
        self.width = self.device.width
        self.height = self.device.height
        self.mode = self.device.mode  # Añadir atributo mode
        self.size = self.device.size  # Añadir atributo size
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self._last_display = None
        logger.info(f"🎭 MockOLED inicializado ({self.width}x{self.height})")
    
    def display(self, image: Image.Image):
        """
        'Muestra' la imagen en la pantalla
        En modo simulación, imprime representación en consola
        """
        self.image = image
        
        # Solo mostrar si cambió significativamente
        if self._has_changed(image):
            self._print_to_console(image)
            self._last_display = image.copy()
    
    def _has_changed(self, image: Image.Image) -> bool:
        """Verifica si la imagen cambió significativamente"""
        if self._last_display is None:
            return True
        
        # Comparar algunos píxeles clave
        pixels_new = image.load()
        pixels_old = self._last_display.load()
        
        changes = 0
        sample_points = [(x, y) for x in range(0, self.width, 8) 
                         for y in range(0, self.height, 4)]
        
        for x, y in sample_points:
            if pixels_new[x, y] != pixels_old[x, y]:
                changes += 1
        
        # Cambió si más del 10% de puntos de muestra difieren
        return changes > len(sample_points) * 0.1
    
    def _print_to_console(self, image: Image.Image):
        """
        Imprime representación ASCII de la pantalla
        Escala la imagen para caber en consola
        """
        # Escalar para consola (divide altura por 2 para aspectos)
        scale_w = max(1, self.width // 64)  # Max 64 chars ancho
        scale_h = max(1, self.height // 8)   # Max 8 líneas alto
        
        pixels = image.load()
        
        print("\n┌" + "─" * (self.width // scale_w) + "┐")
        
        for y in range(0, self.height, scale_h * 2):
            line = "│"
            for x in range(0, self.width, scale_w):
                # Muestrear bloque
                block_on = False
                for dy in range(scale_h * 2):
                    for dx in range(scale_w):
                        px = min(x + dx, self.width - 1)
                        py = min(y + dy, self.height - 1)
                        if pixels[px, py]:
                            block_on = True
                            break
                    if block_on:
                        break
                
                line += "█" if block_on else " "
            
            line += "│"
            print(line)
        
        print("└" + "─" * (self.width // scale_w) + "┘\n")
    
    def clear(self):
        """Limpia la pantalla"""
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)


def get_mock_device(width=128, height=32):
    """Factory para crear mock device"""
    return MockDevice(width, height)
