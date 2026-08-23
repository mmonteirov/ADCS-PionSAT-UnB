"""
test_integration_system.py
==========================
Teste de integração de sistema ponta a ponta:
Simulador -> Receptor UDP -> Digital Twin Engine (4 Camadas) -> Telemetry Logger.
"""

import os
import queue
import socket
import tempfile
import time
import pytest

from scripts.simulate_esp32_transmitter import ESP32TelemetrySimulator
from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.telemetry.udp_receiver import UdpReceiver
from src.ground_station.telemetry.logger import TelemetryLogger
from src.twin.digital_twin_engine import DigitalTwinEngine


def test_full_pipeline_end_to_end():
    test_port = 59125
    pkt_queue: queue.Queue[TelemetryPacket] = queue.Queue()
    receiver = UdpReceiver(host="127.0.0.1", port=test_port, packet_queue=pkt_queue)
    assert receiver.start_listening() is True
    receiver.start()

    twin_engine = DigitalTwinEngine()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "test_integration.csv")
        logger = TelemetryLogger(log_dir=tmpdir)
        logger.start(custom_filename="test_integration.csv")

        # 1. Simula envio de 20 pacotes pelo transmissor ESP32
        sim = ESP32TelemetrySimulator(freq_hz=50.0)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for _ in range(20):
            packet = sim.step()
            raw = packet.pack()
            sock.sendto(raw, ("127.0.0.1", test_port))
            time.sleep(0.005)

        sock.close()
        time.sleep(0.15)
        receiver.stop()

        # 2. Processa pacotes pela fila
        processed_count = 0
        while not pkt_queue.empty():
            pkt = pkt_queue.get_nowait()
            divergence_metrics = twin_engine.process_packet(pkt)
            logger.log_packet(pkt, divergence_metrics=divergence_metrics)
            processed_count += 1

            assert "theta_err_deg" in divergence_metrics
            assert "rmse_theta_deg" in divergence_metrics
            assert "health_status" in divergence_metrics

        logger.stop()

        assert processed_count == 20
        assert os.path.exists(log_file)
        with open(log_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 21  # 1 cabeçalho + 20 linhas de dados
