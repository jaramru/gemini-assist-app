import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import datetime
import os

# =======================
# Configuración API (lectura doble)
# =======================
API_KEY = None

# 1. Intentar leer de st.secrets
if "API_KEY" in st.secrets:
    API_KEY = st.secrets["API_KEY"]

# 2. Si no existe, intentar de variables de entorno
elif "API_KEY" in os.environ:
    API_KEY = os.environ["API_KEY"]

# 3. Si no está configurada, mostrar aviso
if not API_KEY:
    st.error("❌ No se encontró la API_KEY. Añádela en Settings → Secrets de Streamlit Cloud.")
else:
    genai.configure(api_key=API_KEY)

st.set_page_config(page_title="Gemini Assist", page_icon="📊", layout="wide")
st.title("📊 Gemini Assist – Informe Predictivo de Mantenimiento")

# =======================
# Subida de archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file is not None and API_KEY:
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
               Bajo riesgo, Riesgo medio, Riesgo alto.
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

            # =======================
            # Crear PDF
            # =======================
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.multi_cell(0, 10, "Gemini Assist - Informe Predictivo de Mantenimiento", align="C")

            pdf.set_font("Arial", size=12)
            pdf.ln(10)

            # Evitar errores por caracteres problemáticos
            informe_limpio = informe.replace("🟢", "Bajo").replace("🟡", "Medio").replace("🔴", "Alto")

            for linea in informe_limpio.split("\n"):
                if linea.strip():
                    pdf.multi_cell(180, 8, linea, align="J")

            pdf_bytes = pdf.output(dest="S").encode("latin1")

            st.download_button(
                label="📥 Descargar Informe en PDF",
                data=pdf_bytes,
                file_name=f"Informe_GeminiAssist_{datetime.date.today()}.pdf",
                mime="application/pdf",
            )

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
