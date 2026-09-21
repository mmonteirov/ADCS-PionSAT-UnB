#include <inttypes.h>
#include <string.h>

#include "actuator.h"
#include "app_config.h"
#include "app_types.h"
#include "ekf.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "i2c_bus.h"
#include "imu.h"
#include "telemetry_packet.h"
#include "driver/uart.h"

static const char *TAG = "pion_adcs";
static QueueHandle_t sensor_queue;
static QueueHandle_t attitude_queue;
static QueueHandle_t latest_sensor_queue;
static i2c_master_bus_handle_t i2c_bus;
static imu_handle_t imu;

static esp_err_t telemetry_uart_init(void)
{
#ifdef CONFIG_PION_BINARY_TELEMETRY
    if (!uart_is_driver_installed(UART_NUM_0)) {
        const esp_err_t err = uart_driver_install(UART_NUM_0, 1024, 2048, 0,
                                                  NULL, 0);
        if (err != ESP_OK) {
            return err;
        }
    }
    return uart_set_baudrate(UART_NUM_0, 115200U);
#else
    return ESP_OK;
#endif
}
static void register_task_wdt(const char *name)
{
    const esp_err_t err = esp_task_wdt_add(NULL);
    if (err != ESP_OK) {
        ESP_LOGW(name, "Task nao adicionada ao WDT: %s", esp_err_to_name(err));
    }
}

static void sensor_task(void *argument)
{
    (void)argument;
    register_task_wdt("sensor_task");
    TickType_t wake = xTaskGetTickCount();
    unsigned consecutive_errors = 0;

    for (;;) {
        imu_sample_t sample = {0};
        const esp_err_t err = imu_read(&imu, &sample);
        if (err == ESP_OK) {
            sample.timestamp_us = esp_timer_get_time();
            if (xQueueSend(sensor_queue, &sample, 0) != pdPASS) {
                imu_sample_t discarded;
                (void)xQueueReceive(sensor_queue, &discarded, 0);
                (void)xQueueSend(sensor_queue, &sample, 0);
            }
            (void)xQueueOverwrite(latest_sensor_queue, &sample);
            consecutive_errors = 0;
        } else {
            ++consecutive_errors;
            if ((consecutive_errors == 1U) || ((consecutive_errors % 500U) == 0U)) {
                ESP_LOGW("sensor_task", "Leitura indisponivel: %s (erros=%u)",
                         esp_err_to_name(err), consecutive_errors);
            }
        }

        (void)esp_task_wdt_reset();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(APP_SENSOR_PERIOD_MS));
    }
}

static void ekf_task(void *argument)
{
    (void)argument;
    register_task_wdt("ekf_task");
    TickType_t wake = xTaskGetTickCount();
    ekf_t filter;
    imu_sample_t latest = {0};
    int64_t previous_us = 0;

    if (ekf_init(&filter) != ESP_OK) {
        ESP_LOGE("ekf_task", "Falha fatal ao inicializar EKF");
        vTaskDelete(NULL);
    }

    for (;;) {
        bool received = false;
        imu_sample_t candidate;
        while (xQueueReceive(sensor_queue, &candidate, 0) == pdPASS) {
            latest = candidate;
            received = true;
        }

        if (received) {
            float dt_s = APP_EKF_PERIOD_MS / 1000.0f;
            if (previous_us > 0) {
                dt_s = (float)(latest.timestamp_us - previous_us) / 1000000.0f;
            }
            previous_us = latest.timestamp_us;

            attitude_state_t state;
            const esp_err_t err = ekf_step(&filter, &latest, dt_s, &state);
            if (err == ESP_OK) {
                (void)xQueueOverwrite(attitude_queue, &state);
            } else {
                ESP_LOGW("ekf_task", "Amostra rejeitada: %s", esp_err_to_name(err));
            }
        }

        (void)esp_task_wdt_reset();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(APP_EKF_PERIOD_MS));
    }
}

static void control_task(void *argument)
{
    (void)argument;
    register_task_wdt("control_task");
    TickType_t wake = xTaskGetTickCount();

    for (;;) {
        actuator_command_t stop = {
            .timestamp_us = esp_timer_get_time(),
            .normalized_torque = 0.0f,
            .enable = false,
        };
        const esp_err_t err = actuator_apply(&stop);
        if (err != ESP_OK) {
            ESP_LOGE("control_task", "Falha no comando seguro: %s", esp_err_to_name(err));
            (void)actuator_safe_stop();
        }

        (void)esp_task_wdt_reset();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(APP_CONTROL_PERIOD_MS));
    }
}

static void telemetry_task(void *argument)
{
    (void)argument;
    register_task_wdt("telemetry_task");
    TickType_t wake = xTaskGetTickCount();
    attitude_state_t state;
    imu_sample_t sample;
    uint16_t sequence = 0U;

    /* Permite que as mensagens de inicializacao terminem antes do fluxo binario. */
    vTaskDelay(pdMS_TO_TICKS(250U));

    for (;;) {
        if ((xQueuePeek(attitude_queue, &state, 0) == pdPASS) && state.valid &&
            (xQueuePeek(latest_sensor_queue, &sample, 0) == pdPASS)) {
#ifdef CONFIG_PION_BINARY_TELEMETRY
            telemetry_packet_t packet;
            telemetry_packet_build(&packet, &state, &sample, sequence++);
            const int written = uart_write_bytes(UART_NUM_0, &packet, sizeof(packet));
            if (written != (int)sizeof(packet)) {
                ESP_LOGE("telemetry_task", "Falha UART: %d/%u bytes", written,
                         (unsigned)sizeof(packet));
            }
#else
            ESP_LOGI("telemetry_task",
                     "t=%" PRId64 " q=[%.5f %.5f %.5f %.5f] trP=%.6f",
                     state.timestamp_us, state.q[0], state.q[1],
                     state.q[2], state.q[3], state.covariance_trace);
#endif
        }
        (void)esp_task_wdt_reset();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(APP_TELEMETRY_PERIOD_MS));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Inicializando firmware ADCS do PION Sat");

    esp_err_t err = i2c_bus_init(&i2c_bus);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Inicializacao abortada: I2C indisponivel");
        return;
    }

    unsigned found_count = 0;
    err = i2c_bus_scan(i2c_bus, &found_count);
    if ((err != ESP_OK) || (found_count == 0U)) {
        ESP_LOGW(TAG, "Nenhum sensor confirmado; verifique pinagem e alimentacao");
    }

    err = imu_init(&imu, i2c_bus);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Driver especifico da IMU pendente: %s", esp_err_to_name(err));
    }

    err = actuator_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao inicializar atuador: %s", esp_err_to_name(err));
        return;
    }

    err = telemetry_uart_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao inicializar UART de telemetria: %s",
                 esp_err_to_name(err));
        return;
    }

    sensor_queue = xQueueCreate(APP_QUEUE_LENGTH, sizeof(imu_sample_t));
    attitude_queue = xQueueCreate(1, sizeof(attitude_state_t));
    latest_sensor_queue = xQueueCreate(1, sizeof(imu_sample_t));
    if ((sensor_queue == NULL) || (attitude_queue == NULL) ||
        (latest_sensor_queue == NULL)) {
        ESP_LOGE(TAG, "Falha ao alocar filas FreeRTOS");
        return;
    }

    BaseType_t ok = xTaskCreatePinnedToCore(sensor_task, "sensor_100hz", 4096, NULL,
                                            APP_SENSOR_TASK_PRIORITY, NULL,
                                            APP_SENSOR_TASK_CORE);
    if (ok != pdPASS) {
        ESP_LOGE(TAG, "Falha ao criar sensor_task");
        return;
    }
    ok = xTaskCreatePinnedToCore(ekf_task, "ekf_50hz", 6144, NULL,
                                 APP_EKF_TASK_PRIORITY, NULL, APP_EKF_TASK_CORE);
    if (ok != pdPASS) {
        ESP_LOGE(TAG, "Falha ao criar ekf_task");
        return;
    }
    ok = xTaskCreatePinnedToCore(control_task, "control_50hz", 3072, NULL,
                                 APP_CONTROL_TASK_PRIORITY, NULL,
                                 APP_CONTROL_TASK_CORE);
    if (ok != pdPASS) {
        ESP_LOGE(TAG, "Falha ao criar control_task");
        return;
    }
    ok = xTaskCreatePinnedToCore(telemetry_task, "telemetry_20hz", 3072, NULL,
                                 APP_TELEM_TASK_PRIORITY, NULL, APP_TELEM_TASK_CORE);
    if (ok != pdPASS) {
        ESP_LOGE(TAG, "Falha ao criar telemetry_task");
        return;
    }

    ESP_LOGI(TAG, "Tasks criadas; atuador fisico permanece bloqueado");
#ifdef CONFIG_PION_BINARY_TELEMETRY
    ESP_LOGI(TAG, "Telemetria binaria ICD v1.2 ativa: 76 bytes a 20 Hz");
#endif
}
