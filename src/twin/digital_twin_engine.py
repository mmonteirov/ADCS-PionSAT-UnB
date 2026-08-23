"""
digital_twin_engine.py
======================
Orquestrador central do Gemeo Digital (Digital Twin Core - DTiL) do PION Sat.
Integra de forma sincrona e thread-safe as 4 Camadas (0 a 3) a cada pacote de telemetria recebido.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional
import numpy as np

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.twin.layers.layer0_env import EnvironmentLayer0
from src.twin.layers.layer1_dynamics import DynamicsLayer1
from src.twin.layers.layer2_ekf_mirror import EkfMirrorLayer2
from src.twin.layers.layer3_divergence import DivergenceLayer3

logger = logging.getLogger(__name__)


class DigitalTwinEngine:
    """
    Motor do Gemeo Digital em 4 Camadas:
    - Camada 0: Ambiente IGRF-14 e referencial magnetico local
    - Camada 1: Modelo dinamico de Euler 1-eixo com atuacao e atrito de bancada
    - Camada 2: EKF Espelho de precisao dupla (64-bit)
    - Camada 3: Metricas estatisticas de divergencia e calculo online de RMSE
    """

    def __init__(self, mode: str = "lab") -> None:
        self.layer0 = EnvironmentLayer0(mode=mode)
        self.layer1 = DynamicsLayer1()
        self.layer2 = EkfMirrorLayer2()
        self.layer3 = DivergenceLayer3(window_size=600)  # 600 amostras (~120s a 5Hz ou ~30s a 20Hz)

        self.last_time_s: Optional[float] = None
        self.total_processed_packets = 0

    def reset(self) -> None:
        """Reinicia todas as camadas do Gemeo Digital."""
        self.layer1.reset()
        self.layer2.reset()
        self.layer3.reset()
        self.last_time_s = None
        self.total_processed_packets = 0
        logger.info("Motor do Gemeo Digital reiniciado com sucesso.")

    def process_packet(self, packet: TelemetryPacket) -> Dict[str, Any]:
        """
        Processa um pacote de telemetria fisica recebido do satelite.

        Parameters
        ----------
        packet : TelemetryPacket
            Pacote com atitude fisica e telemetria de sensores.

        Returns
        -------
        dict
            Metricas da Camada 3 (theta_err, RMSE, comparacao de velocidades, status).
        """
        now_s = packet.arrival_time_s if packet.arrival_time_s > 0 else time.time()
        if self.last_time_s is None:
            dt = 0.05
        else:
            dt = now_s - self.last_time_s
            if dt <= 0 or dt > 1.0:
                dt = 0.05
        self.last_time_s = now_s

        # 1. Camada 0: Obtem vetor de campo magnetico de referencia
        b_ref_uT = self.layer0.get_reference_magnetic_field_uT(time_s=now_s)

        # 2. Camada 1: Propaga dinamica do satelite no modelo de solo
        w_twin_z, q_twin = self.layer1.step(
            dt=dt,
            pwm_cmd=float(packet.actuator_pwm),
        )

        # 3. Camada 2: Executa EKF espelho 64-bit
        gyro_vec = np.array([packet.gyro_x, packet.gyro_y, packet.gyro_z], dtype=np.float64)
        mag_meas_vec = np.array([packet.mag_x, packet.mag_y, packet.mag_z], dtype=np.float64)

        self.layer2.predict(gyro_raw=gyro_vec, dt=dt)
        self.layer2.update_magnetometer(mag_meas_uT=mag_meas_vec, b_ref_uT=b_ref_uT)
        q_ekf_mirror = self.layer2.q_est

        # 4. Camada 3: Calcula divergencia entre satelite fisico e gemeo digital
        q_sat = np.array([packet.q_w, packet.q_x, packet.q_y, packet.q_z], dtype=np.float64)
        divergence_metrics = self.layer3.update(
            q_sat=q_sat,
            q_twin=q_ekf_mirror,
            omega_sat=packet.gyro_z,
            omega_twin=w_twin_z,
        )

        self.total_processed_packets += 1
        return divergence_metrics
