"""
attitude_renderer_3d.py
=======================
Renderizador 3D acelerado por hardware via PyQtGraph / OpenGL para visualizacao da atitude
e posicao relativa em tempo real do satelite PION Sat a 60 FPS.
Suporta controle de visibilidade do chassi externo e colorizacao de alto contraste.
"""

from __future__ import annotations

import logging
import math
from typing import Optional, Tuple, Dict, Any

import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
from pyqtgraph import Transform3D
import pyqtgraph.opengl as gl

from src.ground_station.visualizer.cad_loader import (
    load_cad_mesh_dual,
)

logger = logging.getLogger(__name__)


def quaternion_to_rotation_matrix(w: float, x: float, y: float, z: float) -> np.ndarray:
    """
    Converte quaterion unitario (w, x, y, z) em matriz de rotacao 3x3 (Body -> Inertial/Lab).
    """
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm > 1e-12:
        w /= norm
        x /= norm
        y /= norm
        z /= norm
    else:
        return np.eye(3, dtype=np.float32)

    R = np.array([
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w),       2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w),       1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w),       2.0 * (y * z + x * w),       1.0 - 2.0 * (x * x + y * y)]
    ], dtype=np.float32)
    return R


class AttitudeRenderer3D(gl.GLViewWidget):
    """
    Viewport 3D OpenGL para renderizacao de atitude e vetores espaciais do satelite.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setBackgroundColor("#080c14")
        self.setCameraPosition(distance=320, elevation=25, azimuth=45)

        # 1. Grade de referencia do laboratorio
        self.grid = gl.GLGridItem()
        self.grid.setSize(x=500, y=500, z=0)
        self.grid.setSpacing(x=50, y=50, z=0)
        self.grid.setColor((30, 45, 70, 160))
        self.grid.translate(0, 0, -100)
        self.addItem(self.grid)

        # 2. Carrega as malhas CAD separadas (Pilha Interna e Chassi)
        cad_dual = load_cad_mesh_dual(cad_path="hardware/cad/Sat com chassi.step")
        
        self.int_base_v = cad_dual["internal_vertices"]
        self.int_faces = cad_dual["internal_faces"]
        self.int_colors = cad_dual["internal_colors"]

        self.cha_base_v = cad_dual["chassis_vertices"]
        self.cha_faces = cad_dual["chassis_faces"]
        # Transparencia em uma malha CAD complexa provoca artefatos de ordem de
        # desenho (faces aparecem e desaparecem durante a rotacao). O chassi
        # possui um controle proprio de visibilidade, portanto mantemo-lo opaco.
        self.cha_colors = cad_dual["chassis_colors"].copy()
        if len(self.cha_colors) > 0:
            self.cha_colors[:, 3] = 1.0

        # Item de malha da Pilha Interna (PCBs, Bateria, Pilares)
        self.internal_mesh_item = gl.GLMeshItem(
            vertexes=self.int_base_v.copy(),
            faces=self.int_faces,
            faceColors=self.int_colors,
            smooth=False,
            shader="shaded",
            glOptions="opaque",
        )
        self.addItem(self.internal_mesh_item)

        # Item de malha do Chassi Externo
        self.chassis_mesh_item = gl.GLMeshItem(
            vertexes=self.cha_base_v.copy(),
            faces=self.cha_faces,
            faceColors=self.cha_colors,
            smooth=False,
            shader="shaded",
            glOptions="opaque",
        )
        self.addItem(self.chassis_mesh_item)
        self.chassis_visible = True

        # 3. Eixos coordenados do referencial do corpo (Body Frame: X-Red, Y-Green, Z-Blue)
        self.axis_length = 95.0
        self.axis_lines = gl.GLLinePlotItem(
            pos=np.zeros((6, 3), dtype=np.float32),
            color=np.array([
                [1.0, 0.2, 0.2, 1.0], [1.0, 0.2, 0.2, 1.0],  # X - Vermelho
                [0.2, 1.0, 0.2, 1.0], [0.2, 1.0, 0.2, 1.0],  # Y - Verde
                [0.2, 0.5, 1.0, 1.0], [0.2, 0.5, 1.0, 1.0],  # Z - Azul
            ], dtype=np.float32),
            width=3.5,
            mode="lines",
        )
        self.addItem(self.axis_lines)

        # 4. Vetor de campo magnetico medido B (Ambar/Amarelo)
        self.mag_vector_line = gl.GLLinePlotItem(
            pos=np.zeros((2, 3), dtype=np.float32),
            color=np.array([[1.0, 0.8, 0.0, 1.0], [1.0, 0.8, 0.0, 1.0]], dtype=np.float32),
            width=3.0,
            mode="lines",
        )
        self.addItem(self.mag_vector_line)

        # Estado atual
        self.current_q = (1.0, 0.0, 0.0, 0.0)
        self.current_pos_mm = (0.0, 0.0, 0.0)
        self.update_attitude(1.0, 0.0, 0.0, 0.0, rel_pos_mm=(0.0, 0.0, 0.0))

    def set_chassis_visible(self, visible: bool) -> None:
        """Ativa ou desativa a exibicao do chassi externo."""
        self.chassis_visible = visible
        self.chassis_mesh_item.setVisible(visible)
        self.update()

    def toggle_chassis_visibility(self) -> bool:
        """Alterna a visibilidade do chassi externo e retorna o novo estado."""
        self.set_chassis_visible(not self.chassis_visible)
        return self.chassis_visible

    def update_attitude(
        self,
        q_w: float,
        q_x: float,
        q_y: float,
        q_z: float,
        rel_pos_mm: Optional[Tuple[float, float, float]] = None,
        mag_vector_uT: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """
        Atualiza a orientacao e translacao 3D do satelite a partir da telemetria recebida.
        """
        self.current_q = (q_w, q_x, q_y, q_z)
        R = quaternion_to_rotation_matrix(q_w, q_x, q_y, q_z)

        if rel_pos_mm is not None:
            self.current_pos_mm = rel_pos_mm
            pos_offset = np.array(rel_pos_mm, dtype=np.float32)
        else:
            pos_offset = np.array(self.current_pos_mm, dtype=np.float32)

        # 1/2. Atualiza somente a matriz de modelo. Recriar todos os vertices e
        # buffers OpenGL a cada pacote causava cintilacao no modelo CAD.
        transform = Transform3D([
            [R[0, 0], R[0, 1], R[0, 2], pos_offset[0]],
            [R[1, 0], R[1, 1], R[1, 2], pos_offset[1]],
            [R[2, 0], R[2, 1], R[2, 2], pos_offset[2]],
            [0.0, 0.0, 0.0, 1.0],
        ])
        self.internal_mesh_item.setTransform(transform)
        self.chassis_mesh_item.setTransform(transform)

        # 3. Eixos de corpo
        origin = pos_offset
        axis_x = origin + R[:, 0] * self.axis_length
        axis_y = origin + R[:, 1] * self.axis_length
        axis_z = origin + R[:, 2] * self.axis_length

        axis_points = np.array([
            origin, axis_x,
            origin, axis_y,
            origin, axis_z,
        ], dtype=np.float32)
        self.axis_lines.setData(pos=axis_points)

        # 4. Vetor de campo magnetico
        if mag_vector_uT is not None:
            bx, by, bz = mag_vector_uT
            b_norm = math.sqrt(bx * bx + by * by + bz * bz)
            if b_norm > 1e-3:
                b_scaled = (np.array([bx, by, bz], dtype=np.float32) / b_norm) * 85.0
                b_world = origin + np.dot(R, b_scaled)
                self.mag_vector_line.setData(pos=np.array([origin, b_world], dtype=np.float32))
            else:
                self.mag_vector_line.setData(pos=np.zeros((2, 3), dtype=np.float32))

        self.update()

    def reset_view(self) -> None:
        """Restaura a camera para a perspectiva e centro padroes."""
        self.opts['center'] = QtGui.QVector3D(0.0, 0.0, 0.0)
        self.opts['distance'] = 320.0
        self.opts['elevation'] = 25.0
        self.opts['azimuth'] = 45.0
        self.opts['fov'] = 60.0
        self.update()
