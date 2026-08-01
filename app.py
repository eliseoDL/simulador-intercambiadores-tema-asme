# ==============================================================================
# ARCHIVO: app.py
# DESCRIPCIÓN: Interfaz Streamlit dual con soporte multifluido (CoolProp),
#              selección de materiales ASME II-D, visualización completa de
#              Área [m²], Casco Ds [mm], U_real y exportación sin errores.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from intercambiador_core import calcular_intercambiador, optimizar_intercambiador, CATALOGO_MATERIALES_CASCO, CATALOGO_MATERIALES_TUBOS
from reporte_pdf import generar_pdf_hoja_datos
from reporte_calc import generar_calc_hoja_datos

st.set_page_config(
    page_title="Simulador y Optimizador de Intercambiadores | TEMA & ASME",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Simulador y Optimizador de Intercambiadores de Casco y Tubos (TEMA / ASME)")
st.markdown(
    "**Motor termodinámico multifluido (`CoolProp`), Método de Kern para Sizing & Rating (Sinnott Cap. 12) y diseño mecánico ASME BPVC Sección VIII Div. 1.**\n\n"
    "*Permite verificar geometrías específicas o ejecutar una optimización combinatoria sobre catálogos comerciales con estimación CAPEX (Sinnott Cap. 6).* "
)

# ==============================================================================
# BARRA LATERAL: MODO, FLUIDOS Y MATERIALES INDEPENDIENTES
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

if "Air" in f_cal or "Methane" in f_cal or "CO2" in f_cal:
    st.sidebar.info("💡 **Sinnott Tabla 12.1:** Para Gas — Agua, el coeficiente *U de prueba* típico recomendado es **20 - 300 [W/m²·K]**.")
elif "Ammonia" in f_cal:
    st.sidebar.info("💡 **Sinnott Tabla 12.1:** Para Amoníaco — Agua, el coeficiente *U de prueba* típico recomendado es **800 - 1400 [W/m²·K]**.")
elif "Ethanol" in f_cal or "Benzene" in f_cal or "Toluene" in f_cal:
    st.sidebar.info("💡 **Sinnott Tabla 12.1:** Para Orgánicos — Agua, el coeficiente *U de prueba* típico recomendado es **500 - 800 [W/m²·K]**.")
else:
    st.sidebar.info("💡 **Sinnott Tabla 12.1:** Para Agua — Agua, el coeficiente *U de prueba* típico recomendado es **800 - 1500 [W/m²·K]**.")

st.sidebar.divider()
st.sidebar.header("🛡️ Materiales Normados (ASME Sec. II-D)")
m_casco_sel = st.sidebar.selectbox("Material Carcasa / Casco [-]", list(CATALOGO_MATERIALES_CASCO.keys()), index=0)
m_tubo_sel = st.sidebar.selectbox("Material del Haz de Tubos [-]", list(CATALOGO_MATERIALES_TUBOS.keys()), index=0)

st.sidebar.divider()
st.sidebar.header("🔧 Parámetros del Proceso")
m_cal = st.sidebar.slider("Caudal Fluido Caliente [kg/s]", 1.0, 20.0, 5.0, 0.5)
T_cal_in = st.sidebar.slider("Temp. Entrada Caliente [°C]", 60.0, 200.0, 120.0, 5.0)
T_cal_out = st.sidebar.slider("Temp. Salida Caliente [°C]", 30.0, 100.0, 60.0, 5.0)
T_frio_in = st.sidebar.slider("Temp. Entrada Fluido Frío [°C]", 15.0, 40.0, 25.0, 1.0)
P_op = st.sidebar.slider("Presión Operativa Lado Casco/Tubos [bar]", 2.0, 40.0, 10.0, 1.0)

U_est = st.sidebar.number_input(
    "Coeficiente U ESTIMADO de Prueba [W/m²·K]",
    min_value=100.0, max_value=2500.0, value=800.0, step=50.0,
    help="U_trial utilizado según Sinnott Cap. 12.3 para inicializar la geometría. El U_real operativo se verifica en los resultados."
)

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
            m_caliente_kg_s=m_cal, T_cal_in_C=T_cal_in, T_cal_out_C=T_cal_out,
            P_cal_bar=P_op, T_frio_in_C=T_frio_in, P_frio_bar=5.0, tipo_tema=tema_tipo,
            pasos_tubos=pasos, U_estimado=U_est, longitud_tubo_m=long_tubo,
            fluido_cal_nombre=f_cal, fluido_frio_nombre=f_frio,
            mat_casco_nombre=m_casco_sel, mat_tubo_nombre=m_tubo_sel
        )

        st.subheader("📊 Métricas Clave y Verificación Convectiva (Sizing vs. Rating)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Área TEMA Instalada [m²]", f"{res['Dimensionamiento TEMA & Kern']['Área Instalada Real [m²]']} m²")
        col2.metric("U Estimado (Arranque) [W/m²·K]", f"{res['Verificación Convectiva (Rating Kern)']['Coef. Global Estimado U_trial [W/m²·K]']} W/m²·K")
        col3.metric("U REAL Calculado (Kern) [W/m²·K]", f"{res['Verificación Convectiva (Rating Kern)']['Coef. Global REAL U_calc [W/m²·K]']} W/m²·K")
        col4.metric("Margen de Seguridad Térmico [%]", f"{res['Verificación Convectiva (Rating Kern)']['Margen Seguridad Térmica [%]']} %")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown(f"**Perfil Térmico en Contracorriente ({f_cal} vs. {f_frio})**")
            pg = res["PerfilGrafico"]
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=pg["z"], y=pg["T_cal"], mode='lines+markers', line=dict(color='#E53E3E', width=3), name='Fluido Caliente [°C]'))
            fig_t.add_trace(go.Scatter(x=pg["z"], y=pg["T_frio"], mode='lines+markers', line=dict(color='#3182CE', width=3), name='Fluido Frío [°C]'))
            fig_t.update_layout(xaxis_title="Longitud Nominal del Haz [m]", yaxis_title="Temperatura [°C]", height=320, margin=dict(l=20,r=20,t=30,b=30))
            st.plotly_chart(fig_t, use_container_width=True)

        with col_g2:
            st.markdown("**Sensibilidad Económica: CAPEX [USD] vs. Caudal [kg/s]**")
            c_test = np.linspace(1.0, 20.0, 10)
            capex_vals = []
            for ct in c_test:
                rt = calcular_intercambiador(m_caliente_kg_s=ct, T_cal_in_C=T_cal_in, T_cal_out_C=T_cal_out, P_cal_bar=P_op, T_frio_in_C=T_frio_in, P_frio_bar=5.0, tipo_tema=tema_tipo, pasos_tubos=pasos, U_estimado=U_est, longitud_tubo_m=long_tubo, fluido_cal_nombre=f_cal, fluido_frio_nombre=f_frio, mat_casco_nombre=m_casco_sel, mat_tubo_nombre=m_tubo_sel)
                capex_vals.append(rt["Diseño Mecánico ASME BPVC"]["CAPEX Estimado [USD]"])
            fig_c = go.Figure()
            fig_c.add_trace(go.Scatter(x=c_test, y=capex_vals, mode='lines+markers', line=dict(color='#2F855A', width=3), name='CAPEX [USD]'))
            fig_c.add_trace(go.Scatter(x=[m_cal], y=[res['Diseño Mecánico ASME BPVC']['CAPEX Estimado [USD]']], mode='markers', marker=dict(color='red', size=11), name='Operación Actual'))
            fig_c.update_layout(xaxis_title="Caudal Fluido Caliente [kg/s]", yaxis_title="CAPEX Estimado [USD]", height=320, margin=dict(l=20,r=20,t=30,b=30))
            st.plotly_chart(fig_c, use_container_width=True)

        st.divider()
        st.subheader("📥 Exportar Especificaciones (Hoja de Datos TEMA / ASME)")
        c_dl1, c_dl2 = st.columns(2)
        meta_m = {"tag": f"HEX-0100 ({tema_tipo})", "proyecto": "PROYECTO GENERAL", "revision": "0", "calculado_por": "E. Livingston"}
        with c_dl1:
            st.download_button("📊 Descargar Planilla Calc (.xlsx)", generar_calc_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.xlsx")
        with c_dl2:
            st.download_button("📄 Descargar PDF Oficial (.pdf)", generar_pdf_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.pdf")

        st.divider()
        st.subheader("📑 Memoria Técnica del Dimensionamiento (Con Unidades Explícitas)")
        tab1, tab2, tab3, tab4 = st.tabs([
            "Dimensionamiento TEMA & Kern",
            "Verificación Convectiva (U Real)",
            "Diseño Mecánico ASME BPVC",
            "Balance Termodinámico"
        ])
        with tab1:
            df_tema = pd.DataFrame(list(res["Dimensionamiento TEMA & Kern"].items()), columns=["Parámetro TEMA / Kern", "Valor Calculado"])
            st.dataframe(df_tema, use_container_width=True, hide_index=True)
        with tab2:
            df_rating = pd.DataFrame(list(res["Verificación Convectiva (Rating Kern)"].items()), columns=["Variable de Convección (Kern)", "Resultado"])
            st.dataframe(df_rating, use_container_width=True, hide_index=True)
        with tab3:
            df_asme = pd.DataFrame(list(res["Diseño Mecánico ASME BPVC"].items()), columns=["Parámetro Mecánico ASME", "Especificación / Valor"])
            st.dataframe(df_asme, use_container_width=True, hide_index=True)
        with tab4:
            df_termo = pd.DataFrame(list(res["Termodinámica"].items()), columns=["Variable de Proceso", "Valor Operativo"])
            st.dataframe(df_termo, use_container_width=True, hide_index=True)

    except ValueError as err_f:
        st.error(f"🚨 **Alerta de Inviabilidad:** {err_f}")

# ==============================================================================
# MODO 2: OPTIMIZADOR E INTELIGENCIA DE CATÁLOGO (GRID SEARCH)
# ==============================================================================
else:
    st.subheader("🚀 Selección Inteligente de Equipos (Grid Search Multicriterio)")
    st.markdown(
        "El motor evalúa automáticamente combinaciones normalizadas del catálogo comercial "
        "(`3/4\"`, `1\"`, `1 1/4\"`, longitudes de `2.5` a `6.0 m`, 1 a 6 pasos) y descarta diseños "
        "inviables por esbeltez estructural ($3 \\le L/D_s \\le 10$), baja eficiencia ($F_t < 0.75$) o "
        "margen térmico convectivo negativo."
    )

    try:
        df_grid, top_rec = optimizar_intercambiador(
            m_cal_kg_s=m_cal, T_cal_in=T_cal_in, T_cal_out=T_cal_out,
            P_cal_bar=P_op, T_frio_in=T_frio_in, P_frio_bar=5.0, U_estimado=U_est,
            f_cal_nombre=f_cal, f_frio_nombre=f_frio,
            mat_casco=m_casco_sel, mat_tubo=m_tubo_sel
        )

        st.markdown("### 🏆 Top 3 Recomendaciones Tecnológicas de Diseño")
        col_t1, col_t2, col_t3 = st.columns(3)

        # --- TARJETA 1: ÓPTIMO ECONÓMICO ---
        with col_t1:
            eco = top_rec["Económico"]
            st.success("💰 **ÓPTIMO ECONÓMICO (Mínimo CAPEX [USD])**")
            st.markdown(f"**Área Instalada [m²]:** `{eco['Área [m²]']} m²` | **TEMA:** `{eco['TEMA [-]']}`")
            st.markdown(f"**Casco Ds [mm]:** `{eco['Casco Ds [mm]']} mm` | **Longitud:** `{eco['Longitud [m]']} m`")
            st.markdown(f"**Tubos [uds]:** `{eco['Tubos [uds]']}` | **OD:** `{eco['OD [mm]']} mm` (`{eco['Pasos [uds]']} pasos`)")
            st.markdown(f"**U Real [W/m²·K]:** `{eco['U Real [W/m²·K]']}` | **Margen:** `{eco['Margen [%]']}%`")
            st.metric("Inversión Estimada [USD]", f"${eco['CAPEX [USD]']:,.2f} USD", delta="Recomendado EPC")

        # --- TARJETA 2: ÓPTIMO COMPACTO ---
        with col_t2:
            comp = top_rec["Compacto"]
            st.info("📐 **ÓPTIMO COMPACTO (Mínimo Footprint [m²])**")
            st.markdown(f"**Área Instalada [m²]:** `{comp['Área [m²]']} m²` | **TEMA:** `{comp['TEMA [-]']}`")
            st.markdown(f"**Casco Ds [mm]:** `{comp['Casco Ds [mm]']} mm` | **Longitud:** `{comp['Longitud [m]']} m`")
            st.markdown(f"**Tubos [uds]:** `{comp['Tubos [uds]']}` | **OD:** `{comp['OD [mm]']} mm` (`{comp['Pasos [uds]']} pasos`)")
            st.markdown(f"**U Real [W/m²·K]:** `{comp['U Real [W/m²·K]']}` | **Margen:** `{comp['Margen [%]']}%`")
            st.metric("Inversión Estimada [USD]", f"${comp['CAPEX [USD]']:,.2f} USD")

        # --- TARJETA 3: ÓPTIMO OPERATIVO ---
        with col_t3:
            oper = top_rec["Operativo"]
            st.warning("🛡️ **ÓPTIMO OPERATIVO (Máximo Margen Convectivo [%])**")
            st.markdown(f"**Área Instalada [m²]:** `{oper['Área [m²]']} m²` | **TEMA:** `{oper['TEMA [-]']}`")
            st.markdown(f"**Casco Ds [mm]:** `{oper['Casco Ds [mm]']} mm` | **Longitud:** `{oper['Longitud [m]']} m`")
            st.markdown(f"**Tubos [uds]:** `{oper['Tubos [uds]']}` | **OD:** `{oper['OD [mm]']} mm` (`{oper['Pasos [uds]']} pasos`)")
            st.markdown(f"**U Real [W/m²·K]:** `{oper['U Real [W/m²·K]']}` | **Margen:** `{oper['Margen [%]']}%`")
            st.metric("Inversión Estimada [USD]", f"${oper['CAPEX [USD]']:,.2f} USD")

        st.divider()

        st.subheader("📈 Frontera de Pareto del Catálogo Evaluado")
        st.markdown("Comparativa de los **equipos factibles**: **Inversión CAPEX [USD] vs. Área Instalada [m²]** clasificados por longitud del tubo:")
        
        fig_pareto = px.scatter(
            df_grid, x="Área [m²]", y="CAPEX [USD]",
            color="Longitud [m]", size="Casco Ds [mm]",
            hover_data=["TEMA [-]", "OD [mm]", "Pasos [uds]", "Ft [-]", "U Real [W/m²·K]", "Margen [%]"],
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig_pareto.update_layout(height=400, margin=dict(l=20,r=20,t=30,b=30))
        st.plotly_chart(fig_pareto, use_container_width=True)

        st.divider()

        st.subheader("📥 Exportar Especificaciones del Equipo Optimizado")
        st.write("Seleccione cuál de los 3 modelos recomendados desea emitir en pliego oficial:")
        
        opcion_descarga = st.selectbox(
            "Modelo a Exportar en Hoja de Datos [-]:",
            options=["Económico (Mínimo CAPEX)", "Compacto (Menor Huella en Planta)", "Operativo (Máximo Margen)"]
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

        meta_opt = {"tag": tag_str, "proyecto": "OPTIMIZACIÓN DE CATÁLOGO", "revision": "0", "calculado_por": "E. Livingston (Optimizador)"}
        
        col_do1, col_do2 = st.columns(2)
        with col_do1:
            st.download_button(
                "📊 Descargar Planilla Calc (.xlsx) [Equipo Optimizado]",
                generar_calc_hoja_datos(res_opt_seleccionado, meta_opt),
                f"Data_Sheet_{tag_str}.xlsx"
            )
        with col_do2:
            st.download_button(
                "📄 Descargar PDF Oficial (.pdf) [Equipo Optimizado]",
                generar_pdf_hoja_datos(res_opt_seleccionado, meta_opt),
                f"Data_Sheet_{tag_str}.pdf"
            )

    except ValueError as error_opt:
        st.error(f"🚨 **Sin Soluciones Viables en Catálogo:** {error_opt}")