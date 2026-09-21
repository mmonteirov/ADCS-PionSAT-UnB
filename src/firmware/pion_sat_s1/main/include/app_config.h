#pragma once

#include "sdkconfig.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"

/* CONFIRMAR no esquema eletrico do PION Sat antes do ensaio. */
#define APP_I2C_PORT              I2C_NUM_0
#define APP_I2C_SDA_GPIO          ((gpio_num_t)CONFIG_PION_I2C_SDA_GPIO)
#define APP_I2C_SCL_GPIO          ((gpio_num_t)CONFIG_PION_I2C_SCL_GPIO)
#define APP_I2C_CLOCK_HZ          400000U
#define APP_I2C_GLITCH_FILTER     7

#define APP_SENSOR_PERIOD_MS      10U   /* 100 Hz */
#define APP_EKF_PERIOD_MS         20U   /* 50 Hz */
#define APP_CONTROL_PERIOD_MS     20U   /* 50 Hz */
#define APP_TELEMETRY_PERIOD_MS   50U   /* 20 Hz inicial */

#define APP_SENSOR_TASK_PRIORITY  10
#define APP_EKF_TASK_PRIORITY     7
#define APP_CONTROL_TASK_PRIORITY 6
#define APP_TELEM_TASK_PRIORITY   4

#define APP_SENSOR_TASK_CORE      0
#define APP_EKF_TASK_CORE         1
#define APP_CONTROL_TASK_CORE     1
#define APP_TELEM_TASK_CORE       0

#define APP_QUEUE_LENGTH          4U

/* Mantem a saida fisica bloqueada enquanto pinagem/driver nao forem validados. */
#ifdef CONFIG_PION_ACTUATOR_ENABLED
#define APP_ACTUATOR_ENABLED      1
#else
#define APP_ACTUATOR_ENABLED      0
#endif
