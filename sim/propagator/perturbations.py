"""
perturbations.py
=================
Torques de perturbacao teoricos atuantes sobre o PionSat: gradiente de
gravidade (orbita) e dipolo magnetico residual (bancada e orbita), alem de
estimativas de ordem de grandeza para pressao de radiacao solar e arrasto
(Nivel 2/3 da Secao 7.3 da proposta -- fora do escopo minimo do artigo, aqui
apenas para a tabela comparativa de ordens de grandeza).

ATUALIZACAO DESTA REVISAO (Ago/2026)
-------------------------------------
- A fonte de inercia PADRAO passa a ser o tensor COMPLETO do CAD (com chassi
  externo montado na posicao correta, params.CAD_FULL_INERTIA_TENSOR_KG_M2),
  substituindo o workaround de "caixa uniforme com massa total" usado na
  revisao anterior. Justificativa quantitativa: o workaround antigo
  subestimava Izz em ~17% frente ao CAD completo (ver
  inertia.py::compare_old_workaround_vs_cad_full()) -- NAO desprezivel.
- O torque de gradiente de gravidade usa o tensor completo 3x3 (com produtos
  de inercia reais do CAD completo), capturando o acoplamento entre eixos.
- O torque residual m x B (dipolo magnetico) NAO depende de massa/inercia e
  portanto e IDENTICO ao usado antes desta atualizacao e da anterior -- e o
  UNICO calculo deste modulo que independe por completo do CAD do chassi.
"""

from __future__ import annotations

import numpy as np

import params
import inertia


# ---------------------------------------------------------------------------
# Selecao do tensor de inercia completo (3x3) a usar nos torques
# ---------------------------------------------------------------------------

def get_inertia_tensor_kg_m2(source: str = "cad_full") -> np.ndarray:
    """
    Retorna o tensor de inercia completo (3x3, kg*m^2) a ser usado nos
    calculos de torque de perturbacao.

      - "cad_full" (PADRAO): tensor completo do CAD, satelite COMPLETO com
        chassi externo (325.0 g). Fonte recomendada -- ver docstring do modulo.
      - "analytical_total": caixa uniforme, massa TOTAL real (328.0 g).
        Workaround da revisao anterior; mantido para comparacao/regressao.
      - "cad_no_chassis": tensor completo do CAD SEM chassi externo (263.5 g).
        Representa apenas a pilha interna -- nao usar isoladamente.
    """
    if source == "cad_full":
        return params.CAD_FULL_INERTIA_TENSOR_KG_M2.copy()
    elif source == "analytical_total":
        return inertia.analytical_inertia_uniform_box(
            mass_kg=params.MEASURED_TOTAL_MASS_KG, dims_m=params.BOX_DIMENSIONS_M
        )
    elif source == "cad_no_chassis":
        return params.CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2.copy()
    else:
        raise ValueError(f"source invalido: {source!r}")


# ---------------------------------------------------------------------------
# Torque de gradiente de gravidade
# ---------------------------------------------------------------------------

def gravity_gradient_torque(
    r_body_unit: np.ndarray,
    r_orbit_m: float,
    I_tensor_kg_m2: np.ndarray | None = None,
    mu_m3_s2: float = params.MU_EARTH_M3_S2,
) -> np.ndarray:
    """
    Torque de gradiente de gravidade [N*m], formula geral com tensor completo:

        tau_gg = (3*mu / r^3) * (u x (I @ u))

    onde u = r_body_unit e o vetor unitario nadir (direcao Terra->satelite,
    ou satelite->Terra conforme convencao) expresso no referencial do corpo,
    e r_orbit_m e a distancia do satelite ao centro da Terra [m].

    Parametros
    ----------
    r_body_unit : array(3,)
        Vetor unitario nadir no referencial do corpo (adimensional).
    r_orbit_m : float
        Distancia orbital ao centro da Terra [m].
    I_tensor_kg_m2 : array(3,3), opcional
        Tensor de inercia completo. Se None, usa get_inertia_tensor_kg_m2()
        com a fonte padrao (caixa uniforme, massa total real).
    mu_m3_s2 : float
        Parametro gravitacional padrao da Terra [m^3/s^2].

    Retorna
    -------
    array(3,)
        Vetor de torque de gradiente de gravidade [N*m] no referencial do corpo.
    """
    if I_tensor_kg_m2 is None:
        I_tensor_kg_m2 = get_inertia_tensor_kg_m2("cad_full")

    u = np.asarray(r_body_unit, dtype=float)
    u = u / np.linalg.norm(u)

    factor = 3.0 * mu_m3_s2 / r_orbit_m**3
    return factor * np.cross(u, I_tensor_kg_m2 @ u)


def gravity_gradient_torque_1axis_simplified(
    theta_rad: float,
    r_orbit_m: float,
    I_axis_kg_m2: float,
    I_other_kg_m2: float,
    mu_m3_s2: float = params.MU_EARTH_M3_S2,
) -> float:
    """
    Forma simplificada 1-eixo (compativel com euler_dynamics.py), coerente com
    a formula usada em DM034/2012 e nos cronogramas do projeto:

        tau_gg ~= (3*mu / (2*r^3)) * (I_other - I_axis) * sin(2*theta)

    Util para a integracao 1-eixo direta sem precisar do vetor nadir completo.
    theta_rad e o angulo entre o eixo de controle e a direcao nadir.
    """
    return (3.0 * mu_m3_s2 / (2.0 * r_orbit_m**3)) * (I_other_kg_m2 - I_axis_kg_m2) * np.sin(2.0 * theta_rad)


