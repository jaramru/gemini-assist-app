import streamlit as st
import pandas as pd
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches, RGBColor
import re

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

    # Portada
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    doc.add_heading("Gemini Assist – Informe Predictivo de Mantenimiento", 0)

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
    # Procesar texto del informe
    # =======================
    doc.add_heading("📄 Informe Detallado", level=1)

    lineas = informe.split("\n")
    tabla_buffer = []
    dentro_tabla = False

    for linea in lineas:
        if not linea.strip():
            continue

        # Encabezados
        if linea.startswith("## "):
            doc.add_heading(linea.replace("##", "").strip(), level=2)
        elif linea.startswith("### "):
            doc.add_heading(linea.replace("###", "").strip(), level=3)

        # Listas
        elif linea.startswith("- "):
            doc.add_paragraph(linea[2:].strip(), style="List Bullet")
        elif re.match(r"^\d+\.", linea.strip()):
            doc.add_paragraph(linea.strip(), style="List Number")

        # Tablas tipo Markdown
        elif "|" in linea:
            if "---" in linea:  # separador de tabla
                continue
            cols = [c.strip() for c in linea.split("|") if c.strip()]
            if not dentro_tabla:
                dentro_tabla = True
                tabla_buffer = [cols]
            else:
                tabla_buffer.append(cols)
        else:
            # Si veníamos construyendo tabla, la cerramos
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
            # Texto normal
            doc.add_paragraph(linea.strip())

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
