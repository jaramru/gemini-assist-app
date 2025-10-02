import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
import os
from datetime import datetime

# ======================
# CONFIGURACIÓN INICIAL
# ======================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo arriba a la izquierda
st.image("images/logo.png", width=120)
st.title("💡 Gemini Assist – Informe Predictivo de Activos Hospitalarios")

# Clave API desde variables de entorno
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("❌ No se encontró la API KEY. Configúrala en Streamlit Cloud.")
else:
    genai.configure(api_key=API_KEY)

# ======================
# FUNCIÓN → GENERAR WORD
# ======================
def generar_word(informe):
    doc = Document()

    # Portada
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Inches(11.69), Inches(8.27)  # A4 horizontal
    sec.top_margin, sec.bottom_margin = Inches(1), Inches(1)
    sec.left_margin, sec.right_margin = Inches(1), Inches(1)

    doc.add_picture("images/logo.png", width=Inches(2))
    titulo = doc.add_paragraph("Gemini Assist\nInforme de Mantenimiento Predictivo")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(20)
    run.bold = True

    doc.add_paragraph(f"Fecha: {datetime.today().strftime('%d-%m-%Y')}").alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_page_break()

    # Contenido del informe
    for linea in informe.split("\n"):
        linea = linea.strip()
        if not linea:
            continue

        # Títulos
        if linea.startswith("###") or linea.startswith("##") or linea.startswith("**"):
            p = doc.add_paragraph(linea.replace("#", "").replace("**", "").strip())
            p.runs[0].font.size = Pt(14)
            p.runs[0].bold = True
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        # Listas numeradas
        elif linea[0].isdigit() and "." in linea[:4]:
            p = doc.add_paragraph(linea.replace("**", "").strip(), style="List Number")
            p.runs[0].font.size = Pt(11)
        # Texto normal
        else:
            p = doc.add_paragraph(linea.replace("**", "").strip())
            p.runs[0].font.size = Pt(11)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    # Guardar en memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ======================
# SUBIDA DE ARCHIVO
# ======================
uploaded_file = st.file_uploader("📂 Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df)

        if st.button("⚡ Generar Informe", type="primary"):
            with st.spinner("Generando informe con Gemini Assist... ⏳"):
                tabla_texto = df.to_string(index=False)

                prompt = f"""
                Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.
                Analiza la siguiente tabla de activos:

                {tabla_texto}

                Con esta información, genera un informe con los apartados:
                1. Ranking de riesgo de fallo en los próximos 3 meses (top 10 activos).
                2. Acciones preventivas para los 3 activos más críticos.
                3. Estimación de ahorro en € y horas si aplico esas medidas.
                4. Panel de alertas clasificando cada activo en: Bajo, Medio o Alto.
                5. Informe ejecutivo final (máximo 5 líneas).

                ➡️ Importante:
                - NO uses asteriscos ni símbolos raros.
                - Usa títulos claros y texto justificado.
                - Estilo neutro, profesional y en blanco y negro.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                if informe:
                    st.success("✅ Informe generado correctamente")
                    st.text_area("📋 Informe generado:", informe, height=300)

                    # Botón descarga Word
                    word_bytes = generar_word(informe)
                    st.download_button(
                        label="⬇️ Descargar Informe en Word",
                        data=word_bytes,
                        file_name="informe_predictivo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error("⚠️ No se pudo generar el informe, intenta de nuevo.")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
