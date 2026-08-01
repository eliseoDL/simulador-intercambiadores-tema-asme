# ==============================================================================
# ARCHIVO: reporte_pdf.py
# DESCRIPCIÓN: Módulo de generación de reportes técnicos inmutables en PDF,
#              con claves unificadas en formato de corchetes [...].
# ==============================================================================

import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generar_pdf_hoja_datos(res_dict, meta_dict=None):
    if meta_dict is None:
        meta_dict = {}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=0.5 * inch, leftMargin=0.5 * inch,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloDataSheet', parent=styles['Heading1'],
        fontSize=11.5, leading=14, textColor=colors.HexColor("#0F2942"),
        fontName="Helvetica-Bold", alignment=1
    )
    texto_celda = ParagraphStyle('TxtC', fontSize=7.2, leading=9.5, fontName="Helvetica", textColor=colors.HexColor("#1A202C"))
    texto_bold = ParagraphStyle('TxtB', fontSize=7.2, leading=9.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#1A202C"))
    texto_head_sec = ParagraphStyle('HeadSec', fontSize=7.8, leading=10.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#FFFFFF"))

    fecha_hoy = datetime.date.today().strftime("%d/%m/%Y")
    tag_str = meta_dict.get("tag", "HEX-0100")
    proy_str = meta_dict.get("proyecto", "PROYECTO GENERAL")
    rev_str = meta_dict.get("revision", "0 - EMISIÓN INICIAL")

    header_data = [
        [
            Paragraph("<b>TEMA EQUIPMENT DATA SHEET</b><br/>HOJA DE ESPECIFICACIÓN TÉCNICA - INTERCAMBIADOR", titulo_style),
            Paragraph(f"<b>TAG NO [-]:</b> {tag_str}<br/><b>REV [-]:</b> {rev_str}<br/><b>PÁG [-]:</b> 1 de 1", texto_celda)
        ],
        [
            Paragraph(f"<b>TIPO TEMA [-]:</b> {res_dict['Dimensionamiento TEMA & Kern']['Clasificación TEMA [-]']} | <b>PROYECTO [-]:</b> {proy_str}", texto_bold),
            Paragraph(f"<b>FECHA [-]:</b> {fecha_hoy}<br/><b>ESTÁNDAR [-]:</b> TEMA / ASME VIII", texto_celda)
        ]
    ]
    tabla_header = Table(header_data, colWidths=[5.3 * inch, 1.9 * inch])
    tabla_header.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#0F2942")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#A0AEC0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_header)
    elementos.append(Spacer(1, 6))

    def crear_bloque_seccion(titulo_seccion, filas_datos):
        tabla_datos = [[Paragraph(f"<b>{titulo_seccion.upper()}</b>", texto_head_sec), ""]]
        for k1, v1, k2, v2 in filas_datos:
            tabla_datos.append([
                Paragraph(f"<b>{k1}:</b>", texto_bold), Paragraph(str(v1), texto_celda),
                Paragraph(f"<b>{k2}:</b>", texto_bold) if k2 else "", Paragraph(str(v2), texto_celda) if v2 else ""
            ])
        t = Table(tabla_datos, colWidths=[2.25 * inch, 1.35 * inch, 2.25 * inch, 1.35 * inch])
        t.setStyle(TableStyle([
            ('SPAN', (0, 0), (3, 0)),
            ('BACKGROUND', (0, 0), (3, 0), colors.HexColor("#1A365D")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#2D3748")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#EDF2F7")),
            ('BACKGROUND', (2, 1), (2, -1), colors.HexColor("#EDF2F7")),
        ]))
        return t

    # 1. TERMODINÁMICA
    t = res_dict["Termodinámica"]
    f_termo = [
        ("Carga Térmica Total [kW]", t["Carga Térmica Total [kW]"], "LMTD Contracorriente [°C]", t["LMTD Contracorriente [°C]"]),
        ("Caudal Proceso Lado Caliente [kg/s]", t["Caudal Fluido Proceso [kg/s]"], "Caudal Servicio Auxiliar [kg/s]", t["Caudal Servicio Auxiliar [kg/s]"]),
        ("Temp. Entrada Caliente [°C]", t["Temp. Entrada Caliente [°C]"], "Temp. Salida Caliente [°C]", t["Temp. Salida Caliente [°C]"]),
        ("Temp. Entrada Frío [°C]", t["Temp. Entrada Frío [°C]"], "Temp. Salida Frío [°C]", t["Temp. Salida Frío [°C]"]),
        ("Factor Corrección Ft [-]", t["Factor Corrección Ft [-]"], "LMTD Efectiva Real [°C]", t["LMTD Efectiva [°C]"])
    ]
    elementos.append(crear_bloque_seccion("1. Condiciones Operativas y Balance Térmico (CoolProp / IF97)", f_termo))
    elementos.append(Spacer(1, 5))

    # 2. GEOMETRÍA TEMA
    d = res_dict["Dimensionamiento TEMA & Kern"]
    f_tema = [
        ("Clasificación Normativa TEMA [-]", d["Clasificación TEMA [-]"], "Pasos por Tubo [uds]", d["Pasos por Tubo [uds]"]),
        ("Área Requerida Teórica [m²]", d["Área Requerida Teórica [m²]"], "Área Instalada Real [m²]", d["Área Instalada Real [m²]"]),
        ("Número Total de Tubos [uds]", d["Número Total de Tubos [uds]"], "Diámetro Exterior Tubo OD [mm]", d["Diámetro Ext. Tubo OD [mm]"]),
        ("Diámetro Interno Casco Ds [mm]", d["Diámetro Interno Casco Ds [mm]"], "Longitud Nominal Tubos [m]", d["Longitud Nominal Tubo [m]"]),
        ("Espaciado de Bafles B [mm]", d["Espaciado de Bafles B [mm]"], "Número de Bafles [uds]", d["Número de Bafles [uds]"])
    ]
    elementos.append(crear_bloque_seccion("2. Dimensionamiento Geométrico (Sinnott Cap. 12 / Método de Kern)", f_tema))
    elementos.append(Spacer(1, 5))

    # 3. VERIFICACIÓN CONVECTIVA
    r = res_dict["Verificación Convectiva (Rating Kern)"]
    f_rating = [
        ("Coef. Estimado de Prueba U_trial [W/m²·K]", r["Coef. Global Estimado U_trial [W/m²·K]"], "Coef. Convectivo Casco h_o [W/m²·K]", r["Coef. Convectivo Casco h_o [W/m²·K]"]),
        ("Coef. Convectivo Tubos h_i [W/m²·K]", r["Coef. Convectivo Tubos h_i [W/m²·K]"], "Coef. Global REAL U_calc [W/m²·K]", r["Coef. Global REAL U_calc [W/m²·K]"]),
        ("Margen Seguridad Térmica [%]", f'{r["Margen Seguridad Térmica [%]"]} %', "Ensuciamiento Normado Rf [m²·K/W]", r["Resistencia Ensuciamiento Rf [m²·K/W]"])
    ]
    elementos.append(crear_bloque_seccion("3. Verificación Convectiva y Sizing vs. Rating (Sinnott Cap. 12.9)", f_rating))
    elementos.append(Spacer(1, 5))

    # 4. MECÁNICA ASME BPVC VIII & MATERIALES
    m = res_dict["Diseño Mecánico ASME BPVC"]
    f_mech = [
        ("Código Diseño Mecánico [-]", "ASME BPVC Sec. VIII Div. 1", "Presión Diseño ASME [bar]", m["Presión Diseño ASME [bar]"]),
        ("Material Carcasa / Casco [-]", m["Material Carcasa [-]"], "Material de los Tubos [-]", m["Material Tubos [-]"]),
        ("Tensión Adm. Carcasa S [MPa]", m["Tensión Adm. Carcasa S [MPa]"], "Tensión Adm. Tubos S [MPa]", m["Tensión Adm. Tubos S [MPa]"]),
        ("Conductividad Tubo k [W/m·K]", m["Conductividad Tubo k [W/m·K]"], "Sobreespesor Corrosión [mm]", m["Sobreespesor Corrosión [mm]"]),
        ("Espesor Comercial Casco [mm]", m["Espesor Casco Comercial [mm]"], "Espesor Tubos BWG [mm]", m["Espesor Tubo Comercial BWG [mm]"]),
        ("Inversión CAPEX [USD]", f"${m['CAPEX Estimado [USD]']:,.2f}", "Metodología CAPEX [-]", "Sinnott Cap. 6 (Class 4/5)")
    ]
    elementos.append(crear_bloque_seccion("4. Diseño Mecánico, Materiales y Presupuesto Económico (ASME VIII / Sinnott Cap. 6)", f_mech))
    elementos.append(Spacer(1, 8))

    # 5. FIRMAS
    c_str = meta_dict.get("calculado_por", "E. Livingston")
    r_str = meta_dict.get("revisado_por", "____________________")
    a_str = meta_dict.get("aprobado_por", "____________________")
    df_firma = [[
        Paragraph(f"<b>CALCULADO POR [-]:</b><br/>{c_str}", texto_celda),
        Paragraph(f"<b>REVISADO POR [-]:</b><br/>{r_str}", texto_celda),
        Paragraph(f"<b>APROBADO POR [-]:</b><br/>{a_str}", texto_celda)
    ]]
    t_firma = Table(df_firma, colWidths=[2.4 * inch, 2.4 * inch, 2.4 * inch])
    t_firma.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#718096")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC"))
    ]))
    elementos.append(t_firma)

    doc.build(elementos)
    buffer.seek(0)
    return buffer