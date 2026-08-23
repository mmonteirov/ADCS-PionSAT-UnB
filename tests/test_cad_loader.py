"""
test_cad_loader.py
==================
Testes automatizados para o carregador de malha CAD e funcoes geometricas tridimensionais.
"""

import numpy as np
import pytest

from src.ground_station.visualizer.cad_loader import (
    load_cad_mesh,
    load_cad_mesh_dual,
    generate_fallback_cubesat_mesh,
)
from src.ground_station.visualizer.attitude_renderer_3d import (
    quaternion_to_rotation_matrix,
)


def test_fallback_cubesat_mesh():
    res = generate_fallback_cubesat_mesh()
    assert len(res) == 8
    iv, ifc, inorm, icol, cv, cfc, cnorm, ccol = res
    assert len(iv) == 8
    assert len(ifc) == 12
    assert len(cv) == 8
    assert len(cfc) == 12


def test_cad_loader_load():
    verts, faces, normals, colors = load_cad_mesh(
        cad_path="hardware/cad/Sat com chassi.step"
    )
    assert len(verts) > 0
    assert len(faces) > 0
    assert len(normals) == len(faces)
    assert len(colors) == len(faces)


def test_cad_loader_dual():
    dual = load_cad_mesh_dual(cad_path="hardware/cad/Sat com chassi.step")
    assert "internal_vertices" in dual
    assert "chassis_vertices" in dual
    assert len(dual["internal_vertices"]) > 0
    assert len(dual["chassis_vertices"]) > 0


def test_quaternion_to_rotation_matrix():
    # Identidade
    R_id = quaternion_to_rotation_matrix(1.0, 0.0, 0.0, 0.0)
    assert np.allclose(R_id, np.eye(3), atol=1e-5)
    assert np.isclose(np.linalg.det(R_id), 1.0, atol=1e-5)

    # 90 graus em torno do eixo Z (Yaw)
    angle = np.pi / 2.0
    qw = np.cos(angle / 2.0)
    qz = np.sin(angle / 2.0)
    R_z90 = quaternion_to_rotation_matrix(qw, 0.0, 0.0, qz)

    # Vetor [1, 0, 0] rodado 90 graus vira [0, 1, 0]
    v = np.array([1.0, 0.0, 0.0])
    v_rot = np.dot(R_z90, v)
    assert np.allclose(v_rot, [0.0, 1.0, 0.0], atol=1e-5)
    assert np.isclose(np.linalg.det(R_z90), 1.0, atol=1e-5)
    assert np.allclose(np.dot(R_z90, R_z90.T), np.eye(3), atol=1e-5)
