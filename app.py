import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import datetime

# =======================
# Configuración API
# =======================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="Gemini Assist", page_icon="📊", layout="wide")
st.title("📊 Gemini Assist – Informe Predictivo de Mantenimiento")

# =======================
# Función para generar PDF
# =======================
def generar_pdf(informe_texto):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Gemini Assist - Informe Predictivo de Mantenimiento", ln=True, align="C")

    pdf.set_font("Arial", size=12)
    pdf.ln(10)  # Espacio

    # Dividir el informe en líneas para no cortar texto
    for linea in informe_texto.split("\n"):
        pdf.multi_cell(0, 10, linea)

    # Guardar en memoria como bytes
    return pdf.output(dest="S").encode("latin1")

# =======================
# Subida de archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df.head())

        if st.button("Generar Informe"):
            tabla_texto = df.head(10).to_string(index=False)

            prompt = f"""
            Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.

            Aquí tienes los datos de activos hospitalarios:
            {tabla_texto}

            Con esta tabla, necesito que hagas lo siguiente:
            1. Ranking de riesgo de fallo en los próximos 3 meses (de mayor a menor).
            2. Acciones preventivas para los 3 activos más críticos.
            3. Estimación de ahorro en € y horas si aplico esas medidas.
            4. Panel de alertas clasificando cada activo en:
               🟢 Bajo riesgo, 🟡 Riesgo medio, 🔴 Riesgo alto.
            5. Un informe ejecutivo de máximo 5 líneas para Dirección.
            """

            with st.spinner("⏳ Generando informe con Gemini..."):
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)

                try:
                    informe = response.text
                except:
                    informe = response.candidates[0].content.parts[0].text

            st.subheader("📑 Informe generado")
            st.write(informe)

            # Botón para descargar PDF
            pdf_bytes = generar_pdf(informe)
            fecha = datetime.date.today().strftime("%Y-%m-%d")

            st.download_button(
                label="📥 Descargar Informe en PDF",
                data=pdf_bytes,
                file_name=f"Informe_GeminiAssist_{fecha}.pdf",
                mime="application/pdf",
            )

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
