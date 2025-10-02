import streamlit as st
import pandas as pd
from fpdf import FPDF
import google.generativeai as genai
from datetime import datetime
import os
import io

# ========================
# Configuración inicial
# ========================
st.set_page_config(page_title="Gemini Assist - Informe Predictivo de Mantenimiento", layout="centered")

# Mostrar logo en la app
if os.path.exists("images/logo.png"):
    st.image("images/logo.png", width=120)

st.title("🔧 Predictivo de Mantenimiento")

# Configuración de API KEY desde secrets
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# ========================
# Clase PDF
# ========================
class PDF(FPDF):
    def header(self):
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 25)
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Gemini Assist - Informe de Mantenimiento Predictivo", border=False, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# ========================
# Función generar PDF
# ========================
def generar_pdf(informe):
    pdf = FPDF()
    pdf.add_page()

    # Registrar fuentes DejaVu (asegúrate de tenerlas en el repo)
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)
    pdf.add_font("DejaVu", "BI", "DejaVuSans-BoldOblique.ttf", uni=True)

    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Gemini Assist – Informe de Mantenimiento Predictivo", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 10, informe)

    # Guardar en memoria
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer, "F")  # "F" para escribir en el buffer
    pdf_buffer.seek(0)
    return pdf_buffer

# Mostrar botón de descarga en Streamlit
if informe:
    pdf_file = generar_pdf(informe)
    st.download_button(
        label="⬇️ Descargar Informe PDF",
        data=pdf_file,
        file_name="Informe_GeminiAssist.pdf",
        mime="application/pdf"
    )


# ========================
# Subir archivo Excel
# ========================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🔄 Generando informe, por favor espera..."):
            # Convertir tabla a texto para el prompt
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

                # Mostrar informe en la app
                st.subheader("📋 Informe Generado")
                st.write(informe)

                # Generar PDF
                pdf_bytes = generar_pdf(informe)

                # Botón de descarga
                st.download_button(
                    label="📥 Descargar Informe en PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_GeminiAssist_{datetime.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
