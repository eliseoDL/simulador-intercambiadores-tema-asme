# ==============================================================================
# ARCHIVO: app.py
# DESCRIPCIÓN: Interfaz Streamlit con presiones operativas hasta 100 bar,
#              visualización explícita de caídas de presión, márgenes térmicos,
#              guía de usuario UX y gráfico dinámico multipaso con choque térmico.
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
    "**Motor termodinámico e hidráulico (`CoolProp`), Método de Kern (Sinnott Cap. 12) y condiciones de Diseño ASME BPVC Sección VIII Div. 1.**\n\n"
    "*Compatible con exportación de corrientes de simuladores de proceso (UniSim / DWSIM / Aspen).* "
)

# ==============================================================================
# FUNCIÓN AUXILIAR 1: GUÍA EDUCATIVA UX DE MARGEN TÉRMICO
# ==============================================================================
def mostrar_guia_margen_termico():
    with st.expander("ℹ️ Guía industrial: ¿Qué es el Margen Térmico (%) y cómo interpretarlo?"):
        st.markdown("""
        El **Margen de Seguridad Térmica (*Thermal Design Margin*)** indica el porcentaje de **superficie de transferencia de calor instalada en exceso** respecto a la superficie requerida por el coeficiente $U_{\\text{calc}}$ del equipo:
        
        $$\\text{Margen Térmico [\\%]} = \\left( \\frac{A_{\\text{instalada}} - A_{\\text{req, real}}}{A_{\\text{req, real}}} \\right) \\times 100$$
        
        ### 📊 ¿Cómo interpretar este valor en una planta?
        
        | Rango del Margen | Diagnóstico | Explicación Operativa |
        |---|---|---|
        | **`< 0 %`** | 🚨 **Insuficiente (Subdimensionado)** | El equipo **no alcanzará las temperaturas especificadas**; le falta área de transferencia o eficiencia convectiva. |
        | **`0 % a +10 %`** | ⚠️ **Ajustado (Sin reserva)** | Funciona al límite con tubos nuevos, pero **fallará rápidamente en cuanto aparezca una mínima incrustación** (*fouling*). |
        | **`+15 % a +35 %`** | ✅ **Óptimo Normativo (API 660 / TEMA)** | **Rango ideal de diseño EPC.** Asegura 1 a 2 años de operación continua sin limpieza, absorbiendo suciedad y picos de carga. |
        | **`> +40 %`** | 💰 **Sobredimensionado (Exceso CAPEX)** | El equipo es innecesariamente grande y costoso para el servicio demandado. |
        """)

