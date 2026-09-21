#include "ekf.h"

#include <math.h>
#include <string.h>

static bool finite_vector(const float *v, size_t n)
{
    for (size_t i = 0; i < n; ++i) {
        if (!isfinite(v[i])) {
            return false;
        }
    }
    return true;
}
static esp_err_t normalize_quaternion(float q[4])
{
    const float norm_sq = q[0] * q[0] + q[1] * q[1] +
                          q[2] * q[2] + q[3] * q[3];
    if (!isfinite(norm_sq) || (norm_sq < 1.0e-12f)) {
        return ESP_ERR_INVALID_STATE;
    }
    const float inv_norm = 1.0f / sqrtf(norm_sq);
    for (size_t i = 0; i < 4; ++i) {
        q[i] *= inv_norm;
    }
    return ESP_OK;
}

static bool inverse_3x3(const float a[3][3], float inv[3][3])
{
    const float det =
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) -
        a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) +
        a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);

    if (!isfinite(det) || (fabsf(det) < 1.0e-9f)) {
        return false;
    }

    const float d = 1.0f / det;
    inv[0][0] =  (a[1][1] * a[2][2] - a[1][2] * a[2][1]) * d;
    inv[0][1] = -(a[0][1] * a[2][2] - a[0][2] * a[2][1]) * d;
    inv[0][2] =  (a[0][1] * a[1][2] - a[0][2] * a[1][1]) * d;
    inv[1][0] = -(a[1][0] * a[2][2] - a[1][2] * a[2][0]) * d;
    inv[1][1] =  (a[0][0] * a[2][2] - a[0][2] * a[2][0]) * d;
    inv[1][2] = -(a[0][0] * a[1][2] - a[0][2] * a[1][0]) * d;
    inv[2][0] =  (a[1][0] * a[2][1] - a[1][1] * a[2][0]) * d;
    inv[2][1] = -(a[0][0] * a[2][1] - a[0][1] * a[2][0]) * d;
    inv[2][2] =  (a[0][0] * a[1][1] - a[0][1] * a[1][0]) * d;
    return true;
}

esp_err_t ekf_init(ekf_t *ekf)
{
    if (ekf == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    memset(ekf, 0, sizeof(*ekf));
    ekf->x[0] = 1.0f;
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        ekf->p[i][i] = (i < 4) ? 0.10f : 0.01f;
    }
    ekf->gyro_process_noise = 1.0e-4f;
    ekf->bias_process_noise = 1.0e-7f;
    ekf->accel_measurement_noise = 2.5e-2f;
    ekf->initialized = true;
    return ESP_OK;
}

static esp_err_t predict(ekf_t *ekf, const float gyro[3], float dt)
{
    const float wx = gyro[0] - ekf->x[4];
    const float wy = gyro[1] - ekf->x[5];
    const float wz = gyro[2] - ekf->x[6];
    const float w = ekf->x[0];
    const float x = ekf->x[1];
    const float y = ekf->x[2];
    const float z = ekf->x[3];
    const float half_dt = 0.5f * dt;

    ekf->x[0] += half_dt * (-x * wx - y * wy - z * wz);
    ekf->x[1] += half_dt * ( w * wx + y * wz - z * wy);
    ekf->x[2] += half_dt * ( w * wy - x * wz + z * wx);
    ekf->x[3] += half_dt * ( w * wz + x * wy - y * wx);

    const esp_err_t norm_err = normalize_quaternion(ekf->x);
    if (norm_err != ESP_OK) {
        return norm_err;
    }

    /* Propagacao conservadora inicial. A1 deve fornecer F e Q definitivos. */
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        ekf->p[i][i] += ((i < 4) ? ekf->gyro_process_noise
                                  : ekf->bias_process_noise) * dt;
    }
    return ESP_OK;
}

