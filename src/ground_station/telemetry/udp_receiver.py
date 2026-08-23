"""
udp_receiver.py
===============
Receptor UDP nao-bloqueante para telemetria em rede da Ground Station do PION Sat.
"""

from __future__ import annotations

import logging
import queue
import socket
import threading
import time
from typing import Optional

from src.ground_station.telemetry.packet_definitions import (
    PACKET_SIZE,
    TelemetryPacket,
)

logger = logging.getLogger(__name__)


class UdpReceiver(threading.Thread):
    """
    Receptor UDP concorrente para ingestao de pacotes de telemetria pela rede.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5005,
        packet_queue: Optional[queue.Queue[TelemetryPacket]] = None,
        max_queue_size: int = 1000,
    ) -> None:
        super().__init__(name="UdpReceiverThread", daemon=True)
        self.host = host
        self.port = port
        self.packet_queue: queue.Queue[TelemetryPacket] = (
            packet_queue if packet_queue is not None else queue.Queue(maxsize=max_queue_size)
        )
        self._running = threading.Event()
        self._socket: Optional[socket.socket] = None

        self.packets_received = 0
        self.crc_errors = 0
        self.bytes_received = 0
        self.packet_rate_hz = 0.0
        self._rate_calc_time = time.time()
        self._rate_calc_count = 0
        self._lock = threading.Lock()

    def start_listening(self) -> bool:
        """Inicializa o socket UDP."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(0.2)
            self._socket.bind((self.host, self.port))
            logger.info(f"Socket UDP escutando em {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar socket UDP em {self.host}:{self.port}: {e}")
            self._socket = None
            return False

    def run(self) -> None:
        """Loop de escuta UDP."""
        if self._socket is None:
            if not self.start_listening():
                return

        self._running.set()

        while self._running.is_set():
            try:
                data, addr = self._socket.recvfrom(2048)
                arrival_time = time.time()
                with self._lock:
                    self.bytes_received += len(data)

                if len(data) == PACKET_SIZE:
                    try:
                        packet = TelemetryPacket.unpack(data, arrival_time=arrival_time, verify_crc=True)
                        with self._lock:
                            self.packets_received += 1
                            self._rate_calc_count += 1

                        try:
                            self.packet_queue.put_nowait(packet)
                        except queue.Full:
                            self.packet_queue.get_nowait()
                            self.packet_queue.put_nowait(packet)

                    except ValueError:
                        with self._lock:
                            self.crc_errors += 1
            except socket.timeout:
                pass
            except Exception as e:
                if self._running.is_set():
                    logger.debug(f"Excecao no socket UDP: {e}")

            # Calculo de taxa 1 Hz
            now = time.time()
            dt = now - self._rate_calc_time
            if dt >= 1.0:
                with self._lock:
                    self.packet_rate_hz = self._rate_calc_count / dt
                    self._rate_calc_count = 0
                    self._rate_calc_time = now

    def stop(self) -> None:
        """Finaliza o receptor UDP."""
        self._running.clear()
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            finally:
                self._socket = None

    def is_listening(self) -> bool:
        """Verifica se o receptor UDP esta escutando."""
        return self._socket is not None and self._running.is_set()

    def is_connected(self) -> bool:
        """Alias para is_listening."""
        return self.is_listening()

    def get_stats(self) -> dict[str, float]:
        """Retorna snapshot das metricas de recepcao UDP."""
        with self._lock:
            return {
                "packets_received": float(self.packets_received),
                "crc_errors": float(self.crc_errors),
                "bytes_received": float(self.bytes_received),
                "packet_rate_hz": self.packet_rate_hz,
                "is_connected": 1.0 if self.is_listening() else 0.0,
            }
