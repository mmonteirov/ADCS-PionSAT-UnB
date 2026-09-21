#include "actuator.h"

#include <math.h>

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "actuator";

esp_err_t actuator_init(void)
{
#if APP_ACTUATOR_ENABLED
    /* Configurar LEDC/MCPWM ou protocolo UART/SPI apos confirmar o driver. */
    return ESP_ERR_NOT_SUPPORTED;
#else
    ESP_LOGW(TAG, "Atuador bloqueado por configuracao de seguranca");
    return ESP_OK;
#endif
}
esp_err_t actuator_apply(const actuator_command_t *command)
{
    if ((command == NULL) || !isfinite(command->normalized_torque) ||
        (command->normalized_torque < -1.0f) ||
        (command->normalized_torque > 1.0f)) {
        return ESP_ERR_INVALID_ARG;
    }
#if APP_ACTUATOR_ENABLED
    return ESP_ERR_NOT_SUPPORTED;
#else
    return command->enable ? ESP_ERR_INVALID_STATE : ESP_OK;
#endif
}

esp_err_t actuator_safe_stop(void)
{
    ESP_LOGI(TAG, "Comando de parada segura aplicado");
    return ESP_OK;
}
