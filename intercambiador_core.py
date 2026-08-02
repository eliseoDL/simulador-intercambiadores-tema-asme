# ==============================================================================
# ARCHIVO: intercambiador_core.py
# DESCRIPCIÓN: Núcleo termodinámico e hidráulico con pérdida de carga Kern (ΔP)
#              precisa en tubos (fricción + cabezales) y optimización API 660.
# ==============================================================================

import CoolProp.CoolProp as CP
import numpy as np
import pandas as pd

CATALOGO_MATERIALES_CASCO = {
    "Acero al Carbono A-516 Gr. 70": {"densidad": 7850.0, "k": 45.0, "sigma_adm_MPa": 138.0},
    "Acero Inoxidable A-240 304": {"densidad": 8000.0, "k": 16.2, "sigma_adm_MPa": 137.0},
    "Acero Inoxidable A-240 316": {"densidad": 8000.0, "k": 13.4, "sigma_adm_MPa": 138.0},
    "Aleación de Níquel Inconel 600": {"densidad": 8470.0, "k": 14.9, "sigma_adm_MPa": 150.0}
}

CATALOGO_MATERIALES_TUBOS = {
    "Acero al Carbono A-179": {"densidad": 7850.0, "k": 50.0, "sigma_adm_MPa": 105.0},
    "Acero Inoxidable A-213 TP304": {"densidad": 8000.0, "k": 16.2, "sigma_adm_MPa": 137.0},
    "Acero Inoxidable A-213 TP316": {"densidad": 8000.0, "k": 13.4, "sigma_adm_MPa": 138.0},
    "Aleación Cu-Ni 90/10 (B-111)": {"densidad": 8940.0, "k": 52.0, "sigma_adm_MPa": 88.0}
}

CATALOGO_TUBOS_OD = [19.05, 25.4, 31.75]  # [mm]
CATALOGO_LONGITUDES = [2.5, 3.0, 4.0, 5.0, 6.0]  # [m]
CATALOGO_PASOS = [1, 2, 4, 6]
CATALOGO_TEMAS = ["BEM", "AEM", "AES", "BEU"]

def _mapear_fluido_coolprop(nombre_amigable: str) -> str:
    mapping = {
        "Agua Desmineralizada (Water)": "Water",
        "Amoníaco Anhidro (Ammonia)": "Ammonia",
        "Etanol / Alcohol (Ethanol)": "Ethanol",
        "Propano Industrial (Propane)": "Propane",
        "Metano / Gas Natural (Methane)": "Methane",
        "Dióxido de Carbono (CO2)": "CO2",
        "Aire Seco (Air)": "Air",
        "Benceno (Benzene)": "Benzene",
        "Tolueno (Toluene)": "Toluene"
    }
    return mapping.get(nombre_amigable, "Water")

def estimar_u_automatico(f_cal: str, f_frio: str) -> float:
    fc = _mapear_fluido_coolprop(f_cal)
    ff = _mapear_fluido_coolprop(f_frio)
    if fc in ["Air", "Methane", "CO2"] or ff in ["Air", "Methane", "CO2"]:
        return 150.0
    elif "Ammonia" in [fc, ff]:
        return 1100.0
    elif fc in ["Ethanol", "Propane", "Benzene", "Toluene"] or ff in ["Ethanol", "Propane", "Benzene", "Toluene"]:
        return 650.0
    else:
        return 1000.0

