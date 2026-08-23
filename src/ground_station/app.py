"""
app.py
======
Janela Principal da Ground Station do PION Sat (PyQt6).
Arquitetura em 5 abas modulares com despacho de telemetria a 60 FPS e integracao com o Gemeo Digital.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.telemetry.serial_receiver import SerialReceiver
from src.ground_station.telemetry.udp_receiver import UdpReceiver
from src.ground_station.telemetry.logger import TelemetryLogger
from src.ground_station.ui.style import AEROSPACE_STYLE_SHEET
from src.ground_station.ui.tab_3d_attitude import Tab3DAttitude
from src.ground_station.ui.tab_sensors import TabSensors
from src.ground_station.ui.tab_adcs import TabADCS
from src.ground_station.ui.tab_divergence import TabDivergence
from src.ground_station.ui.tab_settings import TabSettings
from src.twin.digital_twin_engine import DigitalTwinEngine

logger = logging.getLogger(__name__)


class GroundStationMainWindow(QtWidgets.QMainWindow):
    """
    Janela principal da Estacao de Solo e Gemeo Digital do PION Sat.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        enable_mock: bool = False,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PION SAT — GROUND STATION & DIGITAL TWIN (ADCS-PIONSAT-UNB)")
        self.resize(1360, 880)

        # Fila thread-safe de telemetria
        self.packet_queue: queue.Queue[TelemetryPacket] = queue.Queue(maxsize=2000)

        # Nucleo do Gemeo Digital (4 Camadas DTiL)
        self.twin_engine = DigitalTwinEngine()

        # Gravador CSV
        self.telemetry_logger = TelemetryLogger(log_dir="logs")

        # Conexoes de I/O
        self.serial_receiver: Optional[SerialReceiver] = None
        self.udp_receiver: Optional[UdpReceiver] = None
        self.enable_mock = enable_mock
        self.initial_port = port
        self.initial_baudrate = baudrate

        # Aplicacao do estilo aeroespacial
        self.setStyleSheet(AEROSPACE_STYLE_SHEET)

        # 1. Montagem das Abas (QTabWidget)
        self.tab_widget = QtWidgets.QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        self.tab_3d = Tab3DAttitude(self)
        self.tab_sensors = TabSensors(self)
        self.tab_adcs = TabADCS(self)
        self.tab_divergence = TabDivergence(self)
        self.tab_settings = TabSettings(self)

        self.tab_widget.addTab(self.tab_3d, "Atitude & 3D")
        self.tab_widget.addTab(self.tab_sensors, "Sensores & Bateria")
        self.tab_widget.addTab(self.tab_adcs, "Dinâmica & ADCS")
        self.tab_widget.addTab(self.tab_divergence, "Gêmeo Digital (DTiL)")
        self.tab_widget.addTab(self.tab_settings, "Conexão & Logs")

        # 2. Conexao de sinais das Abas
        self.tab_settings.request_connect.connect(self.connect_serial)
        self.tab_settings.request_disconnect.connect(self.disconnect_serial)
        self.tab_settings.request_start_logging.connect(self.start_logging)
        self.tab_settings.request_stop_logging.connect(self.stop_logging)
        self.tab_settings.request_reset_twin.connect(self.reset_digital_twin)
        self.tab_3d.request_toggle_mock.connect(self.toggle_mock_mode)

        # Thread de emulacao dinamica
        self._mock_thread: Optional[threading.Thread] = None
        self._mock_running = threading.Event()

        # 3. Barra de Status
        self.status_bar = self.statusBar()
        self.lbl_status_link = QtWidgets.QLabel("LINK: DESCONECTADO")
        self.lbl_status_rate = QtWidgets.QLabel("TAXA: 0.0 Hz")
        self.lbl_status_pkts = QtWidgets.QLabel("PACOTES: 0")
        self.lbl_status_crc = QtWidgets.QLabel("ERROS CRC: 0")
        self.lbl_status_twin = QtWidgets.QLabel("DTiL: PRONTO")

        for lbl in (self.lbl_status_link, self.lbl_status_rate, self.lbl_status_pkts, self.lbl_status_crc, self.lbl_status_twin):
            lbl.setStyleSheet("padding: 0 10px; font-weight: 600;")
            self.status_bar.addPermanentWidget(lbl)

        # 4. Timer de atualizacao da GUI a 50 Hz (20 ms)
        self.gui_timer = QtCore.QTimer(self)
        self.gui_timer.timeout.connect(self._process_telemetry_queue)
        self.gui_timer.start(20)

        # 5. Inicializacao automatica: auto-detecta porta USB se nenhuma for especificada
        target_port = self.initial_port
        if not target_port and not self.enable_mock:
            from src.ground_station.telemetry.serial_receiver import list_available_serial_ports
            available = list_available_serial_ports()
            usb_ports = [p for p in available if "USB" in p or "ACM" in p or "COM" in p]
            if usb_ports:
                target_port = usb_ports[0]
                logger.info(f"Porta USB detectada automaticamente: {target_port}")

        if target_port:
            self.connect_serial(target_port, self.initial_baudrate)
        elif self.enable_mock:
            self.toggle_mock_mode(True)

    def toggle_mock_mode(self, active: bool) -> None:
        """Ativa ou desativa a injecao continua de telemetria simulada."""
        if active:
            if not self._mock_running.is_set():
                self._mock_running.set()
                from src.ground_station.telemetry.mock_sender import MockTelemetryGenerator
                generator = MockTelemetryGenerator(freq_hz=20.0)

                def feeder():
                    interval = 1.0 / 20.0
                    while self._mock_running.is_set():
                        t0 = time.time()
                        pkt = generator.generate_next_packet()
                        try:
                            self.packet_queue.put_nowait(pkt)
                        except Exception:
                            pass
                        elapsed = time.time() - t0
                        time.sleep(max(0.0, interval - elapsed))

                self._mock_thread = threading.Thread(target=feeder, daemon=True, name="DynamicMockFeeder")
                self._mock_thread.start()
                self.tab_3d.set_mock_state(True)
                self.lbl_status_link.setText("LINK: EMULADOR / MOCK ATIVO (20 Hz)")
                self.lbl_status_link.setStyleSheet("color: #ffb703; font-weight: bold; padding: 0 10px;")
                logger.info("Emulador de telemetria ativado via interface grafica.")
        else:
            self._mock_running.clear()
            # Esvazia completamente a fila de pacotes acumulada
            while not self.packet_queue.empty():
                try:
                    self.packet_queue.get_nowait()
                except Exception:
                    break
            self.tab_3d.set_mock_state(False)
            self.lbl_status_link.setText("LINK: DESCONECTADO")
            self.lbl_status_link.setStyleSheet("color: #8295b0; font-weight: bold; padding: 0 10px;")
            self.lbl_status_rate.setText("TAXA: 0.0 Hz")
            logger.info("Emulador de telemetria desativado.")

    def connect_serial(self, port: str, baudrate: int = 115200) -> None:
        """Inicia a thread do receptor serial."""
        self.disconnect_serial()
        self.serial_receiver = SerialReceiver(
            port=port,
            baudrate=baudrate,
            packet_queue=self.packet_queue,
        )
        if self.serial_receiver.connect():
            self.serial_receiver.start()
            self.tab_settings.set_connected_state(True, port=port, baud=baudrate)
            self.lbl_status_link.setText(f"LINK: CONECTADO ({port})")
            self.lbl_status_link.setStyleSheet("color: #00ff9d; font-weight: bold; padding: 0 10px;")
        else:
            self.tab_settings.set_connected_state(False)
            self.lbl_status_link.setText("LINK: FALHA AO CONECTAR")
            self.lbl_status_link.setStyleSheet("color: #ff3860; font-weight: bold; padding: 0 10px;")

    def disconnect_serial(self) -> None:
        """Desconecta e finaliza o receptor serial."""
        if self.serial_receiver is not None:
            self.serial_receiver.disconnect()
            self.serial_receiver = None
        self.tab_settings.set_connected_state(False)
        self.lbl_status_link.setText("LINK: DESCONECTADO")
        self.lbl_status_link.setStyleSheet("color: #8295b0; font-weight: bold; padding: 0 10px;")

    def start_logging(self, custom_filename: str) -> None:
        """Inicia gravacao de log CSV."""
        filepath = self.telemetry_logger.start(custom_filename if custom_filename else None)
        self.tab_settings.set_logging_state(True, filepath=filepath, count=0)

    def stop_logging(self) -> None:
        """Para a gravacao de log CSV."""
        count = self.telemetry_logger.recorded_packets_count
        self.telemetry_logger.stop()
        self.tab_settings.set_logging_state(False, count=count)

    def reset_digital_twin(self) -> None:
        """Reinicia o estado interno do Gemeo Digital."""
        self.twin_engine.reset()
        logger.info("Gemeo Digital reiniciado pelo operador.")

    def _process_telemetry_queue(self) -> None:
        """Esvazia a fila de pacotes e despacha para todas as abas da GUI."""
        latest_packet: Optional[TelemetryPacket] = None
        packets_processed = 0

        while not self.packet_queue.empty() and packets_processed < 50:
            try:
                packet = self.packet_queue.get_nowait()
                latest_packet = packet
                packets_processed += 1

                # 1. Processamento pelo Nucleo do Gemeo Digital (Camadas 0 a 3)
                divergence_metrics = self.twin_engine.process_packet(packet)

                # 2. Gravacao em arquivo CSV se ativa
                if self.telemetry_logger.is_logging:
                    self.telemetry_logger.log_packet(packet, divergence_metrics=divergence_metrics)

                # 3. Atualizacao das abas de series temporais
                self.tab_sensors.update_telemetry(packet)
                self.tab_adcs.update_telemetry(packet)
                self.tab_divergence.update_metrics(packet, divergence_data=divergence_metrics)

            except queue.Empty:
                break

        # Atualiza a aba 3D e status com o pacote mais recente
        if latest_packet is not None:
            stats = self.serial_receiver.get_stats() if self.serial_receiver else {}
            self.tab_3d.update_telemetry(latest_packet, stats=stats)

            # Atualiza barra de status
            pkts = stats.get("packets_received", 0)
            rate = stats.get("packet_rate_hz", 0.0)
            crc_err = stats.get("crc_errors", 0)
            self.lbl_status_rate.setText(f"TAXA: {rate:.1f} Hz")
            self.lbl_status_pkts.setText(f"PACOTES: {int(pkts)}")
            self.lbl_status_crc.setText(f"ERROS CRC: {int(crc_err)}")

        if self.telemetry_logger.is_logging:
            st = self.telemetry_logger.get_status()
            self.tab_settings.set_logging_state(True, filepath=st["filepath"], count=st["packets_count"])

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Encerra threads e conexoes de forma limpa ao fechar a janela."""
        self.disconnect_serial()
        if self.udp_receiver is not None:
            self.udp_receiver.stop()
        if self.telemetry_logger.is_logging:
            self.telemetry_logger.stop()
        event.accept()
