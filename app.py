import streamlit as st
import pandas as pd
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

# ==========================
# Configuración inicial
# ==========================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", layout="wide")

genai.configure(api_key=st.secrets["API_KEY"])

# ==========================
# Función para generar Word
# ==========================
def generar_word(informe, df):
    doc = Document()

    # Portada
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    if "images/logo.png":
        try:
            doc.add_picture("images/logo.png", width=Inches(2))
        except:
            pass

    titulo = doc.add_paragraph("Gemini Assist\nInforme Predictivo de Mantenimiento")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    titulo.runs[0].font.size = Pt(20)
    titulo.runs[0].font.bold = True

    doc.add_page_break()

    # Ranking tabla
    doc.add_heading("📊 Ranking de Riesgo (Top 10 activos)", level=1)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"

    # Encabezados
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        run = hdr_cells[i].paragraphs[0].add_run(str(col))
        run.bold = True

    # Filas (máx 10)
    for index, row in df.head(10).iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # Informe detallado
    doc.add_heading("📄 Informe Detallado", level=1)
    doc.add_paragraph(informe)

    # Guardar en memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================
# Interfaz Streamlit
# ==========================
st.title("🔧 Gemini Assist – Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("📂 Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                # Convertir tabla en texto
                tabla_texto = df.head(10).to_string(index=False)

                # Prompt a Gemini
                prompt = f"""
                Soy Gemini Assist, experto en mantenimiento hospitalario.
                Aquí tienes los datos de los activos:
                {tabla_texto}

                Genera un informe con:
                1. Ranking de riesgo de fallo en los próximos 3 meses (máx 10 activos).
                2. Acciones preventivas para los activos críticos.
                3. Estimación de ahorro (€ y horas).
                4. Panel de alertas por colores (🟢 bajo, 🟡 medio, 🔴 alto).
                5. Un informe ejecutivo de máximo 5 líneas para Dirección.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.subheader("📊 Informe generado")
                st.write(informe)

                # Generar Word
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")

