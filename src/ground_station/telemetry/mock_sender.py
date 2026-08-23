"""
mock_sender.py
==============
Emulador de telemetria do nanossatelite PION Sat para testes de bancada e homologacao da Ground Station.
Gera dinamica fisica realista de atitude (quaterion normalizado, gyro, B-field) e sensores ambientais
com variacoes continuas estocasticas (sem dentes de serra artificiais).
"""

from __future__ import annotations

import argparse
import math
import random
import socket
import time
from typing import Optional

from src.ground_station.telemetry.packet_definitions import TelemetryPacket


class MockTelemetryGenerator:
    """
    Gerador de telemetria fisica realista com processos estocasticos contínuos.
    """

    def __init__(self, freq_hz: float = 20.0) -> None:
        self.freq_hz = freq_hz
        self.dt = 1.0 / freq_hz
        self.seq_num = 0
        self.start_time = time.time()

        # Estado rotacional
        self.angle_z = 0.0
        self.angle_y = 0.0
        self.angle_x = 0.0
        self.omega_z = 0.08  # rad/s (~4.6 deg/s)
        self.omega_y = 0.005
        self.omega_x = 0.008

        # Housekeeping continuo
        self.v_bat_mv = 4185.0
        self.i_bat_ma = 162.0
        self.soc_percent = 97
        self.co2_ppm = 428.0
        self.light_lux = 850.0
        self.humidity_raw = 4920.0  # 49.20%
        self.pressure_pa = 101325.0

        # Posicao relativa na bancada (mm)
        self.rel_x = 12
        self.rel_y = -6
        self.rel_z = 0

    def generate_next_packet(self) -> TelemetryPacket:
        """Gera o proximo pacote simulado com incremento temporal dt e variacao suave."""
        self.seq_num = (self.seq_num + 1) & 0xFFFF
        elapsed_s = time.time() - self.start_time
        timestamp_ms = int(elapsed_s * 1000) & 0xFFFFFFFF

        # Integracao suave de atitude
        self.omega_z += (random.gauss(0, 0.001))
        self.omega_y += (random.gauss(0, 0.0005))
        self.omega_x += (random.gauss(0, 0.0005))

        self.angle_z += self.omega_z * self.dt
        self.angle_y = 0.06 * math.sin(self.angle_z * 0.4)
        self.angle_x = 0.04 * math.cos(self.angle_z * 0.3)

        # Conversao Euler para Quaterion (Z-Y-X)
        cz = math.cos(self.angle_z * 0.5)
        sz = math.sin(self.angle_z * 0.5)
        cy = math.cos(self.angle_y * 0.5)
        sy = math.sin(self.angle_y * 0.5)
        cx = math.cos(self.angle_x * 0.5)
        sx = math.sin(self.angle_x * 0.5)

        qw = cx * cy * cz + sx * sy * sz
        qx = sx * cy * cz - cx * sy * sz
        qy = cx * sy * cz + sx * cy * sz
        qz = cx * cy * sz - sx * sy * cz

        q_norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
        if q_norm > 1e-6:
            qw /= q_norm
            qx /= q_norm
            qy /= q_norm
            qz /= q_norm

        # Campo magnetico em Body Frame (uT)
        mag_x = 14.5 * math.cos(self.angle_z) - 2.5 * math.sin(self.angle_z) + random.gauss(0, 0.15)
        mag_y = 14.5 * math.sin(self.angle_z) + 2.5 * math.cos(self.angle_z) + random.gauss(0, 0.15)
        mag_z = -19.5 + random.gauss(0, 0.10)

        # Variacoes estocasticas continuas (Random walk suave)
        self.co2_ppm = max(400.0, min(500.0, self.co2_ppm + random.gauss(0, 0.2)))
        self.light_lux = max(800.0, min(950.0, self.light_lux + random.gauss(0, 1.0)))
        self.humidity_raw = max(4500.0, min(5500.0, self.humidity_raw + random.gauss(0, 1.5)))
        self.pressure_pa = max(101250.0, min(101400.0, self.pressure_pa + random.gauss(0, 1.5)))

        # Bateria decaindo suavemente
        if self.seq_num % 100 == 0:
            self.v_bat_mv = max(3500.0, self.v_bat_mv - 0.05)
            self.soc_percent = max(0, min(100, int((self.v_bat_mv - 3400.0) / (4200.0 - 3400.0) * 100)))

        self.i_bat_ma = max(150.0, min(175.0, self.i_bat_ma + random.gauss(0, 0.3)))

        packet = TelemetryPacket(
            header=0xAA55,
            packet_id=0x01,
            sys_mode=1,  # B-Dot
            timestamp_ms=timestamp_ms,
            q_w=qw,
            q_x=qx,
            q_y=qy,
            q_z=qz,
            gyro_x=self.omega_x + random.gauss(0, 0.0015),
            gyro_y=self.omega_y + random.gauss(0, 0.0015),
            gyro_z=self.omega_z + random.gauss(0, 0.0020),
            mag_x=mag_x,
            mag_y=mag_y,
            mag_z=mag_z,
            rel_pos_x=self.rel_x,
            rel_pos_y=self.rel_y,
            rel_pos_z=self.rel_z,
            co2_ppm=int(round(self.co2_ppm)),
            light_lux=int(round(self.light_lux)),
            humidity_raw=int(round(self.humidity_raw)),
            pressure_pa=float(self.pressure_pa),
            v_bat_mv=int(round(self.v_bat_mv)),
            i_bat_ma=int(round(self.i_bat_ma)),
            soc_percent=self.soc_percent,
            ekf_status=2,  # Convergido
            actuator_pwm=-45,
            seq_num=self.seq_num,
            arrival_time_s=time.time(),
        )

        return packet
