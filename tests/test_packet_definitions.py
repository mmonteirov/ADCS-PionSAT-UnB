"""
test_packet_definitions.py
==========================
Testes unitarios para validacao do protocolo binario de telemetria (ICD de 76 bytes).
"""

import struct
import pytest
from src.ground_station.telemetry.packet_definitions import (
    HEADER_SYNC,
    PACKET_SIZE,
    TelemetryPacket,
    crc16_ccitt,
)


def test_packet_size_and_constants():
    assert PACKET_SIZE == 76
    assert HEADER_SYNC == 0xAA55


def test_crc16_calculation():
    test_data = b"123456789"
    crc = crc16_ccitt(test_data)
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF
    # CRC de dados identicos deve ser deterministico
    assert crc16_ccitt(test_data) == crc


def test_pack_and_unpack_roundtrip():
    original = TelemetryPacket(
        header=HEADER_SYNC,
        packet_id=0x01,
        sys_mode=2,
        timestamp_ms=123456,
        q_w=0.7071068,
        q_x=0.0,
        q_y=0.7071068,
        q_z=0.0,
        gyro_x=0.0123,
        gyro_y=-0.0456,
        gyro_z=0.0789,
        mag_x=12.34,
        mag_y=-5.67,
        mag_z=28.91,
        rel_pos_x=15,
        rel_pos_y=-8,
        rel_pos_z=2,
        co2_ppm=650,
        light_lux=1200,
        humidity_raw=5540,
        pressure_pa=101325.5,
        v_bat_mv=4150,
        i_bat_ma=-120,
        soc_percent=92,
        ekf_status=2,
        actuator_pwm=250,
        seq_num=42,
    )

    packed = original.pack()
    assert len(packed) == 76

    unpacked = TelemetryPacket.unpack(packed, arrival_time=100.0, verify_crc=True)
    assert unpacked.header == HEADER_SYNC
    assert unpacked.packet_id == 0x01
    assert unpacked.sys_mode == 2
    assert unpacked.timestamp_ms == 123456
    assert pytest.approx(unpacked.q_w, rel=1e-5) == original.q_w
    assert pytest.approx(unpacked.q_y, rel=1e-5) == original.q_y
    assert pytest.approx(unpacked.gyro_z, rel=1e-5) == original.gyro_z
    assert pytest.approx(unpacked.mag_z, rel=1e-2) == original.mag_z
    assert unpacked.rel_pos_x == 15
    assert unpacked.co2_ppm == 650
    assert unpacked.light_lux == 1200
    assert pytest.approx(unpacked.humidity_pct, rel=1e-3) == 55.40
    assert pytest.approx(unpacked.pressure_hpa, rel=1e-3) == 1013.255
    assert pytest.approx(unpacked.v_bat_v, rel=1e-3) == 4.150
    assert pytest.approx(unpacked.p_bat_mw, rel=1e-3) == -498.0
    assert unpacked.soc_percent == 92
    assert unpacked.ekf_status == 2
    assert unpacked.actuator_pwm == 250
    assert unpacked.seq_num == 42


def test_invalid_header_raises_error():
    pkt = TelemetryPacket()
    raw = bytearray(pkt.pack())
    # Altera header
    raw[0] = 0x00
    with pytest.raises(ValueError, match="Header de sincronismo invalido"):
        TelemetryPacket.unpack(bytes(raw), verify_crc=True)


def test_invalid_crc_raises_error():
    pkt = TelemetryPacket()
    raw = bytearray(pkt.pack())
    # Altera payload para corromper CRC
    raw[10] ^= 0xFF
    with pytest.raises(ValueError, match="Erro de CRC-16"):
        TelemetryPacket.unpack(bytes(raw), verify_crc=True)


def test_euler_conversion():
    # Quaterion de identidade -> 0, 0, 0
    p_ident = TelemetryPacket(q_w=1.0, q_x=0.0, q_y=0.0, q_z=0.0)
    roll, pitch, yaw = p_ident.euler_angles_deg
    assert pytest.approx(roll, abs=1e-4) == 0.0
    assert pytest.approx(pitch, abs=1e-4) == 0.0
    assert pytest.approx(yaw, abs=1e-4) == 0.0

    # Rotacao de 90 graus em Yaw (Z) -> q = [cos(45), 0, 0, sin(45)]
    p_yaw90 = TelemetryPacket(q_w=0.7071068, q_x=0.0, q_y=0.0, q_z=0.7071068)
    roll, pitch, yaw = p_yaw90.euler_angles_deg
    assert pytest.approx(yaw, abs=0.1) == 90.0
