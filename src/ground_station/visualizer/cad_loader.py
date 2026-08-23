"""
cad_loader.py
=============
Processador e carregador de malhas tridimensionais dos arquivos CAD oficiais do PION Sat (.step).
Separa a pilha interna do chassi externo e aplica cores aeroespaciais de alto contraste e legibilidade.
"""

from __future__ import annotations

import logging
import os
from typing import Tuple, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# Paleta de Cores Aeroespaciais VIBRANTES de Alta Fidelidade (RGBA normalizado 0..1)
COLOR_CHASSIS = [0.22, 0.28, 0.38, 0.88]        # Chassi aluminio anodizado azul-grafite espacial
COLOR_CHASSIS_RAILS = [0.15, 0.20, 0.30, 0.95]  # Trilhos estruturais
COLOR_SOLAR_PANEL = [0.05, 0.12, 0.45, 1.0]     # Celulas solares azul safira profundo
COLOR_PCB_OBC = [0.08, 0.58, 0.24, 1.0]         # Placa OBC verde esmeralda tecnologico
COLOR_PCB_EPS = [0.12, 0.35, 0.70, 1.0]         # Placa EPS azul royal
COLOR_PCB_ADCS = [0.65, 0.18, 0.75, 1.0]        # Placa ADCS purpura metalico
COLOR_PCB_PAYLOAD = [0.80, 0.45, 0.10, 1.0]     # Placa Carga Util dourada/ambar
COLOR_BATTERY = [0.95, 0.55, 0.05, 1.0]         # Bateria Li-Ion laranja ouro vibrante
COLOR_BUSBARS = [0.92, 0.78, 0.18, 1.0]         # Barramentos de cobre/ouro polido
COLOR_PILLARS = [0.82, 0.85, 0.88, 1.0]         # Pilares de sustentacao aluminio prateado
COLOR_SCREWS = [0.90, 0.92, 0.95, 1.0]          # Parafusos e espacadores cromados


def get_part_color(name: str) -> list[float]:
    """Retorna cor vibrante baseada na funcao do componente CAD."""
    n = name.lower()
    if "bateria" in n or "bat" in n:
        return COLOR_BATTERY
    elif "barramento" in n:
        return COLOR_BUSBARS
    elif "pilar" in n:
        return COLOR_PILLARS
    elif "1730" in n:
        return COLOR_SCREWS
    elif "partbody_1" in n:
        return COLOR_PCB_EPS
    elif "partbody_2" in n:
        return COLOR_PCB_OBC
    elif "partbody_3" in n:
        return COLOR_PCB_ADCS
    elif "partbody" in n:
        return COLOR_PCB_PAYLOAD
    elif "part 1_2" in n or "part 1_1" in n or "part 1" in n:
        return COLOR_CHASSIS
    return [0.5, 0.6, 0.7, 1.0]


def is_chassis_component(name: str) -> bool:
    """Identifica se uma peca pertence a estrutura do chassi externo."""
    n = name.lower()
    return "part 1" in n or "chassi" in n


