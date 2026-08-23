#!/usr/bin/env python3
"""
simulate_esp32_transmitter.py
=============================
Transmissor de simulacao de telemetria do nanossatelite PION Sat (ESP32).
Capaz de operar em dois modos de transmissao independentes:
  1. Modo USB Serial (--mode serial): Envia pacotes binarios de 76 bytes por porta serial fisica ou virtual.
  2. Modo Wi-Fi / UDP (--mode udp): Envia datagramas binarios UDP de 76 bytes para a rede local ou localhost.

Permite simular dinamica nominal e injecao de anomalias/falhas para validar o Gemeo Digital (DTiL).
"""

from __future__ import annotations

import argparse
import math
import random
import socket
import sys
import time
from typing import Optional

try:
    import serial
except ImportError:
    serial = None

from src.ground_station.telemetry.packet_definitions import TelemetryPacket


class ESP32TelemetrySimulator:
    """
    Simulador embarcado do ESP32 com modelo estocastico continuo e injecao de falhas.
    """

    def __init__(self, freq_hz: float = 20.0, fault_mode: Optional[str] = None) -> None:
        self.freq_hz = freq_hz
        self.dt = 1.0 / freq_hz
        self.fault_mode = fault_mode
        self.seq_num = 0
        self.start_time = time.time()

        # Estados dinamicos
        self.angle_z = 0.0
        self.angle_y = 0.0
        self.angle_x = 0.0
        self.omega_z = 0.08  # rad/s
        self.omega_y = 0.005
        self.omega_x = 0.008

        # Sensores ambientais e bateria
        self.co2_ppm = 425.0
        self.light_lux = 850.0
        self.humidity_raw = 4950.0
        self.pressure_pa = 101325.0
        self.v_bat_mv = 4185.0
        self.i_bat_ma = 160.0
        self.soc_percent = 97
        self.actuator_pwm = -45

    def step(self) -> TelemetryPacket:
        """Calcula o proximo estado e gera o pacote de telemetria correspondente."""
        self.seq_num = (self.seq_num + 1) & 0xFFFF
        elapsed_s = time.time() - self.start_time
        timestamp_ms = int(elapsed_s * 1000) & 0xFFFFFFFF

        # Injeção de anomalias programadas se configurado
        if self.fault_mode == "divergence_gyro":
            # Injeta velocidade angular anômala no giroscópio Z
            self.omega_z = 0.45 + 0.1 * math.sin(elapsed_s * 2.0)
        elif self.fault_mode == "sensor_noise":
            # Injeta ruído elevado nos sensores
            self.omega_z += random.gauss(0, 0.05)
            self.light_lux = random.uniform(200.0, 50000.0)
        else:
            # Dinâmica nominal suave
            self.omega_z += random.gauss(0, 0.0008)
            self.omega_y += random.gauss(0, 0.0004)
            self.omega_x += random.gauss(0, 0.0004)

        self.angle_z += self.omega_z * self.dt
        if self.angle_z > 2.0 * math.pi:
            self.angle_z -= 2.0 * math.pi
        elif self.angle_z < -2.0 * math.pi:
            self.angle_z += 2.0 * math.pi

        self.angle_y = 0.06 * math.sin(self.angle_z * 0.4)
        self.angle_x = 0.04 * math.cos(self.angle_z * 0.3)

        # Conversão Euler para Quatérnion
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

        # Campo magnético local (uT)
        mag_x = 14.5 * math.cos(self.angle_z) - 2.5 * math.sin(self.angle_z) + random.gauss(0, 0.15)
        mag_y = 14.5 * math.sin(self.angle_z) + 2.5 * math.cos(self.angle_z) + random.gauss(0, 0.15)
        mag_z = -19.5 + random.gauss(0, 0.10)

        # Sensores com passeio aleatório browniano
        if self.fault_mode != "sensor_noise":
            self.co2_ppm = max(400.0, min(550.0, self.co2_ppm + random.gauss(0, 0.2)))
            self.light_lux = max(700.0, min(1200.0, self.light_lux + random.gauss(0, 1.0)))
            self.humidity_raw = max(4500.0, min(5500.0, self.humidity_raw + random.gauss(0, 1.5)))
            self.pressure_pa = max(101250.0, min(101400.0, self.pressure_pa + random.gauss(0, 1.5)))

        # Bateria
        if self.seq_num % 100 == 0:
            self.v_bat_mv = max(3400.0, self.v_bat_mv - 0.05)
            self.soc_percent = max(0, min(100, int((self.v_bat_mv - 3400.0) / (4200.0 - 3400.0) * 100)))

        self.i_bat_ma = max(140.0, min(180.0, self.i_bat_ma + random.gauss(0, 0.3)))

        return TelemetryPacket(
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
            rel_pos_x=12,
            rel_pos_y=-6,
            rel_pos_z=0,
            co2_ppm=int(round(self.co2_ppm)),
            light_lux=int(round(self.light_lux)),
            humidity_raw=int(round(self.humidity_raw)),
            pressure_pa=float(self.pressure_pa),
            v_bat_mv=int(round(self.v_bat_mv)),
            i_bat_ma=int(round(self.i_bat_ma)),
            soc_percent=self.soc_percent,
            ekf_status=2,  # Convergido
            actuator_pwm=self.actuator_pwm,
            seq_num=self.seq_num,
            arrival_time_s=time.time(),
        )


