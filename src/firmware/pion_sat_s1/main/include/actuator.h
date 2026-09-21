#pragma once

#include "app_types.h"
#include "esp_err.h"

esp_err_t actuator_init(void);
esp_err_t actuator_apply(const actuator_command_t *command);
esp_err_t actuator_safe_stop(void);
