"""
style.py
========
Tema escuro de padrao aeroespacial e estilos QSS para a Ground Station do PION Sat.
Diretrizes: Zero emojis, tipografia tecnica de alta legibilidade e cores normativas de engenharia.
"""

from __future__ import annotations

# Paleta de Cores Aeroespaciais (RGB Hex)
COLOR_BG_DARK = "#080c14"        # Fundo principal (Deep Space)
COLOR_BG_PANEL = "#0f1624"       # Superficie dos cartoes/paineis
COLOR_BG_CARD = "#141e30"        # Cartoes internos e caixas de dados
COLOR_BORDER = "#202d42"         # Linhas de divisao e bordas sutis
COLOR_TEXT_PRIMARY = "#e2e8f0"   # Texto principal de alto contraste
COLOR_TEXT_MUTED = "#8295b0"     # Rotulos e unidades tecnicas
COLOR_ACCENT_CYAN = "#00e5ff"    # Destaque de telemetria / enlaces
COLOR_NOMINAL_GREEN = "#00ff9d"  # Estado nominal / convergido
COLOR_WARNING_AMBER = "#ffb703"  # Alertas moderados / atencao
COLOR_ALERT_RED = "#ff3860"      # Erros criticos / divergencia

AEROSPACE_STYLE_SHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Consolas', monospace;
}}

QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Consolas', monospace;
    font-size: 12px;
}}

QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_BG_DARK};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_MUTED};
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    padding: 10px 18px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_ACCENT_CYAN};
    border-top: 2px solid {COLOR_ACCENT_CYAN};
    border-bottom: 1px solid {COLOR_BG_CARD};
}}

QTabBar::tab:hover:!selected {{
    background-color: #182338;
    color: {COLOR_TEXT_PRIMARY};
}}

QGroupBox {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: 700;
    font-size: 11px;
    color: {COLOR_ACCENT_CYAN};
    letter-spacing: 0.8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: {COLOR_BG_PANEL};
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {COLOR_BORDER};
}}

QLabel {{
    color: {COLOR_TEXT_PRIMARY};
}}

QPushButton {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

QPushButton:hover {{
    background-color: #1e2e4a;
    border: 1px solid {COLOR_ACCENT_CYAN};
    color: {COLOR_ACCENT_CYAN};
}}

QPushButton:pressed {{
    background-color: #0b1422;
}}

QPushButton:disabled {{
    background-color: #0d121c;
    color: #4a5568;
    border-color: #1a2233;
}}

QComboBox {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border: 1px solid {COLOR_ACCENT_CYAN};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: #1e2e4a;
    selection-color: {COLOR_ACCENT_CYAN};
    border: 1px solid {COLOR_BORDER};
}}

QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    text-align: center;
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-weight: bold;
}}

QProgressBar::chunk {{
    background-color: {COLOR_NOMINAL_GREEN};
    border-radius: 3px;
}}

QStatusBar {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_MUTED};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 11px;
}}
"""


def format_card_css(border_color: str = COLOR_BORDER) -> str:
    """Retorna folha de estilo para um card individual de sensor."""
    return f"""
    QFrame {{
        background-color: {COLOR_BG_CARD};
        border: 1px solid {border_color};
        border-radius: 6px;
        padding: 10px;
    }}
    """
