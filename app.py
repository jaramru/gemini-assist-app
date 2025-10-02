import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
import re
from datetime import datetime
import os

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo
try:
    st.image("images/logo.png", width=150)
except:
    st.write("")

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")

# ==============================
# CONFIGURACIÓN API KEY
# ==============================
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("❌ No se encontró la API KEY. Configúrala en Streamlit Cloud en [Secrets].")
else:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        st.error(f"⚠️ Error configurando la API KEY: {e}")

# ==============================
# FUNCIÓN PARA LIMPIAR TEXTO
# ==============================
def limpiar_texto(texto):
    """Elimina asteriscos y formato Markdown del texto generado."""
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # elimina negritas Markdown
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)  # viñetas tipo *
    texto = texto.replace("*", "")  # elimina asteriscos sueltos
    return texto.strip()

# ==============================
# FUNCIÓN → GENERAR WORD
# ==============================
def generar_word(informe, df):
    doc = Document()

    # ---------- PORTADA ----------
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo centrado
    try:
        p = doc.add_paragraph()
        run = p.add_run()
        run.add_picture("images/logo.png", width=Inches(2))
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except:
        pass

    # Título principal
    titulo = doc.add_paragraph("Gemini Assist")
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo.runs[0]
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)

    # Subtítulo
    subtitulo = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    subtitulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = subtitulo.runs[0]
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(100, 100, 100)

    # Fecha
    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = fecha.runs[0]
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # ---------- TABLA DE ACTIVOS ----------
    doc.add_heading("📊 Resumen de Activos", level=1)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"

    # Cabecera
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        run = hdr_cells[i].paragraphs[0].add_run(str(col))
        run.bold = True

    # Filas (máx 10)
    for _, row in df.head(10).iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    doc.add_paragraph("\n")

    # ---------- INFORME DETALLADO ----------
    doc.add_heading("📄 Informe Detallado", level=1)

    informe_limpio = limpiar_texto(informe)
    for linea in informe_limpio.split("\n"):
        if not linea.strip():
            continue

        if linea.startswith("### "):
            doc.add_heading(linea.replace("### ", "").strip(), level=2)
        elif linea.startswith("## "):
            doc.add_heading(linea.replace("## ", "").strip(), level=3)
        elif re.match(r"^\d+\.", linea.strip()):
            # Listas numeradas
            p = doc.add_paragraph(linea.strip(), style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        elif linea.startswith("- "):
            # Bullets
            p = doc.add_paragraph(linea.replace("- ", ""), style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        else:
            # Párrafo normal justificado
            p = doc.add_paragraph(linea.strip())
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            run = p.runs[0]
            run.font.size = Pt(11)
            run.font.name = "Calibri"

    # ---------- EXPORTAR ----------
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================
# INTERFAZ STREAMLIT
# ==============================
uploaded_file = st.file_uploader("📂 Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df)

    if st.button("🚀 Generar Informe"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                tabla_texto = df.to_string(index=False)

                prompt = f"""
                Eres Gemini Assist, un sistema predictivo de mantenimiento hospitalario.

                Aquí tienes los datos de activos hospitalarios:
                {tabla_texto}

                Con esta información, genera un informe con los apartados:
                1. Acciones preventivas para los 3 activos más críticos.
                2. Estimación de ahorro en € y horas si aplico esas medidas.
                3. Panel de alertas clasificando cada activo en: Bajo, Medio o Alto.
                4. Informe ejecutivo final (máximo 5 líneas).

                ➡️ Importante:
                - NO uses asteriscos ni símbolos raros.
                - Usa títulos claros y texto justificado.
                - Estilo neutro, profesional y en blanco y negro.
                """

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text

                informe_limpio = limpiar_texto(informe)

                st.subheader("📋 Informe Generado")
                st.write(informe_limpio)

                # Botón descarga Word
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
