import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from datetime import datetime
import re

# =======================
# Función de limpieza de texto
# =======================
def limpiar_texto(texto):
    texto = re.sub(r"\*\*", "", texto)             # quitar ** de Markdown
    texto = re.sub(r"\*", "", texto)               # quitar asteriscos sueltos
    texto = re.sub(r"^\d+\.\s*", "", texto, flags=re.MULTILINE)  # quitar "1.", "2."
    texto = re.sub(r"para Dirección.*", "", texto) # quitar frases residuales
    texto = texto.replace("#", "")                 # quitar encabezados markdown
    return texto.strip()

# =======================
# Clase PDF personalizada
# =======================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.set_text_color(0, 70, 140)
        self.cell(0, 10, "Gemini Assist - Informe de Mantenimiento Predictivo",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(100)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.set_fill_color(230, 230, 250)
        self.cell(0, 10, f" {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def chapter_body(self, text):
        text = limpiar_texto(text)
        self.set_font("Arial", "", 11)
        self.multi_cell(0, 8, text, align="J")  # Justificado
        self.ln()

# =======================
# Configuración de la App
# =======================
st.set_page_config(page_title="Gemini Assist", page_icon="📊", layout="wide")
st.title("📊 Gemini Assist – Informe Predictivo de Mantenimiento")

# API Key desde secrets (en Streamlit Cloud se añadirá en Settings → Secrets)
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# =======================
# Subir archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df.head())

    if st.button("Generar Informe"):
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

        # Llamada a Gemini
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        informe = response.text

        # =======================
        # Mostrar en la web
        # =======================
        st.subheader("📄 Informe generado")
        st.write(informe)

        # =======================
        # Crear PDF profesional
        # =======================
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Portada
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 80, "", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, "INFORME GEMINI ASSIST", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Arial", "", 14)
        pdf.cell(0, 10, "Mantenimiento Predictivo Hospitalario",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(20)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Fecha: {datetime.today().strftime('%d-%m-%Y')}",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.cell(0, 10, "Autor: Gemini Assist", new_x="LMARGIN", new_y="NEXT", align="C")

        # Cuerpo del informe
        pdf.add_page()
        pdf.chapter_title("Informe Completo")
        pdf.chapter_body(informe)

        # Guardar PDF
        nombre_pdf = f"Informe_GeminiAssist_{datetime.today().strftime('%Y-%m')}.pdf"
        pdf.output(nombre_pdf)

        # Botón de descarga
        with open(nombre_pdf, "rb") as f:
            st.download_button("⬇️ Descargar PDF", f, file_name=nombre_pdf)
