# Guia de Setup do Ambiente

> Configuração completa para desenvolvimento e execução das três frentes do projeto:
> firmware embarcado, estação de solo e simulador.

## Pré-requisitos

- **Firmware:** [PlatformIO](https://platformio.org/) ou [ESP-IDF](https://docs.espressif.com/projects/esp-idf/)
- **Ground Station / Simulador:** Python 3.x
- **Hardware/EDA:** [KiCAD](https://www.kicad.org/) para abrir os projetos das PCBs

## Passos

```bash
# Clonar o repositório
git clone https://github.com/seu-org/ekf-hil-sat.git
cd ekf-hil-sat
```

### Firmware (ESP32)

```bash
cd src/firmware
pio run            # compilar
pio run -t upload  # gravar no ESP32
```

### Ground Station

```bash
cd src/ground_station
pip install -r requirements.txt
python main.py
```

### Simulador

```bash
cd sim
python propagator/run_simulation.py
```

> _Seções a detalhar conforme o projeto evolui: configuração da IMU, parâmetros do EKF, calibração da Gaiola de Helmholtz e do mancal a ar._
