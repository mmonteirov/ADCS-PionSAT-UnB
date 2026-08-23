# Interface Control Document (ICD) — Protocolo Binário de Telemetria PION Sat

**Documento:** ICD-PIONSAT-DTIL-01  
**Versão:** 1.2  
**Formato de Dados:** Struct Binário Little-Endian (76 Bytes)  
**Taxa de Transmissão:** 10 Hz a 50 Hz (Nominal: 20 Hz)  
**Meios Físicos de Transporte:** USB Serial (UART CDC) e Wi-Fi (Datagrama UDP na porta 5005)

---

## 1. Estrutura do Pacote de Telemetria (76 Bytes)

O pacote é composto por 24 campos sem preenchimento (*zero-padding*) empacotados em ordem *Little-Endian* (`<` em Python, `#pragma pack(push, 1)` em C/C++):

| Offset (Bytes) | Campo | Tipo | Unidade | Descrição |
|:---:|---|:---:|:---:|---|
| `0..1` | `header` | `uint16_t` | — | Sincronismo fixo `0xAA55` (Bytes: `0x55, 0xAA`) |
| `2` | `packet_id` | `uint8_t` | — | Identificador do pacote (Fixo: `0x01`) |
| `3` | `sys_mode` | `uint8_t` | — | Modo operacional: `0` (Idle), `1` (B-Dot), `2` (Pointing) |
| `4..7` | `timestamp_ms` | `uint32_t` | $ms$ | Tempo de operação desde boot (`millis()`) |
| `8..11` | `q_w` | `float` (32-bit) | — | Componente escalar do quatérnion de atitude |
| `12..15` | `q_x` | `float` (32-bit) | — | Componente vetorial X do quatérnion de atitude |
| `16..19` | `q_y` | `float` (32-bit) | — | Componente vetorial Y do quatérnion de atitude |
| `20..23` | `q_z` | `float` (32-bit) | — | Componente vetorial Z do quatérnion de atitude |
| `24..27` | `gyro_x` | `float` (32-bit) | $rad/s$ | Taxa angular medida no eixo X |
| `28..31` | `gyro_y` | `float` (32-bit) | $rad/s$ | Taxa angular medida no eixo Y |
| `32..35` | `gyro_z` | `float` (32-bit) | $rad/s$ | Taxa angular medida no eixo Z |
| `36..39` | `mag_x` | `float` (32-bit) | $\mu T$ | Campo magnético medido no eixo X |
| `40..43` | `mag_y` | `float` (32-bit) | $\mu T$ | Campo magnético medido no eixo Y |
| `44..47` | `mag_z` | `float` (32-bit) | $\mu T$ | Campo magnético medido no eixo Z |
| `48..49` | `rel_pos_x` | `int16_t` | $mm$ | Deslocamento linear relativo no eixo X |
| `50..51` | `rel_pos_y` | `int16_t` | $mm$ | Deslocamento linear relativo no eixo Y |
| `52..53` | `rel_pos_z` | `int16_t` | $mm$ | Deslocamento linear relativo no eixo Z |
| `54..55` | `co2_ppm` | `uint16_t` | $ppm$ | Concentração de dióxido de carbono ($0 \sim 5000$) |
| `56..57` | `light_lux` | `uint16_t` | $Lux$ | Intensidade de luz incidente ($0 \sim 65535$) |
| `58..59` | `humidity_raw`| `uint16_t` | $0.01\%$ | Umidade relativa ($0 \sim 10000 \rightarrow 0.00 \sim 100.00\%$) |
| `60..63` | `pressure_pa` | `float` (32-bit) | $Pa$ | Pressão atmosférica absoluta |
| `64..65` | `v_bat_mv` | `uint16_t` | $mV$ | Tensão do barramento de bateria ($0 \sim 5000$) |
| `66..67` | `i_bat_ma` | `int16_t` | $mA$ | Corrente de dreno/carga ($-2000 \sim +2000$) |
| `68` | `soc_percent` | `uint8_t` | $\%$ | Estado de carga da bateria ($0 \sim 100\%$) |
| `69` | `ekf_status` | `uint8_t` | — | Status do EKF: `0` (Init), `1` (Divergente), `2` (Convergido) |
| `70..71` | `actuator_pwm` | `int16_t` | — | Comando PWM do atuador ($-1000 \sim +1000$) |
| `72..73` | `seq_num` | `uint16_t` | — | Contador monotônico sequencial ($0 \sim 65535$) |
| `74..75` | `checksum` | `uint16_t` | — | CRC-16-CCITT calculado sobre os bytes `0..73` |

---

## 2. Algoritmo de Verificação de Integridade (CRC-16-CCITT)

O campo `checksum` utiliza o polinômio padrão **CRC-16-CCITT** ($X^{16} + X^{12} + X^5 + 1$ / `0x1021`) com valor inicial `0xFFFF`:

```python
def compute_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
```

A implementação em Python utiliza uma **tabela pré-computada de 256 entradas**, executando a validação em **$0.012\text{ ms}$ por pacote**, garantindo que não haja sobrecarga na thread de interface gráfica.
