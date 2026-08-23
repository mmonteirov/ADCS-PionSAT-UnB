"""
test_layer1_dynamics.py
=======================
Testes unitários para a Camada 1 (Dinâmica Rotacional 1-Eixo RK4 e Atuadores).
"""

import math
import numpy as np
import pytest

from src.twin.layers.layer1_dynamics import DynamicsLayer1


def test_layer1_initial_state():
    dyn = DynamicsLayer1()
    assert dyn.omega_z == 0.0
    assert np.allclose(dyn.q, [1.0, 0.0, 0.0, 0.0])


def test_layer1_pwm_deadband():
    dyn = DynamicsLayer1()
    # PWM abaixo da zona morta (<= 20.0) não deve gerar torque
    torque_deadband = dyn.calculate_actuator_torque(pwm_cmd=15.0)
    assert torque_deadband == 0.0

    torque_neg_deadband = dyn.calculate_actuator_torque(pwm_cmd=-15.0)
    assert torque_neg_deadband == 0.0

    # PWM acima da zona morta deve gerar torque
    torque_active = dyn.calculate_actuator_torque(pwm_cmd=500.0)
    assert torque_active > 0.0

    torque_neg = dyn.calculate_actuator_torque(pwm_cmd=-500.0)
    assert torque_neg < 0.0
    assert np.isclose(torque_active, -torque_neg, atol=1e-8)


def test_layer1_rk4_integration():
    dyn = DynamicsLayer1()
    w_next, q_next = dyn.step(dt=0.05, pwm_cmd=300.0)
    assert w_next > 0.0
    assert np.isclose(np.linalg.norm(q_next), 1.0, atol=1e-6)

    dyn.reset()
    assert dyn.omega_z == 0.0
    assert np.allclose(dyn.q, [1.0, 0.0, 0.0, 0.0])