def calcular_intercambiador(
    m_caliente_kg_s: float, T_cal_in_C: float, T_cal_out_C: float, P_cal_bar: float,
    T_frio_in_C: float, P_frio_bar: float, tipo_tema: str, pasos_tubos: int,
    longitud_tubo_m: float, fluido_cal_nombre: str, fluido_frio_nombre: str,
    mat_casco_nombre: str, mat_tubo_nombre: str, U_estimado: float = None
):
    fc_cp = _mapear_fluido_coolprop(fluido_cal_nombre)
    ff_cp = _mapear_fluido_coolprop(fluido_frio_nombre)

    if T_cal_out_C <= T_frio_in_C:
        raise ValueError("Cruce térmico inválido: La temperatura de salida del caliente no puede ser menor o igual a la entrada del frío.")
    if T_cal_in_C <= T_cal_out_C:
        raise ValueError("La temperatura de entrada del caliente debe ser mayor que su salida.")

    if U_estimado is None or U_estimado <= 0:
        U_estimado = estimar_u_automatico(fluido_cal_nombre, fluido_frio_nombre)

    P_cal_Pa = P_cal_bar * 1e5
    P_frio_Pa = P_frio_bar * 1e5
    T_cal_in_K = T_cal_in_C + 273.15
    T_cal_out_K = T_cal_out_C + 273.15
    T_frio_in_K = T_frio_in_C + 273.15

    T_cal_med_K = (T_cal_in_K + T_cal_out_K) / 2.0
    cp_cal = CP.PropsSI('C', 'T', T_cal_med_K, 'P', P_cal_Pa, fc_cp)
    rho_cal = CP.PropsSI('D', 'T', T_cal_med_K, 'P', P_cal_Pa, fc_cp)
    mu_cal = CP.PropsSI('V', 'T', T_cal_med_K, 'P', P_cal_Pa, fc_cp)
    k_cal = CP.PropsSI('L', 'T', T_cal_med_K, 'P', P_cal_Pa, fc_cp)
    pr_cal = CP.PropsSI('Prandtl', 'T', T_cal_med_K, 'P', P_cal_Pa, fc_cp)

    Q_w = m_caliente_kg_s * cp_cal * (T_cal_in_C - T_cal_out_C)

    T_frio_med_K = T_frio_in_K + 15.0
    cp_frio = CP.PropsSI('C', 'T', T_frio_med_K, 'P', P_frio_Pa, ff_cp)
    rho_frio = CP.PropsSI('D', 'T', T_frio_med_K, 'P', P_frio_Pa, ff_cp)
    mu_frio = CP.PropsSI('V', 'T', T_frio_med_K, 'P', P_frio_Pa, ff_cp)
    k_frio = CP.PropsSI('L', 'T', T_frio_med_K, 'P', P_frio_Pa, ff_cp)
    pr_frio = CP.PropsSI('Prandtl', 'T', T_frio_med_K, 'P', P_frio_Pa, ff_cp)

    m_frio_kg_s = Q_w / (cp_frio * (T_cal_in_C - T_cal_out_C) * 0.8)
    T_frio_out_C = T_frio_in_C + Q_w / (m_frio_kg_s * cp_frio)

    dT1 = T_cal_in_C - T_frio_out_C
    dT2 = T_cal_out_C - T_frio_in_C
    if dT1 <= 0 or dT2 <= 0:
        raise ValueError("Cruce térmico detectado en los extremos del intercambiador.")
    
    lmtd = (dT1 - dT2) / np.log(dT1 / dT2)
    Ft = 0.90 if pasos_tubos > 1 else 0.98
    dT_m = lmtd * Ft

    A_req = Q_w / (U_estimado * dT_m)

    OD_tubo_m = 0.0254
    ID_tubo_m = 0.0221
    at = (np.pi / 4.0) * (ID_tubo_m ** 2)
    
    area_tubo_unitaria = np.pi * OD_tubo_m * longitud_tubo_m
    N_tubos = int(np.ceil(A_req / area_tubo_unitaria))
    
    K1 = 0.249
    n1 = 2.207
    Ds_m = OD_tubo_m * ((N_tubos / K1) ** (1.0 / n1))
    Ds_mm = max(200.0, Ds_m * 1000.0)

    # --------------------------------------------------------------------------
    # 1. HIDRÁULICA Y CAÍDA DE PRESIÓN EN TUBOS (Sinnott Eq. 12.19)
    # --------------------------------------------------------------------------
    v_tubos = (m_frio_kg_s / rho_frio) / max(1.0, (N_tubos / pasos_tubos) * at)
    Re_i = (rho_frio * v_tubos * ID_tubo_m) / mu_frio
    Nu_i = 0.023 * (Re_i ** 0.8) * (pr_frio ** (1.0/3.0))
    h_i = (Nu_i * k_frio) / ID_tubo_m

    # Factor de fricción en tubos rugosos comerciales + pérdidas por retornos de cabezales (2.5 a 4 cabezales por paso)
    f_tubo = max(0.0035, 0.046 * (Re_i ** -0.2))
    factor_cabezales = 2.5 if pasos_tubos == 1 else 4.0
    dP_tubos_Pa = pasos_tubos * (8.0 * f_tubo * (longitud_tubo_m / ID_tubo_m) + factor_cabezales) * (rho_frio * (v_tubos ** 2) / 2.0)
    dP_tubos_bar = dP_tubos_Pa / 1e5

    # --------------------------------------------------------------------------
    # 2. HIDRÁULICA Y CAÍDA DE PRESIÓN EN CASCO (Sinnott Eq. 12.26)
    # --------------------------------------------------------------------------
    De = 0.015
    v_casco = (m_caliente_kg_s / rho_cal) / (Ds_m * 0.05)
    Re_o = (rho_cal * v_casco * De) / mu_cal
    Nu_o = 0.36 * (Re_o ** 0.55) * (pr_cal ** (1.0/3.0))
    h_o = (Nu_o * k_cal) / De

    f_casco = max(0.01, 1.93 * (Re_o ** -0.187))
    N_bafles = max(1, int(longitud_tubo_m / (Ds_m * 0.4)))
    dP_casco_Pa = 8.0 * f_casco * (Ds_m / De) * N_bafles * (rho_cal * (v_casco ** 2) / 2.0)
    dP_casco_bar = dP_casco_Pa / 1e5

    k_metal = CATALOGO_MATERIALES_TUBOS[mat_tubo_nombre]["k"]
    R_fouling = 0.0003
    r_fo = OD_tubo_m / ID_tubo_m
    
    inv_U = (1.0 / h_o) + R_fouling + ((OD_tubo_m * np.log(OD_tubo_m / ID_tubo_m)) / (2.0 * k_metal)) + (r_fo / h_i) + (r_fo * R_fouling)
    U_calc = 1.0 / inv_U

    A_instalada = N_tubos * area_tubo_unitaria
    margen_termico = ((U_calc - U_estimado) / U_estimado) * 100.0

    sigma_adm = CATALOGO_MATERIALES_CASCO[mat_casco_nombre]["sigma_adm_MPa"] * 1e6
    P_dis_Pa = P_cal_Pa * 1.10
    t_min_casco = (P_dis_Pa * (Ds_m / 2.0)) / (sigma_adm * 0.85 - 0.6 * P_dis_Pa) + 0.003
    t_min_casco_mm = max(6.35, t_min_casco * 1000.0)

    factores_tema_capex = {"BEM": 1.00, "AEM": 1.05, "BEU": 1.12, "AES": 1.20}
    factor_capex = factores_tema_capex.get(tipo_tema, 1.0)
    capex = (10000.0 + 450.0 * (A_instalada ** 0.68) * (1.0 + ((P_cal_bar / 50.0) ** 1.2))) * factor_capex

    z_vals = np.linspace(0, longitud_tubo_m, 10)
    T_cal_perfil = T_cal_in_C - (T_cal_in_C - T_cal_out_C) * (z_vals / longitud_tubo_m)
    T_frio_perfil = T_frio_in_C + (T_frio_out_C - T_frio_in_C) * (z_vals / longitud_tubo_m)

    return {
        "Dimensionamiento TEMA & Kern": {
            "Tipo TEMA [-]": tipo_tema,
            "Área Requerida Teórica [m²]": round(A_req, 2),
            "Área Instalada Real [m²]": round(A_instalada, 2),
            "Diámetro de Casco Ds [mm]": round(Ds_mm, 1),
            "Número de Tubos [uds]": int(N_tubos),
            "Longitud del Tubo [m]": float(longitud_tubo_m),
            "Pasos por Tubos [uds]": int(pasos_tubos)
        },
        "Verificación Convectiva (Rating Kern)": {
            "Coef. Global Estimado U_trial [W/m²·K]": round(U_estimado, 1),
            "Coef. Global REAL U_calc [W/m²·K]": round(U_calc, 1),
            "Margen Seguridad Térmica [%]": round(margen_termico, 1),
            "Coeficiente Película Tubos hi [W/m²·K]": round(h_i, 1),
            "Coeficiente Película Casco ho [W/m²·K]": round(h_o, 1)
        },
        "Hidráulica y Caída de Presión (Kern)": {
            "Velocidad Tubos vt [m/s]": round(v_tubos, 2),
            "Caída Presión Tubos ΔPt [bar]": round(dP_tubos_bar, 3), # Garantiza 3 decimales
            "Velocidad Casco vs [m/s]": round(v_casco, 2),
            "Caída Presión Casco ΔPs [bar]": round(dP_casco_bar, 3)  # Garantiza 3 decimales
        },
        "Diseño Mecánico ASME BPVC": {
            "Material Carcasa [-]": mat_casco_nombre,
            "Material Tubos [-]": mat_tubo_nombre,
            "Espesor Mínimo Casco t_min [mm]": round(t_min_casco_mm, 2),
            "Presión de Diseño [bar]": round(P_cal_bar * 1.1, 1),
            "CAPEX Estimado [USD]": round(capex, 2)
        },
        "Termodinámica": {
            "Carga Térmica Q [kW]": round(Q_w / 1000.0, 2),
            "Caudal Fluido Frío [kg/s]": round(m_frio_kg_s, 2),
            "Temperatura Entrada Frío [°C]": round(T_frio_in_C, 2),
            "Temperatura Salida Frío [°C]": round(T_frio_out_C, 2),
            "LMTD Corregida [°C]": round(dT_m, 2),
            "Factor Ft [-]": round(Ft, 2)
        },
        "PerfilGrafico": {
            "z": z_vals.tolist(),
            "T_cal": T_cal_perfil.tolist(),
            "T_frio": T_frio_perfil.tolist()
        }
    }

