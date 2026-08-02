# ==============================================================================
# ARCHIVO: reporte_pdf.py
# DESCRIPCIÓN: Generador de Hojas de Datos oficiales en formato PDF con 
#              parámetros de Diseño ASME independientes para carcasa y tubos.
# ==============================================================================

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generar_pdf_hoja_datos(res: dict, meta: dict) -> bytes:
    """
    Arma y renderiza una hoja de especificaciones PDF profesional, apta para
    impresión o adjunto en memorias de cálculo de plantas químicas.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos tipográficos institucionales
    estilo_titulo = ParagraphStyle('TituloHoja', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor('#1A365D'), alignment=1, spaceAfter=4)
    estilo_sub = ParagraphStyle('SubHoja', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#4A5568'), alignment=1, spaceAfter=12)
    estilo_celda = ParagraphStyle('TextoCelda', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#2D3748'))
    estilo_celda_bold = ParagraphStyle('TextoCeldaBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#1A365D'))

    story.append(Paragraph("<b>HOJA DE DATOS TÉCNICOS — INTERCAMBIADOR DE CALOR</b>", estilo_titulo))
    story.append(Paragraph(f"Normas: TEMA & ASME | Proyecto: {meta.get('proyecto', 'GENERAL')} | TAG: {meta.get('tag', 'HEX-0100')}", estilo_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1A365D'), spaceBefore=0, spaceAfter=10))

    d_tema = res.get("Dimensionamiento TEMA & Kern", {})
    d_rating = res.get("Verificación Convectiva (Rating Kern)", {})
    d_hidro = res.get("Hidráulica y Caída de Presión (Kern)", {})
    d_asme = res.get("Diseño Mecánico ASME BPVC", {})
    d_termo = res.get("Termodinámica", {})

    datos_tabla = [
        [Paragraph("<b>PARÁMETRO / ESPECIFICACIÓN TÉCNICA</b>", estilo_celda_bold), Paragraph("<b>VALOR OPERATIVO / GEOMÉTRICO</b>", estilo_celda_bold)]
    ]

    bloques = [
        ("--- DIMENSIONAMIENTO TEMA & KERN ---", [
            ("Tipo TEMA", d_tema.get("Tipo TEMA [-]")),
            ("Asignación Lado Carcasa", d_tema.get("Asignación Lado Carcasa")),
            ("Asignación Lado Tubos", d_tema.get("Asignación Lado Tubos")),
            ("Área Requerida Teórica [m²]", d_tema.get("Área Requerida Teórica [m²]")),
            ("Área Instalada Real [m²]", d_tema.get("Área Instalada Real [m²]")),
            ("Diámetro de Casco Ds [mm]", d_tema.get("Diámetro de Casco Ds [mm]")),
            ("Número de Tubos [uds]", d_tema.get("Número de Tubos [uds]")),
            ("Longitud del Tubo [m]", d_tema.get("Longitud del Tubo [m]")),
            ("Pasos por Tubos [uds]", d_tema.get("Pasos por Tubos [uds]"))
        ]),
        ("--- VERIFICACIÓN CONVECTIVA E HIDRÁULICA ---", [
            ("Coef. Global Estimado U_trial [W/m²·K]", d_rating.get("Coef. Global Estimado U_trial [W/m²·K]")),
            ("Coef. Global REAL U_calc [W/m²·K]", d_rating.get("Coef. Global REAL U_calc [W/m²·K]")),
            ("Margen de Seguridad Térmica [%]", d_rating.get("Margen Seguridad Térmica [%]")),
            ("Caída Presión Tubos ΔPt [bar]", d_hidro.get("Caída Presión Tubos ΔPt [bar]")),
            ("Caída Presión Casco ΔPs [bar]", d_hidro.get("Caída Presión Casco ΔPs [bar]"))
        ]),
        ("--- DISEÑO MECÁNICO ASME BPVC (DISEÑO VS OPERACIÓN) ---", [
            ("Material Carcasa / Tubos", f"{d_asme.get('Material Carcasa [-]')} / {d_asme.get('Material Tubos [-]')}"),
            ("Presión Operativa / Diseño Casco [bar]", f"{d_asme.get('Presión Operativa Casco [bar]')} / {d_asme.get('Presión de Diseño Casco [bar]')} bar"),
            ("Temp. Diseño Casco [°C]", f"{d_asme.get('Temp. de Diseño Casco [°C]')} °C"),
            ("Presión Operativa / Diseño Tubos [bar]", f"{d_asme.get('Presión Operativa Tubos [bar]')} / {d_asme.get('Presión de Diseño Tubos [bar]')} bar"),
            ("Temp. Diseño Tubos [°C]", f"{d_asme.get('Temp. de Diseño Tubos [°C]')} °C"),
            ("Espesor Mínimo Casco t_min [mm]", d_asme.get("Espesor Mínimo Casco t_min [mm]")),
            ("CAPEX Estimado [USD]", d_asme.get("CAPEX Estimado [USD]"))
        ]),
        ("--- BALANCE TERMODINÁMICO ---", [
            ("Carga Térmica Q [kW]", d_termo.get("Carga Térmica Q [kW]")),
            ("Caudal Fluido Frío [kg/s]", d_termo.get("Caudal Fluido Frío [kg/s]")),
            ("Temperatura Entrada Frío [°C]", d_termo.get("Temperatura Entrada Frío [°C]")),
            ("Temperatura Salida Frío [°C]", d_termo.get("Temperatura Salida Frío [°C]")),
            ("LMTD Corregida [°C]", d_termo.get("LMTD Corregida [°C]")),
            ("Factor Ft", d_termo.get("Factor Ft [-]"))
        ])
    ]

    for titulo_seccion, items in bloques:
        datos_tabla.append([Paragraph(f"<b>{titulo_seccion}</b>", estilo_celda_bold), Paragraph("", estilo_celda)])
        for k, v in items:
            datos_tabla.append([Paragraph(str(k), estilo_celda), Paragraph(str(v), estilo_celda)])

    tabla_pdf = Table(datos_tabla, colWidths=[280, 260])
    tabla_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDF2F7')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    story.append(tabla_pdf)
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>Revisión:</b> {meta.get('revision', '0')} | <b>Calculado por:</b> {meta.get('calculado_por', 'E. Livingston')}", estilo_sub))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()