"""
config.py
=========
Constantes fisicas e parametros nominais do nanossatelite PION Sat para o Gemeo Digital.
Inercia oficial do CAD completo (com chassi): Izz = 5.25e-4 kg*m^2.
"""

from __future__ import annotations
import numpy as np

# Inercia oficial derivada do CAD completo (hardware/cad/Sat com chassi.step)
# Massa total real medida: 325.0 g = 0.325 kg
I3_NOMINAL_KG_M2: float = 5.25e-4

# Tensor de inercia 3x3 completo (kg*m^2)
INERTIA_TENSOR_FULL_KG_M2 = np.array([
    [5.10e-4,  1.20e-6, -1.10e-6],
    [ 1.20e-6, 5.15e-4,  1.50e-7],
    [-1.10e-6,  1.50e-7, 5.25e-4]
], dtype=np.float64)

# Constantes do atuador (magnetorquer / roda de reacao 1-eixo)
MAX_PWM: float = 1000.0
MAX_TORQUE_NM: float = 5.0e-5       # Torque maximo de atuacao (N*m)
DEADBAND_PWM: float = 20.0          # Zona morta de PWM

# Coeficiente de amortecimento aerodinamico / atrito do mancal a ar (N*m*s/rad)
FRICTION_COEFF_DAMPING: float = 1.0e-6

# Dipolo magnetico maximo dos magnetorquers (A*m^2)
MAX_MAGNETIC_DIPOLE_AM2: float = 0.15

# Coordenadas do Laboratorio (UnB / Brasilia)
LAB_LATITUDE_DEG: float = -15.764
LAB_LONGITUDE_DEG: float = -47.871
LAB_ALTITUDE_M: float = 1000.0

# Campo geomagnetico tipico de referencia no laboratorio (NED, em microTesla)
# Brasilia (Anomalia Magnetica do Atlantico Sul / baixa inclinacao): ~23 uT total
LAB_B_FIELD_NED_UT = np.array([14.5, -2.5, -19.5], dtype=np.float64)
