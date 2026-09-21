#pragma once

#include "app_types.h"
#include "esp_err.h"

#define EKF_STATE_DIM 7

typedef struct {
    float x[EKF_STATE_DIM]; /* quaternion [0..3], gyro bias [4..6] */
    float p[EKF_STATE_DIM][EKF_STATE_DIM];
    float gyro_process_noise;
    float bias_process_noise;
    float accel_measurement_noise;
    bool initialized;
} ekf_t;

esp_err_t ekf_init(ekf_t *ekf);
esp_err_t ekf_step(ekf_t *ekf, const imu_sample_t *sample, float dt_s,
                   attitude_state_t *out);
