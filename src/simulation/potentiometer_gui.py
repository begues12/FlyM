"""
GUI de Control de Potenciómetros Simulados
Ventana independiente para controlar los 3 potenciómetros virtuales
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)


class PotentiometerControlGUI:
    """
    Ventana de control para potenciómetros simulados
    Permite ajustar los 3 potenciómetros del sistema:
    - Canal 0: Volumen (0-100%)
    - Canal 1: Ganancia/Filtro (0-50 dB)
    - Canal 2: Squelch/Ruido (0-100%)
    """
    
    def __init__(self, mock_spidev):
        """
        Inicializar GUI de potenciómetros
        
        Args:
            mock_spidev: Instancia de MockSpiDev a controlar
        """
        self.mock_spidev = mock_spidev
        self.root = tk.Toplevel()
        self.root.title("🎛️ Potenciómetros FlyM")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        
        # Valores actuales (0-1023, 10-bit ADC)
        self.pot_values = {
            0: tk.IntVar(value=512),  # Volumen: 50%
            1: tk.IntVar(value=614),  # Ganancia: 60%
            2: tk.IntVar(value=205),  # Squelch: 20%
        }
        
        # Información de potenciómetros
        self.pot_info = {
            0: {'name': 'Volumen', 'min': 0, 'max': 100, 'unit': '%', 'color': '#4CAF50'},
            1: {'name': 'Ganancia/Filtro', 'min': 0, 'max': 50, 'unit': 'dB', 'color': '#2196F3'},
            2: {'name': 'Squelch (Ruido)', 'min': 0, 'max': 100, 'unit': '%', 'color': '#FF9800'},
        }
        
        self._create_widgets()
        self._inject_values_into_mock()
        
        logger.info("🎛️ GUI de potenciómetros inicializada")
    
    def _create_widgets(self):
        """Crear widgets de la interfaz"""
        # Título
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(
            title_frame,
            text="🎛️ Control de Potenciómetros",
            font=('Arial', 14, 'bold')
        ).pack()
        
        ttk.Label(
            title_frame,
            text="Simula los potenciómetros físicos del FlyM Aviation Receiver",
            font=('Arial', 9)
        ).pack()
        
        # Separador
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=20, pady=5)
        
        # Frame para cada potenciómetro
        for channel in [0, 1, 2]:
            self._create_potentiometer_control(channel)
        
        # Separador
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Botones de control
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            button_frame,
            text="↻ Reset Valores",
            command=self._reset_values
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="📊 Mostrar Info",
            command=self._show_info
        ).pack(side=tk.LEFT, padx=5)
        
        # Info de conexión
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(
            info_frame,
            text="✅ Conectado a MockMCP3008 (SPI Simulado)",
            foreground='green',
            font=('Arial', 8)
        ).pack()
    
    def _create_potentiometer_control(self, channel: int):
        """Crear control para un potenciómetro"""
        info = self.pot_info[channel]
        
        # Frame principal
        frame = ttk.LabelFrame(self.root, text=f"Canal {channel}: {info['name']}", padding=10)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Frame superior: valor actual
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X)
        
        # Label del valor
        value_label = ttk.Label(
            top_frame,
            text=f"0 {info['unit']}",
            font=('Arial', 16, 'bold'),
            foreground=info['color']
        )
        value_label.pack(side=tk.LEFT)
        
        # Label del valor ADC raw
        raw_label = ttk.Label(
            top_frame,
            text="(ADC: 0)",
            font=('Arial', 9),
            foreground='gray'
        )
        raw_label.pack(side=tk.LEFT, padx=10)
        
        # Slider
        slider = ttk.Scale(
            frame,
            from_=0,
            to=1023,
            orient=tk.HORIZONTAL,
            variable=self.pot_values[channel],
            command=lambda v, ch=channel: self._on_slider_change(ch, v)
        )
        slider.pack(fill=tk.X, pady=5)
        
        # Labels min/max
        minmax_frame = ttk.Frame(frame)
        minmax_frame.pack(fill=tk.X)
        
        ttk.Label(
            minmax_frame,
            text=f"{info['min']} {info['unit']}",
            font=('Arial', 8)
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            minmax_frame,
            text=f"{info['max']} {info['unit']}",
            font=('Arial', 8)
        ).pack(side=tk.RIGHT)
        
        # Guardar referencias
        self.pot_info[channel]['value_label'] = value_label
        self.pot_info[channel]['raw_label'] = raw_label
        self.pot_info[channel]['slider'] = slider
    
    def _on_slider_change(self, channel: int, value):
        """Callback cuando cambia un slider"""
        try:
            raw_value = int(float(value))
            info = self.pot_info[channel]
            
            # Convertir a valor útil
            mapped_value = int((raw_value / 1023) * info['max'])
            
            # Actualizar labels
            info['value_label'].config(text=f"{mapped_value} {info['unit']}")
            info['raw_label'].config(text=f"(ADC: {raw_value})")
            
            # Inyectar en MockSpiDev
            self._inject_values_into_mock()
            
            logger.debug(f"🎛️ Potenciómetro CH{channel}: {mapped_value} {info['unit']} (raw: {raw_value})")
            
        except Exception as e:
            logger.error(f"Error al cambiar slider: {e}")
    
    def _inject_values_into_mock(self):
        """Inyectar valores actuales en MockSpiDev"""
        try:
            # Crear método personalizado para MockSpiDev
            current_values = {
                0: self.pot_values[0].get(),
                1: self.pot_values[1].get(),
                2: self.pot_values[2].get(),
            }
            
            # Reemplazar método _get_simulated_values del MockSpiDev
            def custom_get_values():
                import random
                # Agregar ruido pequeño para simular ADC real
                noise = random.randint(-3, 3)
                return {
                    ch: max(0, min(1023, val + noise))
                    for ch, val in current_values.items()
                }
            
            self.mock_spidev._get_simulated_values = custom_get_values
            
        except Exception as e:
            logger.error(f"Error al inyectar valores: {e}")
    
    def _reset_values(self):
        """Reset todos los potenciómetros a valores por defecto"""
        self.pot_values[0].set(512)  # Volumen: 50%
        self.pot_values[1].set(614)  # Ganancia: 60%
        self.pot_values[2].set(205)  # Squelch: 20%
        
        logger.info("🔄 Potenciómetros reseteados a valores por defecto")
    
    def _show_info(self):
        """Mostrar información de ayuda"""
        info_text = """
🎛️ Potenciómetros FlyM Aviation Receiver

Canal 0 - VOLUMEN (0-100%)
  Controla el volumen del audio de salida
  Conectado al canal 0 del MCP3008 ADC

Canal 1 - GANANCIA/FILTRO (0-50 dB)
  Controla la ganancia del SDR y filtrado
  Conectado al canal 1 del MCP3008 ADC

Canal 2 - SQUELCH/RUIDO (0-100%)
  Umbral para silenciar ruido de fondo
  Conectado al canal 2 del MCP3008 ADC

Los valores se actualizan en tiempo real
en el sistema simulado.
        """
        
        messagebox.showinfo("Información", info_text.strip())
    
    def run(self):
        """Ejecutar el mainloop de tkinter"""
        self.root.mainloop()
    
    def close(self):
        """Cerrar la ventana"""
        try:
            self.root.destroy()
        except:
            pass


def create_potentiometer_gui(mock_spidev):
    """
    Factory function para crear GUI de potenciómetros
    
    Args:
        mock_spidev: Instancia de MockSpiDev
    
    Returns:
        PotentiometerControlGUI instance
    """
    return PotentiometerControlGUI(mock_spidev)
