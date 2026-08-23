"""
tab_sensors.py
==============
Aba 2: Sensores Ambientais & Housekeeping do PION Sat.
Monitoramento em tempo real de Bateria (V, mA, mW, SoC%), CO2 (ppm), Luz (Lux), Umidade (%RH) e Pressão (hPa).
"""

from __future__ import annotations

from collections import deque
from typing import Optional
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui

from src.ground_station.telemetry.packet_definitions import TelemetryPacket
from src.ground_station.ui.style import (
    COLOR_BG_DARK,
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

MAX_PLOT_POINTS = 200


def create_metric_card(title: str, unit: str = "") -> tuple[QtWidgets.QFrame, QtWidgets.QLabel, QtWidgets.QLabel]:
    """Cria um card visual de sensor com rótulo, valor grande e status."""
    frame = QtWidgets.QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background-color: {COLOR_BG_PANEL};
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
            padding: 8px;
        }}
    """)
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)

    lbl_title = QtWidgets.QLabel(f"{title.upper()} {f'[{unit}]' if unit else ''}")
    lbl_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: 600;")
    layout.addWidget(lbl_title)

    lbl_val = QtWidgets.QLabel("--")
    lbl_val.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 20px; font-weight: bold;")
    layout.addWidget(lbl_val)

    lbl_sub = QtWidgets.QLabel("AGUARDANDO DADOS")
    lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
    layout.addWidget(lbl_sub)

    return frame, lbl_val, lbl_sub


class TabSensors(QtWidgets.QWidget):
    """
    Aba 2: Monitoramento detalhado dos sensores ambientais e subsistema de energia.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.history_len = MAX_PLOT_POINTS
        
        # Buffers temporais
        self.time_buffer = deque(maxlen=self.history_len)
        self.vbat_buffer = deque(maxlen=self.history_len)
        self.pbat_buffer = deque(maxlen=self.history_len)
        self.co2_buffer = deque(maxlen=self.history_len)
        self.lux_buffer = deque(maxlen=self.history_len)
        self.hum_buffer = deque(maxlen=self.history_len)
        self.press_buffer = deque(maxlen=self.history_len)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Linha Superior de Cards de Sensores
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(10)

        # Card Bateria
        self.card_bat, self.val_bat, self.sub_bat = create_metric_card("Bateria", "V / SoC")
        cards_layout.addWidget(self.card_bat)

        # Card CO2
        self.card_co2, self.val_co2, self.sub_co2 = create_metric_card("Dióxido de Carbono", "ppm")
        cards_layout.addWidget(self.card_co2)

        # Card Luz
        self.card_lux, self.val_lux, self.sub_lux = create_metric_card("Luminosidade", "Lux")
        cards_layout.addWidget(self.card_lux)

        # Card Umidade
        self.card_hum, self.val_hum, self.sub_hum = create_metric_card("Umidade Relativa", "% RH")
        cards_layout.addWidget(self.card_hum)

        # Card Pressão
        self.card_press, self.val_press, self.sub_press = create_metric_card("Pressão Atmosférica", "hPa")
        cards_layout.addWidget(self.card_press)

        main_layout.addLayout(cards_layout)

        # 2. Grade de Gráficos Temporais (PyQtGraph)
        pg.setConfigOptions(antialias=True)
        plots_grid = QtWidgets.QGridLayout()
        plots_grid.setSpacing(10)

        # Gráfico 1: Bateria (Tensão & Potência)
        self.plot_bat = pg.PlotWidget(title="PERFIL DE ENERGIA (BATERIA)")
        self.plot_bat.setBackground(COLOR_BG_PANEL)
        self.plot_bat.showGrid(x=True, y=True, alpha=0.2)
        self.plot_bat.setLabel("left", "Tensão (V)", color=COLOR_NOMINAL_GREEN)
        self.plot_bat.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_vbat = self.plot_bat.plot(pen=pg.mkPen(COLOR_NOMINAL_GREEN, width=2), name="Tensão (V)")
        plots_grid.addWidget(self.plot_bat, 0, 0)

        # Gráfico 2: CO2
        self.plot_co2 = pg.PlotWidget(title="CONCENTRAÇÃO DE CO₂ (PPM)")
        self.plot_co2.setBackground(COLOR_BG_PANEL)
        self.plot_co2.showGrid(x=True, y=True, alpha=0.2)
        self.plot_co2.setLabel("left", "CO₂ (ppm)", color=COLOR_ACCENT_CYAN)
        self.plot_co2.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_co2 = self.plot_co2.plot(pen=pg.mkPen(COLOR_ACCENT_CYAN, width=2), name="CO₂")
        plots_grid.addWidget(self.plot_co2, 0, 1)

        # Gráfico 3: Luminosidade (Lux)
        self.plot_lux = pg.PlotWidget(title="INTENSIDADE LUMINOSA (LUX)")
        self.plot_lux.setBackground(COLOR_BG_PANEL)
        self.plot_lux.showGrid(x=True, y=True, alpha=0.2)
        self.plot_lux.setLabel("left", "Luz (Lux)", color=COLOR_WARNING_AMBER)
        self.plot_lux.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_lux = self.plot_lux.plot(pen=pg.mkPen(COLOR_WARNING_AMBER, width=2), name="Luz (Lux)")
        plots_grid.addWidget(self.plot_lux, 1, 0)

        # Gráfico 4: Umidade & Pressão
        self.plot_climate = pg.PlotWidget(title="CLIMATOLOGIA (UMIDADE & PRESSÃO)")
        self.plot_climate.setBackground(COLOR_BG_PANEL)
        self.plot_climate.showGrid(x=True, y=True, alpha=0.2)
        self.plot_climate.setLabel("left", "Umidade (% RH)", color="#a78bfa")
        self.plot_climate.setLabel("bottom", "Amostras", color=COLOR_TEXT_MUTED)
        self.curve_hum = self.plot_climate.plot(pen=pg.mkPen("#a78bfa", width=2), name="Umidade (%RH)")
        plots_grid.addWidget(self.plot_climate, 1, 1)

        main_layout.addLayout(plots_grid, stretch=1)

    def update_telemetry(self, packet: TelemetryPacket) -> None:
        """Atualiza os cards e adiciona pontos aos gráficos temporais."""
        # 1. Atualização dos Cards
        v_bat = packet.v_bat_v
        i_bat = packet.i_bat_ma
        p_bat = packet.p_bat_mw
        soc = packet.soc_percent
        self.val_bat.setText(f"{v_bat:.2f} V ({soc}%)")
        self.sub_bat.setText(f"Corrente: {i_bat:+d} mA | Potência: {p_bat:.1f} mW")
        if soc < 20:
            self.val_bat.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-size: 20px; font-weight: bold;")
        elif soc < 50:
            self.val_bat.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-size: 20px; font-weight: bold;")
        else:
            self.val_bat.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")

        # CO2
        self.val_co2.setText(f"{packet.co2_ppm} ppm")
        if packet.co2_ppm < 1000:
            self.sub_co2.setText("Faixa Nominal (Excelente)")
            self.val_co2.setStyleSheet(f"color: {COLOR_NOMINAL_GREEN}; font-size: 20px; font-weight: bold;")
        elif packet.co2_ppm < 2000:
            self.sub_co2.setText("Faixa Moderada")
            self.val_co2.setStyleSheet(f"color: {COLOR_WARNING_AMBER}; font-size: 20px; font-weight: bold;")
        else:
            self.sub_co2.setText("Concentração Alta / Alerta")
            self.val_co2.setStyleSheet(f"color: {COLOR_ALERT_RED}; font-size: 20px; font-weight: bold;")

        # Luz
        self.val_lux.setText(f"{packet.light_lux} Lux")
        self.sub_lux.setText(f"Radiação incidente: {packet.light_lux / 100.0:.1f} W/m² eq.")

        # Umidade
        self.val_hum.setText(f"{packet.humidity_pct:.1f} %")
        self.sub_hum.setText(f"ADC Bruto: {packet.humidity_raw}")

        # Pressão
        self.val_press.setText(f"{packet.pressure_hpa:.1f} hPa")
        self.sub_press.setText(f"Absoluta: {packet.pressure_pa:.0f} Pa")

        # 2. Atualização dos Buffers
        self.vbat_buffer.append(v_bat)
        self.pbat_buffer.append(p_bat)
        self.co2_buffer.append(packet.co2_ppm)
        self.lux_buffer.append(packet.light_lux)
        self.hum_buffer.append(packet.humidity_pct)
        self.press_buffer.append(packet.pressure_hpa)

        # 3. Atualização das Curvas
        self.curve_vbat.setData(list(self.vbat_buffer))
        self.curve_co2.setData(list(self.co2_buffer))
        self.curve_lux.setData(list(self.lux_buffer))
        self.curve_hum.setData(list(self.hum_buffer))
