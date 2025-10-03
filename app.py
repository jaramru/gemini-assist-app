# -*- coding: utf-8 -*-
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


# =========================================
#  CONFIGURACIÓN UI BÁSICA
# =========================================
st.set_page_config(page_title="Gemini Assist", layout="wide")

# Logo (si existe)
try:
    st.image("images/logo.png", width=140)
except Exception:
    pass

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")


# =========================================
#  API KEY (Secrets → GOOGLE_API_KEY)
# =========================================
API_KEY = None
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
except Exception:
    API_KEY = None

if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error(
        "❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets con:\n\n"
        '```\nGOOGLE_API_KEY="tu_clave"\n```'
    )
    st.stop()

# Configurar Gemini
genai.configure(api_key=API_KEY)


# =========================================
#  SYSTEM INSTRUCTIONS (tono, estructura)
# =========================================
SYSTEM_INSTRUCTIONS = """
Eres "Gemini Assist", un asistente experto en mantenimiento hospitalario.
Objetivo: generar un informe claro, profesional y neutro (blanco y negro), basado en una tabla de activos.

REGLAS DE FORMATO PARA LA SALIDA:
- NO uses Markdown de negritas **…** ni cabeceras ###. Escribe texto plano.
- Usa numeraciones simples (“1. Título”, “2. Título”…). Evita dobles numeraciones como “1.  1.”.
- Usa listas con viñetas simples para acciones (“- Acción …”).
- Mantén un tono ejecutivo, sintético y preciso.

SECCIONES A ENTREGAR (siempre en este orden):
1. Acciones preventivas para los 3 activos más críticos (con razón breve de criticidad).
2. Estimación de ahorro en € y horas si aplico esas medidas (suma aproximada).
3. Panel de alertas (Bajo, Medio, Alto) para cada activo.
4. Informe ejecutivo final (máx. 5 líneas, lenguaje de dirección).

NO incluyas tablas Markdown; usa texto.
"""


# =========================================
#  LIMPIEZAS DE TEXTO Y PREVIEW
# =========================================
def normaliza_numeracion(texto: str) -> str:
    """
    Corrige la doble numeración: '1.  1. Título' → '1. Título'
    y casos '1.1. Título' → '1. Título'.
    """
    texto = re.sub(r'(^|\n)\s*\d+\.\s*\d+\.\s*', r'\1', texto)
    texto = re.sub(r'(^|\n)\s*(\d+)\.\d+\.\s*', r'\1\2. ', texto)
    return texto


def limpiar_para_preview(texto: str) -> str:
    """
    Limpia marcas Markdown y deja el texto listo para mostrar.
    - Quita **negritas**, ### cabeceras.
    - Normaliza numeración.
    - Convierte '-' o '*' al inicio de línea en viñetas '• ' (solo para vista).
    """
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    texto = re.sub(r'(^|\n)\s*###\s*', r'\1', texto)
    texto = re.sub(r'(^|\n)\s*##\s*',  r'\1', texto)

    texto = normaliza_numeracion(texto)

    texto = re.sub(r'(^|\n)\s*-\s+', r'\1• ', texto)
    texto = re.sub(r'(^|\n)\s*\*\s+', r'\1• ', texto)

    return texto.strip()


def to_markdown_preview(texto_limpio: str) -> str:
    """
    Convierte el texto limpio en Markdown “bonito”:
    - Líneas que empiezan con 'N. ' se muestran en **negrita** (títulos).
    - Viñetas '• ' pasan a '- ' (para que Streamlit las pinte como bullets).
    """
    md_lines = []
    for raw in texto_limpio.splitlines():
        line = raw.rstrip()
        if not line.strip():
            md_lines.append("")
            continue

        if re.match(r'^\s*\d+\.\s+', line):
            # Título con numeración simple: lo marcamos en negrita
            md_lines.append(f"**{line.strip()}**")
        elif line.strip().startswith("• "):
            md_lines.append("- " + line.strip()[2:])
        else:
            md_lines.append(line)
    return "\n".join(md_lines)


# =========================================
#  GENERACIÓN DE WORD
# =========================================
def generar_word(informe_texto: str) -> BytesIO:
    """
    Construye un DOCX elegante en blanco y negro con el contenido ya normalizado.
    """
    doc = Document()

    # Márgenes y portada
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Logo centrado (si existe)
    try:
        p = doc.add_paragraph()
        run_logo = p.add_run()
        run_logo.add_picture("images/logo.png", width=Inches(1.8))
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    # Títulos de portada
    pt = doc.add_paragraph("Gemini Assist")
    pt.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = pt.runs[0]
    run.font.size = Pt(26)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)

    stit = doc.add_paragraph("Informe Predictivo de Mantenimiento")
    stit.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    stit.runs[0].font.size = Pt(13)
    stit.runs[0].font.color.rgb = RGBColor(90, 90, 90)

    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    fecha.runs[0].font.size = Pt(11)
    fecha.runs[0].font.color.rgb = RGBColor(70, 70, 70)

    doc.add_page_break()

    # Contenido (ya limpio y normalizado)
    texto = normaliza_numeracion(informe_texto)
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    texto = re.sub(r'(^|\n)\s*###\s*', r'\1', texto)

    for raw in texto.splitlines():
        line = raw.strip()
        if not line:
            doc.add_paragraph("")
            continue

        if re.match(r'^\d+\.\s+', line):
            # Cabecera de sección (Heading 2)
            h = doc.add_paragraph()
            r = h.add_run(line)
            r.bold = True
            r.font.size = Pt(14)
        elif line.startswith("• "):
            # Viñetas
            p = doc.add_paragraph(line[2:], style="List Bullet")
            p.runs[0].font.size = Pt(11)
        else:
            # Párrafos
            p = doc.add_paragraph(line)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            p.runs[0].font.size = Pt(11)

    # Exportar
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# =========================================
#  UI: SUBIDA Y GENERACIÓN
# =========================================
uploaded_file = st.file_uploader("📂 Sube el archivo de activos (Excel)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error leyendo Excel: {e}")
        st.stop()

    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df, use_container_width=True)

    if st.button("🚀 Generar Informe", type="primary"):
        with st.spinner("🧠 Generando informe con Gemini Assist..."):
            try:
                tabla_texto = df.to_string(index=False)

                user_prompt = f"""
A continuación tienes la tabla de activos hospitalarios (Excel textual):

{tabla_texto}

Con esa tabla, genera el informe con exactamente las secciones y reglas indicadas en las instrucciones del sistema.
Recuerda: sin símbolos Markdown, numeración simple (1., 2., 3., 4.) y viñetas simples.
"""

                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=SYSTEM_INSTRUCTIONS
                )
                response = model.generate_content(user_prompt)
                informe = (response.text or "").strip()

                if not informe:
                    st.error("⚠️ No se obtuvo respuesta del modelo.")
                    st.stop()

                # Vista previa (limpia + markdown elegante)
                preview_clean = limpiar_para_preview(informe)
                preview_md = to_markdown_preview(preview_clean)

                st.subheader("📝 Vista previa del informe")
                st.markdown(preview_md)

                # Botón de descarga (Word)
                word_bytes = generar_word(preview_clean)
                st.download_button(
                    label="⬇️ Descargar Informe (Word)",
                    data=word_bytes,
                    file_name="informe_predictivo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"❌ Error al generar el informe: {e}")
