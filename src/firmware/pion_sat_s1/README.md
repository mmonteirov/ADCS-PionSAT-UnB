# Firmware ADCS - PION Sat (Aluno S1)

Base de recuperacao das Semanas 1-4 do cronograma individual. O projeto usa
ESP-IDF 5.2/5.3, FreeRTOS e C nativo.

O firmware foi compilado com ESP-IDF 5.3.5. O projeto inclui uma recomendacao
para a extensao oficial ESP-IDF do VS Code, sem caminhos dependentes de um
computador especifico.

## Estado atual

- Scanner I2C usando a API moderna `i2c_master` do ESP-IDF.
- Tasks separadas: sensores 100 Hz, EKF 50 Hz, controle 50 Hz e telemetria 20 Hz.
- Filas FreeRTOS para impedir compartilhamento inseguro de estado.
- Watchdog alimentado em todas as tasks e periodos com `vTaskDelayUntil()`.
- EKF inicial de 7 estados: quaternion e bias de giroscopio; correcao de
  roll/pitch pelo acelerometro e forma de Joseph para a covariancia.
- Atuador bloqueado por padrao ate a interface eletrica ser confirmada.
- MPU-9250 confirmado por `WHO_AM_I=0x71`, com acelerometro e giroscopio a
  100 Hz; AK8963 confirmado por `WIA=0x48`.
- Modo de IMU simulada desabilitado por padrao na configuracao de bancada.

## Primeiro teste no hardware

Esta versao foi compilada, gravada e executada em um ESP32-D0WD revision 1.0.
O teste encontrou dispositivos I2C nos enderecos `0x20`, `0x40`, `0x5A`,
`0x68` e `0x76`. Consulte [TESTES.md](TESTES.md) para os resultados.

1. Abra esta pasta no VS Code e inicie um terminal integrado.
2. Confirme em `main/include/app_config.h` os GPIOs SDA/SCL. Os valores 21/22
   sao apenas defaults comuns do ESP32, nao uma confirmacao do PION Sat.
3. Execute:

```powershell
idf.py set-target esp32
idf.py fullclean
idf.py build
idf.py -p COMx flash monitor
```

4. Registre os enderecos exibidos pelo scanner I2C.
5. Pare o monitor com `Ctrl+]`.

Com `CONFIG_PION_IMU_SIMULATION=y`, o firmware publica uma IMU em repouso e o
log deve mostrar um quaternion proximo de `[1, 0, 0, 0]`. Use
`idf.py menuconfig`, menu `PION Sat ADCS`, para alterar esse modo.

O script `idf.cmd` e apenas um atalho portatil para terminais nos quais
`idf.py` ja esteja configurado.

## Dados ainda necessarios

- Esquema eletrico oficial para confirmar GPIOs SDA/SCL e orientacao dos eixos.
- Calibracao hard-iron/soft-iron do magnetometro no conjunto montado.
- Modelo do driver da roda e interface real: LEDC/MCPWM, UART ou SPI.
- Frequencia, polaridade, faixa de duty cycle e pino de enable do driver.
- Definicao de A1 para estado, modelo de processo e matrizes Q/R.
- ICD de S2 para payload UDP, endianess, versao e taxa de envio.

## Limites do EKF inicial

O acelerometro corrige inclinacao, mas nao torna o yaw observavel. A fusao do
magnetometro ou de vetores virtuais recebidos do gêmeo digital ainda precisa ser
adicionada. A propagacao completa de `P` por `F P F^T + Q` tambem deve substituir
a aproximacao diagonal assim que A1 entregar o modelo matematico oficial.

O campo `ekf_status=2` atualmente informa apenas que o estado e finito. Ele nao
implementa ainda um teste estatistico de convergencia. Posicao, bateria e
sensores ambientais permanecem em zero ate seus drivers serem validados.

Nao use esta versao para energizar a roda de reacao.
