import streamlit as st
import pandas as pd
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.shared import RGBColor

# =======================
# Configuración API KEY
# =======================
try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = None

if not API_KEY:
    st.error("❌ No se ha encontrado la API_KEY. Añádela en Secrets de Streamlit Cloud.")
else:
    genai.configure(api_key=API_KEY)

# =======================
# Función para generar Word
# =======================
def generar_word(informe, df):
    doc = Document()

    # PORTADA
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    doc.add_heading("Gemini Assist – Informe Predictivo de Mantenimiento", 0)

    # Logo
    try:
        doc.add_picture("images/logo.png", width=Inches(1.5))
    except:
        pass

    doc.add_paragraph("Fecha del Informe:").bold = True

    # Ranking de Riesgo (Top 10 activos)
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
    # Sección de Informe Detallado
    # =======================
    doc.add_heading("📄 Informe Detallado", level=1)

    # Convertir el texto de Gemini en párrafos y títulos
    for linea in informe.split("\n"):
        if linea.strip().startswith("## "):
            doc.add_heading(linea.replace("##", "").strip(), level=2)
        elif linea.strip().startswith("### "):
            doc.add_heading(linea.replace("###", "").strip(), level=3)
        elif linea.strip().startswith("- "):
            p = doc.add_paragraph(linea.replace("- ", "").strip(), style="List Bullet")
            p_format = p.paragraph_format
            p_format.space_after = Pt(6)
        elif linea.strip().startswith("1.") or linea.strip().startswith("2."):
            p = doc.add_paragraph(linea.strip(), style="List Number")
            p_format = p.paragraph_format
            p_format.space_after = Pt(6)
        elif "|" in linea and "---" not in linea:  # Tablas estilo Markdown
            cols = [c.strip() for c in linea.split("|") if c.strip()]
            if cols:
                tbl = doc.add_table(rows=1, cols=len(cols))
                tbl.style = "Medium Shading 1 Accent 1"
                row_cells = tbl.rows[0].cells
                for i, col in enumerate(cols):
                    row_cells[i].text = col
        else:
            if linea.strip():
                p = doc.add_paragraph(linea.strip())
                p_format = p.paragraph_format
                p_format.space_after = Pt(6)

    # Fuente general
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    output = BytesIO()
    doc.save(output)
    return output.getvalue()

# =======================
# Interfaz Streamlit
# =======================
st.title("🛠️ Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
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
                4. Panel de alertas clasificando cada activo en: 🟢 Bajo riesgo, 🟡 Riesgo medio, 🔴 Riesgo alto.
                5. Un informe ejecutivo de máximo 5 líneas para Dirección.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.subheader("📑 Informe Generado")
                st.write(informe)

                # Generar Word profesional
                word_bytes = generar_word(informe, df)

                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