# ---------------------------------------------------------------------------
# Torque de dipolo magnetico residual (NAO afetado por massa/inercia)
# ---------------------------------------------------------------------------

def residual_dipole_torque(m_dipole_A_m2: np.ndarray, B_tesla: np.ndarray) -> np.ndarray:
    """
    Torque residual de dipolo magnetico [N*m]: tau = m x B.

    m_dipole_A_m2 : array(3,) - dipolo magnetico residual do satelite [A*m^2]
    B_tesla       : array(3,) - campo magnetico local no referencial do corpo [T]

    Este torque NAO depende de massa ou inercia do satelite -- nao afetado
    pela atualizacao de dados do CAD desta revisao.
    """
    return np.cross(np.asarray(m_dipole_A_m2, dtype=float), np.asarray(B_tesla, dtype=float))


# ---------------------------------------------------------------------------
# Ordens de grandeza para a tabela comparativa (Semana P3 do cronograma A2)
# ---------------------------------------------------------------------------

def order_of_magnitude_table(
    r_orbit_m: float = params.R_EARTH_M + 500.0e3,
    B_local_T: float = 30.0e-6,
    m_dipole_A_m2: float = 0.02,
    I_source: str = "cad_full",
) -> dict:
    """
    Recalcula a tabela de ordens de grandeza de torques de perturbacao
    (Semana P3 do cronograma A2) com o tensor de inercia atualizado.
    """
    I_tensor = get_inertia_tensor_kg_m2(I_source)
    Iz = I_tensor[2, 2]
    Ix = I_tensor[0, 0]

    tau_gg_max = abs(gravity_gradient_torque_1axis_simplified(
        theta_rad=np.pi / 4, r_orbit_m=r_orbit_m, I_axis_kg_m2=Iz, I_other_kg_m2=Ix,
    ))
    tau_mag_max = np.linalg.norm(
        residual_dipole_torque(np.array([m_dipole_A_m2, 0.0, 0.0]), np.array([0.0, B_local_T, 0.0]))
    )

    return {
        "fonte_de_inercia": I_source,
        "Izz_kg_m2": Iz,
        "tau_gradiente_gravidade_N_m": tau_gg_max,
        "tau_dipolo_residual_N_m": tau_mag_max,
        "razao_mag_sobre_gg": tau_mag_max / tau_gg_max if tau_gg_max > 0 else float("inf"),
    }


if __name__ == "__main__":
    print("== perturbations.py: auto-teste ==")

    I_full = get_inertia_tensor_kg_m2("cad_full")
    I_cad_no_chassis = get_inertia_tensor_kg_m2("cad_no_chassis")
    print(f"\nTensor usado por padrao (CAD completo, com chassi, 325.0 g):\n{I_full}")
    print(f"\nTensor do CAD (pilha interna, sem chassi, 263.5 g), disponivel via "
          f"source='cad_no_chassis':\n{I_cad_no_chassis}")

    print("\n--- Torque de gradiente de gravidade (LEO 500 km, exemplo) ---")
    r_orbit = params.R_EARTH_M + 500.0e3
    u_nadir = np.array([0.0, np.sin(np.pi / 4), np.cos(np.pi / 4)])
    tau_gg_full = gravity_gradient_torque(u_nadir, r_orbit, I_tensor_kg_m2=I_full)
    print(f"tau_gg (formula geral, tensor completo) = {tau_gg_full} N*m")

    tau_gg_1axis = gravity_gradient_torque_1axis_simplified(
        theta_rad=np.pi / 4, r_orbit_m=r_orbit,
        I_axis_kg_m2=I_full[2, 2], I_other_kg_m2=I_full[0, 0],
    )
    print(f"tau_gg (formula 1-eixo simplificada)    = {tau_gg_1axis:.3e} N*m")

    print("\n--- Torque de dipolo residual (exemplo, m=0.02 A*m^2, B=30 uT) ---")
    tau_mag = residual_dipole_torque(np.array([0.02, 0.0, 0.0]), np.array([0.0, 30e-6, 0.0]))
    print(f"tau_mag = {tau_mag} N*m  (nao depende de massa/inercia -> UNICO calculo deste "
          f"modulo totalmente independente do CAD do chassi)")

    print("\n--- Tabela de ordens de grandeza ---")
    tbl_full = order_of_magnitude_table(I_source="cad_full")
    tbl_cad_no_chassis = order_of_magnitude_table(I_source="cad_no_chassis")
    for lbl, tbl in [("cad_full (padrao)", tbl_full), ("cad_no_chassis", tbl_cad_no_chassis)]:
        print(f"\n  fonte = {lbl}")
        for k, v in tbl.items():
            if isinstance(v, float):
                print(f"    {k}: {v:.4e}")
            else:
                print(f"    {k}: {v}")