def run_serial_simulation(port: str, baudrate: int, freq_hz: float, fault_mode: Optional[str]) -> None:
    """Executa a transmissão serial contínua."""
    if serial is None:
        print("Erro: pyserial não está instalado. Instale com 'pip install pyserial'.")
        sys.exit(1)

    print(f"[SIMULADOR ESP32] Iniciando transmissao SERIAL na porta {port} @ {baudrate} bps ({freq_hz:.1f} Hz)...")
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
    except Exception as e:
        print(f"Erro ao abrir porta serial {port}: {e}")
        sys.exit(1)

    sim = ESP32TelemetrySimulator(freq_hz=freq_hz, fault_mode=fault_mode)
    interval = 1.0 / freq_hz
    count = 0
    t_start = time.time()

    try:
        while True:
            t0 = time.time()
            packet = sim.step()
            raw_bytes = packet.pack()
            ser.write(raw_bytes)
            ser.flush()
            count += 1

            if count % int(freq_hz) == 0:
                elapsed = time.time() - t_start
                rate = count / max(1e-6, elapsed)
                r, p, y = packet.euler_angles_deg
                print(f"[SERIAL -> {port}] #{packet.seq_num:05d} | Taxa: {rate:.1f} Hz | Euler=[{r:+5.1f}°, {p:+5.1f}°, {y:+5.1f}°] | Lux={packet.light_lux} | Bat={packet.v_bat_v:.2f}V")

            dt_sleep = max(0.0, interval - (time.time() - t0))
            if dt_sleep > 0:
                time.sleep(dt_sleep)
    except KeyboardInterrupt:
        print("\n[SIMULADOR ESP32] Transmissao serial interrompida pelo usuario.")
    finally:
        ser.close()


def run_udp_simulation(ip: str, port: int, freq_hz: float, fault_mode: Optional[str]) -> None:
    """Executa a transmissão UDP / Wi-Fi contínua."""
    print(f"[SIMULADOR ESP32] Iniciando transmissao WI-FI / UDP para {ip}:{port} ({freq_hz:.1f} Hz)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if ip.endswith(".255"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    sim = ESP32TelemetrySimulator(freq_hz=freq_hz, fault_mode=fault_mode)
    interval = 1.0 / freq_hz
    count = 0
    t_start = time.time()

    try:
        while True:
            t0 = time.time()
            packet = sim.step()
            raw_bytes = packet.pack()
            sock.sendto(raw_bytes, (ip, port))
            count += 1

            if count % int(freq_hz) == 0:
                elapsed = time.time() - t_start
                rate = count / max(1e-6, elapsed)
                r, p, y = packet.euler_angles_deg
                print(f"[WI-FI/UDP -> {ip}:{port}] #{packet.seq_num:05d} | Taxa: {rate:.1f} Hz | Euler=[{r:+5.1f}°, {p:+5.1f}°, {y:+5.1f}°] | Lux={packet.light_lux} | Bat={packet.v_bat_v:.2f}V")

            dt_sleep = max(0.0, interval - (time.time() - t0))
            if dt_sleep > 0:
                time.sleep(dt_sleep)
    except KeyboardInterrupt:
        print("\n[SIMULADOR ESP32] Transmissao UDP interrompida pelo usuario.")
    finally:
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de Telemetria do ESP32 para o PION Sat (USB Serial e Wi-Fi / UDP)."
    )
    parser.add_argument(
        "--mode",
        choices=["serial", "udp"],
        default="udp",
        help="Modo de transmissao: 'serial' para USB Serial ou 'udp' para Wi-Fi/Rede (padrao: udp).",
    )
    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyUSB1",
        help="Porta serial para transmissao no modo serial (padrao: /dev/ttyUSB1).",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Baudrate para o modo serial (padrao: 115200).",
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="127.0.0.1",
        help="Endereco IP de destino para o modo UDP (padrao: 127.0.0.1).",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=5005,
        help="Porta UDP de destino (padrao: 5005).",
    )
    parser.add_argument(
        "--freq",
        type=float,
        default=20.0,
        help="Frequencia de transmissao em Hz (padrao: 20.0).",
    )
    parser.add_argument(
        "--fault",
        choices=["divergence_gyro", "sensor_noise"],
        default=None,
        help="Injeta falha/anomalia programada para teste do Gêmeo Digital.",
    )

    args = parser.parse_args()

    if args.mode == "serial":
        run_serial_simulation(port=args.port, baudrate=args.baud, freq_hz=args.freq, fault_mode=args.fault)
    else:
        run_udp_simulation(ip=args.ip, port=args.udp_port, freq_hz=args.freq, fault_mode=args.fault)


if __name__ == "__main__":
    main()
