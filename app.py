import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from datetime import datetime
from io import BytesIO
import os

# =======================
# Configuración de la API
# =======================
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("❌ No se encontró la API_KEY. Configúrala en Secrets de Streamlit Cloud.")
else:
    genai.configure(api_key=API_KEY)

# =======================
# Clase PDF con logo
# =======================
class PDF(FPDF):
    def header(self):
        if hasattr(self, "logo_path") and self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 8, 25)  # Logo en esquina superior izquierda
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Gemini Assist – Informe Predictivo de Mantenimiento", border=False, ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# =======================
# Función para generar PDF
# =======================
def generar_pdf(informe, logo_path=None, tabla=None):
    pdf = PDF()
    pdf.logo_path = logo_path
    pdf.add_page()

    # Cargar fuentes Unicode
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)

    # --- Portada con logo ---
    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=75, y=30, w=60)  # Logo centrado
        pdf.ln(80)

    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Gemini Assist", ln=True, align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, "Informe Predictivo de Mantenimiento Hospitalario", ln=True, align="C")
    pdf.ln(20)
    pdf.cell(0, 10, f"Fecha: {datetime.today().strftime('%d-%m-%Y')}", ln=True, align="C")
    pdf.cell(0, 10, "Autor: Gemini Assist", ln=True, align="C")

    pdf.add_page()

    # --- Informe ---
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "📄 Análisis General", ln=True)
    pdf.ln(5)

    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 8, informe, align="J")

    # --- Tabla (si existe) ---
    if tabla is not None:
        pdf.ln(10)
        pdf.set_font("DejaVu", "B", 12)
        col_width = pdf.w / len(tabla.columns) - 10
        row_height = 8

        # Encabezado
        for col in tabla.columns:
            pdf.cell(col_width, row_height, str(col), border=1, align="C")
        pdf.ln(row_height)

        pdf.set_font("DejaVu", "", 10)
        for i in range(len(tabla)):
            for col in tabla.columns:
                pdf.cell(col_width, row_height, str(tabla.iloc[i][col]), border=1)
            pdf.ln(row_height)

    return pdf.output(dest="S").encode("latin1")

# =======================
# Interfaz Streamlit
# =======================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", layout="wide")

# Mostrar logo en la app
if os.path.exists("images/logo.png"):
    st.image("images/logo.png", width=200)

st.title("📊 Gemini Assist – Informe Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df.head())

    if st.button("Generar Informe"):
        with st.spinner("⏳ Generando informe con Gemini Assist..."):
            try:
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

                st.subheader("📑 Informe Generado")
                st.write(informe)

                # Generar PDF con logo
                pdf_bytes = generar_pdf(informe, logo_path="images/logo.png", tabla=df.head(5))

                st.download_button(
                    label="⬇️ Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_GeminiAssist_{datetime.today().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
