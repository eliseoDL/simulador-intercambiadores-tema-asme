# ==============================================================================
# ARCHIVO: intercambiador_core.py
# DESCRIPCIÓN: Motor termodinámico multifluido (CoolProp), dimensionamiento
#              (Sinnott/Kern), diseño mecánico (ASME VIII) y optimización
#              combinatoria multicriterio con estimación CAPEX en USD.
# REFERENCIAS BIBLIOGRÁFICAS (PENSAMIENTO CRÍTICO):
#   1. Sinnott, R. & Towler, G. - "Chemical Engineering Design: Principles,
#      Practice and Economics of Plant and Process Design" (Elsevier):
#      - Cap. 6: Ecuación factorial de costo de adquisición CAPEX (Ley 0.68).
#      - Cap. 12: Método de Kern (TEMA), factor Ft, LMTD y Tabla 12.1 (U típico).
#      - Cap. 13: Diseño mecánico de recipientes sometidos a presión interna.
#   2. ASME BPVC Section VIII Division 1 (UG-27 para casco / UG-31 para tubos).
#   3. CoolProp / IAPWS: Propiedades termodinámicas reales de fluidos puros.
# ==============================================================================

import numpy as np
import CoolProp.CoolProp as CP
import pandas as pd

# Mapeo de nombres en la app a los identificadores exactos de la librería CoolProp
MAPEO_FLUIDOS = {
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

# Catálogo normado de materiales para CARCASA / CASCO (Sinnott Cap. 13 & ASME Sec. II-D)
CATALOGO_MATERIALES_CASCO = {
    "Acero al Carbono SA-516 Gr. 70": {"S_mpa": 138.0, "k_w_mk": 50.0, "desc": "Estándar industrial procesos"},
    "Acero Inoxidable SA-240 Type 316": {"S_mpa": 137.0, "k_w_mk": 16.3, "desc": "Alta corrosión / alimentos"},
    "Acero Aleado SA-387 Gr. 11 (Cr-Mo)": {"S_mpa": 145.0, "k_w_mk": 38.0, "desc": "Servicio de alta temperatura"}
}

# Catálogo normado de materiales para TUBOS (Sinnott Cap. 13 & ASME Sec. II-D)
CATALOGO_MATERIALES_TUBOS = {
    "Acero al Carbono SA-179 / SA-214": {"S_mpa": 134.0, "k_w_mk": 50.0, "desc": "Estándar agua/hidrocarburos"},
    "Acero Inoxidable SA-213 Type 316L": {"S_mpa": 115.0, "k_w_mk": 16.3, "desc": "Ácidos / fluidos agresivos"},
    "Cuproníquel SB-111 (Cu-Ni 90/10)": {"S_mpa": 110.0, "k_w_mk": 52.0, "desc": "Agua salobre / refrigeración marina"},
    "Titanio SB-338 Gr. 2": {"S_mpa": 115.0, "k_w_mk": 21.9, "desc": "Cloruros severos / servicio offshore"}
}


def calcular_intercambiador(
    # --- PROCESO (LADO CALIENTE - CASCO POR DEFECTO EN KERN) ---
    m_caliente_kg_s=5.0,
    T_cal_in_C=120.0,
    T_cal_out_C=60.0,
    P_cal_bar=10.0,
    fluido_cal_nombre="Agua Desmineralizada (Water)",
    
    # --- SERVICIO AUXILIAR (LADO FRÍO - TUBOS POR DEFECTO EN KERN) ---
    T_frio_in_C=25.0,
    P_frio_bar=5.0,
    fluido_frio_nombre="Agua Desmineralizada (Water)",
    
    # --- GEOMETRÍA NORMA TEMA (SINNOTT CAP. 12) ---
    tipo_tema="BEM",
    pasos_tubos=2,
    U_estimado=800.0,                         # Coeficiente U ESTIMADO de prueba [W/m²·K]
    diam_ext_tubo_m=0.0254,                   # Tubo 1 pulgada OD
    espesor_tubo_nominal_m=0.00211,           # BWG 14 = 2.11 mm
    longitud_tubo_m=4.0,
    
    # --- SELECCIÓN DE MATERIALES INDEPENDIENTES ---
    mat_casco_nombre="Acero al Carbono SA-516 Gr. 70",
    mat_tubo_nombre="Acero al Carbono SA-179 / SA-214",
    
    # --- MECÁNICA ASME VIII ---
    E_eficiencia_junta=0.85,
    c_corrosion_mm=3.0
):
    """
    Ejecuta el dimensionamiento (Sizing) desde U_estimado y luego efectúa la
    verificación convectiva (Rating de Kern) para obtener el U_real de operación.
    """
    if T_cal_in_C <= T_cal_out_C:
        raise ValueError("La temperatura de entrada del fluido caliente debe ser mayor a su salida.")
    if T_cal_out_C <= T_frio_in_C:
        raise ValueError("Cruce térmico inválido: La salida caliente no puede ser inferior o igual a la entrada fría.")

    # 1. TERMODINÁMICA MULTIFLUIDO Y BALANCE ENERGÉTICO (CoolProp)
    T_cal_media_K = ((T_cal_in_C + T_cal_out_C) / 2.0) + 273.15
    P_cal_pa = P_cal_bar * 1e5
    f_cal = MAPEO_FLUIDOS.get(fluido_cal_nombre, "Water")
    cp_cal = CP.PropsSI('Cpmass', 'T', T_cal_media_K, 'P', P_cal_pa, f_cal)
    mu_cal = CP.PropsSI('V', 'T', T_cal_media_K, 'P', P_cal_pa, f_cal)
    k_cal = CP.PropsSI('L', 'T', T_cal_media_K, 'P', P_cal_pa, f_cal)
    rho_cal = CP.PropsSI('D', 'T', T_cal_media_K, 'P', P_cal_pa, f_cal)

    q_watts = m_caliente_kg_s * cp_cal * (T_cal_in_C - T_cal_out_C)
    q_kw = q_watts / 1000.0

    T_frio_out_C = min(T_frio_in_C + 15.0, T_cal_out_C - 5.0)
    if T_frio_out_C <= T_frio_in_C:
        raise ValueError("Diferencial de temperatura insuficiente para operar con este refrigerante.")

    T_frio_media_K = ((T_frio_in_C + T_frio_out_C) / 2.0) + 273.15
    P_frio_pa = P_frio_bar * 1e5
    f_frio = MAPEO_FLUIDOS.get(fluido_frio_nombre, "Water")
    cp_frio = CP.PropsSI('Cpmass', 'T', T_frio_media_K, 'P', P_frio_pa, f_frio)
    mu_frio = CP.PropsSI('V', 'T', T_frio_media_K, 'P', P_frio_pa, f_frio)
    k_frio = CP.PropsSI('L', 'T', T_frio_media_K, 'P', P_frio_pa, f_frio)
    rho_frio = CP.PropsSI('D', 'T', T_frio_media_K, 'P', P_frio_pa, f_frio)

    m_frio_kg_s = q_watts / (cp_frio * (T_frio_out_C - T_frio_in_C))

    # 2. LMTD Y FACTOR FT
    dt1 = T_cal_in_C - T_frio_out_C
    dt2 = T_cal_out_C - T_frio_in_C
    if dt1 <= 0 or dt2 <= 0:
        raise ValueError("Inviabilidad térmica (ΔT <= 0).")

    lmtd_contra = dt1 if abs(dt1 - dt2) < 1e-4 else (dt1 - dt2) / np.log(dt1 / dt2)

    Ft = 1.0
    if pasos_tubos > 1:
        R = (T_cal_in_C - T_cal_out_C) / (T_frio_out_C - T_frio_in_C)
        S = (T_frio_out_C - T_frio_in_C) / (T_cal_in_C - T_frio_in_C)
        try:
            if abs(R - 1.0) < 1e-4:
                Ft = (S * np.sqrt(2.0)) / ((1.0 - S) * np.log((2.0 - S * (2.0 - np.sqrt(2.0))) / (2.0 - S * (2.0 + np.sqrt(2.0)))))
            else:
                num = np.sqrt(R**2 + 1.0) * np.log((1.0 - S) / (1.0 - R * S))
                den = (R - 1.0) * np.log((2.0 - S * (R + 1.0 - np.sqrt(R**2 + 1.0))) / (2.0 - S * (R + 1.0 + np.sqrt(R**2 + 1.0))))
                Ft = float(num / den)
            Ft = 0.85 if np.isnan(Ft) or np.isinf(Ft) or Ft <= 0 else max(min(Ft, 1.0), 0.75)
        except Exception:
            Ft = 0.85

    lmtd_efectiva = lmtd_contra * Ft
    
    # 3. DIMENSIONAMIENTO GEOMÉTRICO (SIZING DESDE U_ESTIMADO)
    area_req_m2 = q_watts / (U_estimado * lmtd_efectiva)
    area_un_tubo = np.pi * diam_ext_tubo_m * longitud_tubo_m
    numero_tubos = int(np.ceil(area_req_m2 / area_un_tubo))

    K1, n1 = (0.319, 2.142) if pasos_tubos == 1 else (0.249, 2.207)
    diam_casco_m = diam_ext_tubo_m * ((numero_tubos / K1) ** (1.0 / n1))
    espaciado_bafles_m = 0.40 * diam_casco_m
    num_bafles = max(int(np.floor(longitud_tubo_m / espaciado_bafles_m)) - 1, 2)
    area_instalada_m2 = numero_tubos * area_un_tubo

    # 4. VERIFICACIÓN DE INGENIERÍA (RATING DE KERN -> CÁLCULO DE U_REAL)
    diam_int_tubo_m = diam_ext_tubo_m - 2.0 * espesor_tubo_nominal_m
    
    # A) Lado Tubos (Fluido Frío por defecto):
    area_flujo_tubos_m2 = (numero_tubos / pasos_tubos) * (np.pi * (diam_int_tubo_m ** 2) / 4.0)
    vel_tubos_m_s = m_frio_kg_s / (rho_frio * area_flujo_tubos_m2)
    re_tubos = (rho_frio * vel_tubos_m_s * diam_int_tubo_m) / mu_frio
    pr_tubos = (cp_frio * mu_frio) / k_frio
    
    nu_tubos = 0.023 * (re_tubos ** 0.8) * (pr_tubos ** 0.33) if re_tubos > 2100 else 3.66
    h_i = (nu_tubos * k_frio) / diam_int_tubo_m

    # B) Lado Casco (Fluido Caliente por defecto):
    pitch_m = 1.25 * diam_ext_tubo_m
    area_flujo_casco_m2 = ((pitch_m - diam_ext_tubo_m) * diam_casco_m * espaciado_bafles_m) / pitch_m
    vel_casco_m_s = m_caliente_kg_s / (rho_cal * area_flujo_casco_m2)
    
    d_equiv_m = (1.10 / diam_ext_tubo_m) * ((pitch_m ** 2) - 0.917 * (diam_ext_tubo_m ** 2))
    re_casco = (rho_cal * vel_casco_m_s * d_equiv_m) / mu_cal
    pr_casco = (cp_cal * mu_cal) / k_cal
    
    nu_casco = 0.36 * (re_casco ** 0.55) * (pr_casco ** 0.33)
    h_o = (nu_casco * k_cal) / d_equiv_m

    # C) Resistencia térmica y U_real
    prop_mat_tubo = CATALOGO_MATERIALES_TUBOS.get(mat_tubo_nombre, CATALOGO_MATERIALES_TUBOS["Acero al Carbono SA-179 / SA-214"])
    k_metal = prop_mat_tubo["k_w_mk"]
    
    R_fouling_total = 0.0003
    diam_medio_log_m = (diam_ext_tubo_m - diam_int_tubo_m) / np.log(diam_ext_tubo_m / diam_int_tubo_m)
    
    resistencia_total = (1.0 / h_o) + R_fouling_total + ((espesor_tubo_nominal_m * diam_ext_tubo_m) / (k_metal * diam_medio_log_m)) + ((diam_ext_tubo_m / diam_int_tubo_m) * (1.0 / h_i))
    U_real_calculado = 1.0 / resistencia_total
    
    U_req_efectivo = q_watts / (area_instalada_m2 * lmtd_efectiva)
    margen_seguridad_pct = ((U_real_calculado - U_req_efectivo) / U_req_efectivo) * 100.0

    # 5. DISEÑO MECÁNICO ASME BPVC SECCIÓN VIII DIV. 1
    prop_mat_casco = CATALOGO_MATERIALES_CASCO.get(mat_casco_nombre, CATALOGO_MATERIALES_CASCO["Acero al Carbono SA-516 Gr. 70"])
    S_casco_mpa = prop_mat_casco["S_mpa"]
    S_tubo_mpa = prop_mat_tubo["S_mpa"]

    P_max_bar = max(P_cal_bar, P_frio_bar)
    P_dis_bar = max(P_max_bar * 1.10, P_max_bar + 1.5)
    P_dis_mpa = P_dis_bar / 10.0

    diam_casco_mm = diam_casco_m * 1000.0
    esp_casco_calc_mm = (P_dis_mpa * diam_casco_mm) / (2.0 * S_casco_mpa * E_eficiencia_junta - 1.2 * P_dis_mpa) + c_corrosion_mm
    espesores_chapa = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 19.0, 22.0, 25.0, 32.0]
    esp_casco_comercial_mm = next((e for e in espesores_chapa if e >= esp_casco_calc_mm), esp_casco_calc_mm)

    diam_tubo_mm = diam_ext_tubo_m * 1000.0
    esp_tubo_calc_mm = (P_dis_mpa * diam_tubo_mm) / (2.0 * S_tubo_mpa * E_eficiencia_junta + 0.8 * P_dis_mpa) + (c_corrosion_mm / 2.0)
    espesores_bwg = [1.65, 2.11, 2.77, 3.40, 4.19]
    esp_tubo_comercial_mm = next((e for e in espesores_bwg if e >= esp_tubo_calc_mm), esp_tubo_calc_mm)

    factor_presion = 1.0 + (P_dis_bar / 50.0)**1.2
    capex_usd = round(10000.0 + 450.0 * (area_instalada_m2 ** 0.68) * factor_presion, 2)

    # 6. PERFIL TÉRMICO
    z_array = np.linspace(0.0, longitud_tubo_m, 15)
    frac_z = z_array / longitud_tubo_m
    factor_curva = 1.8
    t_cal_array = T_cal_in_C - (T_cal_in_C - T_cal_out_C) * ((1.0 - np.exp(-factor_curva * frac_z)) / (1.0 - np.exp(-factor_curva)))
    t_frio_array = T_frio_out_C - (T_frio_out_C - T_frio_in_C) * ((1.0 - np.exp(-factor_curva * frac_z)) / (1.0 - np.exp(-factor_curva)))

    return {
        "Termodinámica": {
            "Carga Térmica Total [kW]": round(q_kw, 2),
            "Caudal Fluido Proceso [kg/s]": m_caliente_kg_s,
            "Caudal Servicio Auxiliar [kg/s]": round(m_frio_kg_s, 2),
            "Temp. Entrada Caliente [°C]": T_cal_in_C,
            "Temp. Salida Caliente [°C]": round(T_cal_out_C, 2),
            "Temp. Entrada Frío [°C]": T_frio_in_C,
            "Temp. Salida Frío [°C]": round(T_frio_out_C, 2),
            "LMTD Contracorriente [°C]": round(lmtd_contra, 2),
            "Factor Corrección Ft [-]": round(Ft, 3),
            "LMTD Efectiva [°C]": round(lmtd_efectiva, 2)
        },
        "Dimensionamiento TEMA & Kern": {
            "Clasificación TEMA [-]": tipo_tema,
            "Pasos por Tubo [uds]": pasos_tubos,
            "Área Requerida Teórica [m²]": round(area_req_m2, 2),
            "Área Instalada Real [m²]": round(area_instalada_m2, 2),
            "Número Total de Tubos [uds]": numero_tubos,
            "Diámetro Ext. Tubo OD [mm]": diam_tubo_mm,
            "Longitud Nominal Tubo [m]": longitud_tubo_m,
            "Diámetro Interno Casco Ds [mm]": round(diam_casco_mm, 1),
            "Espaciado de Bafles B [mm]": round(espaciado_bafles_m * 1000.0, 1),
            "Número de Bafles [uds]": num_bafles
        },
        "Verificación Convectiva (Rating Kern)": {
            "Coef. Global Estimado U_trial [W/m²·K]": U_estimado,
            "Coef. Convectivo Casco h_o [W/m²·K]": round(h_o, 1),
            "Coef. Convectivo Tubos h_i [W/m²·K]": round(h_i, 1),
            "Coef. Global REAL U_calc [W/m²·K]": round(U_real_calculado, 1),
            "Margen Seguridad Térmica [%]": round(margen_seguridad_pct, 1),
            "Resistencia Ensuciamiento Rf [m²·K/W]": R_fouling_total
        },
        "Diseño Mecánico ASME BPVC": {
            "Presión Diseño ASME [bar]": round(P_dis_bar, 2),
            "Material Carcasa [-]": mat_casco_nombre,
            "Material Tubos [-]": mat_tubo_nombre,
            "Tensión Adm. Carcasa S [MPa]": S_casco_mpa,
            "Tensión Adm. Tubos S [MPa]": S_tubo_mpa,
            "Conductividad Tubo k [W/m·K]": k_metal,
            "Sobreespesor Corrosión [mm]": c_corrosion_mm,
            "Espesor Casco Comercial [mm]": esp_casco_comercial_mm,
            "Espesor Tubo Comercial BWG [mm]": esp_tubo_comercial_mm,
            "CAPEX Estimado [USD]": capex_usd
        },
        "PerfilGrafico": {
            "z": z_array,
            "T_cal": t_cal_array,
            "T_frio": t_frio_array
        }
    }


