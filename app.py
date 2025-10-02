import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
import io
import re

# ==============================
# Función para limpiar el texto
# ==============================
def limpiar_texto(texto):
    """Elimina asteriscos y formato Markdown del texto generado."""
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # negritas
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)  # viñetas
    texto = texto.replace("*", "")  # asteriscos sueltos
    return texto

# ==============================
# Generar Word
# ==============================
def generar_word(informe):
    doc = Document()

    # Logo si existe
    try:
        doc.add_picture("images/logo.png", width=Inches(1.5))
    except:
        pass  

    # Título
    titulo = doc.add_heading("Gemini Assist – Informe Predictivo de Mantenimiento", 0)
    titulo.alignment = 1

    # Texto limpio
    informe_limpio = limpiar_texto(informe)

    for linea in informe_limpio.split("\n"):
        if linea.strip() == "":
            continue
        if linea.startswith("### "):  # Título principal
            doc.add_heading(linea.replace("### ", "").strip(), level=1)
        elif linea.startswith("## "):  # Subtítulo
            doc.add_heading(linea.replace("## ", "").strip(), level=2)
        elif "|" in linea and "---" not in linea:  # Tablas en formato markdown
            cols = [c.strip() for c in linea.split("|") if c.strip()]
            if not hasattr(doc, "_table_started"):
                table = doc.add_table(rows=1, cols=len(cols))
                table.style = "Table Grid"
                hdr_cells = table.rows[0].cells
                for i, col in enumerate(cols):
                    hdr_cells[i].text = col
                doc._table_started = table
            else:
                row_cells = doc._table_started.add_row().cells
                for i, col in enumerate(cols):
                    row_cells[i].text = col
        else:
            doc.add_paragraph(linea)

    # Exportar
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================
# Interfaz Streamlit
# ==============================
st.set_page_config(page_title="Predictivo de Mantenimiento", layout="wide")

st.title("🔧 Predictivo de Mantenimiento")
st.write("Sube el archivo de activos (Excel)")

uploaded_file = st.file_uploader("Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("Generar Informe"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                # Preparar datos para el modelo
                tabla_texto = df.to_string(index=False)

                prompt = f"""
                Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.

                Aquí tienes los datos de activos hospitalarios:
                {tabla_texto}

                Con esta tabla, necesito que hagas lo siguiente:
                1. Ranking de riesgo de fallo en los próximos 3 meses (máx 10 activos).
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

                # Limpiar el texto
                informe_limpio = limpiar_texto(informe)

                # Mostrar en pantalla
                st.subheader("📄 Informe Generado")
                st.write(informe_limpio)

                # Botón para descargar Word
                word_bytes = generar_word(informe)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
