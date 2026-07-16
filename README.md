<div align="center">

<h1>EKF-HIL Sat</h1>

<h3>Validação de Algoritmos Robustos de ADCS para Nanossatélites com Hardware COTS em Ambiente HIL Físico</h3>

[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-blue?style=for-the-badge)](.)
[![Plataforma](https://img.shields.io/badge/plataforma-PION%20Sat%20%7C%20ESP32-blue?style=for-the-badge)](.)

</div>

---

## Contexto

A filosofia do New Space propõe que as limitações do hardware comercial de baixo custo (COTS) podem ser compensadas por software de alta complexidade. Este projeto adota essa premissa como hipótese central de pesquisa: **é possível determinar e controlar a atitude de um nanossatélite com precisão aceitável utilizando exclusivamente hardware de entrada e alto nível de ruído, desde que os algoritmos embarcados sejam suficientemente robustos?**

Para responder experimentalmente, a plataforma educacional PION Sat é equipada com magnetorquers customizados em PCB e testada em um simulador físico de 3 graus de liberdade (mancal a ar esférico + Gaiola de Helmholtz). O principal desafio de engenharia é embarcar um Filtro de Kalman Estendido (EKF) capaz de operar em tempo real sob forte interferência magnética autogerada pelas próprias bobinas de atuação.

> Os resultados serão documentados em um artigo de Prova de Conceito (PoC).

---

## Stack Tecnológica

<table>
  <tr>
    <td valign="top" width="50%">

**Embarcado**
- **C/C++** — Firmware do EKF e drivers dos atuadores
- **FreeRTOS** — Gerenciamento de tarefas em tempo real
- **ESP32** — Microcontrolador do PION Sat
- **I2C** — Comunicação com a IMU de 9 eixos
- **PWM** — Controle dos drivers de ponte-H

  </td>
    <td valign="top" width="50%">

**Simulação e Telemetria**
- **Python** — Ground Station e sockets UDP
- **UDP** — Comunicação com latência alvo < 15 ms
- **IGRF-13** — Modelo do campo geomagnético terrestre
- **KiCAD** — Projeto das PCBs dos magnetorquers

  </td>
  </tr>
</table>

---

## Como Reproduzir

```bash
# Clonar o repositório
git clone https://github.com/seu-org/ekf-hil-sat.git
cd ekf-hil-sat

# Firmware (requer PlatformIO ou ESP-IDF)
cd src/firmware && pio run

# Ground Station
cd src/ground_station && pip install -r requirements.txt && python main.py

# Simulador
cd sim && python propagator/run_simulation.py
```

> Guia completo de configuração do ambiente em [docs/setup.md](docs/setup.md).

---

## Documentação

| Documento | Conteúdo |
|---|---|
| [Arquitetura](docs/arquitetura.md) | Estrutura do repositório e descrição dos módulos |
| [Setup](docs/setup.md) | Pré-requisitos e configuração completa do ambiente |
| [Roadmap](docs/roadmap.md) | Cronograma e fases do projeto |
| [Equipe](docs/equipe.md) | Frentes de trabalho e responsabilidades |
| [Referências](docs/referencias.md) | Bibliografia e fontes técnicas |

---

## Participantes

<div align="center">

<table align="center">
  <tr>
    <td align="center" width="170">
      <a href="https://github.com/mmonteirov">
        <img src="https://wsrv.nl/?url=github.com/mmonteirov.png&w=200&h=200&fit=cover&mask=circle" width="115" alt="Mateus Verly"/><br/>
        <sub><b>Mateus Verly</b></sub>
      </a>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/ThalitaCAguiar">
        <img src="https://wsrv.nl/?url=github.com/ThalitaCAguiar.png&w=200&h=200&fit=cover&mask=circle" width="115" alt="Thalita Aguiar"/><br/>
        <sub><b>Thalita Aguiar</b></sub>
      </a>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/pedrolrm">
        <img src="https://wsrv.nl/?url=github.com/pedrolrm.png&w=200&h=200&fit=cover&mask=circle" width="115" alt="Pedro Manera"/><br/>
        <sub><b>Pedro Manera</b></sub>
      </a>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/diangellis">
        <img src="https://wsrv.nl/?url=github.com/diangellis.png&w=200&h=200&fit=cover&mask=circle" width="115" alt="Gabriel Di Angellis"/><br/>
        <sub><b>Gabriel Di Angellis</b></sub>
      </a>
    </td>
  </tr>
</table>

</div>

---

## Licença

Distribuído sob a licença **MIT**. Consulte [LICENSE](LICENSE) para mais detalhes.
