import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
import os

# ==============================
# Configuración de la página
# ==============================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", page_icon="🛠️", layout="wide")

# Mostrar logo en la app
st.image("images/logo.png", width=120)
st.title("🛠️ Predictivo de Mantenimiento")

# ==============================
# Configuración API Key
# ==============================
API_KEY = st.secrets.get("API_KEY") or os.getenv("API_KEY")
if not API_KEY:
    st.error("❌ No se encontró la API_KEY. Configúrala en Streamlit Cloud (Secrets) o en el entorno local.")
else:
    genai.configure(api_key=API_KEY)

# ==============================
# Subir archivo Excel
# ==============================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

# ==============================
# Función para generar PDF
# ==============================
class PDF(FPDF):
    def header(self):
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 25)  # Logo en PDF
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Informe Predictivo de Mantenimiento – Gemini Assist", ln=True, align="C")
        self.ln(10)

def generar_pdf(texto):
    pdf = PDF()
    pdf.add_page()

    # Fuentes DejaVu para soporte Unicode
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.set_font("DejaVu", size=12)

    # Contenido
    pdf.multi_cell(0, 10, texto)

    # Guardar PDF en memoria
    pdf_output = BytesIO()
    pdf.output(pdf_output, "S")
    return pdf_output.getvalue()

# ==============================
# Procesar Excel y generar informe
# ==============================
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)  # Ahora muestra todos los registros

    if st.button("Generar Informe"):
        with st.spinner("⏳ Generando el informe con Gemini Assist..."):
            try:
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

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.subheader("📋 Informe Generado")
                st.write(informe)

                # Generar PDF y ofrecer descarga
                pdf_bytes = generar_pdf(informe)
                st.download_button(
                    label="📥 Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name="informe_gemini.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {str(e)}")
