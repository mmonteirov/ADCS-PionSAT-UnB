"""
layer2_ekf_mirror.py
====================
Camada 2 do Gemeo Digital: EKF Espelho 64-bit (Extended Kalman Filter em precisao dupla).
Processa a telemetria bruta do satelite (giroscopio e magnetometro) para estimacao precisa de atitude e bias.
"""

from __future__ import annotations

import math
import numpy as np

from src.twin.config import LAB_B_FIELD_NED_UT


def quat_mult(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiplicacao de quaterioes Hamiltonianos q1 * q2."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ], dtype=np.float64)


def quat_rotate_vector(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotaciona o vetor v pelo quaterion q (Body -> Ref / Ref -> Body)."""
    # q * [0, v] * q_conj
    qw, qx, qy, qz = q
    q_vec = np.array([qx, qy, qz], dtype=np.float64)
    uv = np.cross(q_vec, v)
    uuv = np.cross(q_vec, uv)
    return v + 2.0 * (qw * uv + uuv)


class EkfMirrorLayer2:
    """
    Camada 2: Filtro de Kalman Estendido Multiplicativo (MEKF) 64-bit.
    Estado de erro: delta_theta (3x1) e bias de giroscopio (3x1).
    """

    def __init__(self) -> None:
        self.q_est = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self.bias_gyro = np.zeros(3, dtype=np.float64)
        
        # Matriz de covariancia do estado de erro P (6x6)
        self.P = np.eye(6, dtype=np.float64) * 1.0e-2

        # Ruido do processo Q e da medicao R
        self.Q = np.eye(6, dtype=np.float64)
        self.Q[0:3, 0:3] *= 1.0e-4  # Ruido angular do giroscopio
        self.Q[3:6, 3:6] *= 1.0e-7  # Instabilidade do bias do giroscopio

        self.R_mag = np.eye(3, dtype=np.float64) * 0.25  # Ruido do magnetometro (uT^2)

        self.last_timestamp_s: float | None = None
        self.convergence_status = 0  # 0: Init, 1: Divergente, 2: Convergido

    def reset(self) -> None:
        """Reinicia o filtro."""
        self.q_est = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self.bias_gyro = np.zeros(3, dtype=np.float64)
        self.P = np.eye(6, dtype=np.float64) * 1.0e-2
        self.last_timestamp_s = None
        self.convergence_status = 0

    def predict(self, gyro_raw: np.ndarray, dt: float) -> None:
        """
        Passo de propagacao / predicao temporal do EKF com medicao do giroscopio.
        """
        if dt <= 0.0 or dt > 1.0:
            dt = 0.05

        # Velocidade angular compensada por bias
        omega = gyro_raw - self.bias_gyro
        omega_norm = np.linalg.norm(omega)

        # Propagacao cinemática do quaterion de atitude
        if omega_norm > 1e-8:
            axis = omega / omega_norm
            angle = omega_norm * dt
            delta_q = np.array([
                math.cos(angle * 0.5),
                axis[0] * math.sin(angle * 0.5),
                axis[1] * math.sin(angle * 0.5),
                axis[2] * math.sin(angle * 0.5),
            ], dtype=np.float64)
            self.q_est = quat_mult(self.q_est, delta_q)
            self.q_est /= np.linalg.norm(self.q_est)

        # Propagacao da covariancia P_dot ~ F P + P F^T + Q
        # Matriz Jacobiana F (6x6)
        wx, wy, wz = omega
        omega_skew = np.array([
            [0, -wz, wy],
            [wz, 0, -wx],
            [-wy, wx, 0],
        ], dtype=np.float64)

        F = np.eye(6, dtype=np.float64)
        F[0:3, 0:3] -= omega_skew * dt
        F[0:3, 3:6] = -np.eye(3, dtype=np.float64) * dt

        self.P = F @ self.P @ F.T + self.Q * dt

    def update_magnetometer(self, mag_meas_uT: np.ndarray, b_ref_uT: np.ndarray) -> None:
        """
        Passo de correcao / atualizacao com medicao do magnetometro.
        """
        # Predicao do campo no referencial do corpo a partir de q_est
        # b_body_pred = R(q_est)^T * b_ref
        qw, qx, qy, qz = self.q_est
        q_conj = np.array([qw, -qx, -qy, -qz], dtype=np.float64)
        b_body_pred = quat_rotate_vector(q_conj, b_ref_uT)

        # Residuo de inovacao
        y = mag_meas_uT - b_body_pred

        # Matriz Jacobiana de medicao H (3x6)
        bx, by, bz = b_body_pred
        b_skew = np.array([
            [0, -bz, by],
            [bz, 0, -bx],
            [-by, bx, 0],
        ], dtype=np.float64)

        H = np.zeros((3, 6), dtype=np.float64)
        H[0:3, 0:3] = b_skew

        # Ganho de Kalman K = P H^T (H P H^T + R)^-1
        S = H @ self.P @ H.T + self.R_mag
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return

        # Correcao do estado de erro
        delta_x = K @ y

        # Correcao do quaterion de atitude
        delta_theta = delta_x[0:3]
        angle_err = np.linalg.norm(delta_theta)
        if angle_err > 1e-8:
            axis_err = delta_theta / angle_err
            dq = np.array([
                math.cos(angle_err * 0.5),
                axis_err[0] * math.sin(angle_err * 0.5),
                axis_err[1] * math.sin(angle_err * 0.5),
                axis_err[2] * math.sin(angle_err * 0.5),
            ], dtype=np.float64)
            self.q_est = quat_mult(self.q_est, dq)
            self.q_est /= np.linalg.norm(self.q_est)

        # Correcao do bias de giroscopio
        self.bias_gyro += delta_x[3:6]

        # Atualizacao da covariancia P = (I - K H) P
        I_KH = np.eye(6, dtype=np.float64) - K @ H
        self.P = I_KH @ self.P

        # Checagem de convergencia
        trace_p = float(np.trace(self.P[0:3, 0:3]))
        if trace_p < 0.2:
            self.convergence_status = 2  # Convergido
        elif trace_p < 1.0:
            self.convergence_status = 0  # Init
        else:
            self.convergence_status = 1  # Divergente
