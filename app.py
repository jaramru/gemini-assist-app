import os
import re
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import google.generativeai as genai

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# ==============================
# Configuración inicial UI
# ==============================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo y título
try:
    st.image("images/logo.png", width=150)
except Exception:
    pass

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")


# ==============================
# API KEY: st.secrets -> os.getenv
# ==============================
API_KEY = None
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
except Exception:
    API_KEY = None

if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets:\n\n"
             "GOOGLE_API_KEY = \"tu_clave\"")
    GENAI_READY = False
else:
    try:
        genai.configure(api_key=API_KEY)
        # Verificación ligera (no consume apenas tokens)
        genai.GenerativeModel("gemini-2.5-flash").count_tokens("ping")
        st.success("✅ API KEY encontrada y válida. Modelo configurado.")
        GENAI_READY = True
    except Exception as e:
        st.error(f"⚠️ La API KEY está definida pero falló la verificación: {e}")
        GENAI_READY = False


# ==============================
# Utilidades
# ==============================
def limpiar_texto(texto: str) -> str:
    """
    Elimina asteriscos y formato Markdown del texto generado.
    - **negritas** -> negritas
    - * viñetas simples
    - asteriscos sueltos
    """
    if not isinstance(texto, str):
        return ""

    # Quitar **negritas**
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    # Quitar líneas que arrancan con "* " (viñetas)
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)
    # Quitar asteriscos sueltos
    texto = texto.replace("*", "")
    return texto.strip()


def generar_word(informe: str, df: pd.DataFrame) -> BytesIO:
    """
    Genera un documento Word con:
      - Portada con logo
      - Resumen de activos (tabla)
      - Informe Detallado (texto limpio sin * de Markdown)
    Estilo neutro, blanco y negro.
    """
    doc = Document()

    # Márgenes
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # ---------- Portada ----------
    try:
        p_logo = doc.add_paragraph()
        r_logo = p_logo.add_run()
        r_logo.add_picture("images/logo.png", width=Inches(2))
        p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    p_title = doc.add_paragraph("Gemini Assist")
    p_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = p_title.runs[0]
    r.font.size = Pt(28)
    r.bold = True
    r.font.color.rgb = RGBColor(0, 0, 0)

    p_sub = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    p_sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = p_sub.runs[0]
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(90, 90, 90)

    p_date = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    p_date.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = p_date.runs[0]
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # ---------- Resumen de Activos (tabla sencilla, B/N) ----------
    doc.add_heading("Resumen de Activos", level=1)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"

    # Cabeceras
    hdr = table.rows[0].cells
    for i, col in enumerate(df.columns):
        run = hdr[i].paragraphs[0].add_run(str(col))
        run.bold = True

    # Primeras 10 filas como muestra
    for _, row in df.head(10).iterrows():
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = "" if pd.isna(value) else str(value)

    doc.add_paragraph("")  # espacio

    # ---------- Informe Detallado ----------
    doc.add_heading("Informe Detallado", level=1)

    informe_limpio = limpiar_texto(informe)
    for linea in informe_limpio.split("\n"):
        linea = linea.strip()
        if not linea:
            continue

        # Títulos Markdown
        if linea.startswith("### "):
            doc.add_heading(linea.replace("### ", "").strip(), level=2)
            continue
        if linea.startswith("## "):
            doc.add_heading(linea.replace("## ", "").strip(), level=3)
            continue

        # Listas numeradas
        if re.match(r"^\d+\.", linea):
            p = doc.add_paragraph(linea, style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            continue

        # Bullets con guion
        if linea.startswith("- "):
            p = doc.add_paragraph(linea[2:], style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            continue

        # Párrafo normal
        p = doc.add_paragraph(linea)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        if p.runs:
            p.runs[0].font.size = Pt(11)

    # Exportar a memoria
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ==============================
# Interfaz de carga y generación
# ==============================
st.subheader("📁 Sube el archivo de activos (Excel)")
uploaded_file = st.file_uploader(" ", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ No se pudo leer el Excel: {e}")
        st.stop()

    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df, use_container_width=True)

    generar = st.button("🚀 Generar Informe")
    if generar:
        if not GENAI_READY:
            st.error("⚠️ No se puede generar el informe porque la API KEY no es válida.")
            st.stop()

        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                # Texto plano de la tabla (máx 2000 filas para evitar prompts excesivos)
                tabla_texto = df.head(2000).to_string(index=False)

                prompt = f"""
Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.
Analiza los siguientes activos y redacta un informe profesional (neutro, blanco y negro, sin asteriscos ni emojis).

Datos:
{tabla_texto}

Genera cuatro apartados bien titulados:
1) Acciones preventivas para los 3 activos más críticos (explica acción y justificación).
2) Estimación de ahorro en euros y horas si se aplican esas medidas (cálculo razonado).
3) Panel de alertas (clasifica cada activo en Bajo, Medio o Alto riesgo y cita por qué).
4) Informe ejecutivo final (máximo 5 líneas), orientado a Dirección, con impacto y recomendaciones.

Reglas de formato:
- No uses asteriscos, ni markdown de negrita, ni emojis.
- Usa frases completas; títulos claros; texto justificado.
- Evita adornos visuales; estilo ejecutivo conciso.
"""

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                informe = response.text or ""

                informe_limpio = limpiar_texto(informe)

                st.subheader("📋 Informe Generado")
                st.write(informe_limpio)

                # Botón de descarga Word
                word_bytes = generar_word(informe, df)
                st.download_button(
                    label="⬇️ Descargar Informe Word",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al generar el informe: {e}")
else:
    st.info("Carga un archivo .xlsx para comenzar.")
