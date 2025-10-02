import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import os

# ==============================
# CONFIGURACIÓN DE LA APP
# ==============================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", layout="centered")

# Logo y título en la interfaz
st.image("images/logo.png", width=120)
st.markdown("<h1 style='color:#2E86C1;'>🔧 Predictivo de Mantenimiento</h1>", unsafe_allow_html=True)

# Inicializamos la variable informe para evitar NameError
informe = None

# ==============================
# CONFIGURACIÓN DE LA API
# ==============================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# ==============================
# FUNCIÓN PARA CREAR PDF
# ==============================
class PDF(FPDF):
    def header(self):
        # Logo arriba a la izquierda
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 20)
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Gemini Assist – Informe de Mantenimiento Predictivo", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

def generar_pdf(informe_texto):
    pdf = PDF()
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)

    pdf.set_font("DejaVu", "B", 16)
    pdf.add_page()

    # Portada
    pdf.cell(0, 10, "📊 Informe Predictivo de Mantenimiento", ln=True, align="C")
    pdf.ln(20)

    # Contenido
    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 10, informe_texto)

    return pdf.output(dest="S").encode("latin-1")

# ==============================
# SUBIDA DE ARCHIVO EXCEL
# ==============================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df.head())

    if st.button("🚀 Generar Informe"):
        with st.spinner("🔄 Procesando el informe, espera unos segundos..."):
            # Convertir tabla a texto para Gemini
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

            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                st.success("✅ Informe generado con éxito")
                st.markdown("### 📄 Informe")
                st.write(informe)

            except Exception as e:
                st.error(f"❌ Error al generar el informe: {e}")

# ==============================
# BOTÓN DE DESCARGA PDF
# ==============================
if informe:
    try:
        pdf_file = generar_pdf(informe)
        st.download_button(
            label="⬇️ Descargar Informe PDF",
            data=pdf_file,
            file_name="Informe_GeminiAssist.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
