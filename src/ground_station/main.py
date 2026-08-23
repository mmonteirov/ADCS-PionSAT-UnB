"""
main.py
=======
Ponto de Entrada Unificado da Ground Station & Gemeo Digital (PION Sat - UnB).

Exemplos de uso:
    # Conexao direta com satelite fisico conectado a porta USB:
    python src/ground_station/main.py --port /dev/ttyUSB0 --baud 115200

    # Modo emulacao / mock (testes sem hardware):
    python src/ground_station/main.py --mock --mock-freq 20

    # Modo headless (apenas ingestao e gravacao CSV sem interface grafica):
    python src/ground_station/main.py --port /dev/ttyUSB0 --headless
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time

# Garante que a raiz do projeto esteja no sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.app import GroundStationMainWindow
from src.ground_station.telemetry.mock_sender import MockTelemetryGenerator
from src.ground_station.telemetry.serial_receiver import SerialReceiver
from src.ground_station.telemetry.logger import TelemetryLogger
from src.twin.digital_twin_engine import DigitalTwinEngine


def setup_logging(level: int = logging.INFO) -> None:
    """Configura formato de logs padrao no console."""
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_mock_feeder(window: GroundStationMainWindow, freq_hz: float = 20.0) -> None:
    """Thread auxiliar que injeta pacotes simulados diretamente na fila da GUI."""
    generator = MockTelemetryGenerator(freq_hz=freq_hz)
    interval = 1.0 / freq_hz
    logging.info(f"Gerador de telemetria mock iniciado a {freq_hz} Hz...")

    def feeder_loop():
        while True:
            t0 = time.time()
            packet = generator.generate_next_packet()
            try:
                window.packet_queue.put_nowait(packet)
            except Exception:
                pass
            elapsed = time.time() - t0
            time.sleep(max(0.0, interval - elapsed))

    th = threading.Thread(target=feeder_loop, daemon=True, name="MockFeederThread")
    th.start()


def run_headless(port: str, baudrate: int, log_dir: str) -> None:
    """Executa a ingestao serial e gravacao CSV em modo console (sem GUI)."""
    logging.info(f"Iniciando Ground Station em modo HEADLESS na porta {port} ({baudrate} bps)...")
    logger = TelemetryLogger(log_dir=log_dir)
    twin = DigitalTwinEngine()
    receiver = SerialReceiver(port=port, baudrate=baudrate)

    if not receiver.connect():
        logging.error(f"Nao foi possivel conectar a porta {port}. Encerrando.")
        sys.exit(1)

    receiver.start()
    filepath = logger.start()
    logging.info(f"Sessao de telemetria aberta em: {filepath}")
    logging.info("Pressione Ctrl+C para encerrar a sessao.")

    try:
        while True:
            try:
                pkt = receiver.packet_queue.get(timeout=1.0)
                metrics = twin.process_packet(pkt)
                logger.log_packet(pkt, divergence_metrics=metrics)

                roll, pitch, yaw = pkt.euler_angles_deg
                theta_err = metrics.get("theta_err_deg", 0.0)
                rmse = metrics.get("rmse_theta_deg", 0.0)

                sys.stdout.write(
                    f"\r[PKT #{pkt.seq_num:05d}] Euler=[R:{roll:+6.2f} P:{pitch:+6.2f} Y:{yaw:+6.2f}] | "
                    f"CO2={pkt.co2_ppm:4d}ppm | Lux={pkt.light_lux:5d} | "
                    f"Vbat={pkt.v_bat_v:.2f}V ({pkt.soc_percent:3d}%) | "
                    f"Err={theta_err:5.2f}deg RMSE={rmse:5.2f}deg [{metrics['health_status']}]"
                )
                sys.stdout.flush()

            except Exception:
                pass
    except KeyboardInterrupt:
        print("\nFinalizando modo headless...")
    finally:
        receiver.disconnect()
        logger.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="PION Sat — Ground Station & Digital Twin")
    parser.add_argument("--port", type=str, default=None, help="Porta serial USB (ex: /dev/ttyUSB0, COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Taxa de transmissao serial (bps)")
    parser.add_argument("--mock", action="store_true", help="Ativar gerador de telemetria mock")
    parser.add_argument("--mock-freq", type=float, default=20.0, help="Frequencia do mock em Hz")
    parser.add_argument("--log-dir", type=str, default="logs", help="Diretorio para gravacao dos logs CSV")
    parser.add_argument("--headless", action="store_true", help="Executar em modo headless (sem interface grafica)")
    parser.add_argument("--debug", action="store_true", help="Ativar saida de debug")

    args = parser.parse_args()
    setup_logging(logging.DEBUG if args.debug else logging.INFO)

    # Modo Headless
    if args.headless:
        if not args.port:
            logging.error("O modo headless requer a definicao da porta serial via --port.")
            sys.exit(1)
        run_headless(port=args.port, baudrate=args.baud, log_dir=args.log_dir)
        return

    # Modo GUI (PyQt6)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("PionSat Ground Station")

    window = GroundStationMainWindow(
        port=args.port,
        baudrate=args.baud,
        enable_mock=args.mock,
    )

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
