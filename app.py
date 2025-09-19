import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO

# ======================
# Configuración inicial
# ======================
st.set_page_config(page_title="Gemini Assist – Predictivo de Mantenimiento", layout="centered")

# Leer API_KEY desde secrets
API_KEY = st.secrets.get("API_KEY")
genai.configure(api_key=API_KEY)

st.title("📊 Predictivo de Mantenimiento")

# ======================
# Subida de archivo Excel
# ======================
uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    # Inicializamos estados
    if "informe" not in st.session_state:
        st.session_state["informe"] = None
    if "generando" not in st.session_state:
        st.session_state["generando"] = False

    # ======================
    # Botón para generar informe
    # ======================
    if st.button("Generar Informe", disabled=st.session_state["generando"]):
        st.session_state["generando"] = True
        with st.spinner("🧠 Generando informe, por favor espera..."):
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

                if hasattr(response, "text"):
                    st.session_state["informe"] = response.text
                    st.success("✅ Informe generado correctamente")
                else:
                    st.session_state["informe"] = str(response)
                    st.warning("⚠️ Informe generado, pero en formato inesperado")

            except Exception as e:
                st.error(f"❌ Error al generar informe: {e}")
            finally:
                st.session_state["generando"] = False

    # ======================
    # Mostrar informe
    # ======================
    if st.session_state["informe"]:
        st.markdown("### 📄 Informe Generado")
        st.write(st.session_state["informe"])

        # ======================
        # Generar PDF
        # ======================
        def generar_pdf(texto):
            pdf = FPDF()
            pdf.add_page()

            # Usar fuente Unicode DejaVu (para € y acentos)
            pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            pdf.set_font("DejaVu", size=12)

            pdf.multi_cell(0, 10, texto)
            pdf_output = BytesIO()
            pdf.output(pdf_output)
            return pdf_output

        if st.button("📥 Descargar Informe PDF"):
            try:
                pdf_bytes = generar_pdf(st.session_state["informe"])
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name="Informe_GeminiAssist.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ Error al generar el PDF: {e}")


