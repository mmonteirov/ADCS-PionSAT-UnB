"""Referencia minima, sem dependencias externas, para validar a etapa de predicao."""

from math import sqrt


def normalize(q):
    norm = sqrt(sum(value * value for value in q))
    if norm < 1e-12:
        raise ValueError("quaternion degenerado")
    return [value / norm for value in q]


def predict(q, bias, gyro, dt):
    wx, wy, wz = (gyro[i] - bias[i] for i in range(3))
    w, x, y, z = q
    half_dt = 0.5 * dt
    return normalize([
        w + half_dt * (-x * wx - y * wy - z * wz),
        x + half_dt * (w * wx + y * wz - z * wy),
        y + half_dt * (w * wy - x * wz + z * wx),
        z + half_dt * (w * wz + x * wy - y * wx),
    ])


def self_test():
    q = [1.0, 0.0, 0.0, 0.0]
    bias = [0.0, 0.0, 0.0]
    for _ in range(100):
        q = predict(q, bias, [0.0, 0.0, 0.0], 0.01)
    assert abs(q[0] - 1.0) < 1e-7
    assert max(abs(v) for v in q[1:]) < 1e-7
    print("OK: repouso preserva quaternion identidade")


if __name__ == "__main__":
    self_test()
