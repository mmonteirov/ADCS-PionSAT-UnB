#include "imu.h"

#include <string.h>
#include <math.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

static const char *TAG = "imu";

#define IMU_I2C_ADDRESS       0x68U
#define IMU_REG_WHO_AM_I      0x75U
#define IMU_I2C_TIMEOUT_MS    100
#define IMU_EXPECTED_ID        0x71U
#define IMU_REG_SMPLRT_DIV     0x19U
#define IMU_REG_CONFIG         0x1AU
#define IMU_REG_GYRO_CONFIG    0x1BU
#define IMU_REG_ACCEL_CONFIG   0x1CU
#define IMU_REG_ACCEL_CONFIG2  0x1DU
#define IMU_REG_INT_PIN_CFG    0x37U
#define IMU_REG_ACCEL_XOUT_H   0x3BU
#define IMU_REG_USER_CTRL      0x6AU
#define IMU_REG_PWR_MGMT_1     0x6BU
#define IMU_REG_PWR_MGMT_2     0x6CU

#define MAG_I2C_ADDRESS        0x0CU
#define MAG_REG_WIA            0x00U
#define MAG_REG_ST1            0x02U
#define MAG_REG_HXL            0x03U
#define MAG_REG_CNTL1          0x0AU
#define MAG_REG_ASAX           0x10U
#define MAG_EXPECTED_ID        0x48U

#define STANDARD_GRAVITY       9.80665f
#define ACCEL_LSB_PER_G        16384.0f
#define GYRO_LSB_PER_DPS       131.0f
#define DEG_TO_RAD             0.01745329251994329577f
#define MAG_UT_PER_LSB         (4912.0f / 32760.0f)

static esp_err_t read_register(i2c_master_dev_handle_t device,
                               uint8_t reg, uint8_t *value)
{
    if ((device == NULL) || (value == NULL)) {
        return ESP_ERR_INVALID_ARG;
    }
    return i2c_master_transmit_receive(device, &reg, sizeof(reg), value,
                                       sizeof(*value), IMU_I2C_TIMEOUT_MS);
}
static esp_err_t read_registers(i2c_master_dev_handle_t device, uint8_t reg,
                                uint8_t *values, size_t length)
{
    if ((device == NULL) || (values == NULL) || (length == 0U)) {
        return ESP_ERR_INVALID_ARG;
    }
    return i2c_master_transmit_receive(device, &reg, sizeof(reg), values,
                                       length, IMU_I2C_TIMEOUT_MS);
}

static esp_err_t write_register(i2c_master_dev_handle_t device,
                                uint8_t reg, uint8_t value)
{
    if (device == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    const uint8_t command[2] = {reg, value};
    return i2c_master_transmit(device, command, sizeof(command),
                               IMU_I2C_TIMEOUT_MS);
}

static int16_t be_i16(const uint8_t *bytes)
{
    return (int16_t)(((uint16_t)bytes[0] << 8) | bytes[1]);
}

static int16_t le_i16(const uint8_t *bytes)
{
    return (int16_t)(((uint16_t)bytes[1] << 8) | bytes[0]);
}

static esp_err_t probe_identity(imu_handle_t *imu)
{
    const i2c_device_config_t config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = IMU_I2C_ADDRESS,
        .scl_speed_hz = 400000U,
    };
    esp_err_t err = i2c_master_bus_add_device(imu->bus, &config, &imu->device);
    if (err != ESP_OK) {
        return err;
    }

    imu->address = IMU_I2C_ADDRESS;
    err = read_register(imu->device, IMU_REG_WHO_AM_I, &imu->who_am_i);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Identificacao segura: addr=0x%02X WHO_AM_I=0x%02X",
                 imu->address, imu->who_am_i);
    }
    return err;
}

static esp_err_t configure_mpu9250(imu_handle_t *imu)
{
    esp_err_t err = write_register(imu->device, IMU_REG_PWR_MGMT_1, 0x80U);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(100U));

    const struct {
        uint8_t reg;
        uint8_t value;
    } settings[] = {
        {IMU_REG_PWR_MGMT_1, 0x01U},    /* PLL do giroscopio X. */
        {IMU_REG_PWR_MGMT_2, 0x00U},    /* Habilita os seis eixos. */
        {IMU_REG_CONFIG, 0x03U},        /* DLPF giroscopio ~41 Hz. */
        {IMU_REG_SMPLRT_DIV, 0x09U},    /* 1 kHz / (1 + 9) = 100 Hz. */
        {IMU_REG_GYRO_CONFIG, 0x00U},   /* +/-250 graus/s. */
        {IMU_REG_ACCEL_CONFIG, 0x00U},  /* +/-2 g. */
        {IMU_REG_ACCEL_CONFIG2, 0x03U}, /* DLPF acelerometro ~44,8 Hz. */
        {IMU_REG_USER_CTRL, 0x00U},     /* Desabilita mestre I2C interno. */
        {IMU_REG_INT_PIN_CFG, 0x02U},   /* Bypass para o AK8963. */
    };

    for (size_t i = 0; i < sizeof(settings) / sizeof(settings[0]); ++i) {
        err = write_register(imu->device, settings[i].reg, settings[i].value);
        if (err != ESP_OK) {
            return err;
        }
        vTaskDelay(pdMS_TO_TICKS(2U));
    }
    return ESP_OK;
}

static esp_err_t configure_ak8963(imu_handle_t *imu)
{
    const i2c_device_config_t config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MAG_I2C_ADDRESS,
        .scl_speed_hz = 400000U,
    };
    esp_err_t err = i2c_master_bus_add_device(imu->bus, &config,
                                               &imu->magnetometer);
    if (err != ESP_OK) {
        return err;
    }

    uint8_t identity = 0U;
    err = read_register(imu->magnetometer, MAG_REG_WIA, &identity);
    if ((err != ESP_OK) || (identity != MAG_EXPECTED_ID)) {
        ESP_LOGW(TAG, "AK8963 nao confirmado: WIA=0x%02X err=%s", identity,
                 esp_err_to_name(err));
        return (err == ESP_OK) ? ESP_ERR_NOT_FOUND : err;
    }

    err = write_register(imu->magnetometer, MAG_REG_CNTL1, 0x00U);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(10U));
    err = write_register(imu->magnetometer, MAG_REG_CNTL1, 0x0FU);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(10U));

    uint8_t asa[3] = {0};
    err = read_registers(imu->magnetometer, MAG_REG_ASAX, asa, sizeof(asa));
    if (err != ESP_OK) {
        return err;
    }
    for (size_t i = 0; i < 3U; ++i) {
        imu->mag_adjustment[i] = ((float)asa[i] - 128.0f) / 256.0f + 1.0f;
    }

    err = write_register(imu->magnetometer, MAG_REG_CNTL1, 0x00U);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(10U));
    err = write_register(imu->magnetometer, MAG_REG_CNTL1, 0x16U);
    if (err == ESP_OK) {
        vTaskDelay(pdMS_TO_TICKS(10U));
        imu->magnetometer_available = true;
        ESP_LOGI(TAG, "AK8963 confirmado em 0x0C, modo continuo 100 Hz/16-bit");
    }
    return err;
}

static esp_err_t read_accel_gyro_raw(imu_handle_t *imu, int16_t accel[3],
                                     int16_t gyro[3])
{
    uint8_t raw[14];
    const esp_err_t err = read_registers(imu->device, IMU_REG_ACCEL_XOUT_H,
                                         raw, sizeof(raw));
    if (err != ESP_OK) {
        return err;
    }
    for (size_t i = 0; i < 3U; ++i) {
        accel[i] = be_i16(&raw[i * 2U]);
        gyro[i] = be_i16(&raw[8U + i * 2U]);
    }
    return ESP_OK;
}

static esp_err_t calibrate_gyro(imu_handle_t *imu)
{
    const unsigned calibration_samples = 200U;
    int64_t sum[3] = {0};

    ESP_LOGI(TAG, "Calibrando giroscopio por 2 s; mantenha o satelite parado");
    for (unsigned n = 0; n < calibration_samples; ++n) {
        int16_t accel[3];
        int16_t gyro[3];
        const esp_err_t err = read_accel_gyro_raw(imu, accel, gyro);
        if (err != ESP_OK) {
            return err;
        }
        for (size_t axis = 0; axis < 3U; ++axis) {
            sum[axis] += gyro[axis];
        }
        vTaskDelay(pdMS_TO_TICKS(10U));
    }
    for (size_t axis = 0; axis < 3U; ++axis) {
        const float raw_bias = (float)sum[axis] / (float)calibration_samples;
        imu->gyro_bias_rads[axis] = raw_bias * DEG_TO_RAD / GYRO_LSB_PER_DPS;
    }
    ESP_LOGI(TAG, "Bias gyro [rad/s]: %.6f %.6f %.6f",
             imu->gyro_bias_rads[0], imu->gyro_bias_rads[1],
             imu->gyro_bias_rads[2]);
    return ESP_OK;
}

