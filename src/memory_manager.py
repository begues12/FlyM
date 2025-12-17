"""
Memory Manager - Gestión de frecuencias favoritas
Guarda y recupera frecuencias memorizadas con nombres
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """Gestor de memorias de frecuencias"""
    
    def __init__(self, memory_file: str = 'config/memories.json'):
        self.memory_file = Path(memory_file)
        self.memories: Dict[int, Dict] = {}
        self.max_memories = 10
        self.current_memory = 0
        
        self._load_memories()
    
    def _load_memories(self):
        """Cargar memorias desde archivo"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = {int(k): v for k, v in data.items()}
                print(f"✅ {len(self.memories)} memorias cargadas")
            else:
                # Cargar memorias por defecto
                self._load_default_memories()
        except Exception as e:
            logger.error(f"Error cargando memorias: {e}")
            self._load_default_memories()
    
    def _load_default_memories(self):
        """Cargar frecuencias comunes de aviación"""
        self.memories = {
            1: {'name': 'Torre Madrid', 'frequency': 118.1e6, 'mode': 'VHF_AM'},
            2: {'name': 'Torre Barcelona', 'frequency': 118.3e6, 'mode': 'VHF_AM'},
            3: {'name': 'Torre Sevilla', 'frequency': 118.05e6, 'mode': 'VHF_AM'},
            4: {'name': 'Torre Valencia', 'frequency': 118.5e6, 'mode': 'VHF_AM'},
            5: {'name': 'Emergencia', 'frequency': 121.5e6, 'mode': 'VHF_AM'},
            6: {'name': 'ATIS Madrid', 'frequency': 127.8e6, 'mode': 'VHF_AM'},
            7: {'name': 'ADS-B', 'frequency': 1090.0e6, 'mode': 'ADSB'},
            8: {'name': 'Ground Madrid', 'frequency': 121.7e6, 'mode': 'VHF_AM'},
        }
        self._save_memories()
        print("📻 Memorias por defecto cargadas")
    
    def _save_memories(self):
        """Guardar memorias a archivo"""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
            logger.debug("💾 Memorias guardadas")
        except Exception as e:
            logger.error(f"Error guardando memorias: {e}")
    
    def save_memory(self, slot: int, name: str, frequency: float, mode: str = 'VHF_AM'):
        """Guardar frecuencia en memoria"""
        if 1 <= slot <= self.max_memories:
            self.memories[slot] = {
                'name': name,
                'frequency': frequency,
                'mode': mode
            }
            self._save_memories()
            print(f"💾 Memoria {slot} guardada: {name} ({frequency/1e6:.3f} MHz)")
            return True
        return False
    
    def recall_memory(self, slot: int) -> Optional[Dict]:
        """Recuperar frecuencia de memoria"""
        memory = self.memories.get(slot)
        if memory:
            self.current_memory = slot
            print(f"📻 Memoria {slot} recuperada: {memory['name']}")
        return memory
    
    def delete_memory(self, slot: int) -> bool:
        """Eliminar memoria"""
        if slot in self.memories:
            del self.memories[slot]
            self._save_memories()
            print(f"🗑️  Memoria {slot} eliminada")
            return True
        return False
    
    def get_memory(self, slot: int) -> Optional[Dict]:
        """Obtener memoria sin cambiar current"""
        return self.memories.get(slot)
    
    def get_all_memories(self) -> Dict[int, Dict]:
        """Obtener todas las memorias"""
        return self.memories
    
    def get_next_empty_slot(self) -> Optional[int]:
        """Encontrar siguiente slot vacío"""
        for i in range(1, self.max_memories + 1):
            if i not in self.memories:
                return i
        return None
    
    def get_memory_list(self) -> List[str]:
        """Obtener lista de memorias para display"""
        result = []
        for i in range(1, self.max_memories + 1):
            if i in self.memories:
                mem = self.memories[i]
                freq_mhz = mem['frequency'] / 1e6
                result.append(f"{i}: {mem['name'][:12]} {freq_mhz:.3f}")
            else:
                result.append(f"{i}: ---")
        return result
