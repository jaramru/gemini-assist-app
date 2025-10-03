# app.py
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
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo cabecera (no detiene la app si falta)
try:
    st.image("images/logo.png", width=150)
except Exception:
    pass

st.markdown(
    "<h1 style='margin-top:-10px'>🔧 Gemini Assist – Informe Predictivo de Mantenimiento</h1>",
    unsafe_allow_html=True,
)

# ==============================
# API KEY: st.secrets -> os.getenv
# ==============================
API_KEY = None
try:
    # 1) Secrets (preferente)
    API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
except Exception:
    API_KEY = None

# 2) Env var (respaldo)
if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY", None)

GENAI_READY = False
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        # pequeña prueba de config (no llama al modelo todavía)
        _ = genai.GenerationConfig()
        GENAI_READY = True
        st.success("✅ API KEY detectada y configurada correctamente.")
    except Exception as e:
        st.error(f"⚠️ Hubo un problema configurando la API: {e}")
else:
    st.error(
        "❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → **Settings → Secrets** con:\n\n"
        "`GOOGLE_API_KEY=\"tu_clave\"`"
    )

# (Opcional) Bloque de diagnóstico; bórralo si no lo necesitas
with st.expander("🔎 Diagnóstico de API (temporal)"):
    has_secret = False
    try:
        has_secret = "GOOGLE_API_KEY" in st.secrets
    except Exception:
        has_secret = False
    has_env = bool(os.getenv("GOOGLE_API_KEY"))
    st.write("st.secrets contiene GOOGLE_API_KEY:", has_secret)
    st.write("os.getenv('GOOGLE_API_KEY') está definido:", has_env)

# ==============================
# LIMPIEZA DE TEXTO (sin asteriscos/markdown)
# ==============================
def limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    # **negritas** -> negritas sin asteriscos
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    # * viñetas al inicio de línea
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)
    # guiones con espacio como bullets -> dejamos el texto
    texto = re.sub(r"^\-\s*", "", texto, flags=re.MULTILINE)
    # asteriscos sueltos
    texto = texto.replace("*", "")
    # emojis comunes de colores en panel (por si los devuelve)
    texto = texto.replace("🟢", "Bajo").replace("🟡", "Medio").replace("🔴", "Alto")
    return texto.strip()

# ==============================
# GENERAR WORD (estilo neutro, con logo)
# ==============================
def generar_word(informe: str, df: pd.DataFrame) -> BytesIO:
    doc = Document()

    # Márgenes
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo centrado
    try:
        p_logo = doc.add_paragraph()
        r_logo = p_logo.add_run()
        r_logo.add_picture("images/logo.png", width=Inches(2))
        p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    # Título
    p_title = doc.add_paragraph("Gemini Assist")
    p_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = p_title.runs[0]
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = RGBColor(0, 0, 0)

    # Subtítulo
    p_sub = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    p_sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p_sub.runs[0].font.size = Pt(13)
    p_sub.runs[0].font.color.rgb = RGBColor(60, 60, 60)

    # Fecha
    p_date = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    p_date.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p_date.runs[0].font.size = Pt(11)
    p_date.runs[0].font.color.rgb = RGBColor(90, 90, 90)

    doc.add_page_break()

    # Resumen de activos (muestra)
    doc.add_heading("Resumen de activos (muestra)", level=1)
    try:
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = "Table Grid"
        hdr = table.rows[0].cells
        for i, col in enumerate(df.columns):
            rr = hdr[i].paragraphs[0].add_run(str(col))
            rr.bold = True

        # muestra hasta 10 filas
        for _, row in df.head(10).iterrows():
            row_cells = table.add_row().cells
            for i, value in enumerate(row):
                row_cells[i].text = "" if pd.isna(value) else str(value)
    except Exception:
        doc.add_paragraph("(No se pudo renderizar la tabla de activos)")

    doc.add_paragraph("")  # espacio

    # Informe detallado (limpio)
    doc.add_heading("Informe detallado", level=1)
    texto = limpiar_texto(informe)
    for linea in texto.split("\n"):
        if not linea.strip():
            continue
        # Detecta títulos tipo "##" o "###"
        if linea.startswith("### "):
            doc.add_heading(linea[4:].strip(), level=2)
        elif linea.startswith("## "):
            doc.add_heading(linea[3:].strip(), level=3)
        # Listas numeradas
        elif re.match(r"^\d+\.", linea.strip()):
            p = doc.add_paragraph(linea.strip(), style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        else:
            p = doc.add_paragraph(linea.strip())
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            p.runs[0].font.size = Pt(11)
            p.runs[0].font.name = "Calibri"

    # Exportar a memoria
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================
# INTERFAZ
# ==============================
st.subheader("📎 Sube el archivo de activos (Excel)")
uploaded = st.file_uploader(" ", type=["xlsx"], label_visibility="collapsed")

if uploaded is None:
    st.info("Carga un archivo .xlsx para comenzar.")
    st.stop()

# Carga de datos
try:
    df = pd.read_excel(uploaded)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"❌ No se pudo leer el Excel: {e}")
    st.stop()

# Botón generar (deshabilitado si no hay API lista)
generate_btn = st.button("🚀 Generar informe", type="primary", disabled=not GENAI_READY)

if not GENAI_READY:
    st.info("Configura la API y pulsa **Reboot** en Streamlit Cloud para habilitar el botón.")
    st.stop()

if generate_btn:
    with st.spinner("🧠 Generando informe con Gemini Assist..."):
        try:
            # Prepara tabla como texto para el prompt
            tabla_texto = df.to_string(index=False)

            prompt = f"""
            Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.
            Analiza los activos (tabla a continuación) y entrega un informe técnico claro,
            sin asteriscos de Markdown, con estilo neutro y profesional (blanco y negro).

            TABLA DE ACTIVOS:
            {tabla_texto}

            Entrega exactamente estos apartados:
            1. Acciones preventivas para los 3 activos más críticos (breves y accionables).
            2. Estimación de ahorro en euros (€) y horas si se aplican esas medidas.
            3. Panel de alertas por activo: Bajo | Medio | Alto (solo texto, sin emojis).
            4. Informe ejecutivo final (máximo 5 líneas, directo para Dirección).
            """

            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            informe = response.text or ""

            # Mostrar informe en pantalla
            informe_limpio = limpiar_texto(informe)
            st.subheader("📋 Informe generado")
            st.write(informe_limpio)

            # Descargar Word
            word_bytes = generar_word(informe_limpio, df)
            st.download_button(
                label="⬇️ Descargar informe en Word",
                data=word_bytes,
                file_name="informe_predictivo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        except Exception as e:
            st.error(f"❌ Error al generar el informe: {e}")
