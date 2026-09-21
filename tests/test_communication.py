"""
test_communication.py
=====================
Testes unitários e de robustez para a camada de comunicação (Receptor UDP, Serial e Sockets).
"""

import queue
import socket
import threading
import time
import pytest

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.telemetry.udp_receiver import UdpReceiver
from src.ground_station.telemetry.mock_sender import MockTelemetryGenerator


def test_udp_receiver_end_to_end():
    # Cria fila de pacotes e inicializa receptor UDP na porta local de teste
    test_port = 59123
    pkt_queue: queue.Queue[TelemetryPacket] = queue.Queue()
    receiver = UdpReceiver(host="127.0.0.1", port=test_port, packet_queue=pkt_queue)

    assert receiver.start_listening() is True
    receiver.start()

    time.sleep(0.05)

    # Cria gerador e envia 5 pacotes UDP
    generator = MockTelemetryGenerator()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sent_count = 5
    for _ in range(sent_count):
        pkt = generator.generate_next_packet()
        raw = pkt.pack()
        sock.sendto(raw, ("127.0.0.1", test_port))
        time.sleep(0.01)

    sock.close()
    time.sleep(0.1)

    # Para o receptor
    receiver.stop()

    # Verifica pacotes recebidos na fila
    received = []
    while not pkt_queue.empty():
        received.append(pkt_queue.get_nowait())

    assert len(received) == sent_count
    assert received[0].header == 0xAA55
    assert received[0].packet_id == 0x01


def test_udp_receiver_invalid_packets_rejection():
    test_port = 59124
    pkt_queue: queue.Queue[TelemetryPacket] = queue.Queue()
    receiver = UdpReceiver(host="127.0.0.1", port=test_port, packet_queue=pkt_queue)
    receiver.start_listening()
    receiver.start()

    time.sleep(0.05)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Envia lixo binário / pacote corrompido
    sock.sendto(b"INVALID_DATA_NOT_76_BYTES", ("127.0.0.1", test_port))
    # Envia pacote de 76 bytes com CRC inválido
    corrupted = bytearray([0x55, 0xAA] + [0x00] * 74)
    sock.sendto(bytes(corrupted), ("127.0.0.1", test_port))

    sock.close()
    time.sleep(0.1)
    receiver.stop()

    # Nenhum pacote inválido deve ter entrado na fila
    assert pkt_queue.empty()
    stats = receiver.get_stats()
    assert stats["crc_errors"] >= 1


def test_mock_magnetic_vector_is_fixed_in_lab_frame():
    """A emulacao deve girar o satelite, nao o campo magnetico da sala."""
    generator = MockTelemetryGenerator(freq_hz=20.0)

    for _ in range(200):
        pkt = generator.generate_next_packet()
        qw, qx, qy, qz = pkt.q_w, pkt.q_x, pkt.q_y, pkt.q_z

        r00 = 1.0 - 2.0 * (qy * qy + qz * qz)
        r01 = 2.0 * (qx * qy - qz * qw)
        r02 = 2.0 * (qx * qz + qy * qw)
        r10 = 2.0 * (qx * qy + qz * qw)
        r11 = 1.0 - 2.0 * (qx * qx + qz * qz)
        r12 = 2.0 * (qy * qz - qx * qw)
        r20 = 2.0 * (qx * qz - qy * qw)
        r21 = 2.0 * (qy * qz + qx * qw)
        r22 = 1.0 - 2.0 * (qx * qx + qy * qy)

        b_lab = (
            r00 * pkt.mag_x + r01 * pkt.mag_y + r02 * pkt.mag_z,
            r10 * pkt.mag_x + r11 * pkt.mag_y + r12 * pkt.mag_z,
            r20 * pkt.mag_x + r21 * pkt.mag_y + r22 * pkt.mag_z,
        )
        assert b_lab == pytest.approx((14.5, -2.5, -19.5), abs=1e-5)
