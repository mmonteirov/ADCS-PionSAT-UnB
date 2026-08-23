"""
tab_adcs.py
===========
Aba 3: Telemetria ADCS & Dinamica de Atitude do PION Sat.
Graficos de alta taxa para velocidades angulares (omega), campo magnetico (B), atuacao PWM e status do EKF.
"""

from __future__ import annotations

from collections import deque
import math
from typing import Optional
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.ui.style import (
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_ACCENT_CYAN,
    COLOR_NOMINAL_GREEN,
    COLOR_WARNING_AMBER,
    COLOR_ALERT_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)

MAX_PLOT_POINTS = 200


class TabADCS(QtWidgets.QWidget):
    """
    Aba 3 da Ground Station: Dinamica ADCS, atuacao e convergencia de estado.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.history_len = MAX_PLOT_POINTS

        # Buffers temporais
        self.gyro_x_buf = deque(maxlen=self.history_len)
        self.gyro_y_buf = deque(maxlen=self.history_len)
        self.gyro_z_buf = deque(maxlen=self.history_len)

        self.mag_x_buf = deque(maxlen=self.history_len)
        self.mag_y_buf = deque(maxlen=self.history_len)
        self.mag_z_buf = deque(maxlen=self.history_len)
        self.mag_norm_buf = deque(maxlen=self.history_len)

        self.pwm_buf = deque(maxlen=self.history_len)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Painel de Status Superior
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 4, 12, 4)

        self.lbl_gyro_stat = QtWidgets.QLabel("OMEGA: X=+0.000 Y=+0.000 Z=+0.000 rad/s")
        self.lbl_gyro_stat.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
        top_layout.addWidget(self.lbl_gyro_stat)

        self.lbl_mag_stat = QtWidgets.QLabel("MAG |B|: 0.00 uT")
        self.lbl_mag_stat.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")
        top_layout.addWidget(self.lbl_mag_stat)

        self.lbl_pwm_stat = QtWidgets.QLabel("PWM: 0")
        self.lbl_pwm_stat.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: bold;")
        top_layout.addWidget(self.lbl_pwm_stat)

        self.lbl_ekf_stat = QtWidgets.QLabel("EKF: CONVERGIDO")
        self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        top_layout.addWidget(self.lbl_ekf_stat)

        main_layout.addWidget(top_bar)

        # 2. Grade de Graficos (PyQtGraph)
        pg.setConfigOptions(antialias=True)
        plots_grid = QtWidgets.QGridLayout()
        plots_grid.setSpacing(10)

        # Grafico 1: Velocidades Angulares (Omega_x, Omega_y, Omega_z)
        self.plot_gyro = pg.PlotWidget(title="VELOCIDADES ANGULARES (GIROSCOPIO) [rad/s]")
        self.plot_gyro.setBackground(COLOR_BG_PANEL)
        self.plot_gyro.showGrid(x=True, y=True, alpha=0.2)
        self.plot_gyro.setLabel("left", "Omega (rad/s)", color=COLOR_TEXT_PRIMARY)
        self.plot_gyro.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_gyro.addLegend(offset=(10, 10))
        self.curve_gx = self.plot_gyro.plot(pen=pg.mkPen("#ff4d4d", width=2), name="Omega_X")
        self.curve_gy = self.plot_gyro.plot(pen=pg.mkPen("#4dff4d", width=2), name="Omega_Y")
        self.curve_gz = self.plot_gyro.plot(pen=pg.mkPen("#4da6ff", width=2), name="Omega_Z")
        plots_grid.addWidget(self.plot_gyro, 0, 0)

        # Grafico 2: Campo Magnetico (Bx, By, Bz e |B|)
        self.plot_mag = pg.PlotWidget(title="CAMPO MAGNETICO CALIBRADO [uT]")
        self.plot_mag.setBackground(COLOR_BG_PANEL)
        self.plot_mag.showGrid(x=True, y=True, alpha=0.2)
        self.plot_mag.setLabel("left", "B (uT)", color=COLOR_TEXT_PRIMARY)
        self.plot_mag.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_mag.addLegend(offset=(10, 10))
        self.curve_bx = self.plot_mag.plot(pen=pg.mkPen("#ff7b00", width=1.5), name="B_X")
        self.curve_by = self.plot_mag.plot(pen=pg.mkPen("#ffd000", width=1.5), name="B_Y")
        self.curve_bz = self.plot_mag.plot(pen=pg.mkPen("#00e5ff", width=1.5), name="B_Z")
        self.curve_bnorm = self.plot_mag.plot(pen=pg.mkPen("#ffffff", width=2, style=QtCore.Qt.PenStyle.DashLine), name="|B|")
        plots_grid.addWidget(self.plot_mag, 0, 1)

        # Grafico 3: Comando de Atuacao PWM
        self.plot_pwm = pg.PlotWidget(title="COMANDO DE ATUACAO (PWM ATUADOR)")
        self.plot_pwm.setBackground(COLOR_BG_PANEL)
        self.plot_pwm.showGrid(x=True, y=True, alpha=0.2)
        self.plot_pwm.setLabel("left", "PWM (-1000 a +1000)", color=COLOR_ACCENT_CYAN)
        self.plot_pwm.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_pwm = self.plot_pwm.plot(pen=pg.mkPen(COLOR_ACCENT_CYAN, width=2), name="PWM")
        plots_grid.addWidget(self.plot_pwm, 1, 0, 1, 2)

        main_layout.addLayout(plots_grid, stretch=1)

    def update_telemetry(self, packet: TelemetryPacket) -> None:
        """Atualiza graficos e metricas de dinamica."""
        # Atualiza labels de status
        self.lbl_gyro_stat.setText(
            f"OMEGA: X={packet.gyro_x:+.4f} Y={packet.gyro_y:+.4f} Z={packet.gyro_z:+.4f} rad/s"
        )
        b_norm = packet.mag_norm
        self.lbl_mag_stat.setText(f"MAG |B|: {b_norm:.2f} uT (X={packet.mag_x:+.1f} Y={packet.mag_y:+.1f} Z={packet.mag_z:+.1f})")
        self.lbl_pwm_stat.setText(f"PWM: {packet.actuator_pwm:+d}")

        ekf_map = {0: "INIT", 1: "DIVERGENTE", 2: "CONVERGIDO"}
        ekf_text = ekf_map.get(packet.ekf_status, "DESCONHECIDO")
        self.lbl_ekf_stat.setText(f"EKF: {ekf_text}")
        if packet.ekf_status == 2:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        elif packet.ekf_status == 1:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
        else:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")

        # Atualiza buffers
        self.gyro_x_buf.append(packet.gyro_x)
        self.gyro_y_buf.append(packet.gyro_y)
        self.gyro_z_buf.append(packet.gyro_z)

        self.mag_x_buf.append(packet.mag_x)
        self.mag_y_buf.append(packet.mag_y)
        self.mag_z_buf.append(packet.mag_z)
        self.mag_norm_buf.append(b_norm)

        self.pwm_buf.append(packet.actuator_pwm)

        # Atualiza curvas
        self.curve_gx.setData(list(self.gyro_x_buf))
        self.curve_gy.setData(list(self.gyro_y_buf))
        self.curve_gz.setData(list(self.gyro_z_buf))

        self.curve_bx.setData(list(self.mag_x_buf))
        self.curve_by.setData(list(self.mag_y_buf))
        self.curve_bz.setData(list(self.mag_z_buf))
        self.curve_bnorm.setData(list(self.mag_norm_buf))

        self.curve_pwm.setData(list(self.pwm_buf))