esp_err_t imu_init(imu_handle_t *imu, i2c_master_bus_handle_t bus)
{
    if ((imu == NULL) || (bus == NULL)) {
        return ESP_ERR_INVALID_ARG;
    }

    memset(imu, 0, sizeof(*imu));
    imu->bus = bus;
    const esp_err_t probe_err = probe_identity(imu);
    if (probe_err != ESP_OK) {
        ESP_LOGW(TAG, "Nao foi possivel ler WHO_AM_I: %s",
                 esp_err_to_name(probe_err));
    }
#ifdef CONFIG_PION_IMU_SIMULATION
    imu->simulation = true;
    ESP_LOGW(TAG, "Modo de simulacao ativo: IMU em repouso");
    return ESP_OK;
#else
    if ((probe_err != ESP_OK) || (imu->who_am_i != IMU_EXPECTED_ID)) {
        ESP_LOGE(TAG, "MPU-9250 nao confirmado; leitura fisica bloqueada");
        return ESP_ERR_NOT_FOUND;
    }
    esp_err_t err = configure_mpu9250(imu);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao configurar MPU-9250: %s", esp_err_to_name(err));
        return err;
    }
    imu->identified = true;

    err = configure_ak8963(imu);
    if (err != ESP_OK) {
        imu->magnetometer_available = false;
        ESP_LOGW(TAG, "Magnetometro indisponivel; accel/gyro permanecem ativos");
    }
    err = calibrate_gyro(imu);
    if (err != ESP_OK) {
        imu->identified = false;
        ESP_LOGE(TAG, "Falha na calibracao do giroscopio: %s",
                 esp_err_to_name(err));
        return err;
    }
    ESP_LOGI(TAG, "MPU-9250 fisico ativo a 100 Hz");
    return ESP_OK;
#endif
}

esp_err_t imu_read(imu_handle_t *imu, imu_sample_t *sample)
{
    if ((imu == NULL) || (sample == NULL)) {
        return ESP_ERR_INVALID_ARG;
    }
    if (imu->simulation) {
        memset(sample, 0, sizeof(*sample));
        sample->accel_mps2[2] = 9.80665f;
        sample->accel_valid = true;
        sample->gyro_valid = true;
        sample->mag_valid = false;
        ++imu->sample_counter;
        return ESP_OK;
    }
    if (!imu->identified) {
        return ESP_ERR_INVALID_STATE;
    }

    int16_t accel_raw[3];
    int16_t gyro_raw[3];
    esp_err_t err = read_accel_gyro_raw(imu, accel_raw, gyro_raw);
    if (err != ESP_OK) {
        return err;
    }

    memset(sample, 0, sizeof(*sample));
    for (size_t axis = 0; axis < 3U; ++axis) {
        sample->accel_mps2[axis] = (float)accel_raw[axis] *
                                   STANDARD_GRAVITY / ACCEL_LSB_PER_G;
        sample->gyro_rads[axis] = (float)gyro_raw[axis] *
                                  DEG_TO_RAD / GYRO_LSB_PER_DPS -
                                  imu->gyro_bias_rads[axis];
    }
    sample->accel_valid = true;
    sample->gyro_valid = true;

    if (imu->magnetometer_available) {
        uint8_t status = 0U;
        err = read_register(imu->magnetometer, MAG_REG_ST1, &status);
        if ((err == ESP_OK) && ((status & 0x01U) != 0U)) {
            uint8_t raw[7];
            err = read_registers(imu->magnetometer, MAG_REG_HXL, raw,
                                 sizeof(raw));
            if ((err == ESP_OK) && ((raw[6] & 0x08U) == 0U)) {
                for (size_t axis = 0; axis < 3U; ++axis) {
                    imu->last_mag_uT[axis] =
                        (float)le_i16(&raw[axis * 2U]) * MAG_UT_PER_LSB *
                        imu->mag_adjustment[axis];
                }
                imu->has_magnetometer_sample = true;
            }
        }
    }
    if (imu->has_magnetometer_sample) {
        memcpy(sample->mag_uT, imu->last_mag_uT, sizeof(sample->mag_uT));
        sample->mag_valid = true;
    }

    ++imu->sample_counter;
    return ESP_OK;
}