def optimizar_intercambiador(
    m_cal_kg_s=5.0,
    T_cal_in=120.0,
    T_cal_out=60.0,
    P_cal_bar=10.0,
    T_frio_in=25.0,
    P_frio_bar=5.0,
    U_estimado=800.0,
    f_cal_nombre="Agua Desmineralizada (Water)",
    f_frio_nombre="Agua Desmineralizada (Water)",
    mat_casco="Acero al Carbono SA-516 Gr. 70",
    mat_tubo="Acero al Carbono SA-179 / SA-214"
):
    longitudes_m = [2.5, 3.0, 4.0, 5.0, 6.0]
    diametros_m = [0.01905, 0.0254, 0.03175]
    pasos_list = [1, 2, 4, 6]
    tipos_tema = ["BEM", "AES", "BEU"]

    resultados_grid = []

    for l_tubo in longitudes_m:
        for d_ext in diametros_m:
            for p_tubo in pasos_list:
                for tema in tipos_tema:
                    try:
                        res = calcular_intercambiador(
                            m_caliente_kg_s=m_cal_kg_s,
                            T_cal_in_C=T_cal_in,
                            T_cal_out_C=T_cal_out,
                            P_cal_bar=P_cal_bar,
                            T_frio_in_C=T_frio_in,
                            P_frio_bar=P_frio_bar,
                            tipo_tema=tema,
                            pasos_tubos=p_tubo,
                            U_estimado=U_estimado,
                            diam_ext_tubo_m=d_ext,
                            longitud_tubo_m=l_tubo,
                            fluido_cal_nombre=f_cal_nombre,
                            fluido_frio_nombre=f_frio_nombre,
                            mat_casco_nombre=mat_casco,
                            mat_tubo_nombre=mat_tubo
                        )

                        area_inst = res["Dimensionamiento TEMA & Kern"]["Área Instalada Real [m²]"]
                        diam_casco_mm = res["Dimensionamiento TEMA & Kern"]["Diámetro Interno Casco Ds [mm]"]
                        diam_casco_m = diam_casco_mm / 1000.0
                        ft_factor = res["Termodinámica"]["Factor Corrección Ft [-]"]
                        esbeltez = l_tubo / max(diam_casco_m, 0.1)
                        capex = res["Diseño Mecánico ASME BPVC"]["CAPEX Estimado [USD]"]
                        num_tubos = res["Dimensionamiento TEMA & Kern"]["Número Total de Tubos [uds]"]
                        u_real = res["Verificación Convectiva (Rating Kern)"]["Coef. Global REAL U_calc [W/m²·K]"]
                        margen = res["Verificación Convectiva (Rating Kern)"]["Margen Seguridad Térmica [%]"]

                        if ft_factor >= 0.75 and 3.0 <= esbeltez <= 10.0 and margen >= -5.0:
                            resultados_grid.append({
                                "TEMA [-]": tema,
                                "Longitud [m]": l_tubo,
                                "OD [mm]": round(d_ext * 1000.0, 2),
                                "Pasos [uds]": p_tubo,
                                "Área [m²]": area_inst,
                                "Tubos [uds]": num_tubos,
                                "Casco Ds [mm]": diam_casco_mm,
                                "L/Ds [-]": round(esbeltez, 1),
                                "Ft [-]": ft_factor,
                                "U Real [W/m²·K]": u_real,
                                "Margen [%]": margen,
                                "CAPEX [USD]": capex,
                                "_res_full": res
                            })
                    except Exception:
                        continue

    df_opt = pd.DataFrame(resultados_grid)
    if df_opt.empty:
        raise ValueError("Ninguna combinación cumple con esbeltez (3 <= L/Ds <= 10), factor térmico (Ft >= 0.75) y margen convectivo suficiente.")

    opt_eco = df_opt.sort_values(by="CAPEX [USD]", ascending=True).iloc[0]
    opt_comp = df_opt.sort_values(by=["Casco Ds [mm]", "Área [m²]"], ascending=[True, True]).iloc[0]
    opt_oper = df_opt.sort_values(by=["Margen [%]", "Ft [-]"], ascending=[False, False]).iloc[0]

    return df_opt, {
        "Económico": opt_eco.to_dict(),
        "Compacto": opt_comp.to_dict(),
        "Operativo": opt_oper.to_dict()
    }