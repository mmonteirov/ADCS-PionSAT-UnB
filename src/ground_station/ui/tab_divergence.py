"""
tab_divergence.py
=================
Aba 4: Gêmeo Digital & Métricas de Divergência (DTiL - Digital Twin-in-the-Loop).
Comparação em tempo real entre satélite real e modelo matemático, erro angular (θ_err) e RMSE.
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
    Aba 4 da Ground Station: Monitoramento de divergência e validação do Gêmeo Digital.
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

        # Card Erro Angular Instantâneo
        card_err = QtWidgets.QFrame()
        card_err.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_err = QtWidgets.QVBoxLayout(card_err)
        l_err.addWidget(QtWidgets.QLabel("ERRO ANGULAR (θ_err)"))
        self.val_theta_err = QtWidgets.QLabel("0.00 deg")
        self.val_theta_err.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 20px; font-weight: bold;")
        l_err.addWidget(self.val_theta_err)
        self.sub_theta_err = QtWidgets.QLabel("Divergência Instantânea")
        self.sub_theta_err.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_err.addWidget(self.sub_theta_err)
        summary_layout.addWidget(card_err)

        # Card RMSE Janela Móvel
        card_rmse = QtWidgets.QFrame()
        card_rmse.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_rmse = QtWidgets.QVBoxLayout(card_rmse)
        l_rmse.addWidget(QtWidgets.QLabel("RMSE DE ATITUDE (120 s)"))
        self.val_rmse = QtWidgets.QLabel("0.00 deg")
        self.val_rmse.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        l_rmse.addWidget(self.val_rmse)
        self.sub_rmse = QtWidgets.QLabel("Limiar de Aceitação: < 5.0 deg")
        self.sub_rmse.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_rmse.addWidget(self.sub_rmse)
        summary_layout.addWidget(card_rmse)

        # Card Saúde do Gêmeo Digital
        card_health = QtWidgets.QFrame()
        card_health.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        l_h = QtWidgets.QVBoxLayout(card_health)
        l_h.addWidget(QtWidgets.QLabel("STATUS DTiL (GÊMEO DIGITAL)"))
        self.val_health = QtWidgets.QLabel("NOMINAL")
        self.val_health.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        l_h.addWidget(self.val_health)
        self.sub_health = QtWidgets.QLabel("Camadas 0 a 3 Sincronizadas")
        self.sub_health.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        l_h.addWidget(self.sub_health)
        summary_layout.addWidget(card_health)

        main_layout.addLayout(summary_layout)

        # 2. Gráficos Comparativos
        pg.setConfigOptions(antialias=True)
        plots_grid = QtWidgets.QGridLayout()
        plots_grid.setSpacing(10)

        # Gráfico 1: Erro Angular & RMSE
        self.plot_err = pg.PlotWidget(title="ERRO ANGULAR INSTANTÂNEO & RMSE (120 s) [graus]")
        self.plot_err.setBackground(COLOR_BG_PANEL)
        self.plot_err.showGrid(x=True, y=True, alpha=0.2)
        self.plot_err.setLabel("left", "Erro (°)", color=COLOR_ACCENT_CYAN)
        self.plot_err.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_err.addLegend()
        self.curve_err = self.plot_err.plot(pen=pg.mkPen(COLOR_ACCENT_CYAN, width=1.5), name="θ_err (Instantâneo)")
        self.curve_rmse = self.plot_err.plot(pen=pg.mkPen(COLOR_NOMINAL_GREEN, width=2.5), name="RMSE (120 s)")
        plots_grid.addWidget(self.plot_err, 0, 0)

        # Gráfico 2: Velocidade Angular Satélite vs Gêmeo Digital
        self.plot_omega = pg.PlotWidget(title="VELOCIDADE ANGULAR: SATÉLITE REAL VS GÊMEO DIGITAL [rad/s]")
        self.plot_omega.setBackground(COLOR_BG_PANEL)
        self.plot_omega.showGrid(x=True, y=True, alpha=0.2)
        self.plot_omega.setLabel("left", "ωz (rad/s)", color=COLOR_TEXT_PRIMARY)
        self.plot_omega.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.plot_omega.addLegend()
        self.curve_w_sat = self.plot_omega.plot(pen=pg.mkPen(COLOR_NOMINAL_GREEN, width=2), name="Satélite Real")
        self.curve_w_twin = self.plot_omega.plot(pen=pg.mkPen(COLOR_WARNING_AMBER, width=2, style=QtCore.Qt.PenStyle.DashLine), name="Gêmeo Digital (DTiL)")
        plots_grid.addWidget(self.plot_omega, 0, 1)

        main_layout.addLayout(plots_grid, stretch=1)

    def update_metrics(self, packet: TelemetryPacket, divergence_data: Optional[Dict[str, Any]] = None) -> None:
        """Atualiza a aba com as métricas de divergência calculadas pelo motor DTiL."""
        if not divergence_data:
            return

        theta_err = divergence_data.get("theta_err_deg", 0.0)
        rmse_theta = divergence_data.get("rmse_theta_deg", 0.0)
        health = divergence_data.get("health_status", "NOMINAL")
        w_twin = divergence_data.get("w_twin_rad_s", 0.0)
        w_sat = packet.gyro_z

        # 1. Cards
        self.val_theta_err.setText(f"{theta_err:.2f} deg")
        self.val_rmse.setText(f"{rmse_theta:.2f} deg")
        self.val_health.setText(health)

        if health == "NOMINAL":
            self.val_health.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
            self.val_rmse.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        elif health == "ATENCAO":
            self.val_health.setText("ATENÇÃO")
            self.val_health.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-size: 20px; font-weight: bold;")
            self.val_rmse.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-size: 20px; font-weight: bold;")
        else:
            self.val_health.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-size: 20px; font-weight: bold;")
            self.val_rmse.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-size: 20px; font-weight: bold;")

        # 2. Buffers
        self.theta_err_buf.append(theta_err)
        self.rmse_buf.append(rmse_theta)
        self.w_sat_buf.append(w_sat)
        self.w_twin_buf.append(w_twin)

        # 3. Curvas
        self.curve_err.setData(list(self.theta_err_buf))
        self.curve_rmse.setData(list(self.rmse_buf))
        self.curve_w_sat.setData(list(self.w_sat_buf))
        self.curve_w_twin.setData(list(self.w_twin_buf))
