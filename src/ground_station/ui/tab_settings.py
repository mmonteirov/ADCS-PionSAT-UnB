"""
tab_settings.py
===============
Aba 5: Gerenciador de Conexão Serial USB, Gravação de Telemetria e Configurações.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable
from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.telemetry.serial_receiver import list_available_serial_ports
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

logger = logging.getLogger(__name__)


class TabSettings(QtWidgets.QWidget):
    """
    Aba 5 da Ground Station: Gerenciador de comunicação serial e gravação de dados.
    """

    # Sinais emitidos para a janela principal
    request_connect = QtCore.pyqtSignal(str, int)     # port, baudrate
    request_disconnect = QtCore.pyqtSignal()
    request_start_logging = QtCore.pyqtSignal(str)   # custom_filename
    request_stop_logging = QtCore.pyqtSignal()
    request_reset_twin = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self.refresh_ports()

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # 1. Grupo Conexão Serial USB
        group_serial = QtWidgets.QGroupBox("CONEXÃO SERIAL / USB")
        l_serial = QtWidgets.QGridLayout(group_serial)
        l_serial.setSpacing(10)

        l_serial.addWidget(QtWidgets.QLabel("PORTA SERIAL:"), 0, 0)
        self.combo_ports = QtWidgets.QComboBox()
        l_serial.addWidget(self.combo_ports, 0, 1)

        self.btn_refresh = QtWidgets.QPushButton("ATUALIZAR PORTAS")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        l_serial.addWidget(self.btn_refresh, 0, 2)

        l_serial.addWidget(QtWidgets.QLabel("TAXA (BAUDRATE):"), 1, 0)
        self.combo_baud = QtWidgets.QComboBox()
        self.combo_baud.addItems(["115200", "921600", "57600", "230400", "460800"])
        self.combo_baud.setCurrentText("115200")
        l_serial.addWidget(self.combo_baud, 1, 1)

        self.btn_toggle_connect = QtWidgets.QPushButton("CONECTAR")
        self.btn_toggle_connect.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
        self.btn_toggle_connect.clicked.connect(self._on_toggle_connect)
        l_serial.addWidget(self.btn_toggle_connect, 1, 2)

        self.lbl_conn_status = QtWidgets.QLabel("STATUS: DESCONECTADO")
        self.lbl_conn_status.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
        l_serial.addWidget(self.lbl_conn_status, 2, 0, 1, 3)

        main_layout.addWidget(group_serial)

        # 2. Grupo Gravação de Telemetria (CSV)
        group_logging = QtWidgets.QGroupBox("GRAVAÇÃO DE SESSÃO (CSV)")
        l_log = QtWidgets.QGridLayout(group_logging)
        l_log.setSpacing(10)

        l_log.addWidget(QtWidgets.QLabel("NOME DO ARQUIVO:"), 0, 0)
        self.edit_log_name = QtWidgets.QLineEdit()
        self.edit_log_name.setPlaceholderText("Deixe em branco para carimbo de data/hora automático")
        l_log.addWidget(self.edit_log_name, 0, 1)

        self.btn_toggle_log = QtWidgets.QPushButton("INICIAR GRAVAÇÃO")
        self.btn_toggle_log.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
        self.btn_toggle_log.clicked.connect(self._on_toggle_log)
        l_log.addWidget(self.btn_toggle_log, 0, 2)

        self.lbl_log_status = QtWidgets.QLabel("GRAVAÇÃO: INATIVA (0 pacotes gravados)")
        self.lbl_log_status.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        l_log.addWidget(self.lbl_log_status, 1, 0, 1, 3)

        main_layout.addWidget(group_logging)

        # 3. Grupo Telecomandos & Calibração
        group_cmd = QtWidgets.QGroupBox("CALIBRAÇÃO & COMANDOS OPERACIONAIS")
        l_cmd = QtWidgets.QHBoxLayout(group_cmd)
        l_cmd.setSpacing(10)

        btn_reset_twin = QtWidgets.QPushButton("REINICIAR FILTROS / GÊMEO DIGITAL")
        btn_reset_twin.clicked.connect(lambda: self.request_reset_twin.emit())
        l_cmd.addWidget(btn_reset_twin)

        main_layout.addWidget(group_cmd)
        main_layout.addStretch(1)

    def refresh_ports(self) -> None:
        """Atualiza a lista de portas seriais detectadas."""
        ports = list_available_serial_ports()
        current = self.combo_ports.currentText()
        self.combo_ports.clear()
        if ports:
            self.combo_ports.addItems(ports)
            if current in ports:
                self.combo_ports.setCurrentText(current)
            elif "/dev/ttyUSB0" in ports:
                self.combo_ports.setCurrentText("/dev/ttyUSB0")
            elif "/dev/ttyACM0" in ports:
                self.combo_ports.setCurrentText("/dev/ttyACM0")
        else:
            self.combo_ports.addItem("Nenhuma porta encontrada")

    def _on_toggle_connect(self) -> None:
        if self.btn_toggle_connect.text() == "CONECTAR":
            port = self.combo_ports.currentText()
            if not port or port == "Nenhuma porta encontrada":
                QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma porta serial selecionada.")
                return
            baud = int(self.combo_baud.currentText())
            self.request_connect.emit(port, baud)
        else:
            self.request_disconnect.emit()

    def set_connected_state(self, connected: bool, port: str = "", baud: int = 115200) -> None:
        """Atualiza o estado visual da interface de conexão."""
        if connected:
            self.btn_toggle_connect.setText("DESCONECTAR")
            self.btn_toggle_connect.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
            self.lbl_conn_status.setText(f"STATUS: CONECTADO A {port} ({baud} bps)")
            self.lbl_conn_status.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
            self.combo_ports.setEnabled(False)
            self.combo_baud.setEnabled(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.btn_toggle_connect.setText("CONECTAR")
            self.btn_toggle_connect.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
            self.lbl_conn_status.setText("STATUS: DESCONECTADO")
            self.lbl_conn_status.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
            self.combo_ports.setEnabled(True)
            self.combo_baud.setEnabled(True)
            self.btn_refresh.setEnabled(True)

    def _on_toggle_log(self) -> None:
        if "INICIAR" in self.btn_toggle_log.text():
            custom_name = self.edit_log_name.text().strip() or None
            self.request_start_logging.emit(custom_name or "")
        else:
            self.request_stop_logging.emit()

    def set_logging_state(self, is_logging: bool, filepath: str = "", count: int = 0) -> None:
        """Atualiza o estado visual da gravação CSV."""
        if is_logging:
            self.btn_toggle_log.setText("PARAR GRAVAÇÃO")
            self.btn_toggle_log.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-weight: bold;")
            self.lbl_log_status.setText(f"GRAVANDO: {filepath} ({count} pacotes)")
            self.lbl_log_status.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-weight: bold;")
            self.edit_log_name.setEnabled(False)
        else:
            self.btn_toggle_log.setText("INICIAR GRAVAÇÃO")
            self.btn_toggle_log.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold;")
            self.lbl_log_status.setText(f"GRAVAÇÃO: INATIVA (Última sessão: {count} pacotes)")
            self.lbl_log_status.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            self.edit_log_name.setEnabled(True)
