"""
euler_dynamics.py
==================
Integrador RK4 da equacao de Euler para o eixo controlado (Z, alinhado ao eixo
da roda de reacao 1-eixo do PionSat).

    I3 * omega_dot = tau_total(t, omega)          (1 grau de liberdade)

ATUALIZACAO DESTA REVISAO (Ago/2026) - LEIA COM ATENCAO
---------------------------------------------------------
A equipe exportou o CAD do satelite COMPLETO, com o chassi externo montado na
posicao correta (params.CAD_FULL_*, massa = 325.0 g). Checagem de
auto-consistencia: 325.0 - 263.5 (CAD sem chassi) = 61.5 g, EXATAMENTE igual
a massa do chassi externo medida em balanca -- ver
inertia.py::cross_check_cad_chassis_mass(). Isso da confianca alta de que o
CAD completo e a MELHOR fonte disponivel para I3.

Por isso, a fonte PADRAO deste modulo passa a ser `cad_full`: o tensor do CAD
COMPLETO (com chassi), que SUBSTITUI o workaround de "caixa uniforme com
massa total" usado na revisao anterior. Quantificacao do ganho: o workaround
antigo subestimava Izz em +17.1% frente ao CAD completo (ver
inertia.py::compare_old_workaround_vs_cad_full()) -- NAO desprezivel frente
ao limiar de 5% do projeto, portanto a migracao para `cad_full` e importante,
nao apenas cosmetica.

O tensor do CAD sem chassi (`cad_no_chassis`) continua disponivel, mas
representa so a pilha interna (263.5 g) -- NAO usar isoladamente para a
dinamica do corpo completo (ver inertia.py::chassis_contribution_magnitude(),
que mostra +20 a +46% de diferenca de magnitude ao incluir o chassi).

PENDENCIA (ver README/backlog) -- reduzida de escopo nesta revisao: a
transformacao de referencial CAD (mate connector -> canto da caixa) ainda nao
foi registrada, mas deixou de ser BLOQUEANTE para I3, pois agora usamos o
tensor do CAD completo diretamente (nao precisamos mais somar chassi +
pilha interna manualmente). A transformacao continua sendo necessaria para
posicionar corretamente o braco de alavanca dos acelerometros (Capitulo 3)
e para comparar CAD_FULL_CENTER_OF_MASS_MM com a geometria da caixa.

O modulo tambem verifica, na inicializacao, se Z e aproximadamente um eixo
principal de inercia do CAD COMPLETO (produtos de inercia Lxz, Lyz << Lzz).
Isso justifica a simplificacao "1 eixo desacoplado" adotada no projeto: com
os dados do CAD completo, Lxz/Lzz = 0.21% e Lyz/Lzz = 0.03% (ver inertia.py),
portanto o acoplamento entre eixos introduzido por usar Z como eixo de
controle sem re-diagonalizar o tensor e desprezivel para o corpo COMPLETO
(nao apenas para a pilha interna, como na revisao anterior).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

import params
import inertia


# ---------------------------------------------------------------------------
# Selecao da fonte de inercia (I3) para o eixo de controle
# ---------------------------------------------------------------------------

def get_I3_kg_m2(source: str = "cad_full") -> float:
    """
    Retorna o momento de inercia principal Izz [kg*m^2] a ser usado no eixo de
    controle, de acordo com `source`:

      - "cad_full" (PADRAO, recomendado): Izz do tensor do CAD COMPLETO (com
        chassi externo, 325.0 g). Melhor estimativa atual do corpo COMPLETO
        que gira no mancal a ar -- ver docstring do modulo.
      - "analytical_total": caixa uniforme com a massa TOTAL real medida
        (328.0 g). Workaround usado na revisao anterior; mantido para
        comparacao/regressao (subestima Izz em ~17% frente a "cad_full").
      - "cad_no_chassis": Izz do tensor do CAD SEM chassi externo (263.5 g).
        Representa APENAS a pilha interna. NAO usar isoladamente para a
        dinamica do corpo completo.
      - "analytical_no_chassis": caixa uniforme com a massa medida sem chassi
        (266.5 g). Usado apenas para validar "cad_no_chassis" (mesma config.).
    """
    if source == "cad_full":
        return float(params.CAD_FULL_INERTIA_TENSOR_KG_M2[2, 2])
    elif source == "analytical_total":
        I_ana = inertia.analytical_inertia_uniform_box(
            mass_kg=params.MEASURED_TOTAL_MASS_KG, dims_m=params.BOX_DIMENSIONS_M
        )
        return float(I_ana[2, 2])
    elif source == "cad_no_chassis":
        return float(params.CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2[2, 2])
    elif source == "analytical_no_chassis":
        I_ana = inertia.analytical_inertia_uniform_box(
            mass_kg=params.MEASURED_MASS_NO_CHASSIS_KG, dims_m=params.BOX_DIMENSIONS_M
        )
        return float(I_ana[2, 2])
    else:
        raise ValueError(
            f"source invalido: {source!r} (use 'cad_full', 'analytical_total', "
            "'cad_no_chassis' ou 'analytical_no_chassis')"
        )


def check_z_is_principal_axis(rel_threshold: float = 0.02) -> dict:
    """
    Verifica se Z e aproximadamente um eixo principal do tensor do CAD
    COMPLETO (com chassi), ou seja, se os produtos de inercia Lxz e Lyz sao
    desprezivos frente a Izz. Isso fundamenta o uso da equacao de Euler
    1-eixo desacoplada para o corpo COMPLETO (nao apenas para a pilha interna).
    """
    I_cad = params.CAD_FULL_INERTIA_TENSOR_KG_M2
    lxz_over_lzz = abs(I_cad[0, 2]) / I_cad[2, 2]
    lyz_over_lzz = abs(I_cad[1, 2]) / I_cad[2, 2]
    ok = (lxz_over_lzz < rel_threshold) and (lyz_over_lzz < rel_threshold)
    return {
        "Lxz/Lzz": lxz_over_lzz,
        "Lyz/Lzz": lyz_over_lzz,
        "threshold": rel_threshold,
        "z_aproximadamente_principal": bool(ok),
    }


# ---------------------------------------------------------------------------
# Integrador RK4 - equacao de Euler 1-eixo
# ---------------------------------------------------------------------------

def euler_1axis_rk4_step(
    omega: float,
    t: float,
    dt: float,
    torque_func: Callable[[float, float], float],
    I3: float,
) -> float:
    """
    Um passo de RK4 para omega_dot = torque_func(t, omega) / I3.

    Parametros
    ----------
    omega : float
        Velocidade angular atual em torno do eixo de controle [rad/s].
    t : float
        Tempo atual [s].
    dt : float
        Passo de integracao [s].
    torque_func : callable
        Funcao torque_func(t, omega) -> torque total [N*m] no eixo de controle
        (soma de torque de controle + perturbacoes, ver perturbations.py).
    I3 : float
        Momento de inercia principal no eixo de controle [kg*m^2].

    Retorna
    -------
    float
        omega atualizado ao final do passo.
    """
    def f(tt, ww):
        return torque_func(tt, ww) / I3

    k1 = f(t, omega)
    k2 = f(t + dt / 2.0, omega + dt / 2.0 * k1)
    k3 = f(t + dt / 2.0, omega + dt / 2.0 * k2)
    k4 = f(t + dt, omega + dt * k3)

    return omega + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def integrate_euler_1axis(
    omega0: float,
    t0: float,
    t_end: float,
    dt: float,
    torque_func: Callable[[float, float], float],
    I3: float | None = None,
    I3_source: str = "cad_full",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Integra a equacao de Euler 1-eixo de t0 a t_end com passo dt.

    Se `I3` nao for fornecido explicitamente, ele e obtido via
    `get_I3_kg_m2(I3_source)` (padrao: tensor do CAD completo, corpo real
    com chassi -- ver docstring do modulo).

    Retorna (t_array, omega_array).
    """
    if I3 is None:
        I3 = get_I3_kg_m2(I3_source)

    n_steps = int(round((t_end - t0) / dt))
    t_array = t0 + dt * np.arange(n_steps + 1)
    omega_array = np.zeros(n_steps + 1)
    omega_array[0] = omega0

    omega = omega0
    for k in range(n_steps):
        omega = euler_1axis_rk4_step(omega, t_array[k], dt, torque_func, I3)
        omega_array[k + 1] = omega

    return t_array, omega_array


