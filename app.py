import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
import re
from datetime import datetime

# ==============================
# Función para limpiar el texto
# ==============================
def limpiar_texto(texto):
    """Elimina asteriscos y formato Markdown del texto generado."""
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # negritas
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)  # viñetas tipo *
    texto = texto.replace("*", "")  # asteriscos sueltos
    return texto.strip()

# ==============================
# Generar Word con estilo neutro
# ==============================
def generar_word(informe, df):
    # Limpieza aquí 👇
    informe_limpio = limpiar_texto(informe)

    doc = Document()

    # ---------- PORTADA ----------
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

    # Título principal
    titulo = doc.add_paragraph("Gemini Assist")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)

    # Subtítulo
    subtitulo = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    subtitulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = subtitulo.runs[0]
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(100, 100, 100)

    # Fecha
    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = fecha.runs[0]
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # ---------- RANKING TABLA ----------
    doc.add_heading("📊 Ranking de Riesgo (Top 10 activos)", level=1)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"

    # Cabecera
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        run = hdr_cells[i].paragraphs[0].add_run(str(col))
        run.bold = True

    # Filas (máx 10)
    for _, row in df.head(10).iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # ---------- INFORME DETALLADO ----------
    doc.add_heading("📄 Informe Detallado", level=1)

    for linea in informe_limpio.split("\n"):
        if not linea.strip():
            continue

        if linea.startswith("### "):
            doc.add_heading(linea.replace("### ", "").strip(), level=2)
        elif linea.startswith("## "):
            doc.add_heading(linea.replace("## ", "").strip(), level=3)
        elif re.match(r"^\d+\.", linea.strip()):
            # Listas numeradas
            p = doc.add_paragraph(linea.strip(), style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        elif linea.startswith("- "):
            # Bullets
            p = doc.add_paragraph(linea.replace("- ", ""), style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        else:
            # Párrafo normal justificado
            p = doc.add_paragraph(linea.strip())
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            run = p.runs[0]
            run.font.size = Pt(11)
            run.font.name = "Calibri"

    # ---------- EXPORTAR ----------
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================
# Interfaz Streamlit
# ==============================
st.set_page_config(page_title="Gemini Assist", layout="wide")

try:
    st.image("images/logo.png", width=150)
except:
    st.write("")

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("📂 Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("🚀 Generar Informe"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                tabla_texto = df.head(10).to_string(index=False)

                prompt = f"""
                Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.

                Aquí tienes los datos de activos hospitalarios:
                {tabla_texto}

                Con esta tabla, necesito que hagas lo siguiente:
                1. Ranking de riesgo de fallo en los próximos 3 meses (máx 10 activos).
                2. Acciones preventivas para los 3 activos más críticos.
                3. Estimación de ahorro en € y horas si aplico esas medidas.
                4. Panel de alertas clasificando cada activo en:
                   🟢 Bajo riesgo, 🟡 Riesgo medio, 🔴 Riesgo alto.
                5. Un informe ejecutivo de máximo 5 líneas para Dirección.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                informe_limpio = limpiar_texto(informe)

                st.subheader("📋 Informe Generado")
                st.write(informe_limpio)

                # Botón de descarga Word (ya usa texto limpio dentro)
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
