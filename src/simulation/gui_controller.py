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
            'volume': 50,
            'gain': 30,
            'autoscan': 0,  # 0=OFF, 1=ON
            'frequency': 125.0e6,  # Hz
            'recording': False,
            'mode': 'VHF_AM',
            'rssi': 0,
            'current_menu': 'frequency',  # Menú activo
            'memory': 1,  # Slot de memoria actual (0=no guardar, 1-10)
            'vox': 0,  # 0=OFF, 1=ON
            'submenu_open': False,  # Submenú abierto
            'submenu_option': 0,  # Opción seleccionada (0-3)
            'eq_auto': 0  # Ecualizador automático 0=OFF, 1=ON
        }
        
        # Menús disponibles
        self.menus = ['frequency', 'autoscan', 'gain', 'volume', 'memory', 'vox']
        self.menu_index = 0
        
        # Sistema de mantener presionado con aceleración exponencial
        self.button_held = None  # '+' o '-' cuando está presionado
        self.hold_timer = None  # Timer ID de tkinter
        self.hold_delay = 500  # ms inicial (empieza lento)
        self.hold_count = 0  # Contador para calcular aceleración
        
        # Widgets
        self.widgets = {}
    
    def start(self):
        """Inicia la interfaz gráfica en un thread separado"""
        self.running = True
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()
        print("🎮 Interfaz gráfica iniciada")
    
    def set_display_controller(self, display_controller):
        """Establece referencia al display controller para actualizar OLED"""
        self.display_controller = display_controller
        print("🖥️ Display controller vinculado a GUI")
    
    def stop(self):
        """Detiene la interfaz gráfica"""
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
        print("🎮 Interfaz gráfica detenida")
    
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
        """Crea sección de botones de control"""
        frame = ttk.LabelFrame(self.root, text="  🎛️ Controles (Botones)  ", padding=15)
        frame.pack(padx=20, pady=10, fill='x')
        
        # Indicador de menú activo
        menu_frame = ttk.Frame(frame)
        menu_frame.pack(fill='x', pady=(0, 15))
        
    
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Botones de control
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        # Botón MENÚ con detección de HOLD
        menu_btn = tk.Button(btn_frame,
                             text="📋 MENÚ",
                             width=15,
                             font=('Arial', 10),
                             relief=tk.RAISED,
                             borderwidth=2)
        menu_btn.bind('<ButtonPress-1>', lambda e: self._on_menu_button_press())
        menu_btn.bind('<ButtonRelease-1>', lambda e: self._on_menu_button_release())
        menu_btn.pack(side='left', padx=10)
        self.widgets['menu_btn'] = menu_btn
        
        # Timer para detectar hold en botón MENU
        self.menu_hold_timer = None
        self.menu_press_time = None
        
        
        # Botón + con eventos de mantener
        plus_btn = tk.Button(btn_frame,
                            text="➕ +",
                            width=10,
                            font=('Arial', 12),
                            relief=tk.RAISED,
                            borderwidth=2)
        plus_btn.bind('<ButtonPress-1>', lambda e: self._on_button_press('+'))
        plus_btn.bind('<ButtonRelease-1>', lambda e: self._on_button_release())
        plus_btn.pack(side='left', padx=10)
        self.widgets['plus_btn'] = plus_btn
        
        # Botón - con eventos de mantener
        minus_btn = tk.Button(btn_frame,
                             text="➖ -",
                             width=10,
                             font=('Arial', 12),
                             relief=tk.RAISED,
                             borderwidth=2)
        minus_btn.bind('<ButtonPress-1>', lambda e: self._on_button_press('-'))
        minus_btn.bind('<ButtonRelease-1>', lambda e: self._on_button_release())
        minus_btn.pack(side='left', padx=10)
        self.widgets['minus_btn'] = minus_btn
        
        # Valores actuales (mostrar info en tabla de 2 columnas)
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        
        values_frame = ttk.Frame(frame)
        values_frame.pack(fill='x')
        
        # Grid de valores en formato tabla 3x2
        labels = [
            ("Frecuencia:", "frequency_val", f"{self.state['frequency']/1e6:.3f} MHz"),
            ("Auto-Scan:", "autoscan_val", "OFF"),
            ("Ganancia:", "gain_val", f"{self.state['gain']} dB"),
            ("Volumen:", "volume_val", f"{self.state['volume']}%"),
            ("Memoria:", "memory_val", "M1"),
            ("VOX:", "vox_val", "OFF")
        ]
        
        # Organizar en 2 columnas
        for row_idx in range(3):
            row_frame = ttk.Frame(values_frame)
            row_frame.pack(fill='x', pady=2)
            
            # Columna izquierda
            left_idx = row_idx
            if left_idx < len(labels):
                label_text, key, value = labels[left_idx]
                ttk.Label(row_frame, text=label_text, style='Normal.TLabel', width=11).pack(side='left')
                self.widgets[key] = ttk.Label(row_frame, text=value, style='Value.TLabel', width=14)
                self.widgets[key].pack(side='left')
            
            # Columna derecha
            right_idx = row_idx + 3
            if right_idx < len(labels):
                label_text, key, value = labels[right_idx]
                ttk.Label(row_frame, text=label_text, style='Normal.TLabel', width=11).pack(side='left', padx=(20, 0))
                self.widgets[key] = ttk.Label(row_frame, text=value, style='Value.TLabel', width=14)
                self.widgets[key].pack(side='left')

    
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
        
        # Auto-Scan Status
        scan_frame = ttk.Frame(frame)
        scan_frame.pack(fill='x', pady=2)
        
        ttk.Label(scan_frame, text="🔄 Auto-Scan:", style='Normal.TLabel').pack(side='left')
        self.widgets['autoscan_status'] = ttk.Label(scan_frame,
                                                    text="⚫ OFF",
                                                    style='Value.TLabel')
        self.widgets['autoscan_status'].pack(side='right')
        
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
    
    def _on_menu_button_press(self):
        """Callback cuando se presiona botón MENÚ"""
        import time
        self.menu_press_time = time.time()
        
        # Programar detección de HOLD (1 segundo)
        self.menu_hold_timer = self.root.after(1000, self._on_menu_hold_detected)
    
    def _on_menu_button_release(self):
        """Callback cuando se suelta botón MENÚ"""
        import time
        if self.menu_press_time is None:
            return
        
        # Cancelar timer de HOLD si existe
        if self.menu_hold_timer:
            self.root.after_cancel(self.menu_hold_timer)
            self.menu_hold_timer = None
        
        hold_duration = time.time() - self.menu_press_time
        self.menu_press_time = None
        
        # Si fue un click rápido (menos de 1 segundo)
        if hold_duration < 1.0:
            self._on_menu_click()
    
    def _on_menu_hold_detected(self):
        """HOLD detectado en botón MENÚ - abrir submenú"""
        if self.on_control_change:
            self.on_control_change('submenu_toggle', None)
        
        self.menu_hold_timer = None
    
    def _on_menu_click(self):
        """Click normal en botón MENÚ - cambiar menú o confirmar en submenú"""
        if self.on_control_change:
            self.on_control_change('menu_click', None)
    
    def _on_button_press(self, button_type):
        """Callback cuando se presiona botón + o -"""
        self.button_held = button_type
        self.hold_count = 0
        self.hold_delay = 500
        
        # Ejecutar primer cambio inmediatamente
        if button_type == '+':
            self._on_plus_button()
        else:
            self._on_minus_button()
        
        # En el submenú, NO iniciar timer de repetición automática
        if not self.state.get('submenu_open', False):
            self._schedule_button_repeat()
    
    def _on_button_release(self):
        """Callback cuando se suelta el botón"""
        self.button_held = None
        if self.hold_timer:
            self.root.after_cancel(self.hold_timer)
            self.hold_timer = None
        self.hold_count = 0
    
    def _schedule_button_repeat(self):
        """Programa la siguiente repetición del botón con aceleración progresiva"""
        if self.button_held is None:
            return
        
        # Incrementar contador y calcular nuevo delay con aceleración progresiva
        self.hold_count += 1
        
        # Aceleración progresiva:
        # - Inicio: 400ms (lento para control preciso)
        # - Medio: 200ms (acelera)
        # - Rápido: 100ms (más rápido)
        # - Máximo: 50ms (muy rápido para cambios grandes)
        if self.hold_count < 3:
            self.hold_delay = 400  # Lento al inicio: 2.5/seg
        elif self.hold_count < 6:
            self.hold_delay = 200  # Medio: 5/seg
        elif self.hold_count < 10:
            self.hold_delay = 100  # Rápido: 10/seg
        else:
            self.hold_delay = 50   # Muy rápido: 20/seg
        
        # Ejecutar el cambio
        if self.button_held == '+':
            self._on_plus_button()
        else:
            self._on_minus_button()
        
        # Programar siguiente repetición
        self.hold_timer = self.root.after(self.hold_delay, self._schedule_button_repeat)
    
    def _on_plus_button(self):
        """Callback botón + - incrementar valor actual o cambiar valor en submenú"""
        # Si el submenú está abierto, cambiar valor
        if self.state.get('submenu_open', False):
            if self.on_control_change:
                self.on_control_change('submenu_change_value', 1)
            return
        
        menu = self.state['current_menu']
        
        # Pasos e increments
        steps = {
            'frequency': 25000,  # 25 kHz en Hz
            'autoscan': 1,  # Toggle ON/OFF
            'gain': 2,
            'volume': 1,  # Incrementos de 1
            'memory': 1,  # Cambiar slots
            'vox': 1  # Toggle ON/OFF
        }
        
        # Rangos
        ranges = {
            'frequency': (108.0e6, 137.0e6),
            'autoscan': (0, 1),
            'gain': (0, 50),
            'volume': (0, 100),
            'memory': (1, 10),  # 10 slots
            'vox': (0, 1)
        }
        
        current = self.state[menu]
        step = steps[menu]
        min_val, max_val = ranges[menu]
        
        # Multiplicador de step para frecuencia (acelera aún más en hold largo)
        if menu == 'frequency':
            if self.hold_count < 5:
                multiplier = 1  # 25 kHz
            elif self.hold_count < 10:
                multiplier = 4  # 100 kHz
            else:
                multiplier = 10  # 250 kHz - máximo
            step = step * multiplier
        
        # Incrementar
        new_value = min(current + step, max_val)
        
        # Solo actualizar si cambió
        if new_value != current:
            self.state[menu] = new_value
            
            # Actualizar display
            self._update_menu_value_display()
            self._update_all_value_labels()
            
            # Notificar
            if self.on_control_change:
                self.on_control_change(menu, new_value)
            
            # Log solo si no es repetición rápida
            if self.hold_count < 3:
                print(f"➕ {menu}: {new_value}")
    
    def _on_save_memory(self):
        """Callback para guardar memoria actual (simula hold del botón menu)"""
        if self.state['current_menu'] == 'memory':
            memory_slot = self.state['memory']
            print(f"💾 Guardando frecuencia actual en memoria M{memory_slot}")
    
    def _on_minus_button(self):
        """Callback botón - - decrementar valor actual o cambiar valor en submenú"""
        # Si el submenú está abierto, cambiar valor
        if self.state.get('submenu_open', False):
            if self.on_control_change:
                self.on_control_change('submenu_change_value', -1)
            return
        
        menu = self.state['current_menu']
        
        # Pasos
        steps = {
            'frequency': 25000,  # 25 kHz en Hz
            'autoscan': 1,  # Toggle ON/OFF
            'gain': 2,
            'volume': 1,  # Incrementos de 1
            'memory': 1,
            'vox': 1
        }
        
        # Rangos
        ranges = {
            'frequency': (108.0e6, 137.0e6),
            'autoscan': (0, 1),
            'gain': (0, 50),
            'volume': (0, 100),
            'memory': (1, 10),
            'vox': (0, 1)
        }
        
        current = self.state[menu]
        step = steps[menu]
        min_val, max_val = ranges[menu]
        
        # Multiplicador de step para frecuencia (acelera aún más en hold largo)
        if menu == 'frequency':
            if self.hold_count < 5:
                multiplier = 1  # 25 kHz
            elif self.hold_count < 10:
                multiplier = 4  # 100 kHz
            else:
                multiplier = 10  # 250 kHz - máximo
            step = step * multiplier
        
        # Decrementar
        new_value = max(current - step, min_val)
        
        # Solo actualizar si cambió
        if new_value != current:
            self.state[menu] = new_value
            
            # Actualizar display
            self._update_menu_value_display()
            self._update_all_value_labels()
            
            # Notificar
            if self.on_control_change:
                self.on_control_change(menu, new_value)
            
            # Log solo si no es repetición rápida
            if self.hold_count < 3:
                print(f"➖ {menu}: {new_value}")
    
    def _update_menu_value_display(self):
        """Actualizar el display del valor del menú activo"""
        menu = self.state['current_menu']
        value = self.state[menu]
        
        # Formatear según tipo
        if menu == 'frequency':
            text = f"{value/1e6:.3f} MHz"
        elif menu in ['autoscan', 'vox']:
            text = "ON" if value == 1 else "OFF"
        elif menu == 'gain':
            text = f"{value} dB"
        elif menu == 'memory':
            text = f"M{int(value)}"
        else:
            text = f"{value}%"
            
    def _update_all_value_labels(self):
        """Actualizar todos los labels de valores"""
        self.widgets['frequency_val'].config(text=f"{self.state['frequency']/1e6:.3f} MHz")
        autoscan_text = "ON" if self.state['autoscan'] == 1 else "OFF"
        self.widgets['autoscan_val'].config(text=autoscan_text)
        self.widgets['gain_val'].config(text=f"{self.state['gain']} dB")
        self.widgets['volume_val'].config(text=f"{self.state['volume']}%")
        self.widgets['memory_val'].config(text=f"M{int(self.state['memory'])}")
        vox_text = "ON" if self.state['vox'] == 1 else "OFF"
        self.widgets['vox_val'].config(text=vox_text)
    
    def update_state(self, key, value):
        """Actualizar estado desde el sistema principal"""
        if key in self.state:
            self.state[key] = value
            self._update_all_value_labels()
    
    def _on_volume_change(self, value):
        """DEPRECATED - Ya no se usa slider de volumen"""
        pass
    
    def _on_gain_change(self, value):
        """DEPRECATED - Ya no se usa slider de ganancia"""
        pass
    
    def _on_squelch_change(self, value):
        """DEPRECATED - Ya no se usa slider de squelch"""
        pass
    
    def _on_frequency_slider_change(self, value):
        """DEPRECATED - Ya no se usa slider de frecuencia"""
        pass
    
    def _on_frequency_apply(self):
        """DEPRECATED - Ya no se usa entrada manual de frecuencia"""
        pass
    
    def _set_frequency(self, freq_mhz: float):
        """DEPRECATED - Ya no se usa entrada manual de frecuencia"""
        pass
    
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
        
        print(f"✅ Modo: {mode}")
    
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
        
        print(f"✈️ Avión simulado: {aircraft['callsign']} @ {aircraft['altitude']}ft")
    
    def _clear_aircraft(self):
        """Limpiar lista de aviones"""
        if 'aircraft_data' in self.state:
            count = len(self.state['aircraft_data'])
            self.state['aircraft_data'].clear()
            self._update_aircraft_list()
            print(f"🧹 {count} aviones eliminados")
    
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
        # Resetear menú a frequency
        self.menu_index = 0
        self.state['current_menu'] = 'frequency'
        
        # Resetear valores
        self.state['frequency'] = 125.0e6
        self.state['volume'] = 50
        self.state['gain'] = 30
        self.state['autoscan'] = 0
        
        self._update_menu_value_display()
        self._update_all_value_labels()
        
        print("🔄 Valores reseteados")
    
    def _show_help(self):
        """Muestra ayuda"""
        help_text = """
🎭 FlyM Simulator - Ayuda

CONTROLES:
• Menú: Cambia entre pantallas
• +/-: Ajusta el valor del menú activo

MENÚS:
• Frecuencia: 108-137 MHz (pasos 25 kHz)
• Auto-Scan: ON/OFF (búsqueda automática)
• Ganancia: 0-50 dB (filtro de ruido)
• Volumen: 0-100%

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
            
            # Actualizar autoscan status
            if self.state['autoscan'] == 1:
                self.widgets['autoscan_status'].config(text="🔄 ON")
            else:
                self.widgets['autoscan_status'].config(text="⚫ OFF")
            
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
    



# Singleton global
_gui_instance = None

def get_gui_controller(callback: Optional[Callable] = None) -> SimulatorGUI:
    """Obtiene instancia única del controlador GUI"""
    global _gui_instance
    if _gui_instance is None:
        _gui_instance = SimulatorGUI(on_control_change=callback)
    else:
        # Actualizar callback si se proporciona uno nuevo
        if callback is not None:
            print(f"🔄 Actualizando callback de GUI con nuevo callback")
            _gui_instance.on_control_change = callback
    return _gui_instance
