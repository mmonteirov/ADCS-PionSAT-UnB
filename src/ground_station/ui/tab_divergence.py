"""
tab_divergence.py
=================
Aba 4: Gemeo Digital & Metricas de Divergencia (DTiL - Digital Twin-in-the-Loop).
Comparacao em tempo real entre hardware real e modelo matematico, erro angular (theta_err) e RMSE.
"""

from __future__ import annotations

from collections import deque
from typing import Optional, Dict, Any
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


class TabDivergence(QtWidgets.QWidget):
    """
    Aba 4 da Ground Station: Monitoramento de divergencia e validacao do Gemeo Digital.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.history_len = MAX_PLOT_POINTS

        # Buffers
        self.theta_err_buf = deque(maxlen=self.history_len)
        self.rmse_buf = deque(maxlen=self.history_len)
        self.w_sat_buf = deque(maxlen=self.history_len)
        self.w_twin_buf = deque(maxlen=self.history_len)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Cards de Resumo Superior
        summary_layout = QtWidgets.QHBoxLayout()
        summary_layout.setSpacing(10)

        # Card Erro Angular Instantaneo
        card_err = QtWidgets.QFrame()
        card_err.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_err = QtWidgets.QVBoxLayout(card_err)
        l_err.addWidget(QtWidgets.QLabel("ERRO ANGULAR (THETA_ERR)"))
        self.val_theta_err = QtWidgets.QLabel("0.00 deg")
        self.val_theta_err.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 20px; font-weight: bold;")
        l_err.addWidget(self.val_theta_err)
        self.sub_theta_err = QtWidgets.QLabel("Divergencia Instantanea")
        self.sub_theta_err.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_err.addWidget(self.sub_theta_err)
        summary_layout.addWidget(card_err)

        # Card RMSE Janela Movel
        card_rmse = QtWidgets.QFrame()
        card_rmse.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_rmse = QtWidgets.QVBoxLayout(card_rmse)
        l_rmse.addWidget(QtWidgets.QLabel("RMSE DE ATITUDE (120s)"))
        self.val_rmse = QtWidgets.QLabel("0.00 deg")
        self.val_rmse.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        l_rmse.addWidget(self.val_rmse)
        self.sub_rmse = QtWidgets.QLabel("Limiar de Aceitacao: < 5.0 deg")
        self.sub_rmse.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_rmse.addWidget(self.sub_rmse)
        summary_layout.addWidget(card_rmse)

        # Card Saude do Gemeo Digital
        card_health = QtWidgets.QFrame()
        card_health.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_h = QtWidgets.QVBoxLayout(card_health)
        l_h.addWidget(QtWidgets.QLabel("STATUS DTiL (GEMEO DIGITAL)"))
        self.val_health = QtWidgets.QLabel("NOMINAL")
        self.val_health.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        l_h.addWidget(self.val_health)
        self.sub_health = QtWidgets.QLabel("Camadas 0 a 3 Sincronizadas")
        self.sub_health.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_h.addWidget(self.sub_health)
        summary_layout.addWidget(card_health)

        main_layout.addLayout(summary_layout)

        # 2. Graficos Comparativos
        pg.setConfigOptions(antialias=True)
        plots_grid = QtWidgets.QGridLayout()
        plots_grid.setSpacing(10)

        # Grafico 1: Erro Angular e RMSE
        self.plot_err = pg.PlotWidget(title="ERRO DE ATITUDE & RMSE (SATELITE vs GEMEO DIGITAL) [deg]")
        self.plot_err.setBackground(COLOR_BG_PANEL)
        self.plot_err.showGrid(x=True, y=True, alpha=0.2)
        self.plot_err.setLabel("left", "Erro (deg)", color=COLOR_TEXT_PRIMARY)
        self.plot_err.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_err.addLegend(offset=(10, 10))
        self.curve_theta_err = self.plot_err.plot(pen=pg.mkPen(COLOR_ACCENT_CYAN, width=2), name="Theta_Err Instantaneo")
        self.curve_rmse = self.plot_err.plot(pen=pg.mkPen(COLOR_NOMINAL_GREEN, width=2.5, style=QtCore.Qt.PenStyle.DashLine), name="RMSE 120s")
        plots_grid.addWidget(self.plot_err, 0, 0)

        # Grafico 2: Velocidade Angular Sat vs Twin (Eixo Z de Controle)
        self.plot_comp_omega = pg.PlotWidget(title="COMPARACAO DE VELOCIDADE ANGULAR OMEGA_Z (SATELITE vs GEMEO) [rad/s]")
        self.plot_comp_omega.setBackground(COLOR_BG_PANEL)
        self.plot_comp_omega.showGrid(x=True, y=True, alpha=0.2)
        self.plot_comp_omega.setLabel("left", "Omega_Z (rad/s)", color=COLOR_TEXT_PRIMARY)
        self.plot_comp_omega.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_comp_omega.addLegend(offset=(10, 10))
        self.curve_wsat = self.plot_comp_omega.plot(pen=pg.mkPen("#00e5ff", width=2), name="Omega_Z Hardware Sat")
        self.curve_wtwin = self.plot_comp_omega.plot(pen=pg.mkPen("#ffb703", width=2, style=QtCore.Qt.PenStyle.DashLine), name="Omega_Z Digital Twin")
        plots_grid.addWidget(self.plot_comp_omega, 0, 1)

        main_layout.addLayout(plots_grid, stretch=1)

    def update_metrics(
        self,
        packet: TelemetryPacket,
        divergence_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atualiza os graficos com as metricas da Camada 3 do Digital Twin."""
        theta_err = 0.0
        rmse = 0.0
        w_twin = packet.gyro_z
        health = "NOMINAL"

        if divergence_data:
            theta_err = float(divergence_data.get("theta_err_deg", 0.0))
            rmse = float(divergence_data.get("rmse_theta_deg", 0.0))
            w_twin = float(divergence_data.get("twin_omega_z", packet.gyro_z))
            health = str(divergence_data.get("health_status", "NOMINAL"))

        # Atualiza labels
        self.val_theta_err.setText(f"{theta_err:.2f} deg")
        self.val_rmse.setText(f"{rmse:.2f} deg")
        self.val_health.setText(health)

        if health == "NOMINAL":
            self.val_health.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        elif health == "DRIFT":
            self.val_health.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-size: 20px; font-weight: bold;")
        else:
            self.val_health.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-size: 20px; font-weight: bold;")

        # Atualiza buffers
        self.theta_err_buf.append(theta_err)
        self.rmse_buf.append(rmse)
        self.w_sat_buf.append(packet.gyro_z)
        self.w_twin_buf.append(w_twin)

        # Atualiza curvas
        self.curve_theta_err.setData(list(self.theta_err_buf))
        self.curve_rmse.setData(list(self.rmse_buf))
        self.curve_wsat.setData(list(self.w_sat_buf))
        self.curve_wtwin.setData(list(self.w_twin_buf))
