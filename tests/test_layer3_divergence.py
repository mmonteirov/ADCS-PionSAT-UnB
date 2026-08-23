"""
test_layer3_divergence.py
=========================
Testes unitários para a Camada 3 (Métricas de Divergência Twin vs Satélite Físico & Classificação de Saúde).
"""

import math
import numpy as np
import pytest

from src.twin.layers.layer3_divergence import DivergenceLayer3, calculate_angular_error_deg


def test_quaternion_angular_error():
    # Quatérnions idênticos -> erro 0.0 graus
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    q2 = np.array([1.0, 0.0, 0.0, 0.0])
    err_zero = calculate_angular_error_deg(q1, q2)
    assert np.isclose(err_zero, 0.0, atol=1e-5)

    # Rotação de 90 graus em torno de Z (q2 = [cos(45°), 0, 0, sin(45°)])
    q2_90 = np.array([math.cos(math.pi / 4.0), 0.0, 0.0, math.sin(math.pi / 4.0)])
    err_90 = calculate_angular_error_deg(q1, q2_90)
    assert np.isclose(err_90, 90.0, atol=1e-3)

    # Rotação com quatérnio antipodal (representa a mesma rotação)
    q2_anti = -q1
    err_anti = calculate_angular_error_deg(q1, q2_anti)
    assert np.isclose(err_anti, 0.0, atol=1e-5)


def test_sliding_window_rmse():
    l3 = DivergenceLayer3(window_size=50)

    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    angle = np.radians(10.0)
    q2 = np.array([math.cos(angle / 2.0), 0.0, 0.0, math.sin(angle / 2.0)])

    for _ in range(50):
        res = l3.update(q_sat=q1, q_twin=q2, omega_sat=0.0, omega_twin=0.0)

    assert pytest.approx(res["theta_err_deg"], abs=1e-3) == 10.0
    assert pytest.approx(res["rmse_theta_deg"], abs=1e-3) == 10.0
    assert res["health_status"] == "DIVERGENTE"  # > 5 deg
