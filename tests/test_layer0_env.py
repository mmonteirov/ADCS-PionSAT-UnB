"""
test_layer0_env.py
==================
Testes unitários para a Camada 0 (Ambiente Espacial & Campo Magnético IGRF/Bancada).
"""

import numpy as np
import pytest

from src.twin.layers.layer0_env import EnvironmentLayer0


def test_layer0_initialization():
    env = EnvironmentLayer0(mode="lab")
    b_ref = env.get_reference_magnetic_field_uT()
    assert len(b_ref) == 3
    assert np.linalg.norm(b_ref) > 10.0  # uT em Brasília


def test_layer0_mode_orbital():
    env = EnvironmentLayer0(mode="orbit", year_decimal=2026.6)
    b_orb = env.get_reference_magnetic_field_uT(time_s=100.0)
    assert len(b_orb) == 3
    assert np.linalg.norm(b_orb) > 0.0
