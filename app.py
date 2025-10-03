# app.py
from __future__ import annotations

import os
import re
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# =========================================
# Configuración básica de la página / estilo
# =========================================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo (opcional)
LOGO_PATH = "images/logo.png"
if os.path.exists(LOGO_PATH):
    try:
        st.image(LOGO_PATH, width=150)
    except Exception:
        pass

st.title("🛠️ Gemini Assist – Informe Predictivo de Mantenimiento")


# =========================================
# Carga robusta de API KEY (Secrets -> Env)
# =========================================
def load_api_key() -> str | None:
    """Lee la clave desde st.secrets o variable de entorno, la exporta a ENV y configura Gemini."""
    key = None

    # 1) Intentar leer de st.secrets (Streamlit Cloud)
    try:
        key = st.secrets.get("GOOGLE_API_KEY")
        if key:
            key = str(key).strip()
    except Exception:
        key = None

    # 2) Fallback: variable de entorno (útil en local)
    if not key:
        key = os.environ.get("GOOGLE_API_KEY")
        if key:
            key = str(key).strip()

    # 3) Configurar SDK si tenemos clave
    if key:
        os.environ["GOOGLE_API_KEY"] = key
        try:
            genai.configure(api_key=key)
        except Exception as e:
            st.error(f"⚠️ Error configurando la API KEY en Google SDK: {e}")
        return key

    return None


API_KEY = load_api_key()

with st.sidebar:
    st.subheader("🔐 Estado de API Key")
    st.write("• Detectada:", bool(API_KEY))

if not API_KEY:
    st.error(
        '❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets con:\n\n'
        'GOOGLE_API_KEY="tu_clave"'
    )
    st.stop()  # No continuar sin clave


# =========================================
# Utilidades
# =========================================
def limpiar_texto(texto: str) -> str:
    """Elimina negritas y bullets Markdown y asteriscos sueltos."""
    if not texto:
        return ""

    # **negritas** -> negritas
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)

    # bullets que empiezan por "* " al inicio de línea
    texto = re.sub(r"^\*\s*", "", texto, flags=re.MULTILINE)

    # asteriscos sueltos
    texto = texto.replace("*", "")

    # Quitar restos de # (títulos Markdown) si aparecen en medio
    # pero mantenemos números y puntos (listas numeradas)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)

    return texto.strip()


