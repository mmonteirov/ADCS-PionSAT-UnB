"""
logger.py
=========
Gravador de telemetria e dados de sessao em tempo real em formato CSV para o PION Sat.
"""

from __future__ import annotations

import csv
from datetime import datetime
import logging
import os
import threading
from typing import Optional, Dict, Any

from src.ground_station.telemetry.packet_definitions import TelemetryPacket

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "iso_timestamp",
    "arrival_time_s",
    "timestamp_ms",
    "seq_num",
    "sys_mode",
    "ekf_status",
    "q_w",
    "q_x",
    "q_y",
    "q_z",
    "gyro_x_rad_s",
    "gyro_y_rad_s",
    "gyro_z_rad_s",
    "mag_x_uT",
    "mag_y_uT",
    "mag_z_uT",
    "rel_pos_x_mm",
    "rel_pos_y_mm",
    "rel_pos_z_mm",
    "co2_ppm",
    "light_lux",
    "humidity_pct",
    "pressure_pa",
    "v_bat_mv",
    "i_bat_ma",
    "soc_percent",
    "actuator_pwm",
    "theta_err_deg",
    "rmse_theta_deg",
    "health_status",
]


class TelemetryLogger:
    """
    Gerenciador thread-safe de gravacao de sessoes de telemetria em CSV.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = log_dir
        self.is_logging = False
        self.current_filepath: Optional[str] = None
        self._file = None
        self._writer = None
        self._lock = threading.Lock()
        self.recorded_packets_count = 0
        self.start_time: Optional[datetime] = None

        os.makedirs(self.log_dir, exist_ok=True)

    def start(self, custom_filename: Optional[str] = None) -> str:
        """Inicia uma nova sessao de gravacao."""
        with self._lock:
            if self.is_logging:
                return self.current_filepath or ""

            now = datetime.now()
            self.start_time = now
            if custom_filename:
                filename = custom_filename
            else:
                timestamp_str = now.strftime("%Y%m%d_%H%M%S")
                filename = f"telemetry_session_{timestamp_str}.csv"

            self.current_filepath = os.path.join(self.log_dir, filename)
            self._file = open(self.current_filepath, mode="w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow(CSV_HEADERS)
            self._file.flush()

            self.is_logging = True
            self.recorded_packets_count = 0
            logger.info(f"Gravacao de telemetria iniciada: {self.current_filepath}")
            return self.current_filepath

    def log_packet(
        self,
        packet: TelemetryPacket,
        divergence_metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Grava uma linha de dados no arquivo CSV ativo."""
        if not self.is_logging or self._writer is None or self._file is None:
            return

        with self._lock:
            iso_now = datetime.now().isoformat()
            theta_err = 0.0
            rmse_theta = 0.0
            health = "NOMINAL"

            if divergence_metrics:
                theta_err = float(divergence_metrics.get("theta_err_deg", 0.0))
                rmse_theta = float(divergence_metrics.get("rmse_theta_deg", 0.0))
                health = str(divergence_metrics.get("health_status", "NOMINAL"))

            row = [
                iso_now,
                f"{packet.arrival_time_s:.6f}",
                packet.timestamp_ms,
                packet.seq_num,
                packet.sys_mode,
                packet.ekf_status,
                f"{packet.q_w:.6f}",
                f"{packet.q_x:.6f}",
                f"{packet.q_y:.6f}",
                f"{packet.q_z:.6f}",
                f"{packet.gyro_x:.6f}",
                f"{packet.gyro_y:.6f}",
                f"{packet.gyro_z:.6f}",
                f"{packet.mag_x:.3f}",
                f"{packet.mag_y:.3f}",
                f"{packet.mag_z:.3f}",
                packet.rel_pos_x,
                packet.rel_pos_y,
                packet.rel_pos_z,
                packet.co2_ppm,
                packet.light_lux,
                f"{packet.humidity_pct:.2f}",
                f"{packet.pressure_pa:.2f}",
                packet.v_bat_mv,
                packet.i_bat_ma,
                packet.soc_percent,
                packet.actuator_pwm,
                f"{theta_err:.4f}",
                f"{rmse_theta:.4f}",
                health,
            ]
            self._writer.writerow(row)
            self.recorded_packets_count += 1
            if self.recorded_packets_count % 10 == 0:
                self._file.flush()

    def stop(self) -> None:
        """Finaliza e fecha o arquivo de sessao."""
        with self._lock:
            if not self.is_logging:
                return
            if self._file is not None:
                self._file.flush()
                self._file.close()
                self._file = None
                self._writer = None

            self.is_logging = False
            logger.info(
                f"Gravacao finalizada. Total de {self.recorded_packets_count} pacotes gravados em {self.current_filepath}"
            )

    def get_status(self) -> dict[str, Any]:
        """Retorna status atual da gravacao."""
        with self._lock:
            duration_s = (datetime.now() - self.start_time).total_seconds() if self.start_time and self.is_logging else 0.0
            file_size_bytes = 0
            if self.current_filepath and os.path.exists(self.current_filepath):
                file_size_bytes = os.path.getsize(self.current_filepath)

            return {
                "is_logging": self.is_logging,
                "filepath": self.current_filepath or "",
                "packets_count": self.recorded_packets_count,
                "duration_seconds": duration_s,
                "file_size_bytes": file_size_bytes,
            }
