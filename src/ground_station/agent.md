# Diretrizes do Agente — Módulo `ground_station`

> **Documento de Operação e Engenharia de Software para Agentes de IA e Desenvolvedores**  
> **Módulo:** `src/ground_station/` & `src/twin/` | **Projeto:** EKF-HIL Sat (ADCS PionSat UnB)  
> **Linguagem Principal:** Python 3.10+ | **Comunicação:** UDP / Serial  
> **Especificação Completa do Gêmeo Digital:** Veja [`docs/specs/digital_twin_spec.md`](../../docs/specs/digital_twin_spec.md)

---

## 1. Visão Geral e Missão do Agente

O módulo **Ground Station** é a interface de solo responsável pelo monitoramento em tempo real, visualização de atitude, registro de telemetria científica e envio de comandos de controle para o nanossatélite **PION Sat** durante os testes em bancada e no ambiente HIL (*Hardware-in-the-Loop* com mancal a ar e Gaiola de Helmholtz).

### Objetivos Principais:
1. **Recepção de Telemetria de Baixa Latência:** Receber pacotes via UDP (latência alvo $< 15\text{ ms}$) e porta serial com taxa de atualização entre $10\text{ Hz}$ e $50\text{ Hz}$.
2. **Visualização 3D de Atitude:** Renderizar a orientação do satélite em tempo real a partir dos quatérnios estimados pelo EKF (*Extended Kalman Filter*).
3. **Dashboard e Métricas em Tempo Real:** Plotar velocidades angulares ($\boldsymbol{\omega}$), campo magnético ($\mathbf{B}$), corrente/PWM dos magnetorquers, incertezas de covariância do EKF e métricas de saúde (latência, perda de pacotes, taxa de loop).
4. **Command & Control (C2 / Telecomandos):** Enviar ordens operacionais (mudança de modo: *Detumbling*, *Pointing*, *Idle*, calibração, reset de filtros e envio de ganhos).
5. **Gravação e Replay de Dados:** Armazenar sessões de teste com timestamps de alta fidelidade para posterior validação científica e produção de relatórios/artigo PoC.

---

## 2. Estrutura de Diretórios Planejada

```text
src/ground_station/
├── agent.md                    # Este arquivo de diretrizes
├── requirements.txt            # Dependências específicas da Ground Station
├── main.py                     # Ponto de entrada unificado da aplicação
│
├── telemetry/                  # Núcleo de comunicação e dados
│   ├── __init__.py
│   ├── packet_definitions.py   # Dataclasses, structs binárias e enums de estado
│   ├── udp_receiver.py         # Socket UDP não-bloqueante / thread dedicada
│   ├── serial_receiver.py      # Receptor Serial/UART (testes diretos via USB)
│   ├── parser.py               # Decodificador de pacotes com validação CRC/Checksum
│   ├── logger.py               # Gravador de logs (CSV / SQLite / HDF5)
│   └── mock_sender.py          # Emulador de telemetria para testes sem hardware
│
├── visualizer/                 # Visualização gráfica 3D e espacial
│   ├── __init__.py
│   ├── attitude_renderer.py    # Renderizador 3D do satélite (PyQtGraph OpenGL / VisPy / PyVista)
│   ├── vector_overlays.py      # Projeção de vetores (B medido, B modelo, $\tau$ atuadores)
│   └── frames.py               # Conversões de referenciais (Body, ECI, Gaiola/Lab)
│
├── dashboard/                  # Interface do Usuário (GUI / TUI)
│   ├── __init__.py
│   ├── app.py                  # Janela principal da interface (PyQt / PySide / CustomTkinter)
│   ├── plots.py                # Gráficos temporais de alta taxa (quaternions, $\omega$, B, PWM)
│   └── control_panel.py        # Painel de envio de telecomandos e troca de modos
│
└── tests/                      # Testes automatizados do módulo
    ├── test_parser.py          # Validação de parsing e decodificação
    ├── test_packets.py         # Integridade de serialização de pacotes
    └── test_logger.py          # Verificação de persistência e consistência temporal
```

---

## 3. Protocolo e Estrutura de Telemetria

### 3.1. Convenção de Atitude e Referenciais
* **Quatérnios:** Adotar a convenção Hamiltoniana padrão $\mathbf{q} = [q_w, q_x, q_y, q_z]^T$ com norma unitária $\|\mathbf{q}\| = 1$. Indicar explicitamente nas docstrings a rotação representada ($\text{Body} \leftarrow \text{ECI}$ ou $\text{Body} \leftarrow \text{Lab}$).
* **Velocidade Angular:** Vetor $\boldsymbol{\omega} = [\omega_x, \omega_y, \omega_z]^T$ em rad/s ou deg/s (definir unidade explícita no payload).
* **Campo Magnético:** Vetor $\mathbf{B} = [B_x, B_y, B_z]^T$ em $\mu\text{T}$ ou $\text{Tesla}$.

