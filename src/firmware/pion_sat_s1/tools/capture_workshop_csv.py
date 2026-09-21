"""Grava telemetria real da porta serial no CSV oficial da Ground Station."""

from __future__ import annotations

import argparse
import pathlib
import queue
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura CSV para a oficina do PION Sat")
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--ground-station-root", type=pathlib.Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.ground_station_root.resolve()))
    from src.ground_station.telemetry.logger import TelemetryLogger
    from src.ground_station.telemetry.serial_receiver import SerialReceiver

    args.output.parent.mkdir(parents=True, exist_ok=True)
    packets: queue.Queue = queue.Queue(maxsize=2000)
    receiver = SerialReceiver(args.port, args.baud, packet_queue=packets)
    if not receiver.connect():
        print(f"ERRO: nao foi possivel abrir {args.port}", file=sys.stderr)
        return 2

    logger = TelemetryLogger(str(args.output.parent))
    logger.start(args.output.name)
    receiver.start()
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            try:
                logger.log_packet(packets.get(timeout=0.2))
            except queue.Empty:
                pass
    finally:
        receiver.stop()
        receiver.join(timeout=2.0)
        receiver.disconnect()
        logger.stop()

    stats = receiver.get_stats()
    print(f"arquivo={args.output.resolve()}")
    print(f"pacotes={logger.recorded_packets_count} CRC={int(stats['crc_errors'])}")
    return 0 if logger.recorded_packets_count >= 10 and int(stats["crc_errors"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
