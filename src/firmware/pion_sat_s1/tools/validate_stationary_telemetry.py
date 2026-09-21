"""Valida estabilidade da telemetria do PION Sat em repouso."""

from __future__ import annotations

import argparse
import math
import pathlib
import queue
import statistics
import sys
import time


def rotate_body_to_lab(packet) -> tuple[float, float, float]:
    """Aplica ao magnetometro a mesma rotacao usada pelo visualizador 3D."""
    w, x, y, z = packet.q_w, packet.q_x, packet.q_y, packet.q_z
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    bx, by, bz = packet.mag_x, packet.mag_y, packet.mag_z
    return (
        (1 - 2 * (y * y + z * z)) * bx + 2 * (x * y - z * w) * by + 2 * (x * z + y * w) * bz,
        2 * (x * y + z * w) * bx + (1 - 2 * (x * x + z * z)) * by + 2 * (y * z - x * w) * bz,
        2 * (x * z - y * w) * bx + 2 * (y * z + x * w) * by + (1 - 2 * (x * x + y * y)) * bz,
    )


def angular_distance_deg(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    cosine = max(-1.0, min(1.0, dot / (na * nb)))
    return math.degrees(math.acos(cosine))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--ground-station-root", type=pathlib.Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.ground_station_root.resolve()))
    from src.ground_station.telemetry.serial_receiver import SerialReceiver

    packets: queue.Queue = queue.Queue(maxsize=2000)
    receiver = SerialReceiver(args.port, args.baud, packet_queue=packets)
    if not receiver.connect():
        print(f"ERRO: nao foi possivel abrir {args.port}", file=sys.stderr)
        return 2

    receiver.start()
    samples = []
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            try:
                samples.append(packets.get(timeout=0.2))
            except queue.Empty:
                pass
    finally:
        receiver.stop()
        receiver.join(timeout=2.0)
        receiver.disconnect()

    if len(samples) < 2:
        print("REPROVADO: amostras insuficientes")
        return 1

    stats = receiver.get_stats()
    duration = samples[-1].arrival_time_s - samples[0].arrival_time_s
    rate = (len(samples) - 1) / duration
    gaps = sum(
        ((b.seq_num - ((a.seq_num + 1) & 0xFFFF)) & 0xFFFF)
        for a, b in zip(samples, samples[1:])
    )
    q_norms = [p.q_norm for p in samples]
    gyro = [p.gyro_norm for p in samples]
    mag_norms = [p.mag_norm for p in samples]
    rpy = [p.euler_angles_deg for p in samples]
    world_mag = [rotate_body_to_lab(p) for p in samples]
    reference = tuple(statistics.fmean(v[i] for v in world_mag) for i in range(3))
    mag_angles = [angular_distance_deg(v, reference) for v in world_mag]

    print(f"amostras={len(samples)} taxa={rate:.3f}Hz CRC={int(stats['crc_errors'])} gaps={gaps}")
    print(f"|q|={min(q_norms):.6f}..{max(q_norms):.6f}")
    print(f"gyro RMS={math.sqrt(statistics.fmean(v*v for v in gyro)):.6f} pico={max(gyro):.6f} rad/s")
    print(f"|mag| media={statistics.fmean(mag_norms):.2f} faixa={min(mag_norms):.2f}..{max(mag_norms):.2f} uT")
    print(
        "amplitude RPY=(%.3f, %.3f, %.3f) deg"
        % tuple(max(v[i] for v in rpy) - min(v[i] for v in rpy) for i in range(3))
    )
    print(
        "linha amarela: desvio medio=%.3f deg, maximo=%.3f deg"
        % (statistics.fmean(mag_angles), max(mag_angles))
    )
    placeholders_zero = all(
        p.rel_pos_x == p.rel_pos_y == p.rel_pos_z == 0
        and p.co2_ppm == p.light_lux == p.humidity_raw == 0
        and p.pressure_pa == 0.0 and p.v_bat_mv == p.i_bat_ma == p.soc_percent == 0
        for p in samples
    )
    print(f"campos ainda sem driver em zero={placeholders_zero}")
    print(f"atuador sempre seguro={all(p.actuator_pwm == 0 for p in samples)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
