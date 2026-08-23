# Estação de Solo (Ground Station 3D) do PION Sat

Aplicação desktop em **PyQt6** com visualizador 3D OpenGL, ingestão serial USB / UDP de alta taxa e integração direta com o motor do Gêmeo Digital.

---

## Estrutura do Pacote

```text
src/ground_station/
├── app.py                # Janela principal (QMainWindow) e timer de 50 Hz
├── main.py               # Ponto de entrada CLI e auto-detecção de portas USB
├── telemetry/            # Camada de comunicação de telemetria
│   ├── packet_definitions.py  # Struct de 76 bytes, CRC-16 e Euler
│   ├── serial_receiver.py     # Thread de recepção USB Serial assíncrona
│   ├── udp_receiver.py        # Thread de recepção Wi-Fi / UDP
│   ├── logger.py              # Gravador de sessão CSV thread-safe
│   └── mock_sender.py         # Gerador de telemetria para emulação
├── ui/                   # Abas modulares da interface gráfica
│   ├── style.py               # Tema escuro aeroespacial (sem emojis)
│   ├── tab_3d_attitude.py     # Aba 1: Renderização 3D, Quatérnios e Chassi
│   ├── tab_sensors.py         # Aba 2: Bateria, CO2, Luz, Umidade e Pressão
│   ├── tab_adcs.py            # Aba 3: Giroscópios, Magnetômetro e PWM
│   ├── tab_divergence.py      # Aba 4: Divergência DTiL e histórico RMSE
│   └── tab_settings.py        # Aba 5: Gerenciador de portas e gravação CSV
└── visualizer/           # Módulo de renderização 3D CAD
    ├── cad_loader.py          # Processador de malha STEP e separação de peças
    └── attitude_renderer_3d.py# Viewport OpenGL (pyqtgraph.opengl) a 60 FPS
```

---

## Execução

```bash
# Execução normal (Auto-conecta na porta USB ativa)
python src/ground_station/main.py

# Especificando porta e baudrate manualmente
python src/ground_station/main.py --port /dev/ttyUSB0 --baud 115200

# Execução em modo UDP (Wi-Fi)
python src/ground_station/main.py --udp --udp-port 5005
```