def generate_fallback_cubesat_mesh() -> Tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    """
    Gera malha procedural CubeSat 1U separada em:
    (int_verts, int_faces, int_normals, int_colors, cha_verts, cha_faces, cha_normals, cha_colors)
    """
    # Corpo interno (placas e bateria)
    s_in = 40.0
    int_verts = np.array([
        [-s_in, -s_in, -s_in], [s_in, -s_in, -s_in], [s_in, s_in, -s_in], [-s_in, s_in, -s_in],
        [-s_in, -s_in,  s_in], [s_in, -s_in,  s_in], [s_in, s_in,  s_in], [-s_in, s_in,  s_in],
    ], dtype=np.float32)
    
    int_faces = np.array([
        [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
        [0, 5, 1], [0, 4, 5], [2, 6, 7], [2, 7, 3],
        [0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2],
    ], dtype=np.int32)

    int_colors = np.tile(COLOR_PCB_OBC, (12, 1)).astype(np.float32)
    int_colors[0:2] = COLOR_BATTERY
    int_colors[2:4] = COLOR_SOLAR_PANEL

    # Chassi externo (rails)
    s_out = 50.0
    cha_verts = np.array([
        [-s_out, -s_out, -s_out], [s_out, -s_out, -s_out], [s_out, s_out, -s_out], [-s_out, s_out, -s_out],
        [-s_out, -s_out,  s_out], [s_out, -s_out,  s_out], [s_out, s_out,  s_out], [-s_out, s_out,  s_out],
    ], dtype=np.float32)
    cha_faces = int_faces.copy()
    cha_colors = np.tile(COLOR_CHASSIS, (12, 1)).astype(np.float32)

    def calc_normals(verts, fcs):
        v0 = verts[fcs[:, 0]]
        v1 = verts[fcs[:, 1]]
        v2 = verts[fcs[:, 2]]
        n = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(n, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (n / norms).astype(np.float32)

    int_normals = calc_normals(int_verts, int_faces)
    cha_normals = calc_normals(cha_verts, cha_faces)

    return int_verts, int_faces, int_normals, int_colors, cha_verts, cha_faces, cha_normals, cha_colors


def load_cad_mesh_dual(
    cad_path: str = "hardware/cad/Sat com chassi.step",
    cache_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Carrega o modelo CAD STEP e divide a malha em Pilha Interna e Chassi Externo.

    Returns
    -------
    dict com chaves:
        - internal_vertices, internal_faces, internal_normals, internal_colors
        - chassis_vertices, chassis_faces, chassis_normals, chassis_colors
    """
    if cache_path is None:
        base_dir = os.path.dirname(cad_path) or "hardware/cad"
        cache_path = os.path.join(base_dir, "cached_sat_mesh_vibrant.npz")

    # 1. Carregamento do cache se disponivel
    if os.path.exists(cache_path):
        try:
            data = np.load(cache_path)
            return {
                "internal_vertices": data["int_verts"],
                "internal_faces": data["int_faces"],
                "internal_normals": data["int_normals"],
                "internal_colors": data["int_colors"],
                "chassis_vertices": data["cha_verts"],
                "chassis_faces": data["cha_faces"],
                "chassis_normals": data["cha_normals"],
                "chassis_colors": data["cha_colors"],
            }
        except Exception as e:
            logger.warning(f"Erro ao ler cache dual ({e}). Re-processando...")

    # 2. Processamento do arquivo STEP via trimesh
    if os.path.exists(cad_path):
        try:
            import trimesh
            logger.info(f"Processando CAD STEP com chassi separavel: {cad_path}")
            scene = trimesh.load(cad_path)

            int_verts_list, int_faces_list, int_colors_list = [], [], []
            cha_verts_list, cha_faces_list, cha_colors_list = [], [], []
            
            int_offset = 0
            cha_offset = 0

            # Calcula offset global de centralizacao
            all_raw_verts = []
            for geom in scene.geometry.values():
                if hasattr(geom, "vertices") and len(geom.vertices) > 0:
                    v = np.array(geom.vertices, dtype=np.float32)
                    if np.ptp(v, axis=0).max() < 1.0:
                        v *= 1000.0
                    all_raw_verts.append(v)

            global_center = (np.vstack(all_raw_verts).min(axis=0) + np.vstack(all_raw_verts).max(axis=0)) / 2.0

            for name, geom in scene.geometry.items():
                if not hasattr(geom, "vertices") or len(geom.vertices) == 0:
                    continue

                verts = np.array(geom.vertices, dtype=np.float32)
                if np.ptp(verts, axis=0).max() < 1.0:
                    verts *= 1000.0
                verts -= global_center  # Centraliza

                faces = np.array(geom.faces, dtype=np.int32)
                num_faces = len(faces)
                color = get_part_color(name)
                colors = np.tile(color, (num_faces, 1)).astype(np.float32)

                if is_chassis_component(name):
                    cha_verts_list.append(verts)
                    cha_faces_list.append(faces + cha_offset)
                    cha_colors_list.append(colors)
                    cha_offset += len(verts)
                else:
                    int_verts_list.append(verts)
                    int_faces_list.append(faces + int_offset)
                    int_colors_list.append(colors)
                    int_offset += len(verts)

            def assemble_mesh(v_list, f_list, c_list):
                if not v_list:
                    return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.int32), np.zeros((0, 3), dtype=np.float32), np.zeros((0, 4), dtype=np.float32)
                v = np.vstack(v_list)
                f = np.vstack(f_list)
                c = np.vstack(c_list)
                v0 = v[f[:, 0]]
                v1 = v[f[:, 1]]
                v2 = v[f[:, 2]]
                n = np.cross(v1 - v0, v2 - v0)
                norms = np.linalg.norm(n, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                n = (n / norms).astype(np.float32)
                return v, f, n, c

            int_v, int_f, int_n, int_c = assemble_mesh(int_verts_list, int_faces_list, int_colors_list)
            cha_v, cha_f, cha_n, cha_c = assemble_mesh(cha_verts_list, cha_faces_list, cha_colors_list)

            # Salva no cache
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                np.savez_compressed(
                    cache_path,
                    int_verts=int_v, int_faces=int_f, int_normals=int_n, int_colors=int_c,
                    cha_verts=cha_v, cha_faces=cha_f, cha_normals=cha_n, cha_colors=cha_c,
                )
            except Exception:
                pass

            return {
                "internal_vertices": int_v,
                "internal_faces": int_f,
                "internal_normals": int_n,
                "internal_colors": int_c,
                "chassis_vertices": cha_v,
                "chassis_faces": cha_f,
                "chassis_normals": cha_n,
                "chassis_colors": cha_c,
            }

        except Exception as e:
            logger.error(f"Erro ao processar STEP com trimesh: {e}")

    # Fallback
    iv, ifc, inorm, icol, cv, cfc, cnorm, ccol = generate_fallback_cubesat_mesh()
    return {
        "internal_vertices": iv,
        "internal_faces": ifc,
        "internal_normals": inorm,
        "internal_colors": icol,
        "chassis_vertices": cv,
        "chassis_faces": cfc,
        "chassis_normals": cnorm,
        "chassis_colors": ccol,
    }


def load_cad_mesh(
    cad_path: str = "hardware/cad/Sat com chassi.step",
    cache_path: Optional[str] = None,
    scale_to_unit: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Retorna a malha combinada para compatibilidade retroativa."""
    dual = load_cad_mesh_dual(cad_path, cache_path)
    iv, ifc, inorm, icol = dual["internal_vertices"], dual["internal_faces"], dual["internal_normals"], dual["internal_colors"]
    cv, cfc, cnorm, ccol = dual["chassis_vertices"], dual["chassis_faces"], dual["chassis_normals"], dual["chassis_colors"]

    if len(cv) > 0:
        combined_v = np.vstack([iv, cv])
        combined_f = np.vstack([ifc, cfc + len(iv)])
        combined_n = np.vstack([inorm, cnorm])
        combined_c = np.vstack([icol, ccol])
        return combined_v, combined_f, combined_n, combined_c
    return iv, ifc, inorm, icol
