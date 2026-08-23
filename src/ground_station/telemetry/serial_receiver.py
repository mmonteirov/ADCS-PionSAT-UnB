"""
serial_receiver.py
==================
Receptor USB/Serial de alta performance para a Ground Station do PION Sat.
Executa em thread desacoplada, garantindo latencia < 15 ms e zero congelamentos na GUI.

Especificacao: docs/specs/digital_twin_spec.md
Taxa de amostragem: 10 Hz a 50 Hz
"""

from __future__ import annotations

import logging
import queue
import time
import threading
from typing import List, Optional, Tuple

import serial
import serial.tools.list_ports

from src.ground_station.telemetry.packet_definitions import (
    HEADER_SYNC,
    PACKET_SIZE,
    TelemetryPacket,
)

logger = logging.getLogger(__name__)


def list_available_serial_ports() -> List[str]:
    """
    Retorna lista ordenada das portas seriais disponiveis no sistema
    (filtrando preferencialmente /dev/ttyUSB*, /dev/ttyACM* no Linux ou COM* no Windows).
    """
    ports = serial.tools.list_ports.comports()
    port_list: List[str] = []
    for port in sorted(ports, key=lambda p: p.device):
        port_list.append(port.device)
    return port_list


class SerialReceiver(threading.Thread):
    """
    Thread de recepcao serial continua com parser de fluxo binario robusto
    e buffer circular thread-safe (queue.Queue).
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        packet_queue: Optional[queue.Queue[TelemetryPacket]] = None,
        max_queue_size: int = 1000,
        timeout: float = 0.1,
    ) -> None:
        super().__init__(name="SerialReceiverThread", daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.packet_queue: queue.Queue[TelemetryPacket] = (
            packet_queue if packet_queue is not None else queue.Queue(maxsize=max_queue_size)
        )

        self._running = threading.Event()
        self._serial: Optional[serial.Serial] = None

        # Metricas e estatisticas de enlace
        self.packets_received = 0
        self.crc_errors = 0
        self.sync_losses = 0
        self.bytes_received = 0
        self.last_packet_time: float = 0.0
        self.packet_rate_hz: float = 0.0
        self._rate_calc_time = time.time()
        self._rate_calc_count = 0
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Abre a porta serial."""
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=0.5,
            )
            self._serial.reset_input_buffer()
            logger.info(f"Porta serial {self.port} conectada com sucesso a {self.baudrate} bps.")
            return True
        except Exception as e:
            logger.error(f"Falha ao abrir porta serial {self.port}: {e}")
            self._serial = None
            return False

    def disconnect(self) -> None:
        """Fecha a conexao serial de forma limpa."""
        self.stop()
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar porta serial: {e}")
            finally:
                self._serial = None
        logger.info(f"Porta serial {self.port} desconectada.")

    def is_connected(self) -> bool:
        """Verifica se a conexao serial esta ativa."""
        return self._serial is not None and self._serial.is_open and self._running.is_set()

    def run(self) -> None:
        """Loop de execucao principal da thread de recepcao."""
        self._running.set()
        raw_buffer = bytearray()

        while self._running.is_set():
            if self._serial is None or not self._serial.is_open:
                time.sleep(0.05)
                continue

            try:
                # Leitura em lote de bytes disponiveis
                waiting = self._serial.in_waiting
                if waiting > 0:
                    chunk = self._serial.read(waiting)
                else:
                    chunk = self._serial.read(1)

                if chunk:
                    with self._lock:
                        self.bytes_received += len(chunk)
                    raw_buffer.extend(chunk)

                # Busca pelo header de sincronismo 0xAA55 (little-endian: 0x55, 0xAA)
                while len(raw_buffer) >= PACKET_SIZE:
                    # Verifica se os dois primeiros bytes correspondem ao header 0xAA55
                    # Em little-endian uint16: 0x55 seguido de 0xAA
                    if raw_buffer[0] == 0x55 and raw_buffer[1] == 0xAA:
                        packet_data = bytes(raw_buffer[:PACKET_SIZE])
                        arrival_time = time.time()

                        try:
                            packet = TelemetryPacket.unpack(packet_data, arrival_time=arrival_time, verify_crc=True)
                            with self._lock:
                                self.packets_received += 1
                                self.last_packet_time = arrival_time
                                self._rate_calc_count += 1

                            # Insercao no buffer circular thread-safe sem travar
                            try:
                                self.packet_queue.put_nowait(packet)
                            except queue.Full:
                                # Descarta pacote mais antigo para acomodar o mais recente
                                try:
                                    self.packet_queue.get_nowait()
                                    self.packet_queue.put_nowait(packet)
                                except Exception:
                                    pass

                            # Avanca o buffer
                            del raw_buffer[:PACKET_SIZE]

                        except ValueError as ve:
                            # Erro de CRC ou framing
                            with self._lock:
                                self.crc_errors += 1
                            logger.debug(f"Pacote invalido rejeitado: {ve}")
                            # Descarta o primeiro byte para tentar sincronizar novamente
                            del raw_buffer[:1]
                    else:
                        # Header nao corresponde: descarta 1 byte e continua procurando
                        with self._lock:
                            self.sync_losses += 1
                        del raw_buffer[:1]

                # Calculo periodico de frequencia de pacotes (1 Hz)
                now = time.time()
                dt_rate = now - self._rate_calc_time
                if dt_rate >= 1.0:
                    with self._lock:
                        self.packet_rate_hz = self._rate_calc_count / dt_rate
                        self._rate_calc_count = 0
                        self._rate_calc_time = now

            except serial.SerialException as se:
                logger.error(f"Erro serial de E/S na porta {self.port}: {se}")
                time.sleep(0.2)
            except Exception as e:
                logger.exception(f"Excecao inesperada no receptor serial: {e}")
                time.sleep(0.05)

        logger.info("Thread de recepcao serial finalizada.")

    def stop(self) -> None:
        """Sinaliza a interrupcao da thread."""
        self._running.clear()

    def get_stats(self) -> dict[str, float]:
        """Retorna snapshot das metricas de recepcao."""
        with self._lock:
            return {
                "packets_received": float(self.packets_received),
                "crc_errors": float(self.crc_errors),
                "sync_losses": float(self.sync_losses),
                "bytes_received": float(self.bytes_received),
                "packet_rate_hz": self.packet_rate_hz,
                "is_connected": 1.0 if self.is_connected() else 0.0,
            }
