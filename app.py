import re
from io import BytesIO
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

def generar_word(informe, df):
    doc = Document()

    # =======================
    # PORTADA
    # =======================
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo centrado
    try:
        p = doc.add_paragraph()
        run = p.add_run()
        run.add_picture("images/logo.png", width=Inches(2))
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except:
        pass

    # Título
    titulo = doc.add_paragraph("Gemini Assist")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 51, 153)  # Azul corporativo

    subtitulo = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    subtitulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = subtitulo.runs[0]
    run.font.size = Pt(16)
    run.font.italic = True

    # Fecha
    fecha = datetime.now().strftime("%d/%m/%Y")
    fecha_p = doc.add_paragraph(f"Fecha del Informe: {fecha}")
    fecha_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = fecha_p.runs[0]
    run.font.size = Pt(12)

    # Salto de página
    doc.add_page_break()

    # =======================
    # Ranking (Top 10 activos)
    # =======================
    doc.add_heading("⚠️ Ranking de Riesgo (Top 10 activos)", level=1)
    top10 = df.head(10)

    table = doc.add_table(rows=1, cols=len(top10.columns))
    table.style = "Light List Accent 1"

    hdr_cells = table.rows[0].cells
    for i, col in enumerate(top10.columns):
        hdr_cells[i].text = col

    for _, row in top10.iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # =======================
    # Parseo del informe Gemini
    # =======================
    doc.add_heading("📄 Informe Detallado", level=1)

    lineas = informe.split("\n")
    tabla_buffer = []
    dentro_tabla = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        # Quitar separadores Markdown
        if linea.startswith("---") or linea.startswith("```"):
            continue

        # Encabezados
        if linea.startswith("### "):
            doc.add_heading(linea[4:].strip(), level=3)
        elif linea.startswith("## "):
            doc.add_heading(linea[3:].strip(), level=2)
        elif linea.startswith("# "):
            doc.add_heading(linea[2:].strip(), level=1)

        # Listas
        elif linea.startswith(("- ", "* ")):
            doc.add_paragraph(_procesar_negritas(linea[2:].strip()), style="List Bullet")
        elif re.match(r"^\d+\.", linea):
            doc.add_paragraph(_procesar_negritas(linea), style="List Number")

        # Tablas Markdown
        elif "|" in linea:
            if "---" in linea:
                continue
            cols = [c.strip() for c in linea.split("|") if c.strip()]
            if not dentro_tabla:
                dentro_tabla = True
                tabla_buffer = [cols]
            else:
                tabla_buffer.append(cols)
        else:
            # Cerrar tabla si había
            if dentro_tabla and tabla_buffer:
                tbl = doc.add_table(rows=1, cols=len(tabla_buffer[0]))
                tbl.style = "Medium Shading 1 Accent 1"
                hdr_cells = tbl.rows[0].cells
                for i, col in enumerate(tabla_buffer[0]):
                    hdr_cells[i].text = col
                for row in tabla_buffer[1:]:
                    row_cells = tbl.add_row().cells
                    for i, col in enumerate(row):
                        row_cells[i].text = col
                tabla_buffer = []
                dentro_tabla = False

            # Texto normal con negritas
            doc.add_paragraph(_procesar_negritas(linea))

    # Estilo general
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    output = BytesIO()
    doc.save(output)
    return output.getvalue()


# =======================
# Auxiliar para negritas
# =======================
def _procesar_negritas(texto):
    partes = re.split(r"(\*\*.*?\*\*)", texto)
    from docx import Document
    temp_doc = Document()
    p = temp_doc.add_paragraph()
    for parte in partes:
        if parte.startswith("**") and parte.endswith("**"):
            run = p.add_run(parte[2:-2])
            run.bold = True
        else:
            p.add_run(parte)
    return p.text
