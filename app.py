# app.py
# =========================================================
# Gemini Assist – Informe Predictivo de Mantenimiento
# (Streamlit + Google Gemini + Exportación a Word)
# =========================================================

import os
import re
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
import google.generativeai as genai

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="Gemini Assist", layout="wide")


# -----------------------------
# Utilidades
# -----------------------------
def _flatten(d, prefix=""):
    """Aplana dicts anidados de st.secrets para poder buscar claves dentro de secciones."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}".lower()
        if isinstance(v, dict):
            out.update(_flatten(v, prefix=f"{key}."))
        else:
            out[key] = v
    return out


def load_api_key():
    """
    Busca la API Key en:
      1) st.secrets (clave recomendada: GOOGLE_API_KEY)
      2) st.secrets en secciones (p. ej. [general].google_api_key)
      3) Variables de entorno (GOOGLE_API_KEY / GEMINI_API_KEY / API_KEY)
    Configura google.generativeai si la encuentra.
    """
    # 1) secrets (si existen)
    secrets_dict = {}
    try:
        secrets_dict = _flatten(dict(st.secrets))
    except Exception:
        secrets_dict = {}

    candidates = [
        "google_api_key",          # recomendado
        "gemini_api_key",
        "googleapikey",
        "gemini_key",
        "api_key",
        "general.google_api_key",  # por si está dentro de [general]
    ]

    found_key_name = None
    key = None

    for name in candidates:
        if name in secrets_dict and str(secrets_dict[name]).strip():
            found_key_name = name
            key = str(secrets_dict[name]).strip()
            break

    # 2) variables de entorno
    if not key:
        for env in ["GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY"]:
            if os.getenv(env):
                found_key_name = f"env:{env.lower()}"
                key = os.getenv(env).strip()
                break

    # 3) configurar
    if key:
        os.environ["GOOGLE_API_KEY"] = key
        try:
            genai.configure(api_key=key)
        except Exception as e:
            st.error(f"⚠️ Error configurando Google SDK: {e}")
        return key, found_key_name

    return None, None


API_KEY, API_KEY_SOURCE = load_api_key()


def limpiar_texto(texto: str) -> str:
    """Elimina asteriscos y formato Markdown del texto generado."""
    if not texto:
        return ""
    # **negritas**
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    # viñetas con *
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)
    # asteriscos sueltos
    texto = texto.replace("*", "")
    # guiones largos atípicos a guion normal
    texto = texto.replace("–", "-").replace("—", "-")
    return texto.strip()


def generar_word(informe: str, df: pd.DataFrame) -> BytesIO:
    """Crea un .docx con estilo neutro, portada y tabla de activos (blanco y negro)."""
    doc = Document()

    # Márgenes
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo (opcional)
    try:
        p_logo = doc.add_paragraph()
        run_logo = p_logo.add_run()
        run_logo.add_picture("images/logo.png", width=Inches(2))
        p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    # Título
    p_title = doc.add_paragraph("Gemini Assist")
    p_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = p_title.runs[0]
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = RGBColor(0, 0, 0)

    # Subtítulo
    p_sub = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    p_sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p_sub.runs[0].font.size = Pt(14)
    p_sub.runs[0].font.color.rgb = RGBColor(80, 80, 80)

    # Fecha
    p_date = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    p_date.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p_date.runs[0].font.size = Pt(11)
    p_date.runs[0].font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # -------- Resumen de activos (tabla) --------
    doc.add_heading("Resumen de Activos", level=1)
    if not df.empty:
        cols = list(df.columns)
        table = doc.add_table(rows=1, cols=len(cols))
        table.style = "Table Grid"

        # Cabecera
        hdr = table.rows[0].cells
        for i, col in enumerate(cols):
            rr = hdr[i].paragraphs[0].add_run(str(col))
            rr.bold = True

        # Filas (máximo 25 para no hacer Word gigante)
        for _, row in df.head(25).iterrows():
            row_cells = table.add_row().cells
            for i, value in enumerate(row):
                row_cells[i].text = "" if pd.isna(value) else str(value)

    doc.add_paragraph("")

    # -------- Informe detallado --------
    doc.add_heading("Informe Detallado", level=1)
    texto = limpiar_texto(informe)
    for linea in texto.split("\n"):
        l = linea.strip()
        if not l:
            continue

        # Títulos Markdown
        if l.startswith("### "):
            doc.add_heading(l.replace("### ", "").strip(), level=2)
        elif l.startswith("## "):
            doc.add_heading(l.replace("## ", "").strip(), level=3)
        # Listas numeradas
        elif re.match(r"^\d+\.", l):
            p = doc.add_paragraph(l, style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        # Bullets
        elif l.startswith("- "):
            p = doc.add_paragraph(l[2:], style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        # Párrafo normal
        else:
            p = doc.add_paragraph(l)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            if p.runs:
                p.runs[0].font.size = Pt(11)

    # Guardar buffer
    buff = BytesIO()
    doc.save(buff)
    buff.seek(0)
    return buff


# -----------------------------
# Cabecera de la App
# -----------------------------
try:
    st.image("images/logo.png", width=150)
except Exception:
    st.write("")

st.markdown(
    "<h1 style='margin-top:0'>🛠️ Gemini Assist – Informe Predictivo de Mantenimiento</h1>",
    unsafe_allow_html=True,
)

# Estado de API en la barra lateral
with st.sidebar:
    st.subheader("🔐 Estado de API Key")
    st.write("Detectada:", bool(API_KEY))
    st.write("Origen:", API_KEY_SOURCE or "—")
    with st.expander("Diagnóstico de API (temporal)"):
        st.write("Variables de entorno presentes:", [k for k in os.environ.keys() if "API" in k.upper()])


# Aviso si falta la clave
if not API_KEY:
    st.error(
        '❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets con:\n\n'
        'GOOGLE_API_KEY="tu_clave"'
    )

# -----------------------------
# Carga de Excel
# -----------------------------
st.subheader("📎 Sube el archivo de activos (Excel)")
uploaded = st.file_uploader(" ", type=["xlsx"])

df = pd.DataFrame()
if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)  # requiere openpyxl en requirements
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error leyendo Excel: {e}")


# -----------------------------
# Generación del informe
# -----------------------------
btn_disabled = not (API_KEY and not df.empty)
generate = st.button("🚀 Generar Informe", disabled=not (API_KEY and not df.empty))

if generate and btn_disabled is False:
    try:
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            # Convertimos la tabla a texto (no limitar a top10)
            tabla_texto = df.to_string(index=False)

            prompt = f"""
Eres Gemini Assist, un sistema experto en mantenimiento hospitalario. Analiza la siguiente tabla de activos:

{tabla_texto}

Con esta información, genera un informe con los apartados:
1. Acciones preventivas para los 3 activos más críticos.
2. Estimación de ahorro en € y horas si aplico esas medidas (solo estimaciones realistas).
3. Panel de alertas clasificando cada activo en: Bajo, Medio o Alto (breve justificación).
4. Informe ejecutivo final (máximo 5 líneas), claro y accionable.

Requisitos de formato:
- No uses asteriscos ni Markdown decorativo.
- Usa títulos claros y texto justificado.
- Estilo neutro, profesional, blanco y negro.
- Español.
"""

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            informe = response.text or ""

        if not informe.strip():
            st.error("⚠️ No se pudo generar el informe. Intenta de nuevo.")
        else:
            st.success("✅ Informe generado correctamente")

            limpio = limpiar_texto(informe)
            st.text_area("📄 Informe (texto generado)", value=limpio, height=320)

            # Descargar Word
            word_bytes = generar_word(informe, df)
            st.download_button(
                label="⬇️ Descargar Informe Word",
                data=word_bytes,
                file_name="informe_predictivo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    except Exception as e:
        st.error(f"❌ Error al procesar el informe: {e}")
