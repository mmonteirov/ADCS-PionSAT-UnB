"""
inertia.py
==========
Massa, centro de massa e tensor de inercia do PionSat.

TRES fontes de dados sao mantidas lado a lado, de proposito, para permitir a
analise "medido vs. CAD" pedida para o artigo, e para documentar a evolucao
da precisao do pacote ao longo do projeto:

  (A) MODELO ANALITICO - caixa retangular de densidade uniforme, com massa
      real medida e as dimensoes externas nominais (params.BOX_DIMENSIONS_MM).
      Era o UNICO modelo disponivel antes do CAD ser exportado; hoje serve
      como validacao/baseline, nao mais como fonte primaria.

  (B) CAD SEM CHASSI EXTERNO (params.CAD_NO_CHASSIS_*) - export do SolidWorks
      da pilha interna apenas (massa = 263.5 g). Util para validar (A) contra
      uma geometria multi-corpo real (nao apenas uma caixa homogenea).

  (C) CAD COMPLETO, com chassi externo na posicao correta (params.CAD_FULL_*)
      - massa = 325.0 g. Esta e a FONTE PRIMARIA recomendada para
      euler_dynamics.py e perturbations.py a partir desta revisao, pois
      representa o corpo fisico completo que de fato gira no mancal a ar.
      Checagem cruzada de auto-consistencia do CAD: 325.0 - 263.5 = 61.5 g,
      EXATAMENTE igual a massa do chassi externo medida em balanca -- ver
      `cross_check_cad_chassis_mass()`.

Este modulo NAO tenta reconstruir a posicao 3D de cada componente (placas,
pilares) dentro da caixa por soma/subtracao manual de tensores, pois os
centros de massa das duas exportacoes do CAD (B) e (C) NAO estao no mesmo
referencial (cada configuracao do SolidWorks reporta a inercia em torno do
PROPRIO centro de massa -- ver params.py). Combinacoes desse tipo exigiriam a
transformacao de referencial ainda pendente (ver README). Em vez disso, este
modulo usa o tensor (C) diretamente como o tensor do corpo completo.
"""

from __future__ import annotations

import numpy as np

import params


# ---------------------------------------------------------------------------
# (A) MODELO ANALITICO: caixa retangular uniforme
# ---------------------------------------------------------------------------

def analytical_inertia_uniform_box(
    mass_kg: float = params.MEASURED_TOTAL_MASS_KG,
    dims_m: np.ndarray = params.BOX_DIMENSIONS_M,
) -> np.ndarray:
    """
    Tensor de inercia (3x3, kg*m^2) de uma caixa retangular homogenea de massa
    `mass_kg` e dimensoes `dims_m` = (a, b, c) ao longo de (X, Y, Z), calculado
    em torno do proprio centro de massa. Produtos de inercia nulos por
    construcao (caixa homogenea, alinhada aos eixos).

        Ixx = m/12 * (b^2 + c^2)   Iyy = m/12 * (a^2 + c^2)   Izz = m/12 * (a^2 + b^2)
    """
    a, b, c = dims_m
    ixx = mass_kg / 12.0 * (b**2 + c**2)
    iyy = mass_kg / 12.0 * (a**2 + c**2)
    izz = mass_kg / 12.0 * (a**2 + b**2)
    return np.diag([ixx, iyy, izz])


def analytical_center_of_mass_m(dims_m: np.ndarray = params.BOX_DIMENSIONS_M) -> np.ndarray:
    """Centro geometrico da caixa uniforme, medido a partir do canto inferior (0,0,0)."""
    return dims_m / 2.0


# ---------------------------------------------------------------------------
# (B)/(C) TENSORES DO CAD (repassam params, mantidos aqui por conveniencia)
# ---------------------------------------------------------------------------

def cad_no_chassis_inertia_tensor_kg_m2() -> np.ndarray:
    """Tensor de inercia do CAD SEM chassi externo (pilha interna), kg*m^2."""
    return params.CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2.copy()


def cad_full_inertia_tensor_kg_m2() -> np.ndarray:
    """Tensor de inercia do CAD COMPLETO (com chassi externo), kg*m^2. Fonte primaria."""
    return params.CAD_FULL_INERTIA_TENSOR_KG_M2.copy()


