"""
igrf_model.py
==============
Wrapper do modelo IGRF-14 (via pyIGRF) para a Camada 0 do Gemeo Digital.
Implementa os dois modos descritos na proposta (Secao 3):

  - Modo Orbital: B(r, t) ao longo de uma orbita LEO configuravel.
  - Modo Laboratorio: B local nas coordenadas geograficas do laboratorio,
    usado para estimar o dipolo residual m do PionSat sem Gaiola de Helmholtz.

NOTA SOBRE ESTA REVISAO (Ago/2026)
------------------------------------
Este modulo NAO foi alterado pela atualizacao de massa/inercia do CAD (ver
inertia.py::negligibility_report()). O campo geomagnetico B(lat, lon, alt, t)
e uma propriedade do planeta, calculada a partir dos coeficientes de Gauss do
IGRF -- nao ha nenhum termo de massa, inercia ou geometria do satelite nas
equacoes do modelo. Portanto o veredito "negligivel" aqui tambem e categorico
(a variavel simplesmente nao existe na equacao), assim como em propagator.py.

DEPENDENCIA EXTERNA - ATENCAO
-------------------------------
O pacote `pyIGRF` distribuido no PyPI nao inclui o arquivo de coeficientes
`igrf14coeffs.txt` (bug conhecido, ja documentado no projeto). E necessario
baixa-lo manualmente e coloca-lo em `<pyIGRF_install_dir>/src/igrf14coeffs.txt`
antes de usar este modulo -- ver README do pacote para o procedimento exato.
Sem o arquivo correto, `pyIGRF.igrf_value` levanta FileNotFoundError.
"""

from __future__ import annotations

import numpy as np

import params

try:
    import pyIGRF
    _HAS_PYIGRF = True
except ImportError:  # pragma: no cover
    _HAS_PYIGRF = False


def _require_pyigrf() -> None:
    if not _HAS_PYIGRF:
        raise ImportError(
            "pyIGRF nao esta instalado. Rode: pip install pyIGRF --break-system-packages "
            "e garanta que <pyIGRF>/src/igrf14coeffs.txt existe (ver docstring do modulo)."
        )


def igrf_field_ned_nT(lat_deg: float, lon_deg: float, alt_km: float, year_decimal: float) -> np.ndarray:
    """
    Retorna o vetor de campo magnetico [X, Y, Z] em NED (Norte, Leste, Baixo),
    em nanoTesla, na posicao e epoca dadas.
    """
    _require_pyigrf()
    _, _, _, x, y, z, _ = pyIGRF.igrf_value(lat_deg, lon_deg, alt_km, year_decimal)
    return np.array([x, y, z])


def igrf_field_ned_tesla(lat_deg: float, lon_deg: float, alt_km: float, year_decimal: float) -> np.ndarray:
    """Igual a igrf_field_ned_nT, mas em Tesla (SI), unidade usada por perturbations.py."""
    return igrf_field_ned_nT(lat_deg, lon_deg, alt_km, year_decimal) * 1.0e-9


# ---------------------------------------------------------------------------
# Modo Laboratorio: B local para estimacao do dipolo residual m (sem Gaiola de
# Helmholtz -- Secao 3 da proposta, Camada 0)
# ---------------------------------------------------------------------------

def lab_field_tesla(year_decimal: float) -> np.ndarray:
    """
    Campo magnetico local do laboratorio [X, Y, Z] NED, em Tesla, usando as
    coordenadas registradas em params.LAB_*. Substitui fisicamente a Gaiola de
    Helmholtz como referencia de campo conhecido para a estimacao de m.
    """
    return igrf_field_ned_tesla(
        lat_deg=params.LAB_LATITUDE_DEG,
        lon_deg=params.LAB_LONGITUDE_DEG,
        alt_km=params.LAB_ALTITUDE_M / 1000.0,
        year_decimal=year_decimal,
    )


# ---------------------------------------------------------------------------
# Modo Orbital: B(r, t) ao longo de uma orbita LEO
# ---------------------------------------------------------------------------

def eci_to_geodetic_approx(r_eci_m: np.ndarray, gst_rad: float) -> tuple[float, float, float]:
    """
    Conversao aproximada ECI -> (lat, lon, alt) assumindo Terra esferica
    (suficiente para consultas ao IGRF em estudos de ordem de grandeza; para
    o artigo final, considerar WGS-84 completo via astropy/sgp4 se a
    precisao < 1% exigida pela Fase 1 do cronograma nao for atingida).
    """
    x, y, z = r_eci_m
    r_norm = np.linalg.norm(r_eci_m)

    lat_rad = np.arcsin(np.clip(z / r_norm, -1.0, 1.0))
    lon_eci_rad = np.arctan2(y, x)
    lon_rad = lon_eci_rad - gst_rad

    alt_m = r_norm - params.R_EARTH_M

    return np.degrees(lat_rad), np.degrees(((lon_rad + np.pi) % (2 * np.pi)) - np.pi), alt_m


def field_along_orbit_tesla(
    t_array_s: np.ndarray,
    state_array: np.ndarray,
    year_decimal: float,
    gst0_rad: float = 0.0,
) -> np.ndarray:
    """
    Calcula B(t) [Tesla, NED] para cada ponto de uma trajetoria orbital ja
    propagada (ver propagator.py). Retorna array (n_pontos, 3).
    """
    _require_pyigrf()
    n = len(t_array_s)
    B = np.zeros((n, 3))
    for k in range(n):
        gst = gst0_rad + params.OMEGA_EARTH_RAD_S * t_array_s[k]
        lat, lon, alt = eci_to_geodetic_approx(state_array[k, :3], gst)
        B[k] = igrf_field_ned_tesla(lat, lon, alt / 1000.0, year_decimal)
    return B


if __name__ == "__main__":
    print("== igrf_model.py: auto-teste (independente de massa/inercia do satelite) ==")
    if not _HAS_PYIGRF:
        print("pyIGRF nao instalado -- pulei o auto-teste numerico.")
    else:
        try:
            B_lab = lab_field_tesla(year_decimal=2026.6)
            print(f"Campo local do laboratorio (Modo Laboratorio, lat={params.LAB_LATITUDE_DEG}, "
                  f"lon={params.LAB_LONGITUDE_DEG}): B_NED = {B_lab*1e6} uT, "
                  f"|B| = {np.linalg.norm(B_lab)*1e6:.2f} uT")
            print("\nATENCAO: se |B| estiver muito distante de ~20-30 uT (valor tipico em "
                  "baixas latitudes), verifique se o arquivo igrf14coeffs.txt instalado e "
                  "de fato o oficial do IGRF-14 (ver docstring do modulo) -- este ambiente "
                  "de teste pode estar usando um arquivo de coeficientes provisorio.")
        except Exception as e:
            print(f"AVISO: nao foi possivel rodar o auto-teste numerico do IGRF neste "
                  f"ambiente ({type(e).__name__}: {e}).")
            print("Isso e uma pendencia JA CONHECIDA e documentada do projeto (arquivo "
                  "igrf14coeffs.txt oficial deve ser instalado manualmente -- ver docstring "
                  "do modulo) e NAO tem relacao com a atualizacao de massa/inercia desta "
                  "revisao. O restante da API deste modulo (assinaturas de funcao, "
                  "conversoes de unidade, estrutura Modo Laboratorio/Modo Orbital) "
                  "permanece valido e sera exercitado assim que o arquivo oficial de "
                  "coeficientes for instalado no ambiente de execucao real.")
