import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import io

# ========================
# Configuración de la app
# ========================
st.set_page_config(page_title="Gemini Assist – Informe Predictivo de Mantenimiento", layout="centered")
st.title("📊 Gemini Assist – Informe Predictivo de Mantenimiento")

# ========================
# API Key desde Streamlit Cloud
# ========================
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("❌ No se encontró la API_KEY en los Secrets de Streamlit.")
    st.stop()

genai.configure(api_key=API_KEY)

# ========================
# Subida de archivo Excel
# ========================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
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

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        informe = response.text

        st.subheader("📑 Informe generado")
        st.write(informe)

        # ========================
        # Botón de descarga PDF
        # ========================
        if st.button("📥 Descargar Informe PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            pdf.set_font("DejaVu", size=12)
            pdf.multi_cell(0, 10, informe)

            pdf_output = io.BytesIO()
            pdf.output(pdf_output, "F")
            pdf_output.seek(0)

            st.download_button(
                label="📥 Descargar Informe en PDF",
                data=pdf_output,
                file_name="Informe_GeminiAssist.pdf",
                mime="application/pdf"
            )