# ==============================================================================
# FUNCIÓN AUXILIAR 2: GRÁFICO DINÁMICO MULTIPASO Y DIAGNÓSTICO DE CHOQUE TÉRMICO
# ==============================================================================
def generar_grafico_perfil_pasos(res: dict):
    """
    Genera un gráfico dinámico Plotly que muestra la evolución de temperatura
    paso a paso por el haz de tubos, el perfil de temperatura de pared (T_wall)
    y evalúa la agresividad del intercambio (choque térmico dT/dz).
    """
    d_tema = res.get("Dimensionamiento TEMA & Kern", {})
    d_rating = res.get("Verificación Convectiva (Rating Kern)", {})
    d_termo = res.get("Termodinámica", {})

    pasos = int(d_tema.get("Pasos por Tubos [uds]", 2))
    L_tubo = float(d_tema.get("Longitud del Tubo [m]", 3.0))
    L_total = L_tubo * pasos

    T_frio_in = float(d_termo.get("Temperatura Entrada Frío [°C]", 25.0))
    T_frio_out = float(d_termo.get("Temperatura Salida Frío [°C]", 60.0))
    
    perfil_orig = res.get("PerfilGrafico", {})
    T_cal_in = float(perfil_orig.get("T_cal", [120.0, 80.0])[0])
    T_cal_out = float(perfil_orig.get("T_cal", [120.0, 80.0])[-1])

    u_val = float(d_rating.get("Coef. Global REAL U_calc [W/m²·K]", 800.0))
    ho_val = float(d_rating.get("Coeficiente Película Casco ho [W/m²·K]", 1500.0))

    n_puntos = 50 * pasos
    x_total = np.linspace(0, L_total, n_puntos)
    k_decay = 2.0 / max(1.0, L_total)
    
    T_frio_curva = T_frio_in + (T_frio_out - T_frio_in) * (1.0 - np.exp(-k_decay * x_total)) / (1.0 - np.exp(-k_decay * L_total))
    T_cal_curva = T_cal_in - (T_cal_in - T_cal_out) * (1.0 - np.exp(-k_decay * x_total)) / (1.0 - np.exp(-k_decay * L_total))
    
    T_wall_curva = [
        tc - (tc - tf) * (u_val / max(1.0, ho_val)) 
        for tc, tf in zip(T_cal_curva, T_frio_curva)
    ]

    dT_dz_max = abs(T_frio_curva[5] - T_frio_curva[0]) / max(0.01, (x_total[5] - x_total[0]))
    T_wall_max = max(T_wall_curva)

    c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
    c_kpi1.metric("🔥 Temp. Máxima de Pared (T_wall)", f"{T_wall_max:.1f} °C", "Película límite")
    c_kpi2.metric("📈 Gradiente Térmico Máx. (dT/dz)", f"{dT_dz_max:.1f} °C/m", "Severidad inicial")
    
    with c_kpi3:
        if dT_dz_max > 30.0:
            st.error("🔴 **INTERCAMBIO AGRESIVO**\nAlto riesgo de choque térmico / incrustación.")
        elif dT_dz_max > 18.0:
            st.warning("🟡 **INTERCAMBIO MODERADO**\nMonitorear ensuciamiento en Paso 1.")
        else:
            st.success("🟢 **INTERCAMBIO SUAVE**\nCalentamiento progresivo y seguro.")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_total, y=T_cal_curva,
        mode='lines', name='Fluido Caliente (Carcasa/Tubos)',
        line=dict(color='#E53E3E', width=3)
    ))

    fig.add_trace(go.Scatter(
        x=x_total, y=T_frio_curva,
        mode='lines', name='Fluido Frío (Recorrido Tubos)',
        line=dict(color='#3182CE', width=3)
    ))

    fig.add_trace(go.Scatter(
        x=x_total, y=T_wall_curva,
        mode='lines', name='Temp. de Pared Metálica (T_wall)',
        line=dict(color='#DD6B20', width=2, dash='dash')
    ))

    for p in range(1, pasos):
        x_sep = p * L_tubo
        fig.add_vline(
            x=x_sep, line_width=1.5, line_dash="dot", line_color="#A0AEC0",
            annotation_text=f"<b>Retorno Cabezal (Fin Paso {p})</b>",
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color="#4A5568"
        )

    colores_paso = ["rgba(237, 242, 247, 0.4)", "rgba(226, 232, 240, 0.2)"]
    for p in range(pasos):
        fig.add_vrect(
            x0=p * L_tubo, x1=(p + 1) * L_tubo,
            fillcolor=colores_paso[p % 2], layer="below", line_width=0,
            annotation_text=f"<b>PASO {p+1}</b>", annotation_position="bottom right"
        )

    fig.update_layout(
        title="<b>Perfil Térmico Dinámico Multipaso y Agresividad de Película (T_wall)</b><br>"
              "<i>Muestra el calentamiento asintótico en cada paso por el haz de tubos y evalúa el riesgo de daño térmico</i>",
        xaxis_title="Recorrido Acumulado a través del Haz de Tubos [m]",
        yaxis_title="Temperatura Operativa / Metal [°C]",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=480,
        margin=dict(l=40, r=40, t=80, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# BARRA LATERAL UNIFICADA (CONTROLES DE PROCESO Y MATERIALES)
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
st.sidebar.header("🧪 Selección y Asignación de Fluidos")
lista_fluidos = [
    "Agua Desmineralizada (Water)", "Amoníaco Anhidro (Ammonia)", "Etanol / Alcohol (Ethanol)", 
    "Propano Industrial (Propane)", "Metano / Gas Natural (Methane)", 
    "Dióxido de Carbono (CO2)", "Aire Seco (Air)", "Benceno (Benzene)", "Tolueno (Toluene)"
]

f_cal = st.sidebar.selectbox("Fluido Caliente (Proceso) [-]", lista_fluidos, index=0)
f_frio = st.sidebar.selectbox("Fluido Frío (Servicio Auxiliar) [-]", lista_fluidos[:4], index=0)

asig_sel = st.sidebar.selectbox(
    "Asignación: ¿Por dónde pasa el Fluido Caliente? [-]",
    ["Por Carcasa (Lado Casco)", "Por Tubos (Lado Tubos)"],
    index=0
)
asignacion_val = "Carcasa" if "Carcasa" in asig_sel else "Tubos"

u_ref = estimar_u_automatico(f_cal, f_frio)
st.sidebar.info(f"💡 **U Arranque Asignado:** `{u_ref} [W/m²·K]`")

st.sidebar.divider()
st.sidebar.header("🛡️ Materiales Normados (ASME Sec. II-D)")
m_casco_sel = st.sidebar.selectbox("Material Carcasa / Casco [-]", list(CATALOGO_MATERIALES_CASCO.keys()), index=0)
m_tubo_sel = st.sidebar.selectbox("Material del Haz de Tubos [-]", list(CATALOGO_MATERIALES_TUBOS.keys()), index=0)

st.sidebar.divider()
st.sidebar.header("🔧 Parámetros de Corrientes (Simulador)")
m_cal = st.sidebar.slider("Caudal Fluido Caliente [kg/s]", 1.0, 20.0, 5.0, 0.5)

T_cal_in = st.sidebar.slider("Temp. Entrada Caliente [°C]", 20.0, 300.0, 120.0, 5.0)
T_cal_out = st.sidebar.slider("Temp. Salida Caliente [°C]", 10.0, 250.0, 60.0, 5.0)
P_cal_op = st.sidebar.slider("Presión Operativa Fluido Caliente [bar]", 1.0, 100.0, 10.0, 1.0)

st.sidebar.divider()
T_frio_in = st.sidebar.slider("Temp. Entrada Fluido Frío [°C]", 5.0, 40.0, 25.0, 1.0)
P_frio_op = st.sidebar.slider("Presión Operativa Fluido Frío [bar]", 1.0, 100.0, 5.0, 1.0)

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
            m_caliente_kg_s=m_cal, T_cal_in_C=T_cal_in, T_cal_out_C=T_cal_out, P_cal_bar=P_cal_op,
            T_frio_in_C=T_frio_in, P_frio_bar=P_frio_op, tipo_tema=tema_tipo,
            pasos_tubos=pasos, longitud_tubo_m=long_tubo,
            fluido_cal_nombre=f_cal, fluido_frio_nombre=f_frio,
            mat_casco_nombre=m_casco_sel, mat_tubo_nombre=m_tubo_sel,
            asignacion_caliente=asignacion_val
        )

        st.subheader("📊 Métricas Clave y Verificación Convectiva e Hidráulica")
        col1, col2, col3, col4 = st.columns(4)
        
        area_inst = res.get("Dimensionamiento TEMA & Kern", {}).get("Área Instalada Real [m²]", "N/A")
        u_real = res.get("Verificación Convectiva (Rating Kern)", {}).get("Coef. Global REAL U_calc [W/m²·K]", "N/A")
        
        hidro = res.get("Hidráulica y Caída de Presión (Kern)", {})
        dp_t = float(hidro.get("Caída Presión Tubos ΔPt [bar]", 0.01))
        dp_s = float(hidro.get("Caída Presión Casco ΔPs [bar]", 0.01))
        
        margen_term = res.get("Verificación Convectiva (Rating Kern)", {}).get("Margen Seguridad Térmica [%]", "0.0")

        col1.metric("Área TEMA Instalada [m²]", f"{area_inst} m²")
        col2.metric("U REAL Calculado (Kern)", f"{u_real} W/m²·K")
        col3.metric("ΔP Tubos / Casco [bar]", f"{dp_t:.3f} / {dp_s:.3f} bar")
        col4.metric("Margen Térmico [%] (Exceso)", f"{margen_term} %")

        mostrar_guia_margen_termico()

        st.divider()
        col_dl1, col_dl2 = st.columns(2)
        meta_m = {"tag": f"HEX-0100 ({tema_tipo})", "proyecto": "PROYECTO GENERAL", "revision": "0", "calculado_por": "E. Livingston"}
        with col_dl1:
            st.download_button("📊 Descargar Planilla Calc (.xlsx)", generar_calc_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col_dl2:
            st.download_button("📄 Descargar PDF Oficial (.pdf)", generar_pdf_hoja_datos(res, meta_m), f"Data_Sheet_{tema_tipo}.pdf", mime="application/pdf")

        st.divider()
        st.subheader("📑 Memoria Técnica del Dimensionamiento e Hidráulica")
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Dimensionamiento TEMA & Kern",
            "Verificación Convectiva (U Real)",
            "Hidráulica y Caída de Presión ΔP",
            "Diseño Mecánico ASME BPVC (Diseño vs Operación)",
            "Balance Termodinámico",
            "📈 Perfil Térmico Multipaso & Choque"
        ])
        with tab1:
            st.dataframe(pd.DataFrame(list(res.get("Dimensionamiento TEMA & Kern", {}).items()), columns=["Parámetro TEMA / Kern", "Valor Calculado"]), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(pd.DataFrame(list(res.get("Verificación Convectiva (Rating Kern)", {}).items()), columns=["Variable de Convección (Kern)", "Resultado"]), use_container_width=True, hide_index=True)
        with tab3:
            st.dataframe(pd.DataFrame(list(res.get("Hidráulica y Caída de Presión (Kern)", {}).items()), columns=["Variable Hidráulica", "Resultado [bar / m/s]"]), use_container_width=True, hide_index=True)
        with tab4:
            st.dataframe(pd.DataFrame(list(res.get("Diseño Mecánico ASME BPVC", {}).items()), columns=["Parámetro Mecánico ASME", "Especificación / Valor"]), use_container_width=True, hide_index=True)
        with tab5:
            st.dataframe(pd.DataFrame(list(res.get("Termodinámica", {}).items()), columns=["Variable de Proceso", "Valor Operativo"]), use_container_width=True, hide_index=True)
        with tab6:
            st.markdown("### Análisis Longitudinal de Severidad Térmica y Película")
            generar_grafico_perfil_pasos(res)

    except ValueError as err_f:
        st.error(f"🚨 **Alerta de Inviabilidad:** {err_f}")

# ==============================================================================
# MODO 2: OPTIMIZADOR E INTELIGENCIA DE CATÁLOGO (GRID SEARCH)
# ==============================================================================
else:
    st.subheader("🚀 Selección Inteligente de Equipos (Grid Search Multicriterio)")
    st.markdown("El motor evalúa combinaciones de tipos TEMA y geometrías aplicando **criterios hidráulicos ($\Delta P$) y técnico-económicos ASME**.")

    try:
        df_grid, top_rec = optimizar_intercambiador(
            m_cal_kg_s=m_cal, T_cal_in=T_cal_in, T_cal_out=T_cal_out,
            P_cal_bar=P_cal_op, T_frio_in=T_frio_in, P_frio_bar=P_frio_op,
            f_cal_nombre=f_cal, f_frio_nombre=f_frio,
            mat_casco=m_casco_sel, mat_tubo=m_tubo_sel,
            asignacion_caliente=asignacion_val
        )

        st.markdown("### 🏆 Top 3 Recomendaciones Tecnológicas de Diseño")
        col_t1, col_t2, col_t3 = st.columns(3)

        with col_t1:
            eco = top_rec.get("Económico", {})
            st.success("💰 **ÓPTIMO ECONÓMICO**")
            st.markdown(f"**TEMA:** `{eco.get('TEMA [-]', 'BEM')}` | **Área:** `{eco.get('Área [m²]', 0)} m²`")
            st.markdown(f"**Casco Ds:** `{eco.get('Casco Ds [mm]', 0)} mm` | **Longitud:** `{eco.get('Longitud [m]', 0)} m`")
            st.markdown(f"**P Diseño Casco/Tubos:** `{eco.get('P Dis Casco [bar]', 0)}` / `{eco.get('P Dis Tubos [bar]', 0)} bar`")
            dp_t_eco = float(eco.get("ΔP Tubos [bar]", 0.01))
            dp_s_eco = float(eco.get("ΔP Casco [bar]", 0.01))
            st.markdown(f"**ΔP Tubos / Casco:** `{dp_t_eco:.3f}` / `{dp_s_eco:.3f} bar`")
            st.markdown(f"**Mg Térmico (Exceso):** `{eco.get('Margen [%]', 0)}%`")
            st.metric("Inversión Estimada", f"${eco.get('CAPEX [USD]', 0):,.2f} USD")

        with col_t2:
            comp = top_rec.get("Compacto", {})
            st.info("📐 **ÓPTIMO COMPACTO**")
            st.markdown(f"**TEMA:** `{comp.get('TEMA [-]', 'BEM')}` | **Área:** `{comp.get('Área [m²]', 0)} m²`")
            st.markdown(f"**Casco Ds:** `{comp.get('Casco Ds [mm]', 0)} mm` | **Longitud:** `{comp.get('Longitud [m]', 0)} m`")
            st.markdown(f"**P Diseño Casco/Tubos:** `{comp.get('P Dis Casco [bar]', 0)}` / `{comp.get('P Dis Tubos [bar]', 0)} bar`")
            dp_t_comp = float(comp.get("ΔP Tubos [bar]", 0.01))
            dp_s_comp = float(comp.get("ΔP Casco [bar]", 0.01))
            st.markdown(f"**ΔP Tubos / Casco:** `{dp_t_comp:.3f}` / `{dp_s_comp:.3f} bar`")
            st.markdown(f"**Mg Térmico (Exceso):** `{comp.get('Margen [%]', 0)}%`")
            st.metric("Inversión Estimada", f"${comp.get('CAPEX [USD]', 0):,.2f} USD")

        with col_t3:
            oper = top_rec.get("Operativo", {})
            st.warning("🛡️ **ÓPTIMO OPERATIVO (API 660 / EDR)**")
            st.markdown(f"**TEMA:** `{oper.get('TEMA [-]', 'BEM')}` | **Área:** `{oper.get('Área [m²]', 0)} m²`")
            st.markdown(f"**Casco Ds:** `{oper.get('Casco Ds [mm]', 0)} mm` | **Longitud:** `{oper.get('Longitud [m]', 0)} m`")
            st.markdown(f"**P Diseño Casco/Tubos:** `{oper.get('P Dis Casco [bar]', 0)}` / `{oper.get('P Dis Tubos [bar]', 0)} bar`")
            dp_t_oper = float(oper.get("ΔP Tubos [bar]", 0.01))
            dp_s_oper = float(oper.get("ΔP Casco [bar]", 0.01))
            st.markdown(f"**ΔP Tubos / Casco:** `{dp_t_oper:.3f}` / `{dp_s_oper:.3f} bar`")
            st.markdown(f"**Mg Térmico (Exceso):** `{oper.get('Margen [%]', 0)}%`")
            st.metric("Inversión Estimada", f"${oper.get('CAPEX [USD]', 0):,.2f} USD")

        mostrar_guia_margen_termico()

        st.divider()
        st.subheader("📈 Análisis y Diagnóstico Dinámico de Película del Modelo Seleccionado")
        opcion_grafico = st.selectbox(
            "Seleccione qué modelo del Top 3 desea inspeccionar en detalle:",
            options=["Económico (Mínimo CAPEX)", "Compacto (Menor Huella)", "Operativo (Máximo Mérito Hidráulico-Económico)"],
            key="sel_grafico_opt"
        )
        if "Económico" in opcion_grafico:
            res_opt_graf = top_rec["Económico"]["_res_full"]
        elif "Compacto" in opcion_grafico:
            res_opt_graf = top_rec["Compacto"]["_res_full"]
        else:
            res_opt_graf = top_rec["Operativo"]["_res_full"]

        generar_grafico_perfil_pasos(res_opt_graf)

        st.divider()
        st.subheader("📥 Exportar Especificaciones del Equipo Optimizado")
        
        opcion_descarga = st.selectbox(
            "Seleccione el modelo recomendado a exportar:",
            options=["Económico (Mínimo CAPEX)", "Compacto (Menor Huella)", "Operativo (Máximo Mérito Hidráulico-Económico)"]
        )

        if "Económico" in opcion_descarga:
            res_opt_seleccionado = top_rec["Económico"]["_res_full"]
            tag_str = f"HEX-OPT-ECO ({top_rec['Económico'].get('TEMA [-]', 'BEM')})"
        elif "Compacto" in opcion_descarga:
            res_opt_seleccionado = top_rec["Compacto"]["_res_full"]
            tag_str = f"HEX-OPT-CMP ({top_rec['Compacto'].get('TEMA [-]', 'BEM')})"
        else:
            res_opt_seleccionado = top_rec["Operativo"]["_res_full"]
            tag_str = f"HEX-OPT-OPR ({top_rec['Operativo'].get('TEMA [-]', 'BEM')})"

        meta_opt = {"tag": tag_str, "proyecto": "OPTIMIZACIÓN DE CATÁLOGO", "revision": "0", "calculado_por": "E. Livingston"}
        
        col_do1, col_do2 = st.columns(2)
        with col_do1:
            st.download_button("📊 Descargar Planilla Calc (.xlsx)", generar_calc_hoja_datos(res_opt_seleccionado, meta_opt), f"Data_Sheet_{tag_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col_do2:
            st.download_button("📄 Descargar PDF Oficial (.pdf)", generar_pdf_hoja_datos(res_opt_seleccionado, meta_opt), f"Data_Sheet_{tag_str}.pdf", mime="application/pdf")

    except ValueError as error_opt:
        st.error(f"🚨 **Sin Soluciones Viables en Catálogo:** {error_opt}")