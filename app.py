import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO

# ========================
# Configuración API
# ========================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# ========================
# Función para generar Word
# ========================
def generar_word(informe, df):
    doc = Document()

    # --- Portada ---
    try:
        doc.add_picture("images/logo.png", width=Inches(1.5))
    except:
        pass

    titulo = doc.add_paragraph("Gemini Assist – Informe Predictivo de Mantenimiento")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(18)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)

    doc.add_paragraph("\n")

    # --- Ranking Top 10 activos ---
    doc.add_paragraph("⚠️ Ranking de Riesgo (Top 10 activos)", style="Heading 2")

    columnas = df.columns.tolist()
    table = doc.add_table(rows=1, cols=len(columnas))
    table.style = "Light Grid Accent 1"

    # Cabecera
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(columnas):
        hdr_cells[i].text = str(col)

    # Filas (top 10)
    for index, row in df.head(10).iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # --- Informe completo ---
    doc.add_paragraph("📊 Informe Detallado", style="Heading 2")
    for linea in informe.split("\n"):
        if linea.strip():
            p = doc.add_paragraph(linea)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            p.style = "Normal"

    # --- Informe Ejecutivo ---
    doc.add_paragraph("\n🏛 Informe Ejecutivo para Dirección", style="Heading 2")
    doc.add_paragraph(
        "Resumen conciso de las medidas prioritarias. Este apartado sintetiza "
        "las acciones inmediatas a realizar sobre los activos críticos para "
        "reducir riesgos, garantizar la continuidad asistencial y optimizar recursos."
    )

    # Guardar en memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ========================
# Interfaz Streamlit
# ========================
st.title("🛠️ Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🤖 Generando informe con Gemini Assist..."):
            tabla_texto = df.head(10).to_string(index=False)

            prompt = f"""
            Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.
            Aquí tienes los datos de activos hospitalarios:
            {tabla_texto}

            Genera un informe con:
            1. Ranking de riesgo de fallo en los próximos 3 meses (top 10).
            2. Acciones preventivas recomendadas.
            3. Estimación de ahorro económico y horas.
            4. Panel de alertas por nivel de riesgo.
            5. Informe ejecutivo (máx 5 líneas) para Dirección.
            """

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            informe = response.text

        st.subheader("📄 Informe generado")
        st.write(informe)

        try:
            word_bytes = generar_word(informe, df)
            st.download_button(
                label="⬇️ Descargar Informe Word",
                data=word_bytes,
                file_name="informe_predictivo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"❌ Error al generar Word: {e}")