# ---------------------------------------------------------------------------
# CHECAGEM DE AUTO-CONSISTENCIA DO CAD
# ---------------------------------------------------------------------------

def cross_check_cad_chassis_mass() -> dict:
    """
    Verifica se a diferenca de massa entre as duas exportacoes do CAD
    (completo - sem chassi) bate com a massa do chassi externo medida em
    balanca. Uma boa concordancia aqui e evidencia forte de que o CAD esta
    internamente consistente (mesma densidade de material atribuida em ambas
    as exportacoes, sem erro de configuracao).
    """
    cad_delta_g = params.CAD_FULL_MASS_G - params.CAD_NO_CHASSIS_MASS_G
    measured_chassis_g = params.MEASURED_MASSES_G["chassi_externo"]
    diff_g = cad_delta_g - measured_chassis_g

    return {
        "massa_chassi_implicita_no_cad_g": cad_delta_g,
        "massa_chassi_medida_g": measured_chassis_g,
        "diferenca_g": diff_g,
        "concordancia_perfeita": bool(abs(diff_g) < 1e-6),
    }


# ---------------------------------------------------------------------------
# COMPARACAO 1: massa medida (balanca) vs. massa do CAD -- config. COMPLETA
# (fonte primaria de comparacao a partir desta revisao)
# ---------------------------------------------------------------------------

def compare_mass_measured_vs_cad_full() -> dict:
    """Compara a massa medida TOTAL (chassi incluso) contra a massa do CAD completo."""
    m_meas = params.MEASURED_TOTAL_MASS_G
    m_cad = params.CAD_FULL_MASS_G
    delta_g = m_cad - m_meas
    rel = delta_g / m_meas
    n_sigma = abs(delta_g) / params.MEASURED_TOTAL_MASS_SCALE_UNC_G
    negligible = abs(rel) < params.NEGLIGIBLE_MASS_REL_THRESHOLD

    return {
        "massa_medida_g": m_meas,
        "massa_cad_g": m_cad,
        "delta_g": delta_g,
        "delta_relativo_pct": rel * 100.0,
        "sigmas_de_escala_explicados": n_sigma,
        "atribuivel_a_ruido_de_escala": n_sigma < params.SCALE_NOISE_SIGMA_FACTOR,
        "desprezivel_para_o_threshold_do_projeto": negligible,
    }


def compare_mass_measured_vs_cad_no_chassis() -> dict:
    """Mesma comparacao, mas na config. sem chassi externo (mantido para rastreabilidade)."""
    m_meas = params.MEASURED_MASS_NO_CHASSIS_G
    m_cad = params.CAD_NO_CHASSIS_MASS_G
    delta_g = m_cad - m_meas
    rel = delta_g / m_meas
    n_sigma = abs(delta_g) / params.MEASURED_MASS_NO_CHASSIS_SCALE_UNC_G
    negligible = abs(rel) < params.NEGLIGIBLE_MASS_REL_THRESHOLD

    return {
        "massa_medida_g": m_meas,
        "massa_cad_g": m_cad,
        "delta_g": delta_g,
        "delta_relativo_pct": rel * 100.0,
        "sigmas_de_escala_explicados": n_sigma,
        "atribuivel_a_ruido_de_escala": n_sigma < params.SCALE_NOISE_SIGMA_FACTOR,
        "desprezivel_para_o_threshold_do_projeto": negligible,
    }


# ---------------------------------------------------------------------------
# COMPARACAO 2: caixa uniforme com massa real (A) vs. tensor do CAD, na MESMA
# configuracao (sem chassi) -- valida o modelo (A) como proxy de geometria.
# ---------------------------------------------------------------------------

