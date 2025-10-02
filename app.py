import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
import os
from docx import Document


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
        if os.path.exists("images/logo.png"):
            self.image("images/logo.png", 10, 8, 25)
        self.set_font("DejaVu", "B", 12)   # 👉 usamos Arial
        self.cell(0, 10, "Informe Predictivo de Mantenimiento – Gemini Assist", ln=True, align="C")
        self.ln(10)
# =======================
# Generar Word
# =======================
def generar_word(texto):
    doc = Document()
    doc.add_heading("Informe Predictivo de Mantenimiento", 0)

    # Dividimos el texto en líneas y las añadimos al Word
    for linea in texto.split("\n"):
        if linea.strip():
            doc.add_paragraph(linea)

    # Guardamos en memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# =======================
# Interfaz Streamlit
# =======================
st.set_page_config(page_title="Gemini Assist", layout="centered")
st.title("🔧 Predictivo de Mantenimiento")

if os.path.exists("images/logo.png"):
    st.image("images/logo.png", width=120)

# =======================
# Subida de archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)   # 👉 ahora muestra todos los registros

    if st.button("Generar Informe"):
        with st.spinner("⏳ Generando informe con Gemini Assist..."):
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

                st.subheader("📄 Informe Generado")
                st.write(informe)
		
		        # ===============================
                # Botón de descarga Word
                # ===============================
                try:
		               if informe:
                                word_bytes = generar_word(informe)
                                st.download_button(
                                    label="⬇️ Descargar Informe Word",
                                    data=word_bytes,
                                    file_name="informe_predictivo.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                          )

                except Exception as e:
                        st.error(f"❌ Error al procesar el archivo: {e}")
