#include <stdio.h>
#include <string.h>

#include "app_types.h"
#include "telemetry_packet.h"

int main(void)
{
    attitude_state_t state = {
        .timestamp_us = 123456000LL,
        .q = {0.7071068f, 0.0f, 0.7071068f, 0.0f},
        .valid = true,
    };
    imu_sample_t sample = {
        .gyro_rads = {0.0123f, -0.0456f, 0.0789f},
        .mag_uT = {12.34f, -5.67f, 28.91f},
        .gyro_valid = true,
        .mag_valid = true,
    };
    telemetry_packet_t packet;

    telemetry_packet_build(&packet, &state, &sample, 42U);
    return fwrite(&packet, 1U, sizeof(packet), stdout) == sizeof(packet) ? 0 : 1;
}
