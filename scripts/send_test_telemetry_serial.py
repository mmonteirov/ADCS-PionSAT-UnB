"""
send_test_telemetry_serial.py
=============================
Utilitario para transmissao de telemetria de teste pela porta serial USB.
Util para simular o transmissor do satelite em outra porta serial ou adaptador USB-UART.

Exemplo de uso:
    python scripts/send_test_telemetry_serial.py --port /dev/ttyUSB1 --baud 115200 --freq 20
"""

from __future__ import annotations

import argparse
import time
import serial
import serial.tools.list_ports

from src.ground_station.telemetry.mock_sender import MockTelemetryGenerator


def main():
    parser = argparse.ArgumentParser(description="Transmissor Serial de Teste para PION Sat")
    parser.add_argument("--port", type=str, required=True, help="Porta serial de transmissao (ex: /dev/ttyUSB1, COM4)")
    parser.add_argument("--baud", type=int, default=115200, help="Taxa de transmissao serial (bps)")
    parser.add_argument("--freq", type=float, default=20.0, help="Frequencia de envio em Hz")
    args = parser.parse_args()

    print(f"Abrindo porta serial {args.port} a {args.baud} bps...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except Exception as e:
        print(f"Erro ao abrir porta serial {args.port}: {e}")
        return

    generator = MockTelemetryGenerator(freq_hz=args.freq)
    interval = 1.0 / args.freq
    print(f"Transmitindo pacotes binarios de 76 bytes a {args.freq} Hz... (Ctrl+C para parar)")

    count = 0
    try:
        while True:
            t0 = time.time()
            pkt = generator.generate_next_packet()
            data = pkt.pack()
            ser.write(data)
            ser.flush()
            count += 1

            if count % int(args.freq) == 0:
                print(f"[{count:05d} pacotes enviados] Q=[{pkt.q_w:.3f},{pkt.q_x:.3f},{pkt.q_y:.3f},{pkt.q_z:.3f}] | CO2={pkt.co2_ppm}ppm | Bat={pkt.v_bat_v:.2f}V")

            elapsed = time.time() - t0
            time.sleep(max(0.0, interval - elapsed))

    except KeyboardInterrupt:
        print("\nTransmissao finalizada pelo usuario.")
    finally:
        ser.close()
        print("Porta serial fechada.")


if __name__ == "__main__":
    main()
