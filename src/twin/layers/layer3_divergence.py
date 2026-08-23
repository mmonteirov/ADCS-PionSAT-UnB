"""
layer3_divergence.py
====================
Camada 3 do Gemeo Digital: Analise Estatistica e Metricas de Divergencia (DTiL).
Calcula em tempo real o erro angular de atitude (theta_err), residuo de velocidades e RMSE em janela deslizante de 120s.
"""

from __future__ import annotations

from collections import deque
import math
from typing import Dict, Any, Tuple
import numpy as np

from src.twin.layers.layer2_ekf_mirror import quat_mult


def calculate_angular_error_deg(q_actual: np.ndarray, q_predicted: np.ndarray) -> float:
    """
    Calcula o angulo de divergencia espacial (theta_err) entre dois quaternios em graus.
    delta_q = q_actual * q_predicted^-1
    theta_err = 2 * arccos(|delta_q_w|)
    """
    # Conjugado de q_predicted (inverso para quaternio unitario)
    pw, px, py, pz = q_predicted
    p_norm = math.sqrt(pw*pw + px*px + py*py + pz*pz)
    if p_norm > 1e-12:
        q_pred_inv = np.array([pw, -px, -py, -pz], dtype=np.float64) / p_norm
    else:
        q_pred_inv = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

    aw, ax, ay, az = q_actual
    a_norm = math.sqrt(aw*aw + ax*ax + ay*ay + az*az)
    if a_norm > 1e-12:
        q_act_norm = np.array([aw, ax, ay, az], dtype=np.float64) / a_norm
    else:
        q_act_norm = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

    dq = quat_mult(q_act_norm, q_pred_inv)
    qw_abs = min(1.0, abs(dq[0]))
    theta_rad = 2.0 * math.acos(qw_abs)
    return math.degrees(theta_rad)


class DivergenceLayer3:
    """
    Camada 3: Motor de calculo de divergencia, RMSE em janela movel e diagnostico de saude DTiL.
    """

    def __init__(self, window_size: int = 600) -> None:
        self.window_size = window_size
        self.theta_err_history = deque(maxlen=window_size)
        self.omega_err_history = deque(maxlen=window_size)

    def reset(self) -> None:
        """Limpa historico de metricas."""
        self.theta_err_history.clear()
        self.omega_err_history.clear()

    def update(
        self,
        q_sat: np.ndarray,
        q_twin: np.ndarray,
        omega_sat: float,
        omega_twin: float,
    ) -> Dict[str, Any]:
        """
        Calcula as metricas de divergencia para a amostra corrente.

        Returns
        -------
        dict contendo:
            - theta_err_deg: Erro angular instantaneo
            - rmse_theta_deg: RMSE na janela deslizante
            - omega_err_rad_s: Diferenca de velocidade angular
            - health_status: 'NOMINAL' (< 3 deg), 'DRIFT' (3 a 5 deg) ou 'DIVERGENTE' (> 5 deg)
        """
        theta_err = calculate_angular_error_deg(q_sat, q_twin)
        omega_err = abs(omega_sat - omega_twin)

        self.theta_err_history.append(theta_err)
        self.omega_err_history.append(omega_err)

        # Calculo do RMSE = sqrt(mean(err^2))
        err_array = np.array(self.theta_err_history, dtype=np.float64)
        rmse_theta = float(np.sqrt(np.mean(err_array ** 2))) if len(err_array) > 0 else 0.0

        # Classificacao de saude
        if rmse_theta < 3.0:
            health = "NOMINAL"
        elif rmse_theta <= 5.0:
            health = "DRIFT"
        else:
            health = "DIVERGENTE"

        return {
            "theta_err_deg": theta_err,
            "rmse_theta_deg": rmse_theta,
            "omega_err_rad_s": omega_err,
            "twin_omega_z": omega_twin,
            "health_status": health,
        }
