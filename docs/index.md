# EKF-HIL Sat

## ADCS robusto para nanossatélites com hardware COTS

O projeto investiga a determinação e o controle de atitude de um nanossatélite
com a plataforma educacional **PION Sat**, usando sensores e atuadores comerciais de
baixo custo. A validação será realizada em um ambiente físico de *hardware-in-the-loop*
(HIL), composto por mancal a ar esférico e Gaiola de Helmholtz.

O principal desafio é executar em tempo real, no ESP32, um Filtro de Kalman
Estendido (EKF) resistente ao ruído dos sensores e à interferência magnética gerada
pelos próprios magnetorquers.

## Navegue pela documentação

- [Arquitetura](arquitetura.md): estrutura planejada e responsabilidades dos módulos.
- [Configuração do ambiente](setup.md): ferramentas e passos para iniciar o desenvolvimento.
- [Roadmap](roadmap.md): fases e cronograma do projeto.
- [Referências](referencias.md): bibliografia e fontes técnicas.

## Frentes do projeto

| Frente | Tecnologias | Objetivo |
|---|---|---|
| Firmware embarcado | C/C++, FreeRTOS, ESP32 | Estimação de atitude e controle dos magnetorquers |
| Simulação | Python, IGRF-13 | Propagação dinâmica e geração do campo magnético |
| Estação de solo | Python, UDP | Recepção de telemetria e visualização |
| Hardware | KiCad | Desenvolvimento dos magnetorquers em PCB |

!!! info "Projeto em desenvolvimento"
    A documentação evoluirá junto com a implementação e os ensaios do sistema.
