#!/usr/bin/env python3
"""
Decodificador ADS-B (Automatic Dependent Surveillance-Broadcast)
Decodifica mensajes Mode S de 1090 MHz para rastrear aviones
"""

import time
import logging
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ADSBDecoder:
    """Decodificador de mensajes ADS-B"""
    
    # Constantes de ADS-B
    PREAMBLE = [1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0]
    SHORT_MSG_BITS = 56
    LONG_MSG_BITS = 112
    
    def __init__(self, config):
        """
        Inicializar decodificador ADS-B
        
        Args:
            config: Configuración del decodificador
        """
        self.config = config
        
        # Base de datos de aviones detectados
        self.aircraft_db = {}
        
        # Configuración de decodificación
        self.threshold = config.get('threshold', 0.5)
        self.timeout = config.get('aircraft_timeout', 60)  # Segundos
        
        # Estadísticas
        self.stats = {
            'messages_received': 0,
            'messages_decoded': 0,
            'crc_errors': 0
        }
        
        print("✈️  Decodificador ADS-B inicializado")
    
    def decode(self, samples):
        """
        Decodificar mensajes ADS-B de muestras IQ
        
        Args:
            samples: Array de muestras IQ complejas
            
        Returns:
            Lista de mensajes decodificados
        """
        messages = []
        
        try:
            # Convertir a magnitud
            magnitude = np.abs(samples)
            
            # Detectar picos (posibles preámbulos)
            peaks = self._detect_peaks(magnitude)
            
            # Para cada pico, intentar decodificar mensaje
            for peak_idx in peaks:
                msg = self._decode_message(magnitude, peak_idx)
                if msg:
                    messages.append(msg)
                    self.stats['messages_decoded'] += 1
                    
                    # Actualizar base de datos de aviones
                    self._update_aircraft_db(msg)
            
            self.stats['messages_received'] += len(peaks)
            
        except Exception as e:
            logger.error(f"Error al decodificar ADS-B: {e}")
        
        return messages
    
    def _detect_peaks(self, magnitude):
        """
        Detectar picos en la señal (posibles preámbulos)
        
        Args:
            magnitude: Magnitud de la señal
            
        Returns:
            Lista de índices de picos
        """
        peaks = []
        
        # Umbral adaptativo
        threshold = np.mean(magnitude) + 3 * np.std(magnitude)
        
        # Buscar picos que superen el umbral
        for i in range(len(magnitude) - 16):
            if magnitude[i] > threshold:
                # Verificar si parece un preámbulo
                if self._check_preamble(magnitude[i:i+16]):
                    peaks.append(i)
        
        return peaks
    
    def _check_preamble(self, signal_segment):
        """
        Verificar si un segmento parece un preámbulo ADS-B
        
        Args:
            signal_segment: Segmento de señal
            
        Returns:
            True si parece un preámbulo
        """
        if len(signal_segment) < 16:
            return False
        
        # El preámbulo tiene un patrón específico de pulsos
        # Simplificación: verificar alternancia de picos
        avg = np.mean(signal_segment)
        
        high_positions = [0, 2, 7, 9]  # Posiciones con pulsos altos
        
        for pos in high_positions:
            if signal_segment[pos] < avg:
                return False
        
        return True
    
    def _decode_message(self, magnitude, start_idx):
        """
        Decodificar mensaje ADS-B
        
        Args:
            magnitude: Señal de magnitud
            start_idx: Índice de inicio del mensaje
            
        Returns:
            Diccionario con mensaje decodificado o None
        """
        # Saltar preámbulo (16 símbolos)
        data_start = start_idx + 16
        
        # Intentar decodificar mensaje corto (56 bits)
        bits = self._extract_bits(magnitude, data_start, self.SHORT_MSG_BITS)
        
        if bits is None:
            return None
        
        # Verificar CRC
        if not self._check_crc(bits):
            # Intentar mensaje largo (112 bits)
            bits = self._extract_bits(magnitude, data_start, self.LONG_MSG_BITS)
            if bits is None or not self._check_crc(bits):
                self.stats['crc_errors'] += 1
                return None
        
        # Decodificar contenido del mensaje
        message = self._parse_message(bits)
        
        return message
    
    def _extract_bits(self, magnitude, start_idx, num_bits):
        """
        Extraer bits de la señal
        
        Args:
            magnitude: Señal de magnitud
            start_idx: Índice de inicio
            num_bits: Número de bits a extraer
            
        Returns:
            Array de bits o None
        """
        if start_idx + num_bits * 2 > len(magnitude):
            return None
        
        bits = []
        
        # Cada bit está codificado en 2 símbolos (PPM - Pulse Position Modulation)
        for i in range(num_bits):
            idx = start_idx + i * 2
            
            if idx + 1 >= len(magnitude):
                return None
            
            # Comparar amplitud de los dos símbolos
            if magnitude[idx] > magnitude[idx + 1]:
                bits.append(1)
            else:
                bits.append(0)
        
        return np.array(bits, dtype=np.uint8)
    
    def _check_crc(self, bits):
        """
        Verificar CRC del mensaje
        
        Args:
            bits: Bits del mensaje
            
        Returns:
            True si CRC es válido
        """
        # Implementación simplificada
        # En producción, usar el polinomio generador correcto
        
        # Para mensajes de 56 bits, últimos 24 bits son CRC
        if len(bits) < 56:
            return False
        
        # Simplificación: aceptar si no todos son ceros o unos
        crc = bits[-24:]
        if np.all(crc == 0) or np.all(crc == 1):
            return False
        
        return True
    
    def _parse_message(self, bits):
        """
        Parsear mensaje ADS-B
        
        Args:
            bits: Bits del mensaje
            
        Returns:
            Diccionario con datos decodificados
        """
        # Convertir bits a bytes
        msg_bytes = self._bits_to_bytes(bits)
        
        # Tipo de mensaje (primeros 5 bits)
        df = (msg_bytes[0] >> 3) & 0x1F
        
        # ICAO address (24 bits)
        icao = ((msg_bytes[1] << 16) | (msg_bytes[2] << 8) | msg_bytes[3]) & 0xFFFFFF
        icao_hex = f"{icao:06X}"
        
        message = {
            'timestamp': datetime.now(),
            'df': df,
            'icao': icao_hex,
            'raw': msg_bytes
        }
        
        # Decodificar según tipo
        if df == 17:  # ADS-B mensaje extendido
            message.update(self._decode_adsb_extended(msg_bytes))
        elif df == 11:  # All-call reply
            message['type'] = 'all_call'
        elif df == 4 or df == 20:  # Altitude reply
            altitude = self._decode_altitude(msg_bytes)
            message['altitude'] = altitude
            message['type'] = 'altitude'
        
        return message
    
    def _decode_adsb_extended(self, msg_bytes):
        """
        Decodificar mensaje ADS-B extendido (DF=17)
        
        Args:
            msg_bytes: Bytes del mensaje
            
        Returns:
            Diccionario con datos decodificados
        """
        data = {}
        
        # Type code (bits 33-37)
        tc = (msg_bytes[4] >> 3) & 0x1F
        
        data['type_code'] = tc
        
        if 1 <= tc <= 4:
            # Identificación del avión (callsign)
            data['callsign'] = self._decode_callsign(msg_bytes[5:11])
            data['type'] = 'identification'
            
        elif 9 <= tc <= 18:
            # Posición en el aire
            pos_data = self._decode_airborne_position(msg_bytes)
            data.update(pos_data)
            data['type'] = 'position'
            
        elif tc == 19:
            # Velocidad
            vel_data = self._decode_velocity(msg_bytes)
            data.update(vel_data)
            data['type'] = 'velocity'
        
        return data
    
    def _decode_callsign(self, bytes_data):
        """
        Decodificar callsign del avión
        
        Args:
            bytes_data: 6 bytes con el callsign codificado
            
        Returns:
            String con el callsign
        """
        # Charset ADS-B
        charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890 "
        
        callsign = ""
        
        # Cada carácter está en 6 bits
        bits = []
        for byte in bytes_data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        
        for i in range(0, min(48, len(bits)), 6):
            char_code = 0
            for j in range(6):
                if i + j < len(bits):
                    char_code = (char_code << 1) | bits[i + j]
            
            if char_code < len(charset):
                callsign += charset[char_code]
        
        return callsign.strip()
    
    def _decode_airborne_position(self, msg_bytes):
        """
        Decodificar posición en el aire
        
        Args:
            msg_bytes: Bytes del mensaje
            
        Returns:
            Diccionario con latitud, longitud, altitud
        """
        # Extraer altitud (12 bits)
        altitude = self._decode_altitude(msg_bytes)
        
        # Extraer CPR (Compact Position Reporting)
        # Esto requiere dos mensajes consecutivos para calcular posición exacta
        # Implementación simplificada
        
        lat_cpr = ((msg_bytes[6] & 0x03) << 15) | (msg_bytes[7] << 7) | (msg_bytes[8] >> 1)
        lon_cpr = ((msg_bytes[8] & 0x01) << 16) | (msg_bytes[9] << 8) | msg_bytes[10]
        
        return {
            'altitude': altitude,
            'lat_cpr': lat_cpr,
            'lon_cpr': lon_cpr
        }
    
    def _decode_altitude(self, msg_bytes):
        """
        Decodificar altitud
        
        Args:
            msg_bytes: Bytes del mensaje
            
        Returns:
            Altitud en pies
        """
        # Altitud está en AC13 o AC12 format
        ac13 = ((msg_bytes[5] & 0xFF) << 4) | ((msg_bytes[6] & 0xF0) >> 4)
        
        # Remover bit Q
        q_bit = (ac13 >> 4) & 1
        
        if q_bit:
            # Formato de 25 pies
            n = ((ac13 & 0x0FE0) >> 1) | (ac13 & 0x000F)
            altitude = n * 25 - 1000
        else:
            # Formato Gillham (más complejo)
            altitude = 0  # Simplificado
        
        return altitude
    
    def _decode_velocity(self, msg_bytes):
        """
        Decodificar velocidad
        
        Args:
            msg_bytes: Bytes del mensaje
            
        Returns:
            Diccionario con velocidad y heading
        """
        subtype = (msg_bytes[4] >> 1) & 0x07
        
        if subtype == 1 or subtype == 2:
            # Ground speed
            ew_dir = (msg_bytes[5] >> 2) & 1
            ew_vel = ((msg_bytes[5] & 0x03) << 8) | msg_bytes[6]
            
            ns_dir = (msg_bytes[7] >> 7) & 1
            ns_vel = ((msg_bytes[7] & 0x7F) << 3) | (msg_bytes[8] >> 5)
            
            # Calcular velocidad y heading
            ew_vel = ew_vel - 1 if ew_vel > 0 else 0
            ns_vel = ns_vel - 1 if ns_vel > 0 else 0
            
            if ew_dir:
                ew_vel = -ew_vel
            if ns_dir:
                ns_vel = -ns_vel
            
            speed = np.sqrt(ew_vel**2 + ns_vel**2)
            heading = np.arctan2(ew_vel, ns_vel) * 180 / np.pi
            
            if heading < 0:
                heading += 360
            
            return {
                'speed': int(speed),
                'heading': int(heading)
            }
        
        return {}
    
    def _bits_to_bytes(self, bits):
        """
        Convertir array de bits a bytes
        
        Args:
            bits: Array de bits
            
        Returns:
            Array de bytes
        """
        bytes_array = []
        
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            bytes_array.append(byte)
        
        return bytes_array
    
    def _update_aircraft_db(self, message):
        """
        Actualizar base de datos de aviones
        
        Args:
            message: Mensaje decodificado
        """
        icao = message.get('icao')
        if not icao:
            return
        
        # Crear o actualizar entrada
        if icao not in self.aircraft_db:
            self.aircraft_db[icao] = {
                'icao': icao,
                'first_seen': message['timestamp'],
                'messages_count': 0
            }
        
        aircraft = self.aircraft_db[icao]
        aircraft['last_seen'] = message['timestamp']
        aircraft['messages_count'] += 1
        
        # Actualizar datos según tipo de mensaje
        if 'callsign' in message:
            aircraft['callsign'] = message['callsign']
        
        if 'altitude' in message:
            aircraft['altitude'] = message['altitude']
        
        if 'speed' in message:
            aircraft['speed'] = message['speed']
        
        if 'heading' in message:
            aircraft['heading'] = message['heading']
    
    def get_aircraft_list(self):
        """
        Obtener lista de aviones activos
        
        Returns:
            Lista de diccionarios con datos de aviones
        """
        now = datetime.now()
        active_aircraft = []
        
        # Limpiar aviones antiguos
        to_remove = []
        for icao, aircraft in self.aircraft_db.items():
            age = (now - aircraft['last_seen']).total_seconds()
            
            if age > self.timeout:
                to_remove.append(icao)
            else:
                active_aircraft.append(aircraft)
        
        # Remover aviones expirados
        for icao in to_remove:
            del self.aircraft_db[icao]
        
        # Ordenar por mensajes recibidos (más activos primero)
        active_aircraft.sort(key=lambda x: x['messages_count'], reverse=True)
        
        return active_aircraft
    
    def get_stats(self):
        """
        Obtener estadísticas del decodificador
        
        Returns:
            Diccionario con estadísticas
        """
        success_rate = 0
        if self.stats['messages_received'] > 0:
            success_rate = (self.stats['messages_decoded'] / 
                          self.stats['messages_received'] * 100)
        
        return {
            **self.stats,
            'success_rate': success_rate,
            'active_aircraft': len(self.aircraft_db)
        }
