"""
tab_adcs.py
===========
Aba 3: Telemetria ADCS & Dinâmica de Atitude do PION Sat.
Gráficos de alta taxa para velocidades angulares (ômega), campo magnético (B), atuação PWM e status do EKF.
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
    Aba 3 da Ground Station: Dinâmica ADCS, atuação e convergência de estado.
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

        self.lbl_gyro_stat = QtWidgets.QLabel("ÔMEGA: X=+0.000 Y=+0.000 Z=+0.000 rad/s")
        self.lbl_gyro_stat.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
        top_layout.addWidget(self.lbl_gyro_stat)

        self.lbl_mag_stat = QtWidgets.QLabel("MAG |B|: 0.00 μT")
        self.lbl_mag_stat.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")
        top_layout.addWidget(self.lbl_mag_stat)

        self.lbl_pwm_stat = QtWidgets.QLabel("PWM: 0")
        self.lbl_pwm_stat.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: bold;")
        top_layout.addWidget(self.lbl_pwm_stat)

        self.lbl_ekf_stat = QtWidgets.QLabel("EKF: CONVERGIDO")
        self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        top_layout.addWidget(self.lbl_ekf_stat)

        main_layout.addWidget(top_bar)

        # 2. Grade de Gráficos (PyQtGraph)
        pg.setConfigOptions(antialias=True)
        plots_grid = QtWidgets.QGridLayout()
        plots_grid.setSpacing(10)

        # Gráfico 1: Velocidades Angulares (Omega_x, Omega_y, Omega_z)
        self.plot_gyro = pg.PlotWidget(title="VELOCIDADES ANGULARES (GIROSCÓPIO) [rad/s]")
        self.plot_gyro.setBackground(COLOR_BG_PANEL)
        self.plot_gyro.showGrid(x=True, y=True, alpha=0.2)
        self.plot_gyro.setLabel("left", "Ômega (rad/s)", color=COLOR_TEXT_PRIMARY)
        self.plot_gyro.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_gyro.addLegend()
        self.curve_gx = self.plot_gyro.plot(pen=pg.mkPen("#ef4444", width=2), name="ωx (Roll)")
        self.curve_gy = self.plot_gyro.plot(pen=pg.mkPen("#10b981", width=2), name="ωy (Pitch)")
        self.curve_gz = self.plot_gyro.plot(pen=pg.mkPen("#3b82f6", width=2), name="ωz (Yaw)")
        plots_grid.addWidget(self.plot_gyro, 0, 0)

        # Gráfico 2: Campo Magnético (Bx, By, Bz, |B|)
        self.plot_mag = pg.PlotWidget(title="CAMPO MAGNÉTICO (MAGNETÔMETRO) [μT]")
        self.plot_mag.setBackground(COLOR_BG_PANEL)
        self.plot_mag.showGrid(x=True, y=True, alpha=0.2)
        self.plot_mag.setLabel("left", "B (μT)", color=COLOR_TEXT_PRIMARY)
        self.plot_mag.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_mag.addLegend()
        self.curve_mx = self.plot_mag.plot(pen=pg.mkPen("#f59e0b", width=1.5), name="Bx")
        self.curve_my = self.plot_mag.plot(pen=pg.mkPen("#ec4899", width=1.5), name="By")
        self.curve_mz = self.plot_mag.plot(pen=pg.mkPen("#8b5cf6", width=1.5), name="Bz")
        self.curve_mn = self.plot_mag.plot(pen=pg.mkPen(COLOR_NOMINAL_GREEN, width=2), name="|B| Total")
        plots_grid.addWidget(self.plot_mag, 0, 1)

        # Gráfico 3: Atuação de Controle PWM
        self.plot_pwm = pg.PlotWidget(title="COMANDO DE ATUAÇÃO PWM (RODA DE REAÇÃO)")
        self.plot_pwm.setBackground(COLOR_BG_PANEL)
        self.plot_pwm.showGrid(x=True, y=True, alpha=0.2)
        self.plot_pwm.setLabel("left", "PWM (-1000..+1000)", color=COLOR_ACCENT_CYAN)
        self.plot_pwm.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_pwm = self.plot_pwm.plot(pen=pg.mkPen(COLOR_ACCENT_CYAN, width=2), name="PWM Cmd")
        plots_grid.addWidget(self.plot_pwm, 1, 0, 1, 2)

        main_layout.addLayout(plots_grid, stretch=1)

    def update_telemetry(self, packet: TelemetryPacket) -> None:
        """Atualiza os indicadores e adiciona pontos aos gráficos temporais de ADCS."""
        gx, gy, gz = packet.gyro_x, packet.gyro_y, packet.gyro_z
        mx, my, mz = packet.mag_x, packet.mag_y, packet.mag_z
        norm_b = math.sqrt(mx * mx + my * my + mz * mz)
        pwm = packet.actuator_pwm

        # 1. Barra de Status
        self.lbl_gyro_stat.setText(f"ÔMEGA: X={gx:+6.3f} Y={gy:+6.3f} Z={gz:+6.3f} rad/s")
        self.lbl_mag_stat.setText(f"MAG |B|: {norm_b:5.2f} μT")
        self.lbl_pwm_stat.setText(f"PWM: {pwm:+d}")

        ekf_names = {0: "INIT", 1: "DIVERGENTE", 2: "CONVERGIDO"}
        self.lbl_ekf_stat.setText(f"EKF: {ekf_names.get(packet.ekf_status, 'DESCONHECIDO')}")
        if packet.ekf_status == 2:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        elif packet.ekf_status == 1:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
        else:
            self.lbl_ekf_stat.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")

        # 2. Atualização dos Buffers
        self.gyro_x_buf.append(gx)
        self.gyro_y_buf.append(gy)
        self.gyro_z_buf.append(gz)

        self.mag_x_buf.append(mx)
        self.mag_y_buf.append(my)
        self.mag_z_buf.append(mz)
        self.mag_norm_buf.append(norm_b)

        self.pwm_buf.append(pwm)

        # 3. Atualização das Curvas
        self.curve_gx.setData(list(self.gyro_x_buf))
        self.curve_gy.setData(list(self.gyro_y_buf))
        self.curve_gz.setData(list(self.gyro_z_buf))

        self.curve_mx.setData(list(self.mag_x_buf))
        self.curve_my.setData(list(self.mag_y_buf))
        self.curve_mz.setData(list(self.mag_z_buf))
        self.curve_mn.setData(list(self.mag_norm_buf))

        self.curve_pwm.setData(list(self.pwm_buf))
