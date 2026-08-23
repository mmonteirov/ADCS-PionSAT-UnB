"""
layer1_dynamics.py
==================
Camada 1 do Gemeo Digital: Modelo Dinamico de Euler 1-Eixo e Integrador RK4.
Simula o comportamento rotacional em torno do eixo Z (eixo controlado da bancada / mancal a ar).
"""

from __future__ import annotations

import math
import numpy as np

from src.twin.config import (
    I3_NOMINAL_KG_M2,
    MAX_PWM,
    MAX_TORQUE_NM,
    DEADBAND_PWM,
    FRICTION_COEFF_DAMPING,
)


class DynamicsLayer1:
    """
    Camada 1: Integrador de Dinamica 1-eixo com atrito de mancal e resposta de atuador.
    """

    def __init__(self, I3: float = I3_NOMINAL_KG_M2) -> None:
        self.I3 = I3
        self.omega_z: float = 0.0
        self.q: np.ndarray = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)  # [qw, qx, qy, qz]

    def reset(self, omega0: float = 0.0, q0: np.ndarray | None = None) -> None:
        """Reinicia o estado dinamico."""
        self.omega_z = omega0
        if q0 is not None:
            self.q = q0.copy() / np.linalg.norm(q0)
        else:
            self.q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

    def calculate_actuator_torque(self, pwm_cmd: float) -> float:
        """
        Calcula o torque do atuador a partir do comando PWM considerando zona morta.
        """
        abs_pwm = abs(pwm_cmd)
        if abs_pwm <= DEADBAND_PWM:
            return 0.0
        
        effective_pwm = min(abs_pwm - DEADBAND_PWM, MAX_PWM - DEADBAND_PWM)
        torque_mag = (effective_pwm / (MAX_PWM - DEADBAND_PWM)) * MAX_TORQUE_NM
        return math.copysign(torque_mag, pwm_cmd)

    def step(self, dt: float, pwm_cmd: float, tau_ext: float = 0.0) -> tuple[float, np.ndarray]:
        """
        Executa um passo de integracao RK4 para a dinamica de atitude 1-eixo.

        Parameters
        ----------
        dt : float
            Passo de tempo (s).
        pwm_cmd : float
            Comando de atuacao do satelite (-1000 a +1000).
        tau_ext : float
            Torque externo / perturbacao (N*m).

        Returns
        -------
        tuple[float, np.ndarray]
            (omega_z_atualizado, q_atualizado)
        """
        tau_act = self.calculate_actuator_torque(pwm_cmd)

        def total_torque(w: float) -> float:
            # Torque total = Atuador + Perturbacao Externa - Atrito viscoso
            tau_fric = -FRICTION_COEFF_DAMPING * w
            return tau_act + tau_ext + tau_fric

        # RK4 para omega_dot = tau(w) / I3
        def f_omega(w: float) -> float:
            return total_torque(w) / self.I3

        k1_w = f_omega(self.omega_z)
        k2_w = f_omega(self.omega_z + 0.5 * dt * k1_w)
        k3_w = f_omega(self.omega_z + 0.5 * dt * k2_w)
        k4_w = f_omega(self.omega_z + dt * k3_w)

        self.omega_z += (dt / 6.0) * (k1_w + 2.0 * k2_w + 2.0 * k3_w + k4_w)

        # Cinemática de quaterion 1-eixo em Z: q_dot = 0.5 * q * [0, 0, 0, w_z]
        # dqw = -0.5 * qz * wz
        # dqz =  0.5 * qw * wz
        qw, qx, qy, qz = self.q
        half_dt = 0.5 * dt
        w_mid = self.omega_z

        d_qw = -half_dt * qz * w_mid
        d_qz =  half_dt * qw * w_mid

        self.q[0] += d_qw
        self.q[3] += d_qz

        # Renormalizacao
        norm = np.linalg.norm(self.q)
        if norm > 1e-12:
            self.q /= norm

        return self.omega_z, self.q.copy()
