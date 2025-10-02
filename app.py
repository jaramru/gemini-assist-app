import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO

# ==========================
# Función para generar Word
# ==========================
def generar_word(informe, df):
    doc = Document()

    # --- Portada ---
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    if "images/logo.png":
        try:
            doc.add_picture("images/logo.png", width=Inches(1.5))
        except:
            pass

    titulo = doc.add_paragraph("Gemini Assist – Informe Predictivo de Mantenimiento")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(20)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)

    doc.add_paragraph("\n")

    # --- Introducción ---
    p = doc.add_paragraph("📑 Introducción\n")
    p.runs[0].bold = True
    doc.add_paragraph(
        "Este informe ha sido generado automáticamente por Gemini Assist. "
        "Analiza los activos hospitalarios para identificar riesgos inminentes, "
        "proponer acciones preventivas y ofrecer una visión ejecutiva clara."
    )

    # --- Ranking de Riesgo en tabla ---
    doc.add_paragraph("\n⚠️ Ranking de Riesgo (Top activos)\n").runs[0].bold = True
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Light Grid Accent 1"

    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr_cells[i].text = str(col)

    for index, row in df.iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    # --- Informe generado por Gemini ---
    doc.add_paragraph("\n📊 Informe Detallado\n").runs[0].bold = True
    doc.add_paragraph(informe, style="Normal").alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    # --- Informe ejecutivo ---
    doc.add_paragraph("\n🏛 Informe Ejecutivo para Dirección\n").runs[0].bold = True
    doc.add_paragraph(
        "Resumen conciso y estratégico para la toma de decisiones. "
        "Enfatiza la prioridad de las intervenciones preventivas en los activos críticos."
    )

    # Guardar en memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================
# Streamlit App
# ==========================
st.title("🛠️ Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                # Prompt básico
                tabla_texto = df.to_string(index=False)
                prompt = f"""
                Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.

                Aquí tienes los datos:
                {tabla_texto}

                Haz lo siguiente:
                1. Ranking de riesgo (de mayor a menor).
                2. Acciones preventivas recomendadas.
                3. Estimación de ahorro.
                4. Panel de alertas por nivel de riesgo.
                5. Un informe ejecutivo en 5 líneas para Dirección.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.success("✅ Informe generado con éxito")
                st.markdown(informe)

                # Descargar en Word
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
