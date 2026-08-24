"""
params.py
=========
Configuracao central do pacote de simulacao EKF-HIL Sat + Digital Twin (A2 - Dinamica & HIL).

Este modulo concentra:
  1. Dados de massa REAIS medidos em balanca (campanha de pesagem, erro de escala +-0.25 g).
  2. Propriedades de massa extraidas do CAD (SolidWorks "Mass Properties"), referencia
     "Mate connector for reference frame".
  3. Constantes fisicas/orbitais e a posicao do laboratorio (Modo Laboratorio da Camada 0).
  4. Funcoes de conversao de unidade (g -> kg, mm -> m, g*mm^2 -> kg*m^2).

HISTORICO DE REVISAO DESTE ARQUIVO
-----------------------------------
- v1 (pre-projeto): massas estimadas/placeholder, geometria de caixa uniforme 98x98x104 mm.
- v2 (Ago/2026): substituicao das massas placeholder pelas massas REAIS medidas em
  balanca, e tensor de inercia do CAD sem chassi externo como primeira referencia.
- v3 (Ago/2026, esta revisao): adicao do tensor de inercia do CAD COMPLETO (com o
  chassi externo montado na posicao correta). Checagem cruzada: a diferenca de massa
  entre as duas exportacoes do CAD (325.0 - 263.5 = 61.5 g) bate EXATAMENTE com a
  massa do chassi externo medida em balanca (61.5 g) -- forte evidencia de
  consistencia interna do CAD. A partir desta revisao, o tensor CAD_FULL_* passa a
  ser a fonte primaria de massa/inercia para euler_dynamics.py e perturbations.py,
  substituindo o workaround de "caixa uniforme com massa total" usado na v2.

IMPORTANTE - REFERENCIAIS (documentar antes de fechar o Digital Twin, ver README secao
"Pendencias"): os tensores de inercia do CAD (tanto CAD_NO_CHASSIS_* quanto CAD_FULL_*)
foram extraidos com a saida do SolidWorks configurada no referencial "Mate connector
for reference frame" (um conector de acoplamento do CAD), e NAO no referencial
geometrico da caixa externa (canto inferior, 98x98x104 mm) usado historicamente por
este pacote (params.BOX_DIMENSIONS_M) para o calculo analitico e para o braco de
alavanca dos acelerometros (Capitulo 3 de Cordeiro & Waldmann, DM034/2012, replicado
no Capitulo 3 do artigo EKF-HIL Sat). A transformacao rigida entre os dois
referenciais (rotacao + translacao) ainda nao foi registrada pela equipe; ate que
isso seja feito, CAD_*_CENTER_OF_MASS_MM eh tratado como informativo. Note tambem que
os centros de massa das duas exportacoes NAO sao diretamente subtraiveis entre si
(cada configuracao do SolidWorks reporta a inercia em torno do PROPRIO centro de
massa, que muda de posicao entre as duas exportacoes) -- por isso este pacote usa o
CAD_FULL_INERTIA_TENSOR_G_MM2 diretamente como o tensor do corpo completo, em vez de
tentar reconstruir "tensor completo = tensor sem-chassi + tensor do chassi" por
subtracao/soma (o que exigiria um referencial comum, ainda pendente).
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# 1. CONSTANTES FISICAS E ORBITAIS (usadas por propagator.py e perturbations.py)
# ---------------------------------------------------------------------------

MU_EARTH_M3_S2 = 3.986004418e14        # parametro gravitacional padrao da Terra [m^3/s^2]
R_EARTH_M = 6378137.0                  # raio equatorial (WGS-84) [m]
J2 = 1.08262668e-3                     # coeficiente de achatamento J2 (adimensional)
OMEGA_EARTH_RAD_S = 7.2921150e-5       # velocidade de rotacao da Terra [rad/s]

# ---------------------------------------------------------------------------
# 2. LABORATORIO (Modo Laboratorio da Camada 0 - substitui a Gaiola de Helmholtz)
# ---------------------------------------------------------------------------
# TODO(A2): substituir por leitura GPS/planta baixa exata do laboratorio antes da
# campanha de estimacao de m (Fase 3). Placeholder: Brasilia-DF.
LAB_LATITUDE_DEG = -15.7801
LAB_LONGITUDE_DEG = -47.9292
LAB_ALTITUDE_M = 1000.0

# ---------------------------------------------------------------------------
# 3. CONVERSOES DE UNIDADE
# ---------------------------------------------------------------------------

def g_to_kg(mass_g: float) -> float:
    """Converte massa de gramas para quilogramas."""
    return mass_g * 1.0e-3


def mm_to_m(length_mm: float) -> float:
    """Converte comprimento de milimetros para metros."""
    return length_mm * 1.0e-3


def g_mm2_to_kg_m2(inertia_g_mm2: float) -> float:
    """Converte momento/produto de inercia de g*mm^2 para kg*m^2 (fator 1e-9)."""
    return inertia_g_mm2 * 1.0e-9


def mm2_to_m2(area_mm2: float) -> float:
    """Converte area de mm^2 para m^2."""
    return area_mm2 * 1.0e-6


def mm3_to_m3(volume_mm3: float) -> float:
    """Converte volume de mm^3 para m^3."""
    return volume_mm3 * 1.0e-9


# ---------------------------------------------------------------------------
# 4. GEOMETRIA EXTERNA (caixa que envolve o PionSat, usada no modelo analitico
#    de inercia "caixa uniforme" e no braco de alavanca dos acelerometros - Cap. 3)
# ---------------------------------------------------------------------------

BOX_DIMENSIONS_MM = np.array([98.0, 98.0, 104.0])   # (a, b, c) = (X, Y, Z)
BOX_DIMENSIONS_M = mm_to_m(BOX_DIMENSIONS_MM)
SCALE_ERROR_G = 0.25   # erro de escala (leitura) da balanca de laboratorio, +- g

# ---------------------------------------------------------------------------
# 5. MASSAS REAIS MEDIDAS EM BALANCA (campanha Ago/2026)
# ---------------------------------------------------------------------------
# Cada valor tem incerteza +- SCALE_ERROR_G (1 leitura = 1 sigma de escala, nao
# estatistico; nao ha repeticoes registradas ainda, portanto nao se calcula desvio
# padrao amostral aqui, apenas se propaga o erro de escala).
#
# NOTA sobre dupla contagem: "computador de bordo + fios + tampa do chassi" (76.0 g)
# JA INCLUI a "tampa do chassi com parafusos" (34.0 g) listada separadamente abaixo.
# Os dois valores sao mantidos lado a lado apenas para documentar como a pesagem foi
# feita (rastreabilidade); a soma "oficial" da massa total usa a decomposicao de dois
# pesos independentes (chassi externo + satelite sem chassi externo), que NAO tem
# esse problema de sobreposicao. Ver MEASURED_TOTAL_MASS_G.

MEASURED_MASSES_G: dict[str, float] = {
    "chassi_externo": 61.5,
    "satelite_sem_chassi_externo": 266.5,   # decomposicao independente (ver nota acima)
    "pilar_unitario": 1.5,
    "tampa_chassi_com_parafusos": 34.0,
    "placa_interface": 35.5,
    "placa_sensores": 34.0,
    "computador_de_bordo": 37.5,
    "computador_de_bordo_com_fios_e_tampa": 76.0,   # inclui tampa_chassi_com_parafusos
    "placa_potencia": 44.5,
    "tampa_inferior_chassi": 34.0,
}

N_PILARES = 28  # confirmado em memoria do projeto; ajustar se a contagem fisica mudar
MASSA_PILARES_TOTAL_G = MEASURED_MASSES_G["pilar_unitario"] * N_PILARES  # 42.0 g

# --- massa total "oficial" do satelite montado (fonte mais confiavel: 2 pesagens
#     independentes, sem sobreposicao de componentes) ---
MEASURED_TOTAL_MASS_G = (
    MEASURED_MASSES_G["chassi_externo"]
    + MEASURED_MASSES_G["satelite_sem_chassi_externo"]
)  # = 328.0 g

# incerteza de escala combinada (soma de 2 leituras independentes, quadratura)
MEASURED_TOTAL_MASS_SCALE_UNC_G = float(np.sqrt(2) * SCALE_ERROR_G)  # ~= 0.354 g

# --- massa do satelite SEM chassi externo, isolada (para comparar diretamente com
#     o CAD, cuja configuracao "Mate connector for reference frame" tambem exclui
#     o chassi externo - ver docstring do modulo) ---
MEASURED_MASS_NO_CHASSIS_G = MEASURED_MASSES_G["satelite_sem_chassi_externo"]  # 266.5 g
MEASURED_MASS_NO_CHASSIS_SCALE_UNC_G = SCALE_ERROR_G  # 0.25 g (1 pesagem)

MEASURED_TOTAL_MASS_KG = g_to_kg(MEASURED_TOTAL_MASS_G)
MEASURED_MASS_NO_CHASSIS_KG = g_to_kg(MEASURED_MASS_NO_CHASSIS_G)

# ---------------------------------------------------------------------------
# 6. PROPRIEDADES DE MASSA DO CAD (SolidWorks Mass Properties, Ago/2026).
#    Duas configuracoes foram exportadas pela equipe:
#      (a) CAD_NO_CHASSIS_*: satelite SEM o chassi externo (massa = 263.5 g),
#          referencial "Mate connector for reference frame".
#      (b) CAD_FULL_*: satelite COMPLETO, com o chassi externo montado na
#          posicao correta (massa = 325.0 g).
#    Checagem cruzada (auto-consistencia do CAD): 325.0 - 263.5 = 61.5 g,
#    EXATAMENTE igual a massa do chassi externo medida em balanca
#    (MEASURED_MASSES_G["chassi_externo"] = 61.5 g). Forte evidencia de que o
#    CAD (b) e a fonte de verdade recomendada a partir desta revisao para
#    massa/inercia do corpo COMPLETO, substituindo o workaround de "caixa
#    uniforme com massa total" usado nas revisoes anteriores deste pacote.
# ---------------------------------------------------------------------------

# --- (a) SEM chassi externo (mantido para validacao do modelo analitico e
#     rastreabilidade; NAO usar isoladamente como I do corpo completo) ---
CAD_NO_CHASSIS_MASS_G = 263.5
CAD_NO_CHASSIS_MASS_KG = g_to_kg(CAD_NO_CHASSIS_MASS_G)

CAD_NO_CHASSIS_VOLUME_MM3 = 206292.707
CAD_NO_CHASSIS_VOLUME_M3 = mm3_to_m3(CAD_NO_CHASSIS_VOLUME_MM3)

CAD_NO_CHASSIS_SURFACE_AREA_MM2 = 136463.48
CAD_NO_CHASSIS_SURFACE_AREA_M2 = mm2_to_m2(CAD_NO_CHASSIS_SURFACE_AREA_MM2)

CAD_NO_CHASSIS_CENTER_OF_MASS_MM = np.array([66.193, -70.621, 31.6])
CAD_NO_CHASSIS_CENTER_OF_MASS_M = mm_to_m(CAD_NO_CHASSIS_CENTER_OF_MASS_MM)

CAD_NO_CHASSIS_INERTIA_TENSOR_G_MM2 = np.array([
    [442821.555,    853.309,  -1344.076],
    [   853.309, 439977.985,    156.659],
    [ -1344.076,    156.659, 434916.001],
])
CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2 = g_mm2_to_kg_m2(CAD_NO_CHASSIS_INERTIA_TENSOR_G_MM2)

# aliases retrocompativeis (nomes usados nas revisoes anteriores do pacote)
CAD_MASS_G = CAD_NO_CHASSIS_MASS_G
CAD_MASS_KG = CAD_NO_CHASSIS_MASS_KG
CAD_VOLUME_MM3 = CAD_NO_CHASSIS_VOLUME_MM3
CAD_VOLUME_M3 = CAD_NO_CHASSIS_VOLUME_M3
CAD_SURFACE_AREA_MM2 = CAD_NO_CHASSIS_SURFACE_AREA_MM2
CAD_SURFACE_AREA_M2 = CAD_NO_CHASSIS_SURFACE_AREA_M2
CAD_CENTER_OF_MASS_MM = CAD_NO_CHASSIS_CENTER_OF_MASS_MM
CAD_CENTER_OF_MASS_M = CAD_NO_CHASSIS_CENTER_OF_MASS_M
CAD_INERTIA_TENSOR_G_MM2 = CAD_NO_CHASSIS_INERTIA_TENSOR_G_MM2
CAD_INERTIA_TENSOR_KG_M2 = CAD_NO_CHASSIS_INERTIA_TENSOR_KG_M2

# --- (b) COMPLETO, com chassi externo na posicao correta -- FONTE PRIMARIA
#     recomendada para euler_dynamics.py e perturbations.py a partir desta
#     revisao (ver checagem cruzada de massa acima). ---
CAD_FULL_MASS_G = 325.0
CAD_FULL_MASS_KG = g_to_kg(CAD_FULL_MASS_G)

CAD_FULL_VOLUME_MM3 = 267672.691
CAD_FULL_VOLUME_M3 = mm3_to_m3(CAD_FULL_VOLUME_MM3)

CAD_FULL_SURFACE_AREA_MM2 = 214525.237
CAD_FULL_SURFACE_AREA_M2 = mm2_to_m2(CAD_FULL_SURFACE_AREA_MM2)

# Centro de massa do satelite completo [mm]. Mesma ressalva de referencial da
# secao (a): nao comparar diretamente com o centro geometrico da caixa
# 98x98x104 mm sem registrar a transformacao entre referenciais.
CAD_FULL_CENTER_OF_MASS_MM = np.array([43.133, 48.551, 33.348])
CAD_FULL_CENTER_OF_MASS_M = mm_to_m(CAD_FULL_CENTER_OF_MASS_MM)

# Tensor de inercia do satelite COMPLETO em torno do proprio centro de massa
# [g*mm^2]. Esta e a melhor estimativa atual do corpo real que gira no mancal
# a ar (substitui o workaround de caixa uniforme das revisoes anteriores).
CAD_FULL_INERTIA_TENSOR_G_MM2 = np.array([
    [591100.673,    871.477,  -1357.053],
    [   871.477, 588217.989,    189.694],
    [ -1357.053,    189.694, 632946.933],
])
CAD_FULL_INERTIA_TENSOR_KG_M2 = g_mm2_to_kg_m2(CAD_FULL_INERTIA_TENSOR_G_MM2)

# ---------------------------------------------------------------------------
# 7. LIMIARES DE DESPREZIBILIDADE (documentados para reprodutibilidade da
#    analise "medido vs. CAD" feita em inertia.py). Escolha justificada no
#    corpo do artigo (secao de metodologia): o proprio projeto ja adota 1%
#    como criterio de aceitacao para o propagador orbital e para o modelo
#    IGRF-14 vs. pyIGRF (ver EKF-HIL_Sat_Digital_Twin_v2, Secao 6, Fase 1-2).
#    Aplicamos o mesmo criterio de ordem de grandeza (poucos %) para massa e
#    inercia, com margem adicional pois I entra linearmente no torque de
#    perturbacao e na equacao de Euler (erro de 1as ordem se propaga ~1:1).
# ---------------------------------------------------------------------------

NEGLIGIBLE_MASS_REL_THRESHOLD = 0.02       # 2% - referencia para massa total
NEGLIGIBLE_INERTIA_REL_THRESHOLD = 0.05    # 5% - referencia para termos de inercia
# Numero de sigmas de escala acima do qual uma diferenca NAO pode ser atribuida
# a ruido de leitura da balanca (ou seja, eh um efeito fisico real, nao ruido):
SCALE_NOISE_SIGMA_FACTOR = 3.0


if __name__ == "__main__":
    print("== params.py: resumo rapido ==")
    print(f"Massa total medida (chassi + sem-chassi): {MEASURED_TOTAL_MASS_G:.2f} g "
          f"+- {MEASURED_TOTAL_MASS_SCALE_UNC_G:.3f} g (escala)")
    print(f"Massa medida sem chassi externo:          {MEASURED_MASS_NO_CHASSIS_G:.2f} g "
          f"+- {MEASURED_MASS_NO_CHASSIS_SCALE_UNC_G:.3f} g (escala)")
    print(f"Massa CAD sem chassi:                     {CAD_NO_CHASSIS_MASS_G:.2f} g")
    print(f"Massa CAD completo (com chassi):          {CAD_FULL_MASS_G:.2f} g")
    print(f"Massa do chassi implicita no CAD (completo - sem-chassi): "
          f"{CAD_FULL_MASS_G - CAD_NO_CHASSIS_MASS_G:.2f} g "
          f"(medida em balanca: {MEASURED_MASSES_G['chassi_externo']:.2f} g)")
    print(f"Massa pilares (N={N_PILARES}):             {MASSA_PILARES_TOTAL_G:.2f} g")
    print(f"Tensor de inercia CAD completo [kg*m^2]:\n{CAD_FULL_INERTIA_TENSOR_KG_M2}")
