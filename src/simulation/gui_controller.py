"""
Interfaz Gráfica de Control del Simulador FlyM
Permite controlar todos los parámetros del sistema en tiempo real
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import Optional, Callable, Dict, Any
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)


class SimulatorGUI:
    """
    Interfaz gráfica para controlar el simulador FlyM
    Permite ajustar controles, ver estado y activar/desactivar funciones
    """
    
    def __init__(self, on_control_change: Optional[Callable] = None):
        self.on_control_change = on_control_change
        self.root = None
        self.running = False
        self.thread = None
        self.display_controller = None  # Referencia al DisplayController
        
        # Estado del sistema
        self.state = {
            'volume': 60,
            'gain': 25,
            'squelch': 10,
            'frequency': 125.0,  # MHz
            'recording': False,
            'mode': 'VHF_AM',
            'rssi': 0,
            'squelch_open': False
        }
        
        # Widgets
        self.widgets = {}
    
    def start(self):
        """Inicia la interfaz gráfica en un thread separado"""
        self.running = True
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()
        logger.info("🎮 Interfaz gráfica iniciada")
    
    def set_display_controller(self, display_controller):
        """Establece referencia al display controller para actualizar OLED"""
        self.display_controller = display_controller
        logger.info("🖥️ Display controller vinculado a GUI")
    
    def stop(self):
        """Detiene la interfaz gráfica"""
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
        logger.info("🎮 Interfaz gráfica detenida")
    
    def _run_gui(self):
        """Ejecuta el loop principal de la GUI"""
        try:
            self.root = tk.Tk()
            self.root.title("🎭 FlyM Simulator Control Panel")
            self.root.geometry("600x700")
            self.root.resizable(False, False)
            
            # Configurar estilo
            self._setup_style()
            
            # Crear interfaz
            self._create_header()
            self._create_oled_display_section()
            self._create_controls_section()
            self._create_frequency_section()
            self._create_recording_section()
            self._create_aircraft_simulation_section()
            self._create_mode_section()
            self._create_status_section()
            self._create_buttons_section()
            
            # Actualizar periódicamente
            self._schedule_update()
            
            # Ejecutar
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"Error en GUI: {e}")
    
    def _setup_style(self):
        """Configura el estilo visual"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        accent_color = '#4CAF50'
        
        self.root.configure(bg=bg_color)
        
        # Estilos personalizados
        style.configure('Title.TLabel', 
                       background=bg_color, 
                       foreground=accent_color,
                       font=('Arial', 16, 'bold'))
        
        style.configure('Header.TLabel',
                       background=bg_color,
                       foreground=fg_color,
                       font=('Arial', 12, 'bold'))
        
        style.configure('Normal.TLabel',
                       background=bg_color,
                       foreground=fg_color,
                       font=('Arial', 10))
        
        style.configure('Value.TLabel',
                       background=bg_color,
                       foreground=accent_color,
                       font=('Arial', 11, 'bold'))
    
    def _create_header(self):
        """Crea el encabezado"""
        frame = ttk.Frame(self.root)
        frame.pack(pady=20)
        
        title = ttk.Label(frame, 
                         text="🎭 FlyM Simulator Control",
                         style='Title.TLabel')
        title.pack()
        
        subtitle = ttk.Label(frame,
                            text="Control Panel de Pruebas",
                            style='Normal.TLabel')
        subtitle.pack()
    
    def _create_oled_display_section(self):
        """Crea sección que muestra el display OLED simulado"""
        frame = ttk.LabelFrame(self.root, text="  📺 Pantalla OLED SSD1306 (128x32)  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # Canvas para dibujar la pantalla OLED
        # Escalar 4x para que se vea mejor
        scale = 4
        canvas_width = 128 * scale
        canvas_height = 32 * scale
        
        self.widgets['oled_canvas'] = tk.Canvas(
            frame,
            width=canvas_width,
            height=canvas_height,
            bg='#000000',  # Fondo negro como OLED
            highlightthickness=2,
            highlightbackground='#333333'
        )
        self.widgets['oled_canvas'].pack()
        
        # Label de info
        info_frame = ttk.Frame(frame)
        info_frame.pack(pady=5)
        
        ttk.Label(info_frame, 
                 text="Resolución: 128x32 píxeles",
                 style='Normal.TLabel',
                 font=('Arial', 8)).pack(side='left', padx=10)
        
        ttk.Label(info_frame,
                 text="Color: Monocromático (Amarillo/Blanco sobre Negro)",
                 style='Normal.TLabel',
                 font=('Arial', 8)).pack(side='left', padx=10)
    
    def _create_controls_section(self):
        """Crea sección de controles (volumen, ganancia, squelch)"""
        frame = ttk.LabelFrame(self.root, text="  Controles  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # Volumen
        vol_frame = ttk.Frame(frame)
        vol_frame.pack(fill='x', pady=5)
        
        ttk.Label(vol_frame, text="🔊 Volumen:", style='Normal.TLabel').pack(side='left')
        self.widgets['volume_label'] = ttk.Label(vol_frame, 
                                                  text=f"{self.state['volume']}%",
                                                  style='Value.TLabel')
        self.widgets['volume_label'].pack(side='right')
        
        self.widgets['volume_slider'] = ttk.Scale(frame,
                                                   from_=0, to=100,
                                                   orient='horizontal',
                                                   value=self.state['volume'],
                                                   command=self._on_volume_change)
        self.widgets['volume_slider'].pack(fill='x', pady=(0, 10))
        
        # Filtro de Ruido (Gain)
        gain_frame = ttk.Frame(frame)
        gain_frame.pack(fill='x', pady=5)
        
        ttk.Label(gain_frame, text="🎚️ Filtro de Ruido:", style='Normal.TLabel').pack(side='left')
        self.widgets['gain_label'] = ttk.Label(gain_frame,
                                                text=f"{self.state['gain']} dB",
                                                style='Value.TLabel')
        self.widgets['gain_label'].pack(side='right')
        
        self.widgets['gain_slider'] = ttk.Scale(frame,
                                                from_=0, to=50,
                                                orient='horizontal',
                                                value=self.state['gain'],
                                                command=self._on_gain_change)
        self.widgets['gain_slider'].pack(fill='x', pady=(0, 10))
    
    def _create_frequency_section(self):
        """Crea sección de frecuencia"""
        frame = ttk.LabelFrame(self.root, text="  Frecuencia  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # Slider de frecuencia
        freq_slider_frame = ttk.Frame(frame)
        freq_slider_frame.pack(fill='x', pady=5)
        
        ttk.Label(freq_slider_frame, text="📻 Frecuencia:", style='Normal.TLabel').pack(side='left')
        self.widgets['freq_label'] = ttk.Label(freq_slider_frame,
                                                text=f"{self.state['frequency']:.3f} MHz",
                                                style='Value.TLabel')
        self.widgets['freq_label'].pack(side='right')
        
        # Slider para rango VHF (108-137 MHz)
        self.widgets['freq_slider'] = ttk.Scale(frame,
                                                from_=108.0, to=137.0,
                                                orient='horizontal',
                                                value=self.state['frequency'],
                                                command=self._on_frequency_slider_change)
        self.widgets['freq_slider'].pack(fill='x', pady=(0, 10))
        
        # Labels min/max
        minmax_frame = ttk.Frame(frame)
        minmax_frame.pack(fill='x')
        ttk.Label(minmax_frame, text="108.0 MHz", style='Normal.TLabel', font=('Arial', 8)).pack(side='left')
        ttk.Label(minmax_frame, text="137.0 MHz", style='Normal.TLabel', font=('Arial', 8)).pack(side='right')
        
        # Separador
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Entrada manual
        freq_frame = ttk.Frame(frame)
        freq_frame.pack(fill='x')
        
        ttk.Label(freq_frame, text="Manual:", style='Normal.TLabel').pack(side='left')
        
        self.widgets['freq_entry'] = ttk.Entry(freq_frame, width=15)
        self.widgets['freq_entry'].insert(0, str(self.state['frequency']))
        self.widgets['freq_entry'].pack(side='left', padx=10)
        
        ttk.Label(freq_frame, text="MHz", style='Normal.TLabel').pack(side='left')
        
        btn = ttk.Button(freq_frame, text="Aplicar", command=self._on_frequency_apply)
        btn.pack(side='right', padx=5)
        
        # Frecuencias preestablecidas
        preset_frame = ttk.Frame(frame)
        preset_frame.pack(pady=10)
        
        presets = [
            ("118.0", 118.0),
            ("121.5", 121.5),
            ("125.0", 125.0),
            ("1090.0 (ADS-B)", 1090.0)
        ]
        
        for label, freq in presets:
            btn = ttk.Button(preset_frame,
                            text=label,
                            command=lambda f=freq: self._set_frequency(f))
            btn.pack(side='left', padx=5)
    
    def _create_recording_section(self):
        """Crea sección de grabación"""
        frame = ttk.LabelFrame(self.root, text="  Grabación  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        
        self.widgets['record_btn'] = ttk.Button(btn_frame,
                                                text="🔴 Iniciar Grabación",
                                                command=self._toggle_recording,
                                                width=30)
        self.widgets['record_btn'].pack()
        
        self.widgets['record_status'] = ttk.Label(frame,
                                                   text="⚫ No grabando",
                                                   style='Normal.TLabel')
        self.widgets['record_status'].pack(pady=5)
    
    def _create_aircraft_simulation_section(self):
        """Crea sección de simulación de aviones"""
        frame = ttk.LabelFrame(self.root, text="  ✈️ Simulación de Aviones (ADS-B)  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # Info
        ttk.Label(frame,
                 text="Simula la detección de aviones cercanos",
                 style='Normal.TLabel').pack(pady=(0, 10))
        
        # Botones
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        
        ttk.Button(btn_frame,
                  text="➕ Simular Avión Comercial",
                  command=lambda: self._simulate_aircraft('commercial'),
                  width=25).pack(side='left', padx=5)
        
        ttk.Button(btn_frame,
                  text="➕ Simular Avión Privado",
                  command=lambda: self._simulate_aircraft('private'),
                  width=25).pack(side='left', padx=5)
        
        # Botón limpiar
        ttk.Button(frame,
                  text="🧹 Limpiar Aviones",
                  command=self._clear_aircraft,
                  width=52).pack(pady=5)
        
        # Lista de aviones
        self.widgets['aircraft_listbox'] = tk.Listbox(frame, height=4, font=('Courier', 9))
        self.widgets['aircraft_listbox'].pack(fill='x', pady=5)
        
        # Estado
        self.widgets['aircraft_status'] = ttk.Label(frame,
                                                    text="📡 0 aviones detectados",
                                                    style='Normal.TLabel')
        self.widgets['aircraft_status'].pack()
    
    def _create_mode_section(self):
        """Crea sección de modo"""
        frame = ttk.LabelFrame(self.root, text="  Modo de Operación  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        self.widgets['mode_var'] = tk.StringVar(value=self.state['mode'])
        
        modes = [
            ("📻 VHF AM (Aviación)", "VHF_AM"),
            ("✈️  ADS-B (1090 MHz)", "ADSB")
        ]
        
        for label, mode in modes:
            rb = ttk.Radiobutton(frame,
                                text=label,
                                variable=self.widgets['mode_var'],
                                value=mode,
                                command=self._on_mode_change)
            rb.pack(anchor='w', pady=2)
    
    def _create_status_section(self):
        """Crea sección de estado"""
        frame = ttk.LabelFrame(self.root, text="  Estado del Sistema  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # RSSI
        rssi_frame = ttk.Frame(frame)
        rssi_frame.pack(fill='x', pady=2)
        
        ttk.Label(rssi_frame, text="📊 RSSI:", style='Normal.TLabel').pack(side='left')
        self.widgets['rssi_label'] = ttk.Label(rssi_frame,
                                                text="0 dB",
                                                style='Value.TLabel')
        self.widgets['rssi_label'].pack(side='right')
        
        # Squelch Status
        sq_frame = ttk.Frame(frame)
        sq_frame.pack(fill='x', pady=2)
        
        ttk.Label(sq_frame, text="🎚️  Squelch:", style='Normal.TLabel').pack(side='left')
        self.widgets['squelch_status'] = ttk.Label(sq_frame,
                                                    text="⚫ Cerrado",
                                                    style='Value.TLabel')
        self.widgets['squelch_status'].pack(side='right')
        
        # Modo actual
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill='x', pady=2)
        
        ttk.Label(mode_frame, text="📡 Modo:", style='Normal.TLabel').pack(side='left')
        self.widgets['mode_status'] = ttk.Label(mode_frame,
                                                 text=self.state['mode'],
                                                 style='Value.TLabel')
        self.widgets['mode_status'].pack(side='right')
    
    def _create_buttons_section(self):
        """Crea botones de acción"""
        frame = ttk.Frame(self.root)
        frame.pack(padx=20, pady=20)
        
        btn_reset = ttk.Button(frame,
                               text="🔄 Resetear Valores",
                               command=self._reset_values,
                               width=20)
        btn_reset.pack(side='left', padx=5)
        
        btn_help = ttk.Button(frame,
                             text="❓ Ayuda",
                             command=self._show_help,
                             width=20)
        btn_help.pack(side='left', padx=5)
    
    def _on_volume_change(self, value):
        """Callback cambio de volumen"""
        vol = int(float(value))
        self.state['volume'] = vol
        self.widgets['volume_label'].config(text=f"{vol}%")
        
        if self.on_control_change:
            self.on_control_change('volume', vol)
    
    def _on_gain_change(self, value):
        """Callback cambio de ganancia"""
        gain = int(float(value))
        self.state['gain'] = gain
        self.widgets['gain_label'].config(text=f"{gain} dB")
        
        if self.on_control_change:
            self.on_control_change('gain', gain)
    
    def _on_squelch_change(self, value):
        """Callback cambio de squelch"""
        sq = int(float(value))
        self.state['squelch'] = sq
        self.widgets['squelch_label'].config(text=f"{sq}%")
        
        if self.on_control_change:
            self.on_control_change('squelch', sq)
    
    def _on_frequency_slider_change(self, value):
        """Callback cambio de frecuencia por slider"""
        freq = float(value)
        self.state['frequency'] = freq
        self.widgets['freq_label'].config(text=f"{freq:.3f} MHz")
        self.widgets['freq_entry'].delete(0, tk.END)
        self.widgets['freq_entry'].insert(0, f"{freq:.3f}")
        
        if self.on_control_change:
            freq_hz = int(freq * 1e6)
            self.on_control_change('frequency', freq_hz)
    
    def _on_frequency_apply(self):
        """Aplicar frecuencia ingresada"""
        try:
            freq = float(self.widgets['freq_entry'].get())
            self._set_frequency(freq)
        except ValueError:
            messagebox.showerror("Error", "Frecuencia inválida")
    
    def _set_frequency(self, freq_mhz: float):
        """Establecer frecuencia"""
        self.state['frequency'] = freq_mhz
        self.widgets['freq_entry'].delete(0, tk.END)
        self.widgets['freq_entry'].insert(0, str(freq_mhz))
        
        # Actualizar slider si está en rango VHF
        if 108.0 <= freq_mhz <= 137.0:
            self.widgets['freq_slider'].set(freq_mhz)
            self.widgets['freq_label'].config(text=f"{freq_mhz:.3f} MHz")
        
        if self.on_control_change:
            freq_hz = int(freq_mhz * 1e6)
            self.on_control_change('frequency', freq_hz)
        
        logger.info(f"✅ Frecuencia: {freq_mhz} MHz")
    
    def _toggle_recording(self):
        """Alternar grabación"""
        self.state['recording'] = not self.state['recording']
        
        if self.state['recording']:
            self.widgets['record_btn'].config(text="⏹️  Detener Grabación")
            self.widgets['record_status'].config(text="🔴 GRABANDO")
        else:
            self.widgets['record_btn'].config(text="🔴 Iniciar Grabación")
            self.widgets['record_status'].config(text="⚫ No grabando")
        
        if self.on_control_change:
            self.on_control_change('recording', self.state['recording'])
    
    def _on_mode_change(self):
        """Cambio de modo"""
        mode = self.widgets['mode_var'].get()
        self.state['mode'] = mode
        self.widgets['mode_status'].config(text=mode)
        
        if self.on_control_change:
            self.on_control_change('mode', mode)
        
        logger.info(f"✅ Modo: {mode}")
    
    def _simulate_aircraft(self, aircraft_type: str):
        """Simula la detección de un avión"""
        import random
        import time
        
        if aircraft_type == 'commercial':
            # Avión comercial
            callsigns = ['IBE3142', 'RYR8472', 'VLG2834', 'AEA1029', 'UAL455']
            aircraft = {
                'icao': f"{random.randint(100000, 999999):06X}",
                'callsign': random.choice(callsigns),
                'altitude': random.randint(25000, 40000),
                'speed': random.randint(400, 550),
                'heading': random.randint(0, 359),
                'latitude': 40.0 + random.uniform(-0.5, 0.5),
                'longitude': -3.5 + random.uniform(-0.5, 0.5),
                'timestamp': time.time()
            }
        else:
            # Avión privado
            aircraft = {
                'icao': f"{random.randint(100000, 999999):06X}",
                'callsign': f"N{random.randint(100, 999)}AB",
                'altitude': random.randint(5000, 15000),
                'speed': random.randint(120, 250),
                'heading': random.randint(0, 359),
                'latitude': 40.0 + random.uniform(-0.5, 0.5),
                'longitude': -3.5 + random.uniform(-0.5, 0.5),
                'timestamp': time.time()
            }
        
        # Agregar a la lista
        if 'aircraft_data' not in self.state:
            self.state['aircraft_data'] = []
        
        self.state['aircraft_data'].append(aircraft)
        
        # Actualizar UI
        self._update_aircraft_list()
        
        # Notificar al sistema
        if self.on_control_change:
            self.on_control_change('aircraft_detected', aircraft)
        
        logger.info(f"✈️ Avión simulado: {aircraft['callsign']} @ {aircraft['altitude']}ft")
    
    def _clear_aircraft(self):
        """Limpiar lista de aviones"""
        if 'aircraft_data' in self.state:
            count = len(self.state['aircraft_data'])
            self.state['aircraft_data'].clear()
            self._update_aircraft_list()
            logger.info(f"🧹 {count} aviones eliminados")
    
    def _update_aircraft_list(self):
        """Actualiza la lista de aviones en la UI"""
        aircraft_list = self.state.get('aircraft_data', [])
        
        # Limpiar listbox
        self.widgets['aircraft_listbox'].delete(0, tk.END)
        
        # Agregar aviones
        for ac in aircraft_list:
            line = f"{ac['callsign']:<10} ALT:{ac['altitude']:>6}ft SPD:{ac['speed']:>3}kt HDG:{ac['heading']:>3}°"
            self.widgets['aircraft_listbox'].insert(tk.END, line)
        
        # Actualizar estado
        count = len(aircraft_list)
        self.widgets['aircraft_status'].config(
            text=f"📡 {count} aviones detectados"
        )
    
    def _reset_values(self):
        """Resetea todos los valores a defaults"""
        self.widgets['volume_slider'].set(60)
        self.widgets['gain_slider'].set(25)
        self.widgets['squelch_slider'].set(10)
        self.widgets['freq_entry'].delete(0, tk.END)
        self.widgets['freq_entry'].insert(0, "125.0")
        self.widgets['mode_var'].set('VHF_AM')
        
        logger.info("🔄 Valores reseteados")
    
    def _show_help(self):
        """Muestra ayuda"""
        help_text = """
🎭 FlyM Simulator - Ayuda

CONTROLES:
• Volumen: 0-100% (ajusta volumen de audio)
• Ganancia: 0-50 dB (ganancia del receptor)
• Squelch: 0-100% (umbral de ruido)

FRECUENCIAS COMUNES:
• 118-137 MHz: Banda de aviación VHF
• 121.5 MHz: Emergencia
• 1090 MHz: ADS-B

MODOS:
• VHF AM: Comunicaciones de aviación
• ADS-B: Rastreo de aviones

GRABACIÓN:
• Graba audio recibido en formato WAV
• Archivos en carpeta recordings/

SIMULACIÓN:
• Todos los controles funcionan en tiempo real
• Genera señales sintéticas para pruebas
• Compatible con hardware real en Raspberry Pi
"""
        messagebox.showinfo("Ayuda - FlyM Simulator", help_text)
    
    def _schedule_update(self):
        """Programa actualización periódica de la interfaz"""
        if self.running and self.root:
            # Actualizar RSSI aleatorio para demo
            import random
            rssi = -80 + random.randint(0, 40)
            self.widgets['rssi_label'].config(text=f"{rssi} dB")
            
            # Actualizar squelch status
            if self.state['squelch'] < 30:
                self.widgets['squelch_status'].config(text="🟢 Abierto")
            else:
                self.widgets['squelch_status'].config(text="⚫ Cerrado")
            
            # Actualizar display OLED
            self._update_oled_display()
            
            # Reprogramar
            self.root.after(100, self._schedule_update)  # 10 FPS
    
    def _update_oled_display(self):
        """Actualiza el canvas con la imagen del display OLED"""
        try:
            if not self.display_controller:
                logger.debug("No hay display_controller vinculado")
                return
            
            # Obtener la imagen actual del display
            display = self.display_controller.display
            if not display or not hasattr(display, 'image'):
                logger.debug("Display no tiene atributo 'image'")
                return
            
            image = display.image
            if not image:
                logger.debug("Imagen del display es None")
                return
            
            # Convertir imagen PIL (1-bit) a formato que tkinter pueda usar
            # Escalar 4x para mejor visibilidad
            scale = 4
            scaled_width = image.width * scale
            scaled_height = image.height * scale
            
            # Crear imagen RGB para mostrar (amarillo sobre negro, estilo OLED)
            rgb_image = Image.new('RGB', (scaled_width, scaled_height), '#000000')
            pixels_src = image.load()
            pixels_dst = rgb_image.load()
            
            # Color amarillo/blanco para los píxeles encendidos (estilo OLED)
            oled_color = (255, 220, 0)  # Amarillo
            
            # Contar píxeles encendidos para debug
            pixels_on = 0
            for y in range(image.height):
                for x in range(image.width):
                    if pixels_src[x, y]:
                        pixels_on += 1
                        # Dibujar píxel escalado
                        for dy in range(scale):
                            for dx in range(scale):
                                pixels_dst[x * scale + dx, y * scale + dy] = oled_color
            
            if pixels_on > 0:
                logger.debug(f"📺 OLED actualizado: {pixels_on} píxeles encendidos")
            
            # Convertir a PhotoImage
            photo = ImageTk.PhotoImage(rgb_image)
            
            # Actualizar canvas
            canvas = self.widgets['oled_canvas']
            canvas.delete('all')
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            
            # Guardar referencia para evitar garbage collection
            canvas.image = photo
            
        except Exception as e:
            logger.error(f"Error actualizando OLED display: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_closing(self):
        """Maneja cierre de ventana"""
        if messagebox.askokcancel("Salir", "¿Cerrar el Control Panel?"):
            self.stop()
    
    def update_state(self, new_state: Dict[str, Any]):
        """Actualiza el estado desde fuera"""
        self.state.update(new_state)


# Singleton global
_gui_instance = None

def get_gui_controller(callback: Optional[Callable] = None) -> SimulatorGUI:
    """Obtiene instancia única del controlador GUI"""
    global _gui_instance
    if _gui_instance is None:
        _gui_instance = SimulatorGUI(on_control_change=callback)
    return _gui_instance
