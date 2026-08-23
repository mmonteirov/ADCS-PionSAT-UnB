"""
test_ekf_mirror.py
==================
Testes unitarios para as 4 camadas do Gemeo Digital (DTiL) e convergencia do EKF espelho.
"""

import numpy as np
import pytest

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.twin.layers.layer0_env import EnvironmentLayer0
from src.twin.layers.layer1_dynamics import DynamicsLayer1
from src.twin.layers.layer2_ekf_mirror import EkfMirrorLayer2, quat_mult
from src.twin.layers.layer3_divergence import DivergenceLayer3, calculate_angular_error_deg
from src.twin.digital_twin_engine import DigitalTwinEngine


def test_layer0_magnetic_field():
    env = EnvironmentLayer0(mode="lab")
    b_ref = env.get_reference_magnetic_field_uT()
    assert b_ref.shape == (3,)
    assert np.linalg.norm(b_ref) > 10.0  # Em torno de ~24 uT


def test_layer1_dynamics_and_torque():
    dyn = DynamicsLayer1()
    # Teste de zona morta
    assert dyn.calculate_actuator_torque(10.0) == 0.0
    assert dyn.calculate_actuator_torque(500.0) > 0.0
    assert dyn.calculate_actuator_torque(-500.0) < 0.0

    # Teste de integracao RK4
    w_next, q_next = dyn.step(dt=0.1, pwm_cmd=200.0)
    assert np.isclose(np.linalg.norm(q_next), 1.0, atol=1e-6)
    assert w_next > 0.0


def test_layer2_ekf_mirror_convergence():
    ekf = EkfMirrorLayer2()
    gyro = np.array([0.0, 0.0, 0.05])
    mag_meas = np.array([14.5, -2.5, -19.5])
    b_ref = np.array([14.5, -2.5, -19.5])

    # Roda 50 passos do filtro
    for _ in range(50):
        ekf.predict(gyro_raw=gyro, dt=0.05)
        ekf.update_magnetometer(mag_meas_uT=mag_meas, b_ref_uT=b_ref)

    assert np.isclose(np.linalg.norm(ekf.q_est), 1.0, atol=1e-5)
    assert ekf.convergence_status == 2  # Convergido


def test_layer3_angular_error_and_rmse():
    # Quaterioes identicos -> erro zero
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    q2 = np.array([1.0, 0.0, 0.0, 0.0])
    assert calculate_angular_error_deg(q1, q2) == 0.0

    # Rotacao de 10 graus em Z
    angle = np.radians(10.0)
    q_rot10 = np.array([np.cos(angle/2.0), 0.0, 0.0, np.sin(angle/2.0)])
    err = calculate_angular_error_deg(q1, q_rot10)
    assert pytest.approx(err, abs=1e-3) == 10.0

    # Layer 3 Sliding RMSE
    l3 = DivergenceLayer3(window_size=10)
    for _ in range(5):
        res = l3.update(q_sat=q1, q_twin=q_rot10, omega_sat=0.0, omega_twin=0.0)
    
    assert pytest.approx(res["theta_err_deg"], abs=1e-3) == 10.0
    assert pytest.approx(res["rmse_theta_deg"], abs=1e-3) == 10.0
    assert res["health_status"] == "DIVERGENTE"  # > 5 deg


def test_digital_twin_engine_end_to_end():
    engine = DigitalTwinEngine()
    pkt = TelemetryPacket(
        q_w=1.0, q_x=0.0, q_y=0.0, q_z=0.0,
        gyro_z=0.05,
        mag_x=14.5, mag_y=-2.5, mag_z=-19.5,
        actuator_pwm=100,
        arrival_time_s=100.0,
    )

    metrics = engine.process_packet(pkt)
    assert "theta_err_deg" in metrics
    assert "rmse_theta_deg" in metrics
    assert "health_status" in metrics
    assert engine.total_processed_packets == 1
