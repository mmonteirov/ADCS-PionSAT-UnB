#include "i2c_bus.h"

#include <inttypes.h>

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "i2c_bus";

esp_err_t i2c_bus_init(i2c_master_bus_handle_t *out_bus)
{
    if (out_bus == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    const i2c_master_bus_config_t config = {
        .i2c_port = APP_I2C_PORT,
        .sda_io_num = APP_I2C_SDA_GPIO,
        .scl_io_num = APP_I2C_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = APP_I2C_GLITCH_FILTER,
        .flags.enable_internal_pullup = true,
    };

    const esp_err_t err = i2c_new_master_bus(&config, out_bus);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao iniciar I2C: %s", esp_err_to_name(err));
    }
    return err;
}
esp_err_t i2c_bus_scan(i2c_master_bus_handle_t bus, unsigned *found_count)
{
    if ((bus == NULL) || (found_count == NULL)) {
        return ESP_ERR_INVALID_ARG;
    }

    unsigned found = 0;
    ESP_LOGI(TAG, "Scanner I2C iniciado (enderecos 0x08..0x77)");

    for (uint16_t address = 0x08; address <= 0x77; ++address) {
        const esp_err_t err = i2c_master_probe(bus, address, 20);
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "Dispositivo encontrado em 0x%02" PRIX16, address);
            ++found;
        } else if ((err != ESP_ERR_NOT_FOUND) && (err != ESP_ERR_TIMEOUT)) {
            ESP_LOGW(TAG, "Erro ao sondar 0x%02" PRIX16 ": %s",
                     address, esp_err_to_name(err));
        }
    }

    *found_count = found;
    ESP_LOGI(TAG, "Scanner concluido: %u dispositivo(s)", found);
    return ESP_OK;
}