def compare_analytical_vs_cad_no_chassis_inertia() -> dict:
    """
    Compara, componente a componente, o tensor analitico (A) recalculado com
    a massa medida SEM chassi contra o tensor do CAD (B), tambem sem chassi.
    Mede o quanto a hipotese de "caixa homogenea" se afasta da distribuicao
    de massa real DENTRO da pilha interna (sem o efeito do chassi, tratado
    separadamente abaixo).
    """
    I_cad = cad_no_chassis_inertia_tensor_kg_m2()
    I_ana = analytical_inertia_uniform_box(
        mass_kg=params.MEASURED_MASS_NO_CHASSIS_KG, dims_m=params.BOX_DIMENSIONS_M
    )

    diag_cad = np.diag(I_cad)
    diag_ana = np.diag(I_ana)
    rel_diag = (diag_cad - diag_ana) / diag_ana

    frob_rel = np.linalg.norm(I_cad - I_ana, ord="fro") / np.linalg.norm(I_cad, ord="fro")

    off_diag_ratio = {
        "Lxy/Lxx": abs(I_cad[0, 1]) / diag_cad[0],
        "Lxz/Lzz": abs(I_cad[0, 2]) / diag_cad[2],
        "Lyz/Lzz": abs(I_cad[1, 2]) / diag_cad[2],
    }

    negligible_diag = np.all(np.abs(rel_diag) < params.NEGLIGIBLE_INERTIA_REL_THRESHOLD)

    return {
        "I_analitico_kg_m2_diag": diag_ana,
        "I_cad_kg_m2_diag": diag_cad,
        "delta_relativo_diag_pct": rel_diag * 100.0,
        "delta_relativo_frobenius_pct": frob_rel * 100.0,
        "razao_fora_diagonal_sobre_diagonal_pct": {k: v * 100.0 for k, v in off_diag_ratio.items()},
        "desprezivel_para_o_threshold_do_projeto": bool(negligible_diag),
    }


# ---------------------------------------------------------------------------
# COMPARACAO 3: o workaround anterior (caixa uniforme, massa TOTAL) vs. o
# novo tensor do CAD COMPLETO -- quantifica o quanto o workaround usado nas
# revisoes anteriores deste pacote errava, agora que temos o dado real.
# ---------------------------------------------------------------------------

def compare_old_workaround_vs_cad_full() -> dict:
    """
    Compara o modelo (A) com a massa TOTAL real (workaround usado ate a
    revisao anterior, quando so tinhamos o CAD sem chassi) contra o tensor
    (C) do CAD completo, agora disponivel. Isso mede o erro que o workaround
    estava introduzindo -- relevante para o artigo justificar a migracao.
    """
    I_cad_full = cad_full_inertia_tensor_kg_m2()
    I_box_total = analytical_inertia_uniform_box(
        mass_kg=params.MEASURED_TOTAL_MASS_KG, dims_m=params.BOX_DIMENSIONS_M
    )

    diag_cad = np.diag(I_cad_full)
    diag_box = np.diag(I_box_total)
    rel_diag = (diag_cad - diag_box) / diag_cad

    frob_rel = np.linalg.norm(I_cad_full - I_box_total, ord="fro") / np.linalg.norm(I_cad_full, ord="fro")

    negligible_diag = np.all(np.abs(rel_diag) < params.NEGLIGIBLE_INERTIA_REL_THRESHOLD)

    return {
        "I_workaround_caixa_uniforme_kg_m2_diag": diag_box,
        "I_cad_completo_kg_m2_diag": diag_cad,
        "delta_relativo_diag_pct": rel_diag * 100.0,
        "delta_relativo_frobenius_pct": frob_rel * 100.0,
        "desprezivel_para_o_threshold_do_projeto": bool(negligible_diag),
    }


# ---------------------------------------------------------------------------
# COMPARACAO 4 (descritiva): magnitude da contribuicao do chassi externo,
# usando as DUAS exportacoes do CAD (nao rigoroso -- referenciais distintos,
# ver docstring do modulo -- mas informativo em magnitude/ordem de grandeza)
# ---------------------------------------------------------------------------

