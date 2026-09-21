"""Gera resumo e graficos da telemetria gravada pela Ground Station."""

from __future__ import annotations

import argparse
import os
import pathlib

os.environ.setdefault("MPLCONFIGDIR", str(pathlib.Path.cwd() / ".matplotlib-cache"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "arrival_time_s", "seq_num", "q_w", "q_x", "q_y", "q_z",
    "gyro_x_rad_s", "gyro_y_rad_s", "gyro_z_rad_s",
    "mag_x_uT", "mag_y_uT", "mag_z_uT", "actuator_pwm",
}


def quaternion_to_euler_deg(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    w = frame["q_w"].to_numpy(float)
    x = frame["q_x"].to_numpy(float)
    y = frame["q_y"].to_numpy(float)
    z = frame["q_z"].to_numpy(float)
    norm = np.sqrt(w*w + x*x + y*y + z*z)
    w, x, y, z = w/norm, x/norm, y/norm, z/norm
    roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
    yaw = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    return tuple(np.rad2deg(v) for v in (roll, pitch, yaw))


def save_plot(path: pathlib.Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Analise da telemetria do PION Sat")
    parser.add_argument("csv", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("analise_oficina"))
    args = parser.parse_args()

    frame = pd.read_csv(args.csv)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise SystemExit(f"CSV incompativel; colunas ausentes: {sorted(missing)}")
    if len(frame) < 2:
        raise SystemExit("CSV precisa conter pelo menos dois pacotes")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    t = frame["arrival_time_s"].to_numpy(float)
    t = t - t[0]
    duration = t[-1]
    rate_hz = (len(frame) - 1) / duration
    sequence = frame["seq_num"].to_numpy(np.uint16)
    expected = (sequence[:-1].astype(np.uint32) + 1) & 0xFFFF
    gaps = int(np.sum((sequence[1:].astype(np.uint32) - expected) & 0xFFFF))

    q_norm = np.sqrt(sum(frame[name].to_numpy(float)**2 for name in ("q_w", "q_x", "q_y", "q_z")))
    gyro_norm = np.sqrt(sum(frame[name].to_numpy(float)**2 for name in ("gyro_x_rad_s", "gyro_y_rad_s", "gyro_z_rad_s")))
    mag_norm = np.sqrt(sum(frame[name].to_numpy(float)**2 for name in ("mag_x_uT", "mag_y_uT", "mag_z_uT")))
    roll, pitch, yaw = quaternion_to_euler_deg(frame)

    plt.style.use("dark_background")
    colors = ("#ff5a5f", "#42d392", "#4da3ff")

    plt.figure(figsize=(10, 5))
    for values, label, color in zip((roll, pitch, yaw), ("Roll", "Pitch", "Yaw"), colors):
        plt.plot(t, values, label=label, color=color, linewidth=1.6)
    plt.xlabel("Tempo (s)")
    plt.ylabel("Ângulo (graus)")
    plt.title("Atitude estimada")
    plt.grid(alpha=0.2)
    plt.legend()
    save_plot(args.output_dir / "01_atitude.png")

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(t, gyro_norm, color="#4da3ff", linewidth=1.4)
    axes[0].set_ylabel("|ω| (rad/s)")
    axes[0].set_title("Sensores da IMU")
    axes[0].grid(alpha=0.2)
    axes[1].plot(t, mag_norm, color="#ffc857", linewidth=1.4)
    axes[1].set_ylabel("|B| (µT)")
    axes[1].set_xlabel("Tempo (s)")
    axes[1].grid(alpha=0.2)
    save_plot(args.output_dir / "02_imu.png")

    plt.figure(figsize=(10, 4.5))
    plt.plot(t, q_norm, color="#42d392", linewidth=1.4, label="Norma do quaternion")
    plt.axhline(1.0, color="white", linewidth=1, linestyle="--", alpha=0.7)
    plt.ylim(min(0.995, q_norm.min() - 0.001), max(1.005, q_norm.max() + 0.001))
    plt.xlabel("Tempo (s)")
    plt.ylabel("|q|")
    plt.title("Integridade da solução de atitude")
    plt.grid(alpha=0.2)
    save_plot(args.output_dir / "03_quaternion.png")

    summary = pd.DataFrame([{
        "arquivo": str(args.csv),
        "pacotes": len(frame),
        "duracao_s": round(duration, 3),
        "taxa_hz": round(rate_hz, 3),
        "perdas_sequencia": gaps,
        "q_norm_min": q_norm.min(),
        "q_norm_max": q_norm.max(),
        "gyro_pico_rad_s": gyro_norm.max(),
        "mag_min_uT": mag_norm.min(),
        "mag_max_uT": mag_norm.max(),
        "atuador_sempre_zero": bool((frame["actuator_pwm"] == 0).all()),
    }])
    summary.to_csv(args.output_dir / "resumo.csv", index=False)
    print(summary.to_string(index=False))
    print(f"Graficos salvos em: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
