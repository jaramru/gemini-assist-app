import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import io
from datetime import datetime
import os

# =======================
# Configuración de la API
# =======================
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("❌ No se ha encontrado la API_KEY. Configúrala en Streamlit Cloud (Settings > Secrets).")
else:
    genai.configure(api_key=API_KEY)

# =======================
# Clase personalizada PDF
# =======================
class PDF(FPDF):
    def header(self):
        # Logo en la portada
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 25)
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, "Gemini Assist - Informe de Mantenimiento Predictivo", align="C", ln=True)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# =======================
# Interfaz Streamlit
# =======================
st.title("📊 Predictivo de Mantenimiento")
st.write("Sube el archivo de activos (Excel)")

uploaded_file = st.file_uploader("Archivo Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe", type="primary"):
        with st.spinner("⏳ Generando informe..."):
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

            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                # =======================
                # Crear PDF con DejaVu
                # =======================
                pdf = PDF()
                pdf.add_page()

                # Registrar fuentes DejaVu
                pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
                pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
                pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)

                # Portada
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Gemini Assist", ln=True, align="C")
                pdf.ln(10)
                pdf.set_font("DejaVu", "", 12)
                pdf.cell(0, 10, f"Informe generado el {datetime.today().strftime('%d-%m-%Y')}", ln=True, align="C")
                pdf.ln(20)

                # Cuerpo del informe
                pdf.set_font("DejaVu", "", 11)
                pdf.multi_cell(0, 8, informe)

                # Exportar PDF a memoria
                pdf_buffer = io.BytesIO()
                pdf.output(pdf_buffer)
                pdf_buffer.seek(0)

                # Mostrar en pantalla
                st.subheader("📑 Informe Generado")
                st.write(informe)

                # Botón de descarga
                st.download_button(
                    label="⬇️ Descargar Informe PDF",
                    data=pdf_buffer,
                    file_name=f"Informe_GeminiAssist_{datetime.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
