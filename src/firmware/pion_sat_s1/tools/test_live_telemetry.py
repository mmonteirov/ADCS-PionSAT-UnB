"""Teste de bancada da telemetria binaria do PION Sat."""

from __future__ import annotations

import argparse
import pathlib
import queue
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=60.0)
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
    deadline = time.monotonic() + args.seconds
    started = time.monotonic()
    next_report = started + 1.0
    received = []
    try:
        while time.monotonic() < deadline:
            try:
                received.append(packets.get(timeout=0.2))
            except queue.Empty:
                pass
            now = time.monotonic()
            if now >= next_report:
                elapsed = max(now - started, 0.001)
                last = received[-1] if received else None
                if last is None:
                    print(f"[{elapsed:5.1f}s] aguardando pacotes...", flush=True)
                else:
                    live_stats = receiver.get_stats()
                    roll, pitch, yaw = last.euler_angles_deg
                    print(
                        f"[{elapsed:5.1f}s] pacotes={len(received):4d} "
                        f"taxa={len(received) / elapsed:5.2f}Hz "
                        f"seq={last.seq_num:5d} CRC={int(live_stats['crc_errors'])} "
                        f"RPY=({roll:6.1f},{pitch:6.1f},{yaw:6.1f})deg "
                        f"|gyro|={last.gyro_norm:.3f}rad/s "
                        f"|mag|={last.mag_norm:.1f}uT PWM={last.actuator_pwm}",
                        flush=True,
                    )
                next_report += 1.0
    finally:
        receiver.stop()
        receiver.join(timeout=2.0)
        receiver.disconnect()

    stats = receiver.get_stats()
    duration = max(args.seconds, 0.001)
    active_duration = (
        received[-1].arrival_time_s - received[0].arrival_time_s
        if len(received) >= 2
        else duration
    )
    rate = (len(received) - 1) / max(active_duration, 0.001)
    crc_errors = int(stats["crc_errors"])
    sequence_gaps = 0
    timestamp_resets = 0
    norm_min = float("inf")
    norm_max = 0.0

    for previous, current in zip(received, received[1:]):
        expected = (previous.seq_num + 1) & 0xFFFF
        if current.seq_num != expected:
            sequence_gaps += (current.seq_num - expected) & 0xFFFF
        if current.timestamp_ms < previous.timestamp_ms:
            timestamp_resets += 1
    for packet in received:
        norm_min = min(norm_min, packet.q_norm)
        norm_max = max(norm_max, packet.q_norm)

    print(f"porta={args.port} duracao={args.seconds:.1f}s")
    print(f"pacotes={len(received)} taxa={rate:.2f}Hz bytes={int(stats['bytes_received'])}")
    print(f"crc_erros={crc_errors} perdas_sequencia={sequence_gaps} resets={timestamp_resets}")
    if received:
        print(f"seq={received[0].seq_num}->{received[-1].seq_num} |q|={norm_min:.6f}..{norm_max:.6f}")
        gyro_peak = max(packet.gyro_norm for packet in received)
        mag_min = min(packet.mag_norm for packet in received)
        mag_max = max(packet.mag_norm for packet in received)
        euler_start = received[0].euler_angles_deg
        euler_end = received[-1].euler_angles_deg
        print(f"pico_gyro={gyro_peak:.3f}rad/s |mag|={mag_min:.1f}..{mag_max:.1f}uT")
        print(
            "RPY inicio=(%.1f, %.1f, %.1f) fim=(%.1f, %.1f, %.1f) graus"
            % (*euler_start, *euler_end)
        )

    passed = (
        len(received) >= 10
        and rate >= 18.0
        and crc_errors == 0
        and sequence_gaps == 0
        and timestamp_resets == 0
        and 0.99 <= norm_min <= norm_max <= 1.01
        and all(packet.actuator_pwm == 0 for packet in received)
    )
    print("RESULTADO: APROVADO" if passed else "RESULTADO: REPROVADO")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
