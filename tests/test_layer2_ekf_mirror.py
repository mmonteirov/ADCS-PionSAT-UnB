"""
test_layer2_ekf_mirror.py
=========================
Testes unitários para a Camada 2 (Filtro de Kalman Estendido Espelho — MEKF 64-bit).
"""

import numpy as np
import pytest

from src.twin.layers.layer2_ekf_mirror import EkfMirrorLayer2, quat_mult


def test_ekf_mirror_state_initialization():
    ekf = EkfMirrorLayer2()
    assert np.allclose(ekf.q_est, [1.0, 0.0, 0.0, 0.0])
    assert np.allclose(ekf.bias_gyro, [0.0, 0.0, 0.0])
    assert ekf.P.shape == (6, 6)
    assert np.all(np.diag(ekf.P) > 0)


def test_quat_mult_properties():
    # Identidade
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    q2 = np.array([0.0, 1.0, 0.0, 0.0])
    assert np.allclose(quat_mult(q1, q2), q2)


def test_ekf_mirror_predict_step():
    ekf = EkfMirrorLayer2()
    P_init_trace = np.trace(ekf.P)

    gyro = np.array([0.0, 0.0, 0.1])
    dt = 0.05
    ekf.predict(gyro_raw=gyro, dt=dt)

    assert len(ekf.q_est) == 4
    assert np.isclose(np.linalg.norm(ekf.q_est), 1.0, atol=1e-5)
    assert np.trace(ekf.P) >= P_init_trace


def test_ekf_mirror_reset():
    ekf = EkfMirrorLayer2()
    ekf.predict(np.array([0.5, 0.5, 0.5]), dt=0.5)
    ekf.reset()
    assert np.allclose(ekf.q_est, [1.0, 0.0, 0.0, 0.0])
    assert np.allclose(ekf.bias_gyro, [0.0, 0.0, 0.0])