def chassis_contribution_magnitude() -> dict:
    """
    Compara, apenas em MAGNITUDE (nao decomposicao rigorosa via eixos
    paralelos, pois os dois tensores do CAD estao em referenciais de CM
    distintos -- ver docstring do modulo), o quanto os momentos de inercia
    diagonais aumentam entre a config. sem chassi e a config. completa.
    """
    diag_no_chassis = np.diag(params.CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2)
    diag_full = np.diag(params.CAD_FULL_INERTIA_TENSOR_KG_M2)
    increase_pct = (diag_full - diag_no_chassis) / diag_no_chassis * 100.0

    return {
        "Ixx_aumento_pct": increase_pct[0],
        "Iyy_aumento_pct": increase_pct[1],
        "Izz_aumento_pct": increase_pct[2],
        "fracao_massa_chassi_pct": (
            params.MEASURED_MASSES_G["chassi_externo"] / params.MEASURED_TOTAL_MASS_G * 100.0
        ),
    }


def negligibility_report(verbose: bool = True) -> dict:
    """
    Monta o relatorio consolidado de desprezibilidade, com veredito por
    quantidade (massa, inercia) e por modulo downstream.
    """
    mass_full = compare_mass_measured_vs_cad_full()
    mass_no_chassis = compare_mass_measured_vs_cad_no_chassis()
    inertia_no_chassis = compare_analytical_vs_cad_no_chassis_inertia()
    workaround_vs_full = compare_old_workaround_vs_cad_full()
    chassis_mag = chassis_contribution_magnitude()
    cross_check = cross_check_cad_chassis_mass()

    report = {
        "massa_config_completa": mass_full,
        "massa_config_sem_chassis": mass_no_chassis,
        "inercia_mesma_config_sem_chassis": inertia_no_chassis,
        "workaround_antigo_vs_cad_completo": workaround_vs_full,
        "contribuicao_chassi_magnitude": chassis_mag,
        "checagem_cruzada_cad": cross_check,
        "veredito_por_modulo": {
            "propagator.py": (
                "NAO AFETADO. Propagacao de 2 corpos + J2 usa apenas posicao/velocidade; "
                "a massa do satelite se cancela (m_sat << M_terra). Nenhuma alteracao de "
                "massa/inercia impacta este modulo, com ou sem chassi."
            ),
            "igrf_model.py": (
                "NAO AFETADO. O campo B(r,t) do IGRF-14 depende so de posicao/tempo, "
                "nao de propriedades do satelite (com ou sem chassi)."
            ),
            "euler_dynamics.py": (
                f"AFETADO. Massa (config. completa): CAD={mass_full['massa_cad_g']:.1f} g vs. "
                f"medida={mass_full['massa_medida_g']:.1f} g "
                f"({mass_full['delta_relativo_pct']:+.2f}%, DESPREZIVEL). "
                f"O tensor do CAD COMPLETO (com chassi) e agora a fonte PRIMARIA de I3 "
                f"(substitui o workaround de caixa uniforme, que subestimava Izz em "
                f"{workaround_vs_full['delta_relativo_diag_pct'][2]:+.1f}% -- NAO desprezivel)."
            ),
            "perturbations.py": (
                "AFETADO pelo mesmo motivo de euler_dynamics.py. O tensor completo do CAD "
                "(com produtos de inercia) e a fonte primaria do torque de gradiente de "
                "gravidade. O torque residual m x B nao depende de massa/inercia."
            ),
        },
    }

    if verbose:
        _print_report(report)

    return report


