"""
test_serial_parser.py
=====================
Testes unitarios para o receptor serial, maquina de estados de sincronismo e gravador CSV.
"""

import os
import queue
import time
import pytest

from src.ground_station.telemetry.packet_definitions import (
    PACKET_SIZE,
    TelemetryPacket,
)
from src.ground_station.telemetry.logger import TelemetryLogger


def test_parser_with_noise_and_framing():
    pkt1 = TelemetryPacket(seq_num=101, co2_ppm=450)
    pkt2 = TelemetryPacket(seq_num=102, co2_ppm=890)

    data1 = pkt1.pack()
    data2 = pkt2.pack()

    # Injeta lixo aleatorio antes, entre e depois dos pacotes
    garbage_prefix = b"\xFF\x00\x12\x34\x55\x11"
    garbage_middle = b"\xAA\x00\xEE\xDD"
    garbage_suffix = b"\x12\x34\x56"

    stream = garbage_prefix + data1 + garbage_middle + data2 + garbage_suffix

    # Simula a maquina de estados de recepcao do SerialReceiver
    parsed_packets = []
    raw_buffer = bytearray()

    for byte in stream:
        raw_buffer.append(byte)
        while len(raw_buffer) >= PACKET_SIZE:
            if raw_buffer[0] == 0x55 and raw_buffer[1] == 0xAA:
                packet_data = bytes(raw_buffer[:PACKET_SIZE])
                try:
                    p = TelemetryPacket.unpack(packet_data, verify_crc=True)
                    parsed_packets.append(p)
                    del raw_buffer[:PACKET_SIZE]
                except ValueError:
                    del raw_buffer[:1]
            else:
                del raw_buffer[:1]

    assert len(parsed_packets) == 2
    assert parsed_packets[0].seq_num == 101
    assert parsed_packets[0].co2_ppm == 450
    assert parsed_packets[1].seq_num == 102
    assert parsed_packets[1].co2_ppm == 890


def test_parsing_latency():
    pkt = TelemetryPacket(seq_num=1)
    data = pkt.pack()

    # Testa desempacotamento de 1000 pacotes consecutivos medindo tempo medio
    t0 = time.perf_counter()
    n_packets = 1000
    for _ in range(n_packets):
        _ = TelemetryPacket.unpack(data, verify_crc=True)
    t1 = time.perf_counter()

    avg_latency_ms = ((t1 - t0) / n_packets) * 1000.0
    print(f"\nLatencia media de desempacotamento: {avg_latency_ms:.4f} ms")
    assert avg_latency_ms < 2.0  # Requisito de saida da Fase 1: < 2.0 ms


def test_telemetry_logger(tmp_path):
    log_dir = str(tmp_path / "logs")
    logger = TelemetryLogger(log_dir=log_dir)

    filepath = logger.start(custom_filename="test_session.csv")
    assert os.path.exists(filepath)

    pkt1 = TelemetryPacket(seq_num=1, v_bat_mv=4200, i_bat_ma=150)
    pkt2 = TelemetryPacket(seq_num=2, v_bat_mv=4190, i_bat_ma=152)

    logger.log_packet(pkt1, divergence_metrics={"theta_err_deg": 0.12, "rmse_theta_deg": 0.10})
    logger.log_packet(pkt2, divergence_metrics={"theta_err_deg": 0.15, "rmse_theta_deg": 0.11})

    status = logger.get_status()
    assert status["is_logging"] is True
    assert status["packets_count"] == 2

    logger.stop()
    status_stopped = logger.get_status()
    assert status_stopped["is_logging"] is False

    # Valida linhas do arquivo
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 3  # Header + 2 rows
        assert "iso_timestamp" in lines[0]
        assert "4200" in lines[1]
        assert "4190" in lines[2]
