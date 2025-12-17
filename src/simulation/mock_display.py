"""
Mock OLED Display para simulación
Simula pantalla SSD1306 mostrando en consola
"""

import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MockDevice:
    """Mock del device I2C"""
    
    def __init__(self, width=128, height=32):
        self.width = width
        self.height = height
        self.mode = "1"  # 1-bit color
        self.size = (width, height)
        logger.debug(f"🎭 MockDevice: {width}x{height}")


class MockCanvas:
    """Mock de luma.core.render.canvas para ser usado como context manager"""
    
    def __init__(self, device):
        self.device = device
        self.image = Image.new(device.mode, device.size)
        self.draw = ImageDraw.Draw(self.image)
    
    def __enter__(self):
        """Retorna el objeto draw para dibujar"""
        return self.draw
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Al salir del contexto, muestra la imagen en el display"""
        self.device.display(self.image)
        return False


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
        print(f"🎭 MockOLED inicializado ({self.width}x{self.height})")
    
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
        Muestra el contenido real de texto extraído de la imagen
        """
        # Deshabilitado para evitar spam en consola
        # Solo loggear cambios significativos
        pass
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """
        Intenta extraer texto de la imagen escaneando píxeles
        Analiza regiones comunes donde aparece texto
        """
        # Analizar diferentes zonas de la pantalla
        text_lines = []
        
        # Línea superior (0-16): Frecuencia o Título
        top_text = self._scan_text_region(image, 0, 0, self.width, 16)
        if top_text:
            text_lines.append(top_text)
        
        # Línea inferior (16-32): Modo, RSSI, valores
        bottom_text = self._scan_text_region(image, 0, 16, self.width, 32)
        if bottom_text:
            text_lines.append(bottom_text)
        
        return '\n'.join(text_lines) if text_lines else ""
    
    def _scan_text_region(self, image: Image.Image, x1: int, y1: int, x2: int, y2: int) -> str:
        """
        Escanea una región específica y detecta patrones de texto
        Retorna descripción aproximada del contenido
        """
        pixels = image.load()
        
        # Contar píxeles encendidos por columna para detectar caracteres
        char_columns = []
        in_char = False
        char_start = 0
        
        for x in range(x1, x2):
            col_pixels = sum(1 for y in range(y1, y2) if pixels[x, y])
            
            if col_pixels > 0:
                if not in_char:
                    in_char = True
                    char_start = x
            else:
                if in_char and (x - char_start) > 2:  # Mínimo 3 píxeles de ancho
                    char_columns.append((char_start, x))
                in_char = False
        
        # Si hay caracteres detectados
        if char_columns:
            # Analizar densidad de píxeles para estimar contenido
            total_pixels = sum(1 for x in range(x1, x2) for y in range(y1, y2) if pixels[x, y])
            area = (x2 - x1) * (y2 - y1)
            density = total_pixels / area if area > 0 else 0
            
            # Generar descripción aproximada basada en posición y densidad
            if y1 < 16:  # Línea superior
                if density > 0.3:  # Mucho contenido = número grande
                    return self._estimate_large_text(image, x1, y1, x2, y2, char_columns)
                else:
                    return self._estimate_small_text(image, x1, y1, x2, y2, char_columns)
            else:  # Línea inferior
                return self._estimate_bottom_line(image, x1, y1, x2, y2, pixels)
        
        return ""
    
    def _estimate_large_text(self, image: Image.Image, x1: int, y1: int, x2: int, y2: int, chars) -> str:
        """Estima texto grande (frecuencia o valores)"""
        pixels = image.load()
        
        # Detectar si hay punto decimal
        has_decimal = False
        for x in range(x1, x2):
            # Buscar patrón de punto (píxeles en parte baja)
            bottom_pixels = sum(1 for y in range(y1 + 10, y2) if pixels[x, y])
            if bottom_pixels > 0 and bottom_pixels < 3:
                has_decimal = True
                break
        
        # Aproximar número basado en ancho
        width = x2 - x1
        if width > 80 and has_decimal:
            return "🎯 Frecuencia: ###.### MHz"
        elif width > 60:
            return "🎯 Valor: ## dB o ##%"
        else:
            return "🎯 Texto: [Contenido]"
    
    def _estimate_small_text(self, image: Image.Image, x1: int, y1: int, x2: int, y2: int, chars) -> str:
        """Estima texto pequeño (etiquetas)"""
        width = x2 - x1
        if width > 80:
            return "📝 Etiqueta: [Título o Descripción]"
        elif width > 40:
            return "📝 [Texto Mediano]"
        else:
            return "📝 [Etiqueta]"
    
    def _estimate_bottom_line(self, image: Image.Image, x1: int, y1: int, x2: int, y2: int, pixels) -> str:
        """Estima contenido de línea inferior"""
        parts = []
        
        # Detectar barras de progreso (líneas horizontales largas)
        for y in range(y1, y2):
            consecutive = 0
            for x in range(x1, x2):
                if pixels[x, y]:
                    consecutive += 1
                else:
                    if consecutive > 20:  # Barra detectada
                        bar_percent = int((consecutive / (x2 - x1)) * 100)
                        return f"▓{'█' * (bar_percent // 5)}{'░' * (20 - bar_percent // 5)}▓ {bar_percent}%"
                    consecutive = 0
        
        # Detectar texto pequeño en izquierda y derecha
        left_pixels = sum(1 for x in range(x1, x1 + 60) for y in range(y1, y2) if pixels[x, y])
        right_pixels = sum(1 for x in range(x2 - 60, x2) for y in range(y1, y2) if pixels[x, y])
        
        if left_pixels > 50:
            parts.append("📡 [Modo/Estado]")
        if right_pixels > 50:
            parts.append("📶 [Señal]")
        
        return "  ".join(parts) if parts else "📊 [Información del Sistema]"
    
    def _print_graphic_representation(self, image: Image.Image, pixels):
        """Fallback: representación gráfica ASCII"""
        scale_w = max(1, self.width // 64)
        scale_h = max(1, self.height // 8)
        
        print("┌" + "─" * (self.width // scale_w) + "┐")
        
        for y in range(0, self.height, scale_h * 2):
            line = "│"
            for x in range(0, self.width, scale_w):
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
        
        print("└" + "─" * (self.width // scale_w) + "┘")
    
    def clear(self):
        """Limpia la pantalla"""
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)


def canvas(device):
    """
    Mock de luma.core.render.canvas
    Retorna un context manager para dibujar en el device
    """
    return MockCanvas(device)


def get_mock_device(width=128, height=32):
    """Factory para crear mock device"""
    return MockDevice(width, height)
