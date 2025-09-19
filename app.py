import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from datetime import datetime

# =======================
# Configuración de la API
# =======================
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("❌ No se encontró la API_KEY. Configúrala en Secrets de Streamlit Cloud.")
else:
    genai.configure(api_key=API_KEY)

# =======================
# Título principal
# =======================
st.title("📊 Predictivo de Mantenimiento")
st.write("Sube el archivo de activos (Excel)")

# =======================
# Subir archivo Excel
# =======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df.head())

    # =======================
    # Botón para generar informe
    # =======================
    if st.button("Generar Informe"):
        with st.spinner("⏳ Generando informe con Gemini Assist..."):
            try:
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

                # Mostrar el informe en pantalla
                st.subheader("📑 Informe Generado")
                st.write(informe)

                # =======================
                # Generar PDF con DejaVu
                # =======================
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
                pdf.set_font("DejaVu", size=12)

                pdf.multi_cell(0, 10, "Gemini Assist - Informe de Mantenimiento Predictivo\n\n")
                pdf.multi_cell(0, 10, informe)

                nombre_pdf = f"Informe_GeminiAssist_{datetime.today().strftime('%Y-%m-%d')}.pdf"
                pdf.output(nombre_pdf)

                # ✅ Botón final de descarga
                with open(nombre_pdf, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar Informe PDF",
                        data=f,
                        file_name=nombre_pdf,
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
