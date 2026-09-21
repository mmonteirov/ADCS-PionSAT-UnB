#pragma once

#include <stddef.h>
#include <stdint.h>

#include "app_types.h"

#define TELEMETRY_HEADER       0xAA55U
#define TELEMETRY_PACKET_ID    0x01U
#define TELEMETRY_PACKET_SIZE  76U

typedef struct __attribute__((packed)) {
    uint16_t header;
    uint8_t packet_id;
    uint8_t sys_mode;
    uint32_t timestamp_ms;
    float q[4];
    float gyro_rads[3];
    float mag_uT[3];
    int16_t rel_pos_mm[3];
    uint16_t co2_ppm;
    uint16_t light_lux;
    uint16_t humidity_raw;
    float pressure_pa;
    uint16_t v_bat_mv;
    int16_t i_bat_ma;
    uint8_t soc_percent;
    uint8_t ekf_status;
    int16_t actuator_pwm;
    uint16_t seq_num;
    uint16_t checksum;
} telemetry_packet_t;

_Static_assert(sizeof(telemetry_packet_t) == TELEMETRY_PACKET_SIZE,
               "Pacote de telemetria deve ter exatamente 76 bytes");

uint16_t telemetry_crc16_ccitt(const uint8_t *data, size_t length);

void telemetry_packet_build(telemetry_packet_t *packet,
                            const attitude_state_t *state,
                            const imu_sample_t *sample,
                            uint16_t sequence);
