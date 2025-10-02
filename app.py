import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
import os

# =======================
# Configuración inicial
# =======================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Mostrar logo arriba
try:
    st.image("images/logo.png", width=200)
except:
    st.warning("⚠️ No se encontró el logo en la carpeta 'images/'.")

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")

# Configuración de Gemini API
genai.configure(api_key=st.secrets["API_KEY"])


# =======================
# Función para generar Word
# =======================
def generar_word(informe, df):
    doc = Document()

    # Portada
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    try:
        doc.add_picture("images/logo.png", width=Inches(2))
    except:
        pass

    titulo = doc.add_paragraph("Gemini Assist\nInforme Predictivo de Mantenimiento")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(20)
    run.bold = True

    doc.add_page_break()

    # Ranking tabla
    doc.add_heading("📊 Ranking de Riesgo (Top 10 activos)", level=1)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"

    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        run = hdr_cells[i].paragraphs[0].add_run(str(col))
        run.bold = True

    for _, row in df.head(10).iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # Informe Detallado
    doc.add_heading("📄 Informe Detallado", level=1)

    for line in informe.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("### "):  # Encabezado nivel 2
            doc.add_heading(line.replace("### ", "").strip(), level=2)
        elif line.startswith("**") and line.endswith("**"):  # Negritas solas
            p = doc.add_paragraph()
            run = p.add_run(line.replace("**", ""))
            run.bold = True
        elif "|" in line and "---" not in line:  # Línea de tabla tipo markdown
            cols = [c.strip() for c in line.split("|") if c.strip()]
            table = doc.add_table(rows=1, cols=len(cols))
            table.style = "Table Grid"
            row_cells = table.rows[0].cells
            for i, val in enumerate(cols):
                row_cells[i].text = val
        else:
            doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# =======================
# Subir archivo Excel
# =======================
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

                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.subheader("📄 Informe Generado")
                st.markdown(informe)

                # Botón descarga Word
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
