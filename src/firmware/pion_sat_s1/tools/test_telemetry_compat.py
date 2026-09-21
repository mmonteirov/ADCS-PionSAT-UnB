"""Compila o serializador C e valida o pacote com a Ground Station oficial."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ground-station-root",
        type=pathlib.Path,
        required=True,
        help="Raiz do clone ADCS-PionSAT-UnB",
    )
    args = parser.parse_args()

    firmware_root = pathlib.Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="pion_telemetry_") as temporary:
        executable = pathlib.Path(temporary) / "telemetry_golden.exe"
        compile_command = [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{firmware_root / 'main' / 'include'}",
            str(firmware_root / "main" / "telemetry_packet.c"),
            str(firmware_root / "tools" / "telemetry_golden.c"),
            "-o",
            str(executable),
        ]
        subprocess.run(compile_command, check=True)
        raw_packet = subprocess.run(
            [str(executable)], check=True, capture_output=True
        ).stdout

    sys.path.insert(0, str(args.ground_station_root.resolve()))
    from src.ground_station.telemetry.packet_definitions import (  # noqa: PLC0415
        PACKET_SIZE,
        TelemetryPacket,
    )

    packet = TelemetryPacket.unpack(raw_packet, verify_crc=True)
    assert len(raw_packet) == PACKET_SIZE == 76
    assert packet.timestamp_ms == 123456
    assert packet.seq_num == 42
    assert packet.ekf_status == 2
    assert packet.actuator_pwm == 0
    assert abs(packet.q_norm - 1.0) < 1e-5
    assert abs(packet.gyro_z - 0.0789) < 1e-6
    assert abs(packet.mag_z - 28.91) < 1e-4

    print("OK: C -> 76 bytes -> CRC valido -> Ground Station Python")
    print(
        f"seq={packet.seq_num} t={packet.timestamp_ms} ms "
        f"|q|={packet.q_norm:.6f} gyro_z={packet.gyro_z:.4f} rad/s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
