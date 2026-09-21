#pragma once

#include "driver/i2c_master.h"
#include "esp_err.h"

esp_err_t i2c_bus_init(i2c_master_bus_handle_t *out_bus);
esp_err_t i2c_bus_scan(i2c_master_bus_handle_t bus, unsigned *found_count);
