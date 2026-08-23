"""
tab_3d_attitude.py
==================
Aba 1: Visão Geral & Atitude 3D em Tempo Real.
Renderiza o modelo CAD colorido do satélite orientando-se pelos quatérnios reais,
com suporte a ativação/desativação do chassi e modo de simulação integrado.
"""

from __future__ import annotations

from typing import Optional
from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.visualizer.attitude_renderer_3d import AttitudeRenderer3D
from src.ground_station.ui.style import (
    COLOR_BG_PANEL,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_ACCENT_CYAN,
    COLOR_NOMINAL_GREEN,
    COLOR_WARNING_AMBER,
    COLOR_ALERT_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)


class Tab3DAttitude(QtWidgets.QWidget):
    """
    Aba 1 da Ground Station: Visualizador 3D do satélite e resumo de atitude.
    """

    request_toggle_mock = QtCore.pyqtSignal(bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Viewport 3D Principal (Esquerda / Centro)
        self.viewport_3d = AttitudeRenderer3D(self)
        main_layout.addWidget(self.viewport_3d, stretch=3)

        # 2. Barra Lateral de Telemetria e Controles (Direita)
        sidebar = QtWidgets.QWidget()
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        # Card: Atitude (Ângulos de Euler e Quatérnios)
        group_attitude = QtWidgets.QGroupBox("ATITUDE ESPACIAL")
        layout_att = QtWidgets.QVBoxLayout(group_attitude)
        layout_att.setSpacing(6)

        grid_euler = QtWidgets.QGridLayout()
        grid_euler.setSpacing(8)

        lbl_r_title = QtWidgets.QLabel("ROLL (PHI)")
        lbl_r_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        self.val_roll = QtWidgets.QLabel("+0.00 deg")
        self.val_roll.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 16px; font-weight: bold;")

        lbl_p_title = QtWidgets.QLabel("PITCH (THETA)")
        lbl_p_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        self.val_pitch = QtWidgets.QLabel("+0.00 deg")
        self.val_pitch.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 16px; font-weight: bold;")

        lbl_y_title = QtWidgets.QLabel("YAW (PSI)")
        lbl_y_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        self.val_yaw = QtWidgets.QLabel("+0.00 deg")
        self.val_yaw.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 16px; font-weight: bold;")

        grid_euler.addWidget(lbl_r_title, 0, 0)
        grid_euler.addWidget(self.val_roll, 1, 0)
        grid_euler.addWidget(lbl_p_title, 0, 1)
        grid_euler.addWidget(self.val_pitch, 1, 1)
        grid_euler.addWidget(lbl_y_title, 0, 2)
        grid_euler.addWidget(self.val_yaw, 1, 2)
        layout_att.addLayout(grid_euler)

        self.val_quat = QtWidgets.QLabel("Q = [1.0000, 0.0000, 0.0000, 0.0000]")
        self.val_quat.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; padding-top: 4px;")
        layout_att.addWidget(self.val_quat)

        sidebar_layout.addWidget(group_attitude)

        # Card: Posição Relativa na Bancada
        group_pos = QtWidgets.QGroupBox("POSIÇÃO RELATIVA (BANCADA)")
        layout_pos = QtWidgets.QHBoxLayout(group_pos)
        
        self.val_pos_x = QtWidgets.QLabel("DX: 0 mm")
        self.val_pos_y = QtWidgets.QLabel("DY: 0 mm")
        self.val_pos_z = QtWidgets.QLabel("DZ: 0 mm")
        for lbl in (self.val_pos_x, self.val_pos_y, self.val_pos_z):
            lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
            layout_pos.addWidget(lbl)
        
        sidebar_layout.addWidget(group_pos)

        # Card: Resumo da Bateria
        group_bat = QtWidgets.QGroupBox("SISTEMA DE ENERGIA (EPS)")
        layout_bat = QtWidgets.QVBoxLayout(group_bat)
        
        h_bat = QtWidgets.QHBoxLayout()
        self.val_vbat = QtWidgets.QLabel("0.00 V")
        self.val_vbat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 15px; font-weight: bold;")
        self.val_ibat = QtWidgets.QLabel("0 mA")
        self.val_ibat.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        h_bat.addWidget(self.val_vbat)
        h_bat.addWidget(self.val_ibat)
        layout_bat.addLayout(h_bat)

        self.bar_soc = QtWidgets.QProgressBar()
        self.bar_soc.setRange(0, 100)
        self.bar_soc.setValue(100)
        self.bar_soc.setFixedHeight(14)
        self.bar_soc.setFormat("SoC %p%")
        layout_bat.addWidget(self.bar_soc)

        sidebar_layout.addWidget(group_bat)

        # Card: Status Operacional
        group_status = QtWidgets.QGroupBox("STATUS OPERACIONAL")
        layout_st = QtWidgets.QGridLayout(group_status)
        layout_st.setSpacing(6)

        layout_st.addWidget(QtWidgets.QLabel("MODO:"), 0, 0)
        self.val_mode = QtWidgets.QLabel("IDLE")
        self.val_mode.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")
        layout_st.addWidget(self.val_mode, 0, 1)

        layout_st.addWidget(QtWidgets.QLabel("EKF:"), 1, 0)
        self.val_ekf = QtWidgets.QLabel("CONVERGIDO")
        self.val_ekf.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        layout_st.addWidget(self.val_ekf, 1, 1)

        layout_st.addWidget(QtWidgets.QLabel("ENLACE:"), 2, 0)
        self.val_rate = QtWidgets.QLabel("0.0 Hz (0 pkts)")
        self.val_rate.setStyleSheet(f"color: {COLOR_ACCENT_CYAN};")
        layout_st.addWidget(self.val_rate, 2, 1)

        sidebar_layout.addWidget(group_status)

        # Card: Controles 3D e Emulação
        group_ctrl = QtWidgets.QGroupBox("CONTROLES DE VISUALIZAÇÃO")
        layout_ctrl = QtWidgets.QVBoxLayout(group_ctrl)
        layout_ctrl.setSpacing(8)

        # Botão de Alternar Visibilidade do Chassi
        self.btn_toggle_chassis = QtWidgets.QPushButton("CHASSI: VISÍVEL")
        self.btn_toggle_chassis.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
        self.btn_toggle_chassis.clicked.connect(self._on_toggle_chassis)
        layout_ctrl.addWidget(self.btn_toggle_chassis)

        # Botão de Reset de Câmera
        btn_reset_cam = QtWidgets.QPushButton("REINICIAR CÂMERA 3D")
        btn_reset_cam.clicked.connect(self.viewport_3d.reset_view)
        layout_ctrl.addWidget(btn_reset_cam)

        # Botão de Emulação / Simulador
        self.btn_mock_sim = QtWidgets.QPushButton("ATIVAR EMULAÇÃO / TESTE")
        self.btn_mock_sim.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")
        self.btn_mock_sim.clicked.connect(self._on_toggle_mock)
        layout_ctrl.addWidget(self.btn_mock_sim)

        sidebar_layout.addWidget(group_ctrl)
        sidebar_layout.addStretch(1)
        main_layout.addWidget(sidebar, stretch=1)

    def _on_toggle_chassis(self) -> None:
        """Alterna a exibição do chassi externo."""
        is_vis = self.viewport_3d.toggle_chassis_visibility()
        if is_vis:
            self.btn_toggle_chassis.setText("CHASSI: VISÍVEL")
            self.btn_toggle_chassis.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
        else:
            self.btn_toggle_chassis.setText("CHASSI: OCULTO (PILHA INTERNA)")
            self.btn_toggle_chassis.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")

    def _on_toggle_mock(self) -> None:
        """Ativa/desativa o gerador de telemetria de teste."""
        self._is_mock_active = not getattr(self, "_is_mock_active", False)
        self.set_mock_state(self._is_mock_active)
        self.request_toggle_mock.emit(self._is_mock_active)

    def set_mock_state(self, active: bool) -> None:
        """Sincroniza o estado visual do botão de emulação."""
        self._is_mock_active = active
        if active:
            self.btn_mock_sim.setText("DESATIVAR EMULAÇÃO")
            self.btn_mock_sim.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
        else:
            self.btn_mock_sim.setText("ATIVAR EMULAÇÃO / TESTE")
            self.btn_mock_sim.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")

    def update_telemetry(self, packet: TelemetryPacket, stats: Optional[dict[str, float]] = None) -> None:
        """Atualiza a aba com o pacote de telemetria mais recente."""
        # 1. Viewport 3D
        self.viewport_3d.update_attitude(
            q_w=packet.q_w,
            q_x=packet.q_x,
            q_y=packet.q_y,
            q_z=packet.q_z,
            rel_pos_mm=(float(packet.rel_pos_x), float(packet.rel_pos_y), float(packet.rel_pos_z)),
            mag_vector_uT=(packet.mag_x, packet.mag_y, packet.mag_z),
        )

        # 2. Ângulos de Euler
        roll, pitch, yaw = packet.euler_angles_deg
        self.val_roll.setText(f"{roll:+6.2f} deg")
        self.val_pitch.setText(f"{pitch:+6.2f} deg")
        self.val_yaw.setText(f"{yaw:+6.2f} deg")

        self.val_quat.setText(
            f"Q = [{packet.q_w:+.4f}, {packet.q_x:+.4f}, {packet.q_y:+.4f}, {packet.q_z:+.4f}]"
        )

        # 3. Posição relativa
        self.val_pos_x.setText(f"DX: {packet.rel_pos_x:+d} mm")
        self.val_pos_y.setText(f"DY: {packet.rel_pos_y:+d} mm")
        self.val_pos_z.setText(f"DZ: {packet.rel_pos_z:+d} mm")

        # 4. Bateria
        self.val_vbat.setText(f"{packet.v_bat_v:.2f} V")
        self.val_ibat.setText(f"{packet.i_bat_ma:+d} mA")
        self.bar_soc.setValue(int(packet.soc_percent))
        if packet.soc_percent < 20:
            self.bar_soc.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLOR_ALERT_RED}; }}")
        elif packet.soc_percent < 50:
            self.bar_soc.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLOR_WARNING_AMBER}; }}")
        else:
            self.bar_soc.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLOR_NOMINAL_GREEN}; }}")

        # 5. Modos e Status
        modes_map = {0: "IDLE", 1: "B-DOT", 2: "POINTING", 3: "CALIBRAÇÃO"}
        self.val_mode.setText(modes_map.get(packet.sys_mode, f"MODO {packet.sys_mode}"))

        ekf_map = {0: "INIT", 1: "DIVERGENTE", 2: "CONVERGIDO"}
        ekf_text = ekf_map.get(packet.ekf_status, "DESCONHECIDO")
        self.val_ekf.setText(ekf_text)
        if packet.ekf_status == 2:
            self.val_ekf.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        elif packet.ekf_status == 1:
            self.val_ekf.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
        else:
            self.val_ekf.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-weight: bold;")

        # Taxa de pacotes
        if stats:
            rate = stats.get("packet_rate_hz", 0.0)
            pkts = int(stats.get("packets_received", 0))
            self.val_rate.setText(f"{rate:.1f} Hz ({pkts} pkts)")
