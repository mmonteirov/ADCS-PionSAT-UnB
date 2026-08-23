"""
packet_definitions.py
=====================
Definicao do protocolo binario de telemetria (ICD) de 76 bytes (little-endian)
para comunicacao em tempo real com o nanossatelite PION Sat.

Especificacao: docs/specs/digital_twin_spec.md (Secao 3)
Header de sincronismo: 0xAA55 (2 bytes)
Tamanho do pacote: 76 bytes
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import struct
from typing import Any, Tuple


HEADER_SYNC: int = 0xAA55
STRUCT_FORMAT: str = "<HBB I 4f 3f 3f 3h HHH f HhBB h H H"
PACKET_SIZE: int = struct.calcsize(STRUCT_FORMAT)  # 76 bytes

assert PACKET_SIZE == 76, f"STRUCT_SIZE invalido: esperado 76 bytes, obtido {PACKET_SIZE}"


# Tabela pre-calculada de CRC-16-CCITT (poly 0x1021) para deserializacao ultra-rapida (< 0.02 ms)
CRC16_TABLE: list[int] = []
for i in range(256):
    curr = i << 8
    for _ in range(8):
        if curr & 0x8000:
            curr = ((curr << 1) ^ 0x1021) & 0xFFFF
        else:
            curr = (curr << 1) & 0xFFFF
    CRC16_TABLE.append(curr)


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    """
    Calcula o checksum CRC-16-CCITT usando tabela lookup pre-computada.
    """
    crc = init
    table = CRC16_TABLE
    for byte in data:
        crc = ((crc << 8) ^ table[((crc >> 8) ^ byte) & 0xFF]) & 0xFFFF
    return crc


@dataclass
class TelemetryPacket:
    """
    Representacao em alto nivel de um pacote de telemetria recebido do PION Sat.

    Unidades:
    - timestamp_ms: milissegundos desde o boot
    - q_w, q_x, q_y, q_z: quaterion de atitude (adimensional, norma 1.0)
    - gyro_x, gyro_y, gyro_z: velocidade angular (rad/s)
    - mag_x, mag_y, mag_z: campo magnetico calibrado (microTesla)
    - rel_pos_x, rel_pos_y, rel_pos_z: posicao relativa (mm)
    - co2_ppm: concentracao de CO2 (ppm)
    - light_lux: intensidade luminosa (Lux)
    - humidity_raw: umidade escalonada (0..10000 -> 0.00..100.00 %)
    - pressure_pa: pressao absoluta (Pa)
    - v_bat_mv: tensao de bateria (mV)
    - i_bat_ma: corrente de carga/descarga (mA)
    - soc_percent: estado de carga da bateria (0..100 %)
    - ekf_status: status do filtro (0: Init, 1: Divergente, 2: Convergido)
    - actuator_pwm: comando de atuacao (-1000 a +1000)
    - seq_num: numero sequencial do pacote
    - checksum: CRC-16-CCITT dos bytes 0..73
    """

    header: int = HEADER_SYNC
    packet_id: int = 0x01
    sys_mode: int = 1
    timestamp_ms: int = 0

    # Atitude
    q_w: float = 1.0
    q_x: float = 0.0
    q_y: float = 0.0
    q_z: float = 0.0

    # Giroscopio (rad/s)
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0

    # Magnetometro (uT)
    mag_x: float = 0.0
    mag_y: float = 0.0
    mag_z: float = 0.0

    # Posicao Relativa (mm)
    rel_pos_x: int = 0
    rel_pos_y: int = 0
    rel_pos_z: int = 0

    # Sensores de Housekeeping / Ambiente
    co2_ppm: int = 400
    light_lux: int = 500
    humidity_raw: int = 5000  # 50.00%
    pressure_pa: float = 101325.0

    # Bateria
    v_bat_mv: int = 4200
    i_bat_ma: int = 150
    soc_percent: int = 95

    # ADCS & Atuacao
    ekf_status: int = 2
    actuator_pwm: int = 0
    seq_num: int = 0
    checksum: int = 0

    # Timestamp de recepcao no solo (segundos epoch float)
    arrival_time_s: float = 0.0

    @property
    def humidity_pct(self) -> float:
        """Retorna a umidade relativa em porcentagem (% RH)."""
        return self.humidity_raw / 100.0

    @property
    def pressure_hpa(self) -> float:
        """Retorna a pressao em hectopascais (hPa)."""
        return self.pressure_pa / 100.0

    @property
    def v_bat_v(self) -> float:
        """Retorna a tensao de bateria em Volts (V)."""
        return self.v_bat_mv / 1000.0

    @property
    def p_bat_mw(self) -> float:
        """Retorna a potencia instantanea da bateria em miliWatts (mW)."""
        return (self.v_bat_mv * self.i_bat_ma) / 1000.0

    @property
    def q_norm(self) -> float:
        """Norma euclidiana do quaterion de atitude."""
        return math.sqrt(self.q_w**2 + self.q_x**2 + self.q_y**2 + self.q_z**2)

    @property
    def gyro_norm(self) -> float:
        """Magnitude da velocidade angular total (rad/s)."""
        return math.sqrt(self.gyro_x**2 + self.gyro_y**2 + self.gyro_z**2)

    @property
    def mag_norm(self) -> float:
        """Magnitude do campo magnetico medido (uT)."""
        return math.sqrt(self.mag_x**2 + self.mag_y**2 + self.mag_z**2)

    @property
    def euler_angles_deg(self) -> Tuple[float, float, float]:
        """
        Converte o quaterion (q_w, q_x, q_y, q_z) em angulos de Euler (Roll, Pitch, Yaw) em graus.
        Sequencia intrinseca Z-Y-X (Yaw-Pitch-Roll standard aerospace).
        """
        w, x, y, z = self.q_w, self.q_x, self.q_y, self.q_z
        norm = math.sqrt(w * w + x * x + y * y + z * z)
        if norm > 1e-12:
            w /= norm
            x /= norm
            y /= norm
            z /= norm

        # Roll (phi em torno do eixo X)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        # Pitch (theta em torno do eixo Y)
        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1.0:
            pitch = math.copysign(math.pi / 2.0, sinp)
        else:
            pitch = math.asin(sinp)

        # Yaw (psi em torno do eixo Z)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))

    def pack(self) -> bytes:
        """
        Serializa a dataclass no formato binario exato de 76 bytes com CRC-16.
        """
        payload_no_crc = struct.pack(
            "<HBB I 4f 3f 3f 3h HHH f HhBB h H",
            self.header,
            self.packet_id,
            self.sys_mode,
            self.timestamp_ms,
            self.q_w,
            self.q_x,
            self.q_y,
            self.q_z,
            self.gyro_x,
            self.gyro_y,
            self.gyro_z,
            self.mag_x,
            self.mag_y,
            self.mag_z,
            int(self.rel_pos_x),
            int(self.rel_pos_y),
            int(self.rel_pos_z),
            int(self.co2_ppm),
            int(self.light_lux),
            int(self.humidity_raw),
            float(self.pressure_pa),
            int(self.v_bat_mv),
            int(self.i_bat_ma),
            int(self.soc_percent),
            int(self.ekf_status),
            int(self.actuator_pwm),
            int(self.seq_num),
        )
        calculated_crc = crc16_ccitt(payload_no_crc)
        return payload_no_crc + struct.pack("<H", calculated_crc)

    @classmethod
    def unpack(cls, raw_bytes: bytes, arrival_time: float = 0.0, verify_crc: bool = True) -> TelemetryPacket:
        """
        Deserializa um buffer de 76 bytes em uma instancia de TelemetryPacket.

        Parameters
        ----------
        raw_bytes : bytes
            Buffer de 76 bytes.
        arrival_time : float
            Timestamp do momento da recepcao no host.
        verify_crc : bool
            Se True, levanta ValueError caso o CRC-16 seja invalido.

        Returns
        -------
        TelemetryPacket
        """
        if len(raw_bytes) != PACKET_SIZE:
            raise ValueError(
                f"Tamanho de pacote incorreto: esperado {PACKET_SIZE} bytes, recebido {len(raw_bytes)}"
            )

        fields = struct.unpack(STRUCT_FORMAT, raw_bytes)
        header = fields[0]
        if header != HEADER_SYNC:
            raise ValueError(f"Header de sincronismo invalido: 0x{header:04X} != 0x{HEADER_SYNC:04X}")

        received_crc = fields[-1]
        if verify_crc:
            calc_crc = crc16_ccitt(raw_bytes[:74])
            if calc_crc != received_crc:
                raise ValueError(
                    f"Erro de CRC-16: calculado 0x{calc_crc:04X}, recebido 0x{received_crc:04X}"
                )

        return cls(
            header=fields[0],
            packet_id=fields[1],
            sys_mode=fields[2],
            timestamp_ms=fields[3],
            q_w=fields[4],
            q_x=fields[5],
            q_y=fields[6],
            q_z=fields[7],
            gyro_x=fields[8],
            gyro_y=fields[9],
            gyro_z=fields[10],
            mag_x=fields[11],
            mag_y=fields[12],
            mag_z=fields[13],
            rel_pos_x=fields[14],
            rel_pos_y=fields[15],
            rel_pos_z=fields[16],
            co2_ppm=fields[17],
            light_lux=fields[18],
            humidity_raw=fields[19],
            pressure_pa=fields[20],
            v_bat_mv=fields[21],
            i_bat_ma=fields[22],
            soc_percent=fields[23],
            ekf_status=fields[24],
            actuator_pwm=fields[25],
            seq_num=fields[26],
            checksum=fields[27],
            arrival_time_s=arrival_time,
        )

    def to_dict(self) -> dict[str, Any]:
        """Exporta os campos para dicionario serializavel."""
        d = asdict(self)
        d["humidity_pct"] = self.humidity_pct
        d["pressure_hpa"] = self.pressure_hpa
        d["v_bat_v"] = self.v_bat_v
        d["p_bat_mw"] = self.p_bat_mw
        roll, pitch, yaw = self.euler_angles_deg
        d["euler_roll_deg"] = roll
        d["euler_pitch_deg"] = pitch
        d["euler_yaw_deg"] = yaw
        return d