def _print_report(report: dict) -> None:
    mf = report["massa_config_completa"]
    mn = report["massa_config_sem_chassis"]
    i = report["inercia_mesma_config_sem_chassis"]
    w = report["workaround_antigo_vs_cad_completo"]
    cm = report["contribuicao_chassi_magnitude"]
    cc = report["checagem_cruzada_cad"]

    print("=" * 78)
    print("RELATORIO DE DESPREZIBILIDADE - MASSA/INERCIA MEDIDA vs. CAD")
    print("=" * 78)

    print("\n--- CHECAGEM DE AUTO-CONSISTENCIA DO CAD ---")
    print(f"  Massa do chassi implicita no CAD (completo - sem chassi): "
          f"{cc['massa_chassi_implicita_no_cad_g']:.2f} g")
    print(f"  Massa do chassi medida em balanca:                        "
          f"{cc['massa_chassi_medida_g']:.2f} g")
    print(f"  Diferenca: {cc['diferenca_g']:.4f} g "
          f"({'CONCORDANCIA PERFEITA' if cc['concordancia_perfeita'] else 'ha diferenca'})")

    print("\n--- MASSA (configuracao COMPLETA, com chassi) [fonte primaria] ---")
    print(f"  Medida em balanca : {mf['massa_medida_g']:.2f} g "
          f"(+- {params.MEASURED_TOTAL_MASS_SCALE_UNC_G:.3f} g de escala)")
    print(f"  CAD completo      : {mf['massa_cad_g']:.2f} g")
    print(f"  Delta             : {mf['delta_g']:+.2f} g  ({mf['delta_relativo_pct']:+.2f} %)")
    print(f"  Sigmas de escala explicados: {mf['sigmas_de_escala_explicados']:.1f} "
          f"({'ruido de escala' if mf['atribuivel_a_ruido_de_escala'] else 'NAO eh so ruido de escala'})")
    print(f"  Desprezivel (< {params.NEGLIGIBLE_MASS_REL_THRESHOLD*100:.0f}%)? "
          f"{'SIM' if mf['desprezivel_para_o_threshold_do_projeto'] else 'NAO'}")

    print("\n--- MASSA (configuracao sem chassi, rastreabilidade) ---")
    print(f"  Medida={mn['massa_medida_g']:.2f} g | CAD={mn['massa_cad_g']:.2f} g | "
          f"delta={mn['delta_relativo_pct']:+.2f} % | "
          f"{'SIM' if mn['desprezivel_para_o_threshold_do_projeto'] else 'NAO'} desprezivel")

    print("\n--- INERCIA, MESMA CONFIG. (caixa uniforme sem chassi vs. CAD sem chassi) ---")
    labels = ["Ixx", "Iyy", "Izz"]
    for lbl, ana, cad, drel in zip(
        labels, i["I_analitico_kg_m2_diag"], i["I_cad_kg_m2_diag"], i["delta_relativo_diag_pct"]
    ):
        print(f"  {lbl}: analitico={ana:.6e} | CAD={cad:.6e} | delta={drel:+.2f} %")
    print(f"  Frobenius: {i['delta_relativo_frobenius_pct']:.2f} % -- "
          f"{'SIM' if i['desprezivel_para_o_threshold_do_projeto'] else 'NAO'} desprezivel "
          f"(valida a caixa uniforme como proxy da pilha interna)")
    print("  Razao fora-diagonal/diagonal do CAD (Z ~ eixo principal?):")
    for k, v in i["razao_fora_diagonal_sobre_diagonal_pct"].items():
        print(f"    {k} = {v:.3f} %")

    print("\n--- WORKAROUND ANTIGO (caixa uniforme, massa TOTAL) vs. CAD COMPLETO (novo) ---")
    for lbl, box, cad, drel in zip(
        labels, w["I_workaround_caixa_uniforme_kg_m2_diag"],
        w["I_cad_completo_kg_m2_diag"], w["delta_relativo_diag_pct"]
    ):
        print(f"  {lbl}: workaround={box:.6e} | CAD completo={cad:.6e} | delta={drel:+.2f} %")
    print(f"  Frobenius: {w['delta_relativo_frobenius_pct']:.2f} % -- "
          f"{'SIM' if w['desprezivel_para_o_threshold_do_projeto'] else 'NAO -> workaround NAO era bom o suficiente'} "
          f"desprezivel")

    print("\n--- Contribuicao do chassi (magnitude, CAD sem-chassi vs. CAD completo) ---")
    print(f"  Fracao de massa do chassi: {cm['fracao_massa_chassi_pct']:.1f} %")
    print(f"  Aumento de Ixx/Iyy/Izz ao incluir o chassi: "
          f"{cm['Ixx_aumento_pct']:+.1f}% / {cm['Iyy_aumento_pct']:+.1f}% / {cm['Izz_aumento_pct']:+.1f}%")

    print("\n--- VEREDITO POR MODULO DOWNSTREAM ---")
    for mod, txt in report["veredito_por_modulo"].items():
        print(f"\n  [{mod}]")
        print(f"  {txt}")
    print("\n" + "=" * 78)


if __name__ == "__main__":
    negligibility_report(verbose=True)
