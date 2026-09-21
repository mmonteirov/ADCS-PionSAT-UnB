#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    int64_t timestamp_us;
    float accel_mps2[3];
    float gyro_rads[3];
    float mag_uT[3];
    bool accel_valid;
    bool gyro_valid;
    bool mag_valid;
} imu_sample_t;

typedef struct {
    int64_t timestamp_us;
    float q[4];              /* [w, x, y, z] */
    float gyro_bias_rads[3];
    float covariance_trace;
    bool valid;
} attitude_state_t;

typedef struct {
    int64_t timestamp_us;
    float normalized_torque; /* [-1, +1] */
    bool enable;
} actuator_command_t;
