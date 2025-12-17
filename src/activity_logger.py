"""
Activity Logger - Registro de actividad de transmisiones
Guarda log de todas las transmisiones detectadas
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ActivityLogger:
    """Registrador de actividad de transmisiones"""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_log_file = self.log_dir / f"activity_{datetime.now().strftime('%Y%m%d')}.json"
        self.session_log: List[Dict] = []
        self.current_transmission = None
        
        print(f"📝 Activity Logger iniciado: {self.current_log_file}")
    
    def start_transmission(self, frequency: float, rssi: float = 0):
        """Registrar inicio de transmisión"""
        self.current_transmission = {
            'start_time': datetime.now().isoformat(),
            'frequency': frequency,
            'frequency_mhz': frequency / 1e6,
            'rssi_start': rssi,
            'rssi_peak': rssi
        }
    
    def update_transmission(self, rssi: float):
        """Actualizar nivel de señal durante transmisión"""
        if self.current_transmission:
            if rssi > self.current_transmission.get('rssi_peak', -100):
                self.current_transmission['rssi_peak'] = rssi
    
    def end_transmission(self, rssi: float = 0):
        """Registrar fin de transmisión"""
        if self.current_transmission:
            self.current_transmission['end_time'] = datetime.now().isoformat()
            self.current_transmission['rssi_end'] = rssi
            
            # Calcular duración
            start = datetime.fromisoformat(self.current_transmission['start_time'])
            end = datetime.fromisoformat(self.current_transmission['end_time'])
            duration = (end - start).total_seconds()
            self.current_transmission['duration_seconds'] = round(duration, 2)
            
            # Guardar en sesión
            self.session_log.append(self.current_transmission.copy())
            
            # Guardar a archivo
            self._append_to_log_file(self.current_transmission)
            
            print(f"📝 Transmisión registrada: {self.current_transmission['frequency_mhz']:.3f} MHz, {duration:.1f}s")
            
            self.current_transmission = None
    
    def _append_to_log_file(self, entry: Dict):
        """Agregar entrada al archivo de log"""
        try:
            # Leer log existente
            if self.current_log_file.exists():
                with open(self.current_log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = {'date': datetime.now().strftime('%Y-%m-%d'), 'transmissions': []}
            
            # Agregar nueva entrada
            log_data['transmissions'].append(entry)
            
            # Guardar
            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error guardando log: {e}")
    
    def get_session_stats(self) -> Dict:
        """Obtener estadísticas de la sesión"""
        if not self.session_log:
            return {
                'total_transmissions': 0,
                'total_duration': 0,
                'frequencies': []
            }
        
        total_duration = sum(t.get('duration_seconds', 0) for t in self.session_log)
        frequencies = list(set(t['frequency_mhz'] for t in self.session_log))
        
        return {
            'total_transmissions': len(self.session_log),
            'total_duration': round(total_duration, 1),
            'frequencies': frequencies,
            'avg_duration': round(total_duration / len(self.session_log), 1) if self.session_log else 0
        }
    
    def get_recent_transmissions(self, count: int = 10) -> List[Dict]:
        """Obtener transmisiones recientes"""
        return self.session_log[-count:] if self.session_log else []
    
    def clear_session_log(self):
        """Limpiar log de sesión (no afecta archivo)"""
        self.session_log.clear()
        print("🗑️  Log de sesión limpiado")