def optimizar_intercambiador(
    m_cal_kg_s, T_cal_in, T_cal_out, P_cal_bar, T_frio_in, P_frio_bar,
    f_cal_nombre, f_frio_nombre, mat_casco, mat_tubo
):
    resultados_grid = []
    resultados_backup = []
    U_auto_base = estimar_u_automatico(f_cal_nombre, f_frio_nombre)

    # Factores de Mantenibilidad y Riesgo de Ciclo de Vida (API 660 / Sinnott)
    factores_confiabilidad_api660 = {"AES": 0.82, "BEU": 0.88, "AEM": 0.95, "BEM": 1.10}

    for od in CATALOGO_TUBOS_OD:
        for L in CATALOGO_LONGITUDES:
            for pasos in CATALOGO_PASOS:
                for tema in CATALOGO_TEMAS:
                    try:
                        res = calcular_intercambiador(
                            m_caliente_kg_s=m_cal_kg_s, T_cal_in_C=T_cal_in, T_cal_out_C=T_cal_out,
                            P_cal_bar=P_cal_bar, T_frio_in_C=T_frio_in, P_frio_bar=5.0,
                            tipo_tema=tema, pasos_tubos=pasos, longitud_tubo_m=L,
                            fluido_cal_nombre=f_cal_nombre, fluido_frio_nombre=f_frio_nombre,
                            mat_casco_nombre=mat_casco, mat_tubo_nombre=mat_tubo,
                            U_estimado=U_auto_base
                        )
                        Ds = res["Dimensionamiento TEMA & Kern"]["Diámetro de Casco Ds [mm]"]
                        esbeltez = L / (Ds / 1000.0)
                        margen = res["Verificación Convectiva (Rating Kern)"]["Margen Seguridad Térmica [%]"]
                        capex = res["Diseño Mecánico ASME BPVC"]["CAPEX Estimado [USD]"]
                        area = res["Dimensionamiento TEMA & Kern"]["Área Instalada Real [m²]"]
                        
                        hidro = res.get("Hidráulica y Caída de Presión (Kern)", {})
                        dP_tub = hidro.get("Caída Presión Tubos ΔPt [bar]", 0.01)
                        dP_cas = hidro.get("Caída Presión Casco ΔPs [bar]", 0.01)
                        
                        # Índice de Mérito API 660 / TCO LIFECYCLE
                        penalizacion_dP = (1.0 + max(0.0, (dP_tub - 0.5) * 3.0)) * (1.0 + max(0.0, (dP_cas - 0.5) * 3.0))
                        factor_riesgo_tema = factores_confiabilidad_api660.get(tema, 1.0)
                        factor_penalizacion_margen = max(0.1, 1.0 + (margen / 100.0))
                        
                        indice_merito_api = (capex * penalizacion_dP * factor_riesgo_tema) / (area * factor_penalizacion_margen)

                        item_dict = {
                            "TEMA [-]": tema, 
                            "OD [mm]": od, 
                            "Longitud [m]": L, 
                            "Pasos [uds]": pasos,
                            "Área [m²]": area,
                            "Casco Ds [mm]": Ds,
                            "U Real [W/m²·K]": res["Verificación Convectiva (Rating Kern)"]["Coef. Global REAL U_calc [W/m²·K]"],
                            "Margen [%]": margen,
                            "ΔP Tubos [bar]": round(dP_tub, 3), # Precisión 3 decimales
                            "ΔP Casco [bar]": round(dP_cas, 3), # Precisión 3 decimales
                            "Ft [-]": res["Termodinámica"]["Factor Ft [-]"],
                            "CAPEX [USD]": capex,
                            "Índice de Mérito": indice_merito_api,
                            "T Frío Salida [°C]": res["Termodinámica"]["Temperatura Salida Frío [°C]"],
                            "_res_full": res
                        }

                        resultados_backup.append(item_dict)

                        if 1.0 <= esbeltez <= 40.0 and margen >= -80.0:
                            resultados_grid.append(item_dict)
                    except Exception:
                        continue

    if not resultados_grid:
        if resultados_backup:
            resultados_grid = resultados_backup
        else:
            raise ValueError("No se encontraron diseños factibles con los parámetros actuales en el catálogo comercial.")

    df = pd.DataFrame(resultados_grid)
    
    idx_eco = df["CAPEX [USD]"].idxmin()
    idx_comp = df["Área [m²]"].idxmin()
    idx_oper = df["Índice de Mérito"].idxmin()

    top_rec = {
        "Económico": df.loc[idx_eco].to_dict(),
        "Compacto": df.loc[idx_comp].to_dict(),
        "Operativo": df.loc[idx_oper].to_dict()
    }
    return df, top_rec