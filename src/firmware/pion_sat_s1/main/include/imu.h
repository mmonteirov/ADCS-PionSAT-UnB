#pragma once

#include "app_types.h"
#include "driver/i2c_master.h"
#include "esp_err.h"

typedef struct {
    i2c_master_bus_handle_t bus;
    i2c_master_dev_handle_t device;
    i2c_master_dev_handle_t magnetometer;
    bool identified;
    bool simulation;
    bool magnetometer_available;
    uint8_t address;
    uint8_t who_am_i;
    float gyro_bias_rads[3];
    float mag_adjustment[3];
    float last_mag_uT[3];
    bool has_magnetometer_sample;
    uint32_t sample_counter;
} imu_handle_t;

/*
 * Esta camada permanece deliberadamente generica. Depois do scanner, substituir
 * imu_identify()/imu_read() por um driver que valide WHO_AM_I e registradores
 * do modelo real da IMU.
 */
esp_err_t imu_init(imu_handle_t *imu, i2c_master_bus_handle_t bus);
esp_err_t imu_read(imu_handle_t *imu, imu_sample_t *sample);
