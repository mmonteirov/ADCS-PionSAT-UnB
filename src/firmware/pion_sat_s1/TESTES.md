# Testes do firmware

## Resultado consolidado

Testes realizados em 27/08/2026 com ESP-IDF 5.3.5 e PION Sat conectado por
UART/USB.

| Teste | Resultado |
| --- | --- |
| Referencia matematica do EKF em repouso | Aprovado |
| Compilacao completa do ESP-IDF | Aprovado |
| Verificacao de tamanho da aplicacao | Aprovado, 165776 bytes |
| Gravacao do bootloader | Aprovado, hash verificado |
| Gravacao da tabela de particoes | Aprovado, hash verificado |
| Gravacao da aplicacao | Aprovado, hash verificado |
| Inicializacao FreeRTOS dual-core | Aprovado |
| Scanner I2C | Aprovado |
| Execucao continuada do EKF | Aprovado |
| Bloqueio do atuador | Aprovado |
| Suite Python do repositorio ADCS-PionSAT-UnB | Aprovado, 32/32 testes |
| Observacao serial continua por 15 s | Aprovado, 292 amostras EKF |
| Compatibilidade C com ICD v1.2 do GitHub | Aprovado, 76 bytes e CRC valido |
| Telemetria binaria fisica por 60 s (18/09/2026) | Aprovado, 1201 pacotes |
| Identificacao da IMU fisica | MPU-9250, WHO_AM_I 0x71 |
| Identificacao do magnetometro | AK8963, WIA 0x48 |
| Leitura fisica em repouso | Aprovada, gyro proximo de zero e mag presente |
| Resposta fisica ao movimento (18/09/2026) | Aprovada, 901 pacotes/45 s |

## Evidencias observadas

- MCU identificado: ESP32-D0WD revision 1.0.
- Dispositivos I2C encontrados: `0x20`, `0x40`, `0x5A`, `0x68` e `0x76`.
- Modo de IMU simulada ativo para o primeiro teste.
- Quaternion permaneceu proximo da identidade: `[1, 0, 0, 0]`.
- A covariancia permaneceu finita durante a observacao.
- Atuador permaneceu bloqueado por configuracao de seguranca.
- Nao houve acionamento do watchdog nem reinicializacao inesperada.
- Durante 15 segundos foram recebidos 32236 bytes e 292 amostras do EKF.
- Todas as amostras observadas de quaternion e covariancia eram finitas.
- A suite do repositorio de destino concluiu em 2,17 s, sem falhas.
- Na COM5, o receptor oficial recebeu 1201 pacotes em 60 s (20,02 Hz).
- O ensaio binario teve zero erro de CRC, zero perda de sequencia e zero reset.
- A sequencia avancou de 645 a 1845 e a norma do quaternion ficou em 1,000000.
- O comando do atuador permaneceu em zero durante todo o ensaio.
- A simulacao da IMU foi desativada apos confirmacao experimental do MPU-9250.
- O giroscopio e calibrado por 2 s a cada boot; o satelite deve permanecer parado.
- O magnetometro apresentou norma em torno de 130 uT e ainda requer calibracao
  hard-iron/soft-iron antes de uso cientifico ou correcao de yaw no EKF.
- No ensaio manual de movimento, a norma do giroscopio atingiu 6,260 rad/s,
  o magnetometro variou de 78,4 a 117,5 uT e os tres angulos de Euler responderam.
- O ensaio de movimento manteve 20,00 Hz, CRC zero, nenhuma perda de sequencia,
  nenhuma reinicializacao e PWM igual a zero.
- Em novo ensaio estacionario de 20 s, foram recebidos 400 pacotes a 20,000 Hz,
  sem CRC invalido ou perda de sequencia.
- Nesse repouso, o giroscopio teve RMS de 0,001654 rad/s e pico de
  0,006985 rad/s; as amplitudes de roll/pitch/yaw foram 0,044/0,059/0,035 graus.
- A linha de campo magnetico no visualizador oscilou em media 0,487 grau e no
  maximo 1,269 grau. A norma medida ficou entre 106,10 e 110,13 uT, confirmando
  que o magnetometro ainda necessita calibracao no conjunto montado.

## Teste de referencia reproduzivel

```powershell
python tools/ekf_reference.py
```

Saida esperada:

```text
OK: repouso preserva quaternion identidade
```

## Escopo e limitacoes

Os ensaios atuais validam a aquisicao fisica do MPU-9250/AK8963, o pipeline
FreeRTOS, o pacote binario e a resposta de roll/pitch/yaw ao movimento. Ainda nao
validam uma solucao absoluta completa de atitude: o magnetometro nao foi
calibrado nem fundido no EKF, o yaw permanece nao observavel e a propagacao de
covariancia ainda e simplificada. A roda de reacao continua desabilitada.
