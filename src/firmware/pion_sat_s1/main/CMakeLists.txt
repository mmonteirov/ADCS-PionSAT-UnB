idf_component_register(
    SRCS
        "app_main.c"
        "i2c_bus.c"
        "imu.c"
        "ekf.c"
        "actuator.c"
        "telemetry_packet.c"
    INCLUDE_DIRS "include"
    REQUIRES driver esp_timer esp_system
)
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wall
    -Wextra
    -Werror=return-type
)