static esp_err_t update_accel(ekf_t *ekf, const float accel[3])
{
    const float norm = sqrtf(accel[0] * accel[0] + accel[1] * accel[1] +
                             accel[2] * accel[2]);
    if (!isfinite(norm) || (norm < 7.35f) || (norm > 12.26f)) {
        return ESP_ERR_INVALID_RESPONSE; /* rejeita movimento linear/outlier */
    }

    const float z_meas[3] = {accel[0] / norm, accel[1] / norm, accel[2] / norm};
    const float w = ekf->x[0], x = ekf->x[1], y = ekf->x[2], z = ekf->x[3];
    const float h[3] = {
        2.0f * (x * z - w * y),
        2.0f * (y * z + w * x),
        w * w - x * x - y * y + z * z,
    };
    const float residual[3] = {
        z_meas[0] - h[0], z_meas[1] - h[1], z_meas[2] - h[2]
    };
    const float H[3][EKF_STATE_DIM] = {
        {-2*y,  2*z, -2*w,  2*x, 0, 0, 0},
        { 2*x,  2*w,  2*z,  2*y, 0, 0, 0},
        { 2*w, -2*x, -2*y,  2*z, 0, 0, 0},
    };

    float ph_t[EKF_STATE_DIM][3] = {0};
    float s[3][3] = {0};
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            for (size_t k = 0; k < EKF_STATE_DIM; ++k) {
                ph_t[i][j] += ekf->p[i][k] * H[j][k];
            }
        }
    }
    for (size_t i = 0; i < 3; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            for (size_t k = 0; k < EKF_STATE_DIM; ++k) {
                s[i][j] += H[i][k] * ph_t[k][j];
            }
        }
        s[i][i] += ekf->accel_measurement_noise;
    }

    float s_inv[3][3];
    if (!inverse_3x3(s, s_inv)) {
        return ESP_ERR_INVALID_STATE;
    }

    float gain[EKF_STATE_DIM][3] = {0};
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            for (size_t k = 0; k < 3; ++k) {
                gain[i][j] += ph_t[i][k] * s_inv[k][j];
            }
        }
    }
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            ekf->x[i] += gain[i][j] * residual[j];
        }
    }
    if (normalize_quaternion(ekf->x) != ESP_OK) {
        return ESP_ERR_INVALID_STATE;
    }

    /* Joseph form: P = (I-KH)P(I-KH)' + KRK' */
    float ikh[EKF_STATE_DIM][EKF_STATE_DIM] = {0};
    float temp[EKF_STATE_DIM][EKF_STATE_DIM] = {0};
    float updated[EKF_STATE_DIM][EKF_STATE_DIM] = {0};
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        ikh[i][i] = 1.0f;
        for (size_t j = 0; j < EKF_STATE_DIM; ++j) {
            for (size_t k = 0; k < 3; ++k) {
                ikh[i][j] -= gain[i][k] * H[k][j];
            }
        }
    }
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        for (size_t j = 0; j < EKF_STATE_DIM; ++j) {
            for (size_t k = 0; k < EKF_STATE_DIM; ++k) {
                temp[i][j] += ikh[i][k] * ekf->p[k][j];
            }
        }
    }
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        for (size_t j = 0; j < EKF_STATE_DIM; ++j) {
            for (size_t k = 0; k < EKF_STATE_DIM; ++k) {
                updated[i][j] += temp[i][k] * ikh[j][k];
            }
            for (size_t k = 0; k < 3; ++k) {
                updated[i][j] += gain[i][k] *
                    ekf->accel_measurement_noise * gain[j][k];
            }
        }
    }
    memcpy(ekf->p, updated, sizeof(updated));
    return ESP_OK;
}

esp_err_t ekf_step(ekf_t *ekf, const imu_sample_t *sample, float dt_s,
                   attitude_state_t *out)
{
    if ((ekf == NULL) || (sample == NULL) || (out == NULL) ||
        !ekf->initialized || !sample->gyro_valid ||
        !finite_vector(sample->gyro_rads, 3) ||
        !isfinite(dt_s) || (dt_s <= 0.0f) || (dt_s > 0.1f)) {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = predict(ekf, sample->gyro_rads, dt_s);
    if (err != ESP_OK) {
        return err;
    }
    if (sample->accel_valid && finite_vector(sample->accel_mps2, 3)) {
        const esp_err_t update_err = update_accel(ekf, sample->accel_mps2);
        if ((update_err != ESP_OK) && (update_err != ESP_ERR_INVALID_RESPONSE)) {
            return update_err;
        }
    }

    memset(out, 0, sizeof(*out));
    out->timestamp_us = sample->timestamp_us;
    memcpy(out->q, ekf->x, sizeof(out->q));
    memcpy(out->gyro_bias_rads, &ekf->x[4], sizeof(out->gyro_bias_rads));
    for (size_t i = 0; i < EKF_STATE_DIM; ++i) {
        out->covariance_trace += ekf->p[i][i];
    }
    out->valid = finite_vector(ekf->x, EKF_STATE_DIM);
    return out->valid ? ESP_OK : ESP_ERR_INVALID_STATE;
}
