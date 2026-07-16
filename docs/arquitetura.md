# Arquitetura e Estrutura do Repositório

> Visão geral da organização do código e da responsabilidade de cada módulo.
> A estrutura abaixo representa o layout planejado do projeto.

```text
ADCS-PIONSAT-UNB/
│
├── src/
│   ├── firmware/          # Código C/C++ embarcado (EKF, B-dot, drivers)
│   │   ├── ekf/           # Implementação do Filtro de Kalman Estendido
│   │   ├── control/       # Algoritmo B-dot e leis de controle
│   │   └── drivers/       # IMU, magnetorquers, comunicação
│   └── ground_station/    # Estação de solo em Python
│       ├── telemetry/     # Recepção e parsing UDP
│       └── visualizer/    # Renderizador 3D do satélite
│
├── sim/                   # Simulador orbital e dinâmico
│   ├── propagator/        # Equações de Euler + modelo IGRF
│   └── helmholtz/         # Modelo da Gaiola de Helmholtz
│
├── hardware/              # Arquivos KiCAD das PCBs dos magnetorquers
│   ├── magnetorquer_x/
│   ├── magnetorquer_y/
│   └── magnetorquer_z/
│
├── docs/                  # Documentação técnica e relatórios
│   ├── proposta/
│   ├── relatorios/
│   └── paper/             # Manuscrito IEEE (PoC)
│
├── tests/                 # Critérios de aceitação e logs de validação
└── scripts/               # Utilitários de calibração e análise de dados
```

## Módulos principais

| Módulo | Descrição |
|---|---|
| `src/firmware/ekf` | Filtro de Kalman Estendido embarcado para determinação de atitude |
| `src/firmware/control` | Lei de controle B-dot e atuação dos magnetorquers |
| `src/firmware/drivers` | Drivers de IMU (I2C), geração de PWM e comunicação |
| `src/ground_station` | Estação de solo: telemetria UDP e visualização 3D |
| `sim/propagator` | Propagador de dinâmica orbital (equações de Euler) + modelo IGRF-13 |
| `sim/helmholtz` | Modelo da Gaiola de Helmholtz |
| `hardware` | Projeto das PCBs dos magnetorquers (KiCAD) |
| `tests` | Critérios de aceitação mensuráveis e logs de validação |
| `scripts` | Calibração e análise de dados |
