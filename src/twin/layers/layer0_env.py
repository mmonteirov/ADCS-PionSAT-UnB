"""
layer0_env.py
=============
Camada 0 do Gemeo Digital: Modelo de Ambiente Espacial e Geomagnetico (IGRF-14 / Laboratorio).
Fornece o vetor de campo magnetico de referencia B_ref(t, r) para estimacao de atitude e controle.
"""

from __future__ import annotations

import logging
import numpy as np

from src.twin.config import (
    LAB_LATITUDE_DEG,
    LAB_LONGITUDE_DEG,
    LAB_ALTITUDE_M,
    LAB_B_FIELD_NED_UT,
)

logger = logging.getLogger(__name__)


class EnvironmentLayer0:
    """
    Camada 0: Modelo de campo geomagnetico e perturbacoes ambientais.
    """

    def __init__(self, mode: str = "lab", year_decimal: float = 2026.6) -> None:
        self.mode = mode
        self.year_decimal = year_decimal
        self.b_lab_ref_uT = LAB_B_FIELD_NED_UT.copy()

    def get_reference_magnetic_field_uT(self, time_s: float = 0.0) -> np.ndarray:
        """
        Retorna o vetor de campo magnetico de referencia [Bx, By, Bz] em microTesla.

        Parameters
        ----------
        time_s : float
            Tempo decorrido em segundos.

        Returns
        -------
        np.ndarray (3,)
            Vetor B em microTesla no referencial de referencia local (NED/Lab).
        """
        if self.mode == "lab":
            return self.b_lab_ref_uT.copy()
        else:
            # Em modo orbital, simula rotacao orbital em LEO (~90 min periodo)
            orb_rate = 2.0 * np.pi / 5400.0
            bx = 15.0 * np.cos(orb_rate * time_s)
            by = 10.0 * np.sin(orb_rate * time_s)
            bz = -20.0
            return np.array([bx, by, bz], dtype=np.float64)
