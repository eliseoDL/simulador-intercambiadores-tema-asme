# ==============================================================================
# ARCHIVO: reporte_calc.py
# DESCRIPCIÓN: Generador de planillas de cálculo en formato Excel (.xlsx)
#              con diseño profesional para Hojas de Datos TEMA / ASME.
# ==============================================================================

import io
import pandas as pd

def generar_calc_hoja_datos(res: dict, meta: dict) -> bytes:
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_meta = pd.DataFrame([
            {"Parámetro de Proyecto": "TAG del Equipo", "Valor": meta.get("tag", "HEX-0100")},
            {"Parámetro de Proyecto": "Proyecto", "Valor": meta.get("proyecto", "GENERAL")},
            {"Parámetro de Proyecto": "Revisión", "Valor": meta.get("revision", "0")},
            {"Parámetro de Proyecto": "Calculado Por", "Valor": meta.get("calculado_por", "E. Livingston")}
        ])
        df_meta.to_excel(writer, sheet_name='Hoja de Datos', index=False, startrow=1, startcol=1)

        d_tema = res.get("Dimensionamiento TEMA & Kern", {})
        d_rating = res.get("Verificación Convectiva (Rating Kern)", {})
        d_asme = res.get("Diseño Mecánico ASME BPVC", {})
        d_termo = res.get("Termodinámica", {})

        filas_resumen = [
            ("--- DIMENSIONAMIENTO TEMA & KERN ---", ""),
            ("Tipo TEMA", d_tema.get("Tipo TEMA [-]")),
            ("Área Requerida Teórica [m²]", d_tema.get("Área Requerida Teórica [m²]")),
            ("Área Instalada Real [m²]", d_tema.get("Área Instalada Real [m²]")),
            ("Diámetro de Casco Ds [mm]", d_tema.get("Diámetro de Casco Ds [mm]")),
            ("Número de Tubos [uds]", d_tema.get("Número de Tubos [uds]")),
            ("Longitud del Tubo [m]", d_tema.get("Longitud del Tubo [m]")),
            ("Pasos por Tubos [uds]", d_tema.get("Pasos por Tubos [uds]")),
            ("--- VERIFICACIÓN CONVECTIVA (RATING) ---", ""),
            ("Coef. Global Estimado U_trial [W/m²·K]", d_rating.get("Coef. Global Estimado U_trial [W/m²·K]")),
            ("Coef. Global REAL U_calc [W/m²·K]", d_rating.get("Coef. Global REAL U_calc [W/m²·K]")),
            ("Margen de Seguridad Térmica [%]", d_rating.get("Margen Seguridad Térmica [%]")),
            ("Coeficiente Película Tubos hi [W/m²·K]", d_rating.get("Coeficiente Película Tubos hi [W/m²·K]")),
            ("Coeficiente Película Casco ho [W/m²·K]", d_rating.get("Coeficiente Película Casco ho [W/m²·K]")),
            ("--- DISEÑO MECÁNICO ASME BPVC ---", ""),
            ("Material Carcasa", d_asme.get("Material Carcasa [-]")),
            ("Material Tubos", d_asme.get("Material Tubos [-]")),
            ("Espesor Mínimo Casco t_min [mm]", d_asme.get("Espesor Mínimo Casco t_min [mm]")),
            ("Presión de Diseño [bar]", d_asme.get("Presión de Diseño [bar]")),
            ("CAPEX Estimado [USD]", d_asme.get("CAPEX Estimado [USD]")),
            ("--- TERMODINÁMICA ---", ""),
            ("Carga Térmica Q [kW]", d_termo.get("Carga Térmica Q [kW]")),
            ("Temperatura Salida Frío [°C]", d_termo.get("Temperatura Salida Frío [°C]")),
            ("LMTD Corregida [°C]", d_termo.get("LMTD Corregida [°C]")),
            ("Factor Ft", d_termo.get("Factor Ft [-]"))
        ]

        df_datos = pd.DataFrame(filas_resumen, columns=["Especificación Técnica / Variable", "Valor Operativo / Geométrico"])
        df_datos.to_excel(writer, sheet_name='Hoja de Datos', index=False, startrow=8, startcol=1)

    output.seek(0)
    return output.getvalue()