import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import io

# ========================
# Configuración clave API
# ========================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# ========================
# Función para generar Word
# ========================
def generar_word(informe):
    doc = Document()

    # Logo
    try:
        doc.add_picture("images/logo.png", width=Inches(1.5))
    except:
        pass

    # Título centrado
    titulo = doc.add_paragraph("Gemini Assist – Informe Predictivo de Mantenimiento")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(16)
    run.bold = True

    doc.add_paragraph("")  # espacio

    # Solo las primeras 10 líneas del informe
    lineas = informe.split("\n")[:10]
    for linea in lineas:
        if linea.strip():
            p = doc.add_paragraph(linea)
            p.style = "Normal"

    # Guardar en memoria
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ========================
# Interfaz Streamlit
# ========================
st.title("🔧 Predictivo de Mantenimiento")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🤖 Generando informe con Gemini Assist..."):
            # Tomar las primeras filas para no saturar
            tabla_texto = df.head(5).to_string(index=False)

            prompt = f"""
            Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.
            Aquí tienes los datos de activos hospitalarios:
            {tabla_texto}

            Genera un informe técnico breve en texto claro y conciso.
            """

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            informe = response.text

        st.subheader("📄 Informe generado")
        st.write(informe)

        try:
            word_bytes = generar_word(informe)
            st.download_button(
                label="⬇️ Descargar Informe Word",
                data=word_bytes,
                file_name="informe_predictivo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"❌ Error al generar Word: {e}")
