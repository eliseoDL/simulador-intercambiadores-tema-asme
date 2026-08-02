# ==============================================================================
# ARCHIVO: app.py
# DESCRIPCIÓN: Interfaz Streamlit con métricas de Caída de Presión (ΔP) y velocidad.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from intercambiador_core import calcular_intercambiador, optimizar_intercambiador, estimar_u_automatico, CATALOGO_MATERIALES_CASCO, CATALOGO_MATERIALES_TUBOS
from reporte_pdf import generar_pdf_hoja_datos
from reporte_calc import generar_calc_hoja_datos

st.set_page_config(
    page_title="Simulador y Optimizador de Intercambiadores | TEMA & ASME",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Simulador y Optimizador de Intercambiadores de Casco y Tubos (TEMA / ASME)")
st.markdown(
    "**Motor termodinámico e hidráulico (`CoolProp`), Método de Kern (Sinnott Cap. 12) con cálculo de caídas de presión ($\Delta P$) y diseño mecánico ASME BPVC.**"
)

# ==============================================================================
# BARRA LATERAL UNIFICADA
# ==============================================================================
st.sidebar.header("🎛️ Modo de Operación")
modo_app = st.sidebar.radio(
    "Seleccione el tipo de análisis:",
    options=[
        "⚙️ Verificación y Simulación Manual",
        "🚀 Optimizador e Inteligencia de Catálogo"
    ]
)

st.sidebar.divider()
st.sidebar.header("🧪 Selección de Fluidos (CoolProp / IF97)")
lista_fluidos = [
    "Agua Desmineralizada (Water)", "Amoníaco Anhidro (Ammonia)", "Etanol / Alcohol (Ethanol)", 
    "Propano Industrial (Propane)", "Metano / Gas Natural (Methane)", 
    "Dióxido de Carbono (CO2)", "Aire Seco (Air)", "Benceno (Benzene)", "Tolueno (Toluene)"
]

f_cal = st.sidebar.selectbox("Fluido Lado Caliente (Proceso) [-]", lista_fluidos, index=0)
f_frio = st.sidebar.selectbox("Fluido Lado Frío (Servicio Auxiliar) [-]", lista_fluidos[:4], index=0)

u_ref = estimar_u_automatico(f_cal, f_frio)
st.sidebar.info(f"💡 **Coeficiente U de Arranque Asignado:** `{u_ref} [W/m²·K]`")

st.sidebar.divider()
st.sidebar.header("🛡️ Materiales Normados (ASME Sec. II-D)")
m_casco_sel = st.sidebar.selectbox("Material Carcasa / Casco [-]", list(CATALOGO_MATERIALES_CASCO.keys()), index=0)
m_tubo_sel = st.sidebar.selectbox("Material del Haz de Tubos [-]", list(CATALOGO_MATERIALES_TUBOS.keys()), index=0)

st.sidebar.divider()
st.sidebar.header("🔧 Parámetros de Proceso y Temperaturas")
m_cal = st.sidebar.slider("Caudal Fluido Caliente [kg/s]", 1.0, 20.0, 5.0, 0.5)

T_cal_in = st.sidebar.slider("Temp. Entrada Caliente [°C]", 20.0, 300.0, 120.0, 5.0)
T_cal_out = st.sidebar.slider("Temp. Salida Caliente [°C]", 10.0, 250.0, 60.0, 5.0)
T_frio_in = st.sidebar.slider("Temp. Entrada Fluido Frío [°C]", 5.0, 40.0, 25.0, 1.0)
P_op = st.sidebar.slider("Presión Operativa Lado Casco/Tubos [bar]", 2.0, 40.0, 10.0, 1.0)

# ==============================================================================
# MODO 1: VERIFICACIÓN Y SIMULACIÓN MANUAL
# ==============================================================================
if modo_app == "⚙️ Verificación y Simulación Manual":
    st.sidebar.header("📐 Geometría Manual (Sinnott Cap. 12)")
    tema_tipo = st.sidebar.selectbox("Clasificación Normativa TEMA [-]", ["BEM", "AEM", "AES", "BEU", "AEP"], index=0)
    pasos = st.sidebar.selectbox("Pasos por Tubos [uds]", [1, 2, 4, 6], index=1)
    long_tubo = st.sidebar.selectbox("Longitud Normalizada [m]", [2.5, 3.0, 4.0, 5.0, 6.0], index=2)

    try:
        res = calcular_intercambiador(
            m_caliente_kg_s=m_cal, T_cal_in_C=T_cal_in, T_cal_out_C=T_cal_out, P_cal_bar=P_op,
            T_frio_in_C=T_frio_in, P_frio_bar=5.0, tipo_tema=tema_tipo,
            pasos_tubos=pasos, longitud_tubo_m=long_tubo,
            fluido_cal_nombre=f_cal, fluido_frio_nombre=f_frio,
            mat_casco_nombre=m_casco_sel, mat_tubo_nombre=m_tubo_sel
        )

        st.subheader("📊 Métricas Clave y Verificación Convectiva e Hidráulica")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Área TEMA Instalada [m²]", f"{res['Dimensionamiento TEMA & Kern']['Área Instalada Real [m²]']} m²")
        col2.metric("U REAL Calculado (Kern)", f"{res['Verificación Convectiva (Rating Kern)']['Coef. Global REAL U_calc [W/m²·K]']} W/m²·K")
        col3.metric("ΔP Tubos / Casco [bar]", f"{res['Hidráulica y Caída de Presión (Kern)']['Caída Presión Tubos ΔPt [bar]']} / {res['Hidráulica y Caída de Presión (Kern)']['Caída Presión Casco ΔPs [bar]']} bar")
        col4.metric("Margen Térmico [%]", f"{res['Verificación Convectiva (Rating Kern)']['Margen Seguridad Térmica [%]']} %")

        st.divider()
        col_dl1, col_dl2 = st.columns(2)
        meta_m = {"tag": f"HEX-0100 ({tema_tipo})", "proyecto": "PROYECTO GENERAL", "revision": "0", "calculado_por": "E. Livingston"}
        with col_dl1:
            st.download_button("📊 Descargar Planilla Calc (.xlsx)", generar_calc_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col_dl2:
            st.download_button("📄 Descargar PDF Oficial (.pdf)", generar_pdf_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.pdf", mime="application/pdf")

        st.divider()
        st.subheader("📑 Memoria Técnica del Dimensionamiento e Hidráulica")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Dimensionamiento TEMA & Kern",
            "Verificación Convectiva (U Real)",
            "Hidráulica y Caída de Presión ΔP",
            "Diseño Mecánico ASME BPVC",
            "Balance Termodinámico"
        ])
        with tab1:
            st.dataframe(pd.DataFrame(list(res["Dimensionamiento TEMA & Kern"].items()), columns=["Parámetro TEMA / Kern", "Valor Calculado"]), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(pd.DataFrame(list(res["Verificación Convectiva (Rating Kern)"].items()), columns=["Variable de Convección (Kern)", "Resultado"]), use_container_width=True, hide_index=True)
        with tab3:
            st.dataframe(pd.DataFrame(list(res["Hidráulica y Caída de Presión (Kern)"].items()), columns=["Variable Hidráulica", "Resultado [bar / m/s]"]), use_container_width=True, hide_index=True)
        with tab4:
            st.dataframe(pd.DataFrame(list(res["Diseño Mecánico ASME BPVC"].items()), columns=["Parámetro Mecánico ASME", "Especificación / Valor"]), use_container_width=True, hide_index=True)
        with tab5:
            st.dataframe(pd.DataFrame(list(res["Termodinámica"].items()), columns=["Variable de Proceso", "Valor Operativo"]), use_container_width=True, hide_index=True)

    except ValueError as err_f:
        st.error(f"🚨 **Alerta de Inviabilidad:** {err_f}")

# ==============================================================================
# MODO 2: OPTIMIZADOR E INTELIGENCIA DE CATÁLOGO (GRID SEARCH)
# ==============================================================================
else:
    st.subheader("🚀 Selección Inteligente de Equipos (Grid Search Multicriterio)")
    st.markdown("El motor evalúa combinaciones de tipos TEMA y geometrías aplicando **criterios hidráulicos ($\Delta P$) y técnico-económicos**.")

    try:
        df_grid, top_rec = optimizar_intercambiador(
            m_cal_kg_s=m_cal, T_cal_in=T_cal_in, T_cal_out=T_cal_out,
            P_cal_bar=P_op, T_frio_in=T_frio_in, P_frio_bar=5.0,
            f_cal_nombre=f_cal, f_frio_nombre=f_frio,
            mat_casco=m_casco_sel, mat_tubo=m_tubo_sel
        )

        st.markdown("### 🏆 Top 3 Recomendaciones Tecnológicas de Diseño")
        col_t1, col_t2, col_t3 = st.columns(3)

        with col_t1:
            eco = top_rec["Económico"]
            st.success("💰 **ÓPTIMO ECONÓMICO**")
            st.markdown(f"**TEMA:** `{eco['TEMA [-]']}` | **Área:** `{eco['Área [m²]']} m²`")
            st.markdown(f"**Casco Ds:** `{eco['Casco Ds [mm]']} mm` | **Longitud:** `{eco['Longitud [m]']} m`")
            st.markdown(f"**T Frío In/Out:** `{T_frio_in}°C` ➔ `{eco['T Frío Salida [°C]']}°C`")
            st.markdown(f"**ΔP Tubos / Casco:** `{eco['ΔP Tubos [bar]']}` / `{eco['ΔP Casco [bar]']} bar`")
            st.metric("Inversión Estimada", f"${eco['CAPEX [USD]']:,.2f} USD")

        with col_t2:
            comp = top_rec["Compacto"]
            st.info("📐 **ÓPTIMO COMPACTO**")
            st.markdown(f"**TEMA:** `{comp['TEMA [-]']}` | **Área:** `{comp['Área [m²]']} m²`")
            st.markdown(f"**Casco Ds:** `{comp['Casco Ds [mm]']} mm` | **Longitud:** `{comp['Longitud [m]']} m`")
            st.markdown(f"**T Frío In/Out:** `{T_frio_in}°C` ➔ `{comp['T Frío Salida [°C]']}°C`")
            st.markdown(f"**ΔP Tubos / Casco:** `{comp['ΔP Tubos [bar]']}` / `{comp['ΔP Casco [bar]']} bar`")
            st.metric("Inversión Estimada", f"${comp['CAPEX [USD]']:,.2f} USD")

        with col_t3:
            oper = top_rec["Operativo"]
            st.warning("🛡️ **ÓPTIMO OPERATIVO (API 660 / EDR)**")
            st.markdown(f"**TEMA:** `{oper['TEMA [-]']}` | **Área:** `{oper['Área [m²]']} m²`")
            st.markdown(f"**Casco Ds:** `{oper['Casco Ds [mm]']} mm` | **Longitud:** `{oper['Longitud [m]']} m`")
            st.markdown(f"**T Frío In/Out:** `{T_frio_in}°C` ➔ `{oper['T Frío Salida [°C]']}°C`")
            st.markdown(f"**ΔP Tubos / Casco:** `{oper['ΔP Tubos [bar]']}` / `{oper['ΔP Casco [bar]']} bar`")
            st.metric("Inversión Estimada", f"${oper['CAPEX [USD]']:,.2f} USD")

        st.divider()
        st.subheader("📥 Exportar Especificaciones del Equipo Optimizado")
        
        opcion_descarga = st.selectbox(
            "Seleccione el modelo recomendado a exportar:",
            options=["Económico (Mínimo CAPEX)", "Compacto (Menor Huella)", "Operativo (Máximo Mérito Hidráulico-Económico)"]
        )

        if "Económico" in opcion_descarga:
            res_opt_seleccionado = top_rec["Económico"]["_res_full"]
            tag_str = f"HEX-OPT-ECO ({top_rec['Económico']['TEMA [-]']})"
        elif "Compacto" in opcion_descarga:
            res_opt_seleccionado = top_rec["Compacto"]["_res_full"]
            tag_str = f"HEX-OPT-CMP ({top_rec['Compacto']['TEMA [-]']})"
        else:
            res_opt_seleccionado = top_rec["Operativo"]["_res_full"]
            tag_str = f"HEX-OPT-OPR ({top_rec['Operativo']['TEMA [-]']})"

        meta_opt = {"tag": tag_str, "proyecto": "OPTIMIZACIÓN DE CATÁLOGO", "revision": "0", "calculado_por": "E. Livingston"}
        
        col_do1, col_do2 = st.columns(2)
        with col_do1:
            st.download_button("📊 Descargar Planilla Calc (.xlsx)", generar_calc_hoja_datos(res_opt_seleccionado, meta_opt), f"Data_Sheet_{tag_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col_do2:
            st.download_button("📄 Descargar PDF Oficial (.pdf)", generar_pdf_hoja_datos(res_opt_seleccionado, meta_opt), f"Data_Sheet_{tag_str}.pdf", mime="application/pdf")

    except ValueError as error_opt:
        st.error(f"🚨 **Sin Soluciones Viables en Catálogo:** {error_opt}")