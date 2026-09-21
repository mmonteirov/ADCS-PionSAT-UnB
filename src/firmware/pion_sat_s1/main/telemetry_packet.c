#include "telemetry_packet.h"

#include <string.h>

uint16_t telemetry_crc16_ccitt(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xFFFFU;

    if (data == NULL) {
        return crc;
    }

    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (unsigned bit = 0; bit < 8U; ++bit) {
            crc = (crc & 0x8000U) != 0U
                      ? (uint16_t)((crc << 1) ^ 0x1021U)
                      : (uint16_t)(crc << 1);
        }
    }
    return crc;
}
void telemetry_packet_build(telemetry_packet_t *packet,
                            const attitude_state_t *state,
                            const imu_sample_t *sample,
                            uint16_t sequence)
{
    if ((packet == NULL) || (state == NULL) || (sample == NULL)) {
        return;
    }

    memset(packet, 0, sizeof(*packet));
    packet->header = TELEMETRY_HEADER;
    packet->packet_id = TELEMETRY_PACKET_ID;
    packet->sys_mode = 0U; /* Idle: atuacao fisica bloqueada nesta etapa. */
    packet->timestamp_ms = (uint32_t)(state->timestamp_us / 1000LL);
    memcpy(packet->q, state->q, sizeof(packet->q));

    if (sample->gyro_valid) {
        memcpy(packet->gyro_rads, sample->gyro_rads, sizeof(packet->gyro_rads));
    }
    if (sample->mag_valid) {
        memcpy(packet->mag_uT, sample->mag_uT, sizeof(packet->mag_uT));
    }

    /* Sensores ambientais, bateria e posicao ainda nao possuem drivers
     * validados. Permanecem em zero para nao simular uma medicao real. */
    packet->ekf_status = state->valid ? 2U : 0U;
    packet->actuator_pwm = 0;
    packet->seq_num = sequence;
    packet->checksum = telemetry_crc16_ccitt(
        (const uint8_t *)packet, offsetof(telemetry_packet_t, checksum));
}
