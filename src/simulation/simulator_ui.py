"""
Interfaz de usuario para el simulador
Permite controlar el sistema desde la consola
"""

import threading
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SimulatorUI:
    """
    Interfaz de usuario del simulador
    Permite interactuar con los controles simulados
    """
    
    def __init__(self, on_control_change: Optional[Callable] = None):
        self.on_control_change = on_control_change
        self.running = False
        self.thread = None
        
        # Estado de controles
        self.controls = {
            'volume': 60,
            'gain': 25,
            'squelch': 10,
            'recording': False
        }
    
    def start(self):
        """Inicia la UI del simulador"""
        self.running = True
        self.thread = threading.Thread(target=self._ui_loop, daemon=True)
        self.thread.start()
        print("🎮 Simulador UI iniciado")
        self._print_help()
    
    def stop(self):
        """Detiene la UI del simulador"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("🎮 Simulador UI detenido")
    
    def _ui_loop(self):
        """Loop principal de la UI"""
        while self.running:
            try:
                time.sleep(0.1)  # Pequeña pausa
            except KeyboardInterrupt:
                break
    
    def _print_help(self):
        """Imprime ayuda de comandos"""
        print("\n" + "="*60)
        print("🎭 MODO SIMULACIÓN - Comandos disponibles:")
        print("="*60)
        print("  v [0-100]  - Ajustar volumen (ej: v 75)")
        print("  g [0-50]   - Ajustar ganancia (ej: g 30)")
        print("  s [0-100]  - Ajustar squelch (ej: s 15)")
        print("  r          - Toggle grabación")
        print("  f [MHz]    - Cambiar frecuencia (ej: f 125.5)")
        print("  h          - Mostrar esta ayuda")
        print("  q          - Salir")
        print("="*60)
        print("Estado inicial:")
        self._print_status()
        print()
    
    def _print_status(self):
        """Imprime estado actual"""
        print(f"  📻 Volumen: {self.controls['volume']}%")
        print(f"  📡 Ganancia: {self.controls['gain']} dB")
        print(f"  🔇 Squelch: {self.controls['squelch']}%")
        print(f"  🔴 Grabando: {'SÍ' if self.controls['recording'] else 'NO'}")
    
    def handle_command(self, command: str):
        """
        Procesa comando del usuario
        Llamar desde el código principal si se lee stdin
        """
        parts = command.strip().lower().split()
        
        if not parts:
            return
        
        cmd = parts[0]
        
        try:
            if cmd == 'v' and len(parts) > 1:
                # Volumen
                value = int(parts[1])
                value = max(0, min(100, value))
                self.controls['volume'] = value
                if self.on_control_change:
                    self.on_control_change('volume', value)
                print(f"✅ Volumen: {value}%")
            
            elif cmd == 'g' and len(parts) > 1:
                # Ganancia
                value = int(parts[1])
                value = max(0, min(50, value))
                self.controls['gain'] = value
                if self.on_control_change:
                    self.on_control_change('gain', value)
                print(f"✅ Ganancia: {value} dB")
            
            elif cmd == 's' and len(parts) > 1:
                # Squelch
                value = int(parts[1])
                value = max(0, min(100, value))
                self.controls['squelch'] = value
                if self.on_control_change:
                    self.on_control_change('squelch', value)
                print(f"✅ Squelch: {value}%")
            
            elif cmd == 'r':
                # Toggle grabación
                self.controls['recording'] = not self.controls['recording']
                if self.on_control_change:
                    self.on_control_change('recording', self.controls['recording'])
                print(f"✅ Grabación: {'INICIADA' if self.controls['recording'] else 'DETENIDA'}")
            
            elif cmd == 'f' and len(parts) > 1:
                # Frecuencia
                freq_mhz = float(parts[1])
                freq_hz = int(freq_mhz * 1e6)
                if self.on_control_change:
                    self.on_control_change('frequency', freq_hz)
                print(f"✅ Frecuencia: {freq_mhz} MHz")
            
            elif cmd == 'h':
                # Ayuda
                self._print_help()
            
            elif cmd == 'q':
                # Salir
                print("👋 Saliendo del simulador...")
                self.running = False
            
            else:
                print(f"❌ Comando desconocido: {cmd}")
                print("   Escribe 'h' para ver ayuda")
        
        except ValueError as e:
            print(f"❌ Valor inválido: {e}")
        except Exception as e:
            logger.error(f"Error procesando comando: {e}")


# Función helper para testing interactivo
def run_interactive_simulator(callback: Optional[Callable] = None):
    """
    Ejecuta simulador en modo interactivo
    Útil para desarrollo y debugging
    """
    ui = SimulatorUI(on_control_change=callback)
    ui.start()
    
    print("\n💡 Ingresa comandos (escribe 'h' para ayuda):\n")
    
    try:
        while ui.running:
            try:
                command = input("🎮 > ")
                ui.handle_command(command)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n")
                break
    finally:
        ui.stop()


if __name__ == "__main__":
    # Test del simulador
    def test_callback(control_type, value):
        print(f"[CALLBACK] {control_type} = {value}")
    
    run_interactive_simulator(test_callback)
