import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
import os

# =======================
# Configuración API KEY
# =======================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# =======================
# Clase PDF personalizada
# =======================
class PDF(FPDF):
    def header(self):
        # Logo si existe
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 25)
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Informe Predictivo de Mantenimiento – Gemini Assist", ln=True, align="C")
        self.ln(10)

def generar_pdf(texto):
    pdf = PDF()
    pdf.add_page()

    # Registrar fuentes DejaVu
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)

    # Texto normal
    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 10, texto)

    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin1")  # Exportar en bytes
    pdf_output.write(pdf_bytes)
    return pdf_output.getvalue()

# =======================
# Interfaz Streamlit
# =======================
st.set_page_config(page_title="Gemini Assist", layout="centered")

st.title("🔧 Predictivo de Mantenimiento")

# Logo arriba en la app
if os.path.exists("images/logo.png"):
    st.image("images/logo.png", width=120)

# =======================
# Subida de archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df.head())

    if st.button("Generar Informe"):
        with st.spinner("⏳ Generando informe con Gemini Assist..."):
            try:
                # Convertir tabla a texto para el prompt
                tabla_texto = df.to_string(index=False)

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
                informe = response.text

                # Mostrar en la app
                st.subheader("📄 Informe Generado")
                st.write(informe)

                # Botón de descarga
                pdf_bytes = generar_pdf(informe)
                st.download_button(
                    label="⬇️ Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name="informe_predictivo.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