def generar_word(informe: str, df: pd.DataFrame) -> BytesIO:
    """Crea un archivo Word sobrio b/n con portada y resumen de tabla."""
    doc = Document()

    # ---------- PORTADA ----------
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo centrado (opcional)
    if os.path.exists(LOGO_PATH):
        try:
            p_logo = doc.add_paragraph()
            r_logo = p_logo.add_run()
            r_logo.add_picture(LOGO_PATH, width=Inches(2))
            p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        except Exception:
            pass

    # Título
    p_title = doc.add_paragraph("Gemini Assist")
    p_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r_title = p_title.runs[0]
    r_title.font.size = Pt(28)
    r_title.bold = True
    r_title.font.color.rgb = RGBColor(0, 0, 0)

    # Subtítulo
    p_sub = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    p_sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r_sub = p_sub.runs[0]
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = RGBColor(80, 80, 80)

    # Fecha
    p_fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    p_fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r_fecha = p_fecha.runs[0]
    r_fecha.font.size = Pt(11)
    r_fecha.font.color.rgb = RGBColor(90, 90, 90)

    doc.add_page_break()

    # ---------- RESUMEN DE ACTIVOS ----------
    doc.add_heading("Resumen de activos (vista abreviada)", level=1)
    # Para evitar documentos muy grandes, mostramos hasta 15 filas
    df_vis = df.head(15).copy()

    table = doc.add_table(rows=1, cols=len(df_vis.columns))
    table.style = "Table Grid"

    # Cabecera
    hdr = table.rows[0].cells
    for i, col in enumerate(df_vis.columns):
        run = hdr[i].paragraphs[0].add_run(str(col))
        run.bold = True

    # Filas
    for _, row in df_vis.iterrows():
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = "" if pd.isna(val) else str(val)

    doc.add_paragraph()

    # ---------- INFORME DETALLADO ----------
    doc.add_heading("Informe detallado", level=1)
    texto = limpiar_texto(informe)

    for linea in texto.splitlines():
        s = linea.strip()
        if not s:
            continue

        # Titulares sencillos detectados por heurística
        if re.match(r"^\d+\.\s", s) and len(s) < 140:
            # encabezado corto enumerado
            h = doc.add_paragraph()
            rr = h.add_run(s)
            rr.bold = True
            rr.font.size = Pt(12)
        elif re.match(r"^[-–•]\s", s):
            # viñetas -> estilo Lista
            p = doc.add_paragraph(s[1:].strip(), style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        elif re.match(r"^\d+\.\s", s):
            # listas numeradas
            p = doc.add_paragraph(s, style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        else:
            # párrafo normal
            p = doc.add_paragraph(s)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            for r in p.runs:
                r.font.size = Pt(11)
                r.font.name = "Calibri"

    # ---------- EXPORTAR ----------
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# =========================================
# Interfaz principal
# =========================================
st.markdown("#### 📎 Sube el archivo de activos (Excel)")
uploaded_file = st.file_uploader(" ", type=["xlsx"], label_visibility="collapsed")

if not uploaded_file:
    st.info("Carga un archivo .xlsx para comenzar.")
    st.stop()

# Leer Excel con openpyxl (robusto)
try:
    df = pd.read_excel(uploaded_file, engine="openpyxl")
except Exception:
    df = pd.read_excel(uploaded_file)  # fallback

st.success("✅ Archivo cargado correctamente")
st.dataframe(df, use_container_width=True)

# Estado para deshabilitar botón mientras se genera
if "generating" not in st.session_state:
    st.session_state.generating = False


def _set_generating(val: bool):
    st.session_state.generating = val


# Botón para generar informe
btn = st.button(
    "🚀 Generar Informe",
    disabled=st.session_state.generating,
    type="primary",
)

if btn:
    _set_generating(True)

    with st.spinner("🧠 Generando informe con Gemini Assist…"):
        try:
            # Convertimos la tabla a texto para el prompt (acotado)
            tabla_texto = df.head(20).to_string(index=False)

            prompt = f"""
Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.
Analiza la siguiente tabla de activos y redacta un informe en TEXTO PLANO (sin Markdown, sin asteriscos).

Tabla (muestra):
{tabla_texto}

Estructura requerida:
1. Ranking de riesgo de fallo en los próximos 3 meses (si no es claro por datos, razona y ordena por criticidad, coste y tiempo de parada; máximo 10 líneas).
2. Acciones preventivas para los 3 activos más críticos (pasos concretos y justificación).
3. Estimación orientativa de ahorro (€ y horas) si se aplican las medidas propuestas.
4. Panel de alertas: clasifica cada activo en Bajo, Medio o Alto (breve justificación si procede).
5. Informe ejecutivo final (máximo 5 líneas).

Condiciones de estilo:
- No utilices asteriscos, ni negritas, ni viñetas de Markdown.
- Usa frases claras y completas, numeraciones normales (1., 2., 3.) si hace falta.
- Tono profesional y neutro; no uses emojis.
- Evita encabezados con #; escribe texto limpio.
"""

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt, request_options={"timeout": 120})
            informe = response.text or ""

            informe_limpio = limpiar_texto(informe)

            st.subheader("📋 Informe generado")
            st.text_area("Vista previa (texto)", informe_limpio, height=300)

            # Descarga Word
            word_bytes = generar_word(informe_limpio, df)
            st.download_button(
                label="⬇️ Descargar Informe Word",
                data=word_bytes,
                file_name="informe_predictivo.docx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.wordprocessingml.document"
                ),
            )

        except Exception as e:
            st.error(f"❌ Error al generar el informe: {e}")

        finally:
            _set_generating(False)

