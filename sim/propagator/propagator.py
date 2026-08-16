"""
propagator.py
==============
Propagador orbital RK4 com perturbacao J2 (2 corpos + achatamento terrestre).

NOTA SOBRE ESTA REVISAO (Ago/2026)
------------------------------------
Este modulo NAO foi alterado numericamente pela atualizacao de massa/inercia
do CAD (ver inertia.py::negligibility_report()). Motivo fisico: a equacao de
movimento translacional usada aqui e a aproximacao de massa pontual/restrita
de dois corpos,

    r_ddot = -mu/|r|^3 * r + a_J2

onde mu = G*M_terra e o parametro gravitacional padrao da TERRA, nao do
satelite. A massa do satelite se cancela na deducao de F=ma para o problema
de 2 corpos quando m_satelite << M_terra (por um fator de ~10^22 aqui), o que
e sempre verdade para qualquer CubeSat/PicoSat real. Ou seja: massa e inercia
do PionSat sao estruturalmente irrelevantes para propagator.py, independente
de qualquer precisao de balanca ou CAD -- por isso o veredito de
"negligivel" para este modulo e categorico (nao e uma questao de threshold
numerico, e sim de a variavel nao aparecer na equacao).
"""

from __future__ import annotations

import numpy as np

import params


def two_body_j2_acceleration(r_eci_m: np.ndarray) -> np.ndarray:
    """
    Aceleracao gravitacional (2 corpos + J2) em ECI [m/s^2], dado o vetor
    posicao r_eci_m [m]. Independe da massa do satelite (ver docstring).
    """
    r = np.asarray(r_eci_m, dtype=float)
    r_norm = np.linalg.norm(r)

    mu = params.MU_EARTH_M3_S2
    Re = params.R_EARTH_M
    J2 = params.J2

    a_two_body = -mu / r_norm**3 * r

    x, y, z = r
    factor = 1.5 * J2 * mu * Re**2 / r_norm**5
    zr2 = (z / r_norm) ** 2
    a_j2 = factor * np.array([
        x * (5.0 * zr2 - 1.0),
        y * (5.0 * zr2 - 1.0),
        z * (5.0 * zr2 - 3.0),
    ])

    return a_two_body + a_j2


def _state_derivative(state: np.ndarray) -> np.ndarray:
    """state = [rx, ry, rz, vx, vy, vz] -> [vx, vy, vz, ax, ay, az]."""
    r = state[:3]
    v = state[3:]
    a = two_body_j2_acceleration(r)
    return np.concatenate([v, a])


def rk4_step(state: np.ndarray, dt: float) -> np.ndarray:
    """Um passo de RK4 para o vetor de estado orbital [r, v] (6,)."""
    k1 = _state_derivative(state)
    k2 = _state_derivative(state + dt / 2.0 * k1)
    k3 = _state_derivative(state + dt / 2.0 * k2)
    k4 = _state_derivative(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def propagate(
    r0_eci_m: np.ndarray,
    v0_eci_m_s: np.ndarray,
    t_end_s: float,
    dt_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Propaga o estado orbital [r, v] de t=0 a t=t_end_s com passo dt_s.
    Retorna (t_array, state_array) com state_array.shape == (n_steps+1, 6).
    """
    n_steps = int(round(t_end_s / dt_s))
    t_array = dt_s * np.arange(n_steps + 1)

    state = np.concatenate([np.asarray(r0_eci_m, dtype=float), np.asarray(v0_eci_m_s, dtype=float)])
    state_array = np.zeros((n_steps + 1, 6))
    state_array[0] = state

    for k in range(n_steps):
        state = rk4_step(state, dt_s)
        state_array[k + 1] = state

    return t_array, state_array


def circular_orbit_initial_state(altitude_m: float, inclination_rad: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Estado inicial (r, v) para uma orbita circular simples no plano XY inclinado."""
    r_mag = params.R_EARTH_M + altitude_m
    v_mag = np.sqrt(params.MU_EARTH_M3_S2 / r_mag)

    r0 = np.array([r_mag, 0.0, 0.0])
    v0 = v_mag * np.array([0.0, np.cos(inclination_rad), np.sin(inclination_rad)])
    return r0, v0


if __name__ == "__main__":
    print("== propagator.py: auto-teste (independente de massa/inercia do satelite) ==")

    r0, v0 = circular_orbit_initial_state(altitude_m=500.0e3, inclination_rad=np.radians(51.6))
    T_orbit = 2.0 * np.pi * np.sqrt(np.linalg.norm(r0) ** 3 / params.MU_EARTH_M3_S2)
    print(f"Altitude: 500 km | Periodo teorico: {T_orbit/60:.2f} min")

    t_arr, state_arr = propagate(r0, v0, t_end_s=T_orbit, dt_s=1.0)
    r_final = state_arr[-1, :3]
    r_mag_final = np.linalg.norm(r_final)
    r_mag_inicial = np.linalg.norm(r0)

    print(f"|r| inicial = {r_mag_inicial/1000:.3f} km")
    print(f"|r| apos 1 orbita = {r_mag_final/1000:.3f} km "
          f"(variacao = {abs(r_mag_final-r_mag_inicial):.3f} m -- J2 causa precessao, "
          f"nao afeta |r| em 1a ordem para orbita quase-circular)")
