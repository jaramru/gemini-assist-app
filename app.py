import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import io

# ========================
# Configuración
# ========================
st.set_page_config(page_title="Gemini Assist – Informe Predictivo de Mantenimiento", layout="centered")
st.title("📊 Predictivo de Mantenimiento")

# ========================
# API Key
# ========================
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("❌ No se encontró la API_KEY en los Secrets de Streamlit.")
    st.stop()

genai.configure(api_key=API_KEY)

# ========================
# Subida de archivo
# ========================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        try:
            # Convertimos la tabla a texto
            tabla_texto = df.to_string(index=False)

            # Prompt
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

            # Llamada a Gemini
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)

            # Guardamos el informe en session_state
            st.session_state["informe"] = response.text

        except Exception as e:
            st.error(f"❌ Error al generar informe: {e}")

# ========================
# Mostrar informe
# ========================
if "informe" in st.session_state:
    st.subheader("📑 Informe generado")
    st.write(st.session_state["informe"])

    # ========================
    # Descargar en PDF
    # ========================
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", size=12)
    pdf.multi_cell(0, 10, st.session_state["informe"])

    pdf_output = io.BytesIO()
    pdf.output(pdf_output, "F")
    pdf_output.seek(0)

    st.download_button(
        label="📥 Descargar Informe PDF",
        data=pdf_output,
        file_name="Informe_GeminiAssist.pdf",
        mime="application/pdf"
    )
