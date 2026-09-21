# Guia passo a passo - firmware S1

## Etapa 1 - abrir e compilar

1. Abra no VS Code a pasta `pion_sat_s1_firmware`.
2. Abra `Terminal > New Terminal`.
3. Execute:

```powershell
.\idf.cmd --version
.\idf.cmd set-target esp32
.\idf.cmd build
```

Resultado esperado: `Project build complete`.

## Etapa 2 - executar sem IMU fisica

O modo simulado esta habilitado por padrao. Ele gera, a 100 Hz:

- acelerometro: `[0, 0, 9.80665] m/s2`;
- giroscopio: `[0, 0, 0] rad/s`;
- magnetometro: invalido/ausente.

Isso exercita sensor task, queue, EKF task, controle seguro, telemetria e WDT.

## Etapa 3 - conectar o ESP32

1. Conecte o PION Sat por USB.
2. No PowerShell, veja a porta nova:

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

3. Substitua `COMx` pela porta detectada:

```powershell
.\idf.cmd -p COMx flash
```

Com a telemetria binaria habilitada, use a Ground Station em vez de
`idf.py monitor`. Consulte `OFICINA_MODULO_2.md`.

## Etapa 4 - scanner I2C

O scanner roda antes das tasks. Confirme no esquema os GPIOs antes do teste.
Para alterar os defaults:

```powershell
.\idf.cmd menuconfig
```

Abra `PION Sat ADCS`, configure SDA/SCL, salve e compile novamente. Guarde o
log com os enderecos encontrados; ele e a evidencia da Semana 1.

## Etapa 5 - implementar a IMU real

Nao desative a simulacao antes de obter:

- modelo exato da IMU;
- endereco I2C esperado;
- registrador e valor de `WHO_AM_I`;
- registradores de reset/configuracao;
- escalas de acelerometro, giroscopio e magnetometro;
- ordem e endianess dos bytes em leitura burst.

Depois disso, implemente em `main/imu.c`:

1. adicionar o dispositivo ao barramento;
2. ler e validar `WHO_AM_I`;
3. configurar ranges e taxa de amostragem;
4. fazer leitura burst;
5. converter para SI;
6. marcar cada campo como valido somente após `ESP_OK`.

So entao desmarque `Usar IMU simulada em repouso` no `menuconfig`.

## Etapa 6 - validacao da Semana 2

Medir durante pelo menos 60 segundos:

- sensor task: 100 Hz;
- EKF task: 50 Hz;
- ausencia de reset por watchdog;
- perda/overflow da queue;
- stack minima de cada task;
- tempo de execucao do EKF.

## Etapa 7 - dependencias da equipe

- A1: convencao de quaternion, frames, F/H/Q/R e controlador.
- S2: formato binario, endianess, sequence, timestamp e taxa UDP.
- Hardware: IMU, pinagem e interface eletrica da roda.

O atuador continua bloqueado ate essas informacoes serem verificadas.
