import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ===============================
# Configuración inicial
# ===============================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", layout="centered")

st.image("images/logo.png", width=120)
st.title("🔧 Predictivo de Mantenimiento")

# ===============================
# Configuración API
# ===============================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

# ===============================
# Función para generar Word
# ===============================
def generar_word(informe_texto):
    doc = Document()
    doc.add_heading("Gemini Assist - Informe Predictivo de Mantenimiento", level=0)

    for linea in informe_texto.split("\n"):
        if linea.strip() != "":
            doc.add_paragraph(linea)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ===============================
# Subida de archivo Excel
# ===============================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df)

        if st.button("Generar Informe"):
            with st.spinner("⏳ Generando informe, por favor espera..."):
                try:
                    # Convertir datos en texto
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

                    # Llamada al modelo
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                    informe = response.text

                    # Mostrar informe
                    st.subheader("📑 Informe Generado")
                    st.write(informe)

                    # Botón de descarga Word
                    try:
                        if informe:
                            word_bytes = generar_word(informe)
                            st.download_button(
                                label="📄 Descargar Informe en Word",
                                data=word_bytes,
                                file_name="informe_predictivo.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                    except Exception as e:
                        st.error(f"❌ Error al procesar el archivo Word: {e}")

                except Exception as e:
                    st.error(f"❌ Error al generar el informe: {e}")

    except Exception as e:
        st.error(f"❌ Error al leer el archivo Excel: {e}")