### 3.2. Formato do Pacote de Telemetria (Binário / UDP)
Para minimizar overhead de rede e garantir latência $< 15\text{ ms}$, priorizar empacotamento binário (`struct.pack` / `ctypes`) com sincronismo de cabeçalho e verificação de integridade:

| Campo | Tipo | Bytes | Descrição |
|---|---|---|---|
| `HEADER` | `uint16` | 2 | Bytes mágicos de sincronismo (ex: `0xAA55`) |
| `PACKET_ID` | `uint8` | 1 | ID do tipo de pacote (Telemetria geral, Debug EKF, Status) |
| `TIMESTAMP_MS`| `uint32` | 4 | Timestamp em ms do microcontrolador (ESP32) |
| `Q_W, Q_X, Q_Y, Q_Z` | `float32[4]` | 16 | Quatérnio de atitude estimado pelo EKF |
| `GYRO_X, Y, Z` | `float32[3]` | 12 | Velocidade angular medida pela IMU ($\text{rad/s}$) |
| `MAG_X, Y, Z` | `float32[3]` | 12 | Campo magnético calibrado ($\mu\text{T}$) |
| `PWM_X, Y, Z` | `int16[3]` | 6 | Ciclo de trabalho dos magnetorquers ($-1000$ a $+1000$) |
| `EKF_STATE` | `uint8` | 1 | Estado do filtro (0: INIT, 1: UNCONVERGED, 2: CONVERGED) |
| `SYS_MODE` | `uint8` | 1 | Modo operacional (0: IDLE, 1: BDOT, 2: POINTING, 3: CALIB) |
| `CHECKSUM` | `uint16` | 2 | CRC-16 ou Checksum Fletcher dos bytes anteriores |

---

## 4. Requisitos de Engenharia e Boas Práticas

Ao desenvolver ou refatorar qualquer arquivo neste módulo, o agente **DEVE** seguir as seguintes regras:

### 4.1. Concorrência e Performance de I/O
1. **Desacoplamento de Threads:** A recepção UDP/Serial **NUNCA** deve bloquear a thread principal da interface gráfica ou renderizador 3D.
2. **Comunicação entre Threads:** Utilizar `queue.Queue` (thread-safe) ou buffer circular com lock mínimo para enviar dados parseados da camada de telemetria para os gráficos e visualizador.
3. **Resiliência a Perda de Pacotes:** O parser deve tratar pacotes incompletos, fora de ordem ou corrompidos sem levantar exceções não tratadas que interrompam o fluxo contínuo.

### 4.2. Padrões de Código Python
* **Versão:** Python 3.10+ (utilizar `from __future__ import annotations`).
* **Tipagem Estática:** Usar type hints em todas as assinaturas de funções e métodos.
* **Docstrings:** Documentar parâmetros, tipos de retorno, unidades de medida e tratamento de exceções.
* **Modo Headless / CLI:** O núcleo de telemetria e gravação deve ser executável em modo headless (sem GUI) para automação em servidores CI ou scripts de teste.

### 4.3. Emulação e Mocking
* O submódulo `telemetry/mock_sender.py` deve estar sempre funcional, gerando dados sintéticos (ex: integrador dinâmico simples ou leitura de arquivos de simulação prévios em `sim/`) para permitir o desenvolvimento da interface e visualizador sem necessidade do hardware físico conectado.

---

## 5. Comandos e Procedimentos de Execução

```bash
# Navegar até a pasta da Ground Station
cd src/ground_station

# Instalar dependências da Ground Station
pip install -r requirements.txt

# Executar a aplicação principal
python main.py

# Executar o emulador de telemetria em outro terminal (para testes de bancada/mock)
python telemetry/mock_sender.py --freq 20 --mode mock

# Executar suíte de testes unitários do módulo
pytest tests/
```

---

## 6. Papel dos Agentes na Manutenção Deste Módulo
* Ao adicionar novos campos no firmware ESP32, atualizar sincronamente `packet_definitions.py`, o `parser.py` e a documentação deste arquivo.
* Ao implementar novas bibliotecas gráficas (ex: atualização de Qt ou OpenGL), assegurar compatibilidade multiplataforma (Linux / Windows) e baixo consumo de CPU/GPU.
* Manter a rastreabilidade com os objetivos científicos descritos no `README.md` e `docs/arquitetura.md`.