if __name__ == "__main__":
    print("== euler_dynamics.py: auto-teste ==")

    chk = check_z_is_principal_axis()
    print(f"Z e aproximadamente eixo principal (CAD completo)? {chk['z_aproximadamente_principal']} "
          f"(Lxz/Lzz={chk['Lxz/Lzz']*100:.3f}%, Lyz/Lzz={chk['Lyz/Lzz']*100:.3f}%, "
          f"limiar={chk['threshold']*100:.0f}%)")

    I3_cad_full = get_I3_kg_m2("cad_full")
    I3_total_workaround = get_I3_kg_m2("analytical_total")
    I3_cad_no_chassis = get_I3_kg_m2("cad_no_chassis")

    print(f"\nI3 (CAD completo, com chassi, 325.0 g)         = {I3_cad_full:.6e} kg*m^2  <- PADRAO")
    print(f"I3 (workaround antigo: caixa uniforme, 328.0 g) = {I3_total_workaround:.6e} kg*m^2")
    print(f"I3 (CAD, sem chassi, 263.5 g)                   = {I3_cad_no_chassis:.6e} kg*m^2")

    print(f"\nMigracao do workaround antigo para o CAD completo (o quanto o workaround errava):")
    print(f"  workaround vs. CAD completo: "
          f"{(I3_total_workaround - I3_cad_full) / I3_cad_full * 100:+.2f} % "
          f"-> NAO desprezivel (por isso a fonte padrao mudou)")

    print(f"\nEfeito de ignorar o chassi por completo (referencia, ja conhecido):")
    print(f"  CAD sem chassi vs. CAD completo: "
          f"{(I3_cad_no_chassis - I3_cad_full) / I3_cad_full * 100:+.2f} %")

    # Sanity check classico: torque nulo -> omega constante (conservacao)
    t_arr, w_arr = integrate_euler_1axis(
        omega0=0.05, t0=0.0, t_end=100.0, dt=0.1,
        torque_func=lambda t, w: 0.0, I3_source="cad_full",
    )
    print(f"\nTeste de conservacao (tau=0): omega(0)={w_arr[0]:.6f} rad/s, "
          f"omega({t_arr[-1]:.0f}s)={w_arr[-1]:.6f} rad/s "
          f"(deve ser identico, sem torque)")

    # Sanity check: torque constante -> omega(t) = omega0 + (tau/I3)*t (rampa linear)
    tau_const = 1.0e-6  # N*m, ordem de grandeza de torque residual/perturbacao
    t_arr2, w_arr2 = integrate_euler_1axis(
        omega0=0.0, t0=0.0, t_end=100.0, dt=0.1,
        torque_func=lambda t, w: tau_const, I3_source="cad_full",
    )
    omega_analitico_final = tau_const / I3_cad_full * t_arr2[-1]
    print(f"\nTeste de rampa (tau=const={tau_const:.1e} N*m): "
          f"omega numerico={w_arr2[-1]:.6f} rad/s, "
          f"omega analitico={omega_analitico_final:.6f} rad/s, "
          f"erro={abs(w_arr2[-1]-omega_analitico_final):.3e} rad/s")
