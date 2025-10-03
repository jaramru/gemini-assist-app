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
# Configuración general
# ==============================
st.set_page_config(page_title="Gemini Assist – Informe Predictivo", layout="wide")

# Logo (cabecera simple, sin panel lateral)
try:
    st.image("images/logo.png", width=150)
except Exception:
    pass

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")


# ==============================
# API Key (sin panel lateral)
# ==============================
def get_api_key() -> str | None:
    # 1) st.secrets
    if hasattr(st, "secrets") and "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    # 2) Variables de entorno
    return os.getenv("GOOGLE_API_KEY")


API_KEY = get_api_key()
if not API_KEY:
    st.error(
        "❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets con:\n\n"
        '`GOOGLE_API_KEY="tu_clave"`'
    )
else:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        st.error(f"⚠️ Error configurando la API KEY: {e}")


# ==============================
# Utilidades de limpieza y formato
# ==============================
_bullet_regex = re.compile(r"^\s*[-•]\s*")

def normaliza_numeracion(linea: str) -> str:
    """
    Arregla encabezados del tipo '1. 1. Título' → '1. Título'
    y también elimina numeraciones duplicadas como '2. 2. 2.' etc.
    """
    # Quita repeticiones del patrón: "d. " repetido
    linea = re.sub(r"^(\s*\d+\.\s+)(\d+\.\s+)+", r"\1", linea)
    return linea

def limpiar_texto_base(texto: str) -> str:
    """
    - Elimina **negritas** Markdown (se aplicará negrita en Word o con Markdown controlado).
    - Quita asteriscos sueltos.
    - Convierte bullets '-', '*' a '• ' para homogeneidad.
    - Normaliza numeración duplicada tipo '1. 1.'
    """
    # Quitar **negritas** de Markdown
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)

    # Sustituir bullets comunes por •
    lineas = []
    for raw in texto.splitlines():
        l = raw.rstrip()

        # Normalización de numeración
        l = normaliza_numeracion(l)

        # Reemplazos de bullets: "* ", "- "
        if re.match(r"^\s*[\*\-]\s+", l):
            l = re.sub(r"^\s*[\*\-]\s+", "• ", l)

        # Eliminar asteriscos sueltos restantes
        if "*" in l:
            l = l.replace("*", "")

        lineas.append(l)

    return "\n".join(lineas).strip()

def es_encabezado(linea: str) -> bool:
    """
    Consideramos encabezado una línea que:
    - Comienza por número + punto + espacio (e.g., '1. ...'), o
    - Contiene frases típicas de sección del informe.
    """
    if re.match(r"^\d+\.\s", linea.strip()):
        return True

    # Fallback por si el modelo no numera algún título, detectamos frases comunes:
    patrones = [
        "Acciones Preventivas", "Acciones preventivas",
        "Estimación de ahorro", "Estimacion de ahorro",
        "Panel de alertas", "Informe ejecutivo",
    ]
    return any(pat.lower() in linea.lower() for pat in patrones)


# ==============================
# Generación de DOCX (sin “Resumen de activos”)
# ==============================
def generar_word(informe: str) -> BytesIO:
    doc = Document()

    # Márgenes y portada
    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)

    # Logo
    try:
        p_logo = doc.add_paragraph()
        r_logo = p_logo.add_run()
        r_logo.add_picture("images/logo.png", width=Inches(2))
        p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    # Título portada
    tit = doc.add_paragraph("Gemini Assist")
    tit.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rt = tit.runs[0]
    rt.bold = True
    rt.font.size = Pt(26)

    subt = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    subt.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rs = subt.runs[0]
    rs.font.size = Pt(13)
    rs.font.color.rgb = RGBColor(90, 90, 90)

    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rf = fecha.runs[0]
    rf.font.size = Pt(11)
    rf.font.color.rgb = RGBColor(90, 90, 90)

    doc.add_page_break()

    # Contenido (sin “Resumen de activos”)
    texto = limpiar_texto_base(informe)

    for raw in texto.splitlines():
        linea = raw.strip()
        if not linea:
            continue

        # Encabezado
        if es_encabezado(linea):
            p = doc.add_paragraph()
            r = p.add_run(linea)
            r.bold = True
            r.font.size = Pt(13)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            continue

        # Bullet
        if _bullet_regex.match(linea):
            p = doc.add_paragraph(linea[_bullet_regex.match(linea).end():], style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            for run in p.runs:
                run.font.size = Pt(11)
            continue

        # Párrafo normal
        p = doc.add_paragraph(linea)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        for run in p.runs:
            run.font.size = Pt(11)

    # Exportar
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ==============================
# Interfaz principal
# ==============================
st.subheader("📎 Sube el archivo de activos (Excel)")
uploaded_file = st.file_uploader("Arrastra y suelta, o pulsa en **Browse files**", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df.head(50), use_container_width=True)

        if st.button("🚀 Generar Informe", type="primary"):
            with st.spinner("🧠 Generando informe con Gemini Assist..."):
                try:
                    # Preparamos texto de la tabla (no incluimos resumen en Word)
                    tabla_texto = df.to_string(index=False)

                    prompt = f"""
Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.

Analiza la siguiente tabla de activos y genera **EXCLUSIVAMENTE** el contenido del informe (sin tablas y sin “Resumen de activos”):

{tabla_texto}

Secciones que debes entregar (texto, bien redactado, sin Markdown y sin asteriscos):
1. Acciones preventivas para los 3 activos más críticos.
   - Usa viñetas con “•” (no asteriscos).
2. Estimación de ahorro en € y horas si se aplican esas medidas.
   - Usa viñetas con “•”.
3. Panel de alertas por activo (Bajo, Medio, Alto).
   - Viñetas “•”.
4. Informe ejecutivo final (máximo 5 líneas).
   - Párrafo directo, sin viñetas.

Reglas:
- No uses **negritas** ni # ni * (no Markdown).
- Numera los títulos como “1. ...”, “2. ...” (sin repetir “1. 1.”).
- Usa “• ” para viñetas dentro de cada sección.
- Redacción profesional, clara, en español.
"""

                    model = genai.GenerativeModel("gemini-2.5-flash")
                    resp = model.generate_content(prompt)
                    informe_raw = resp.text or ""

                    # Limpieza/normalización
                    informe_limpio = limpiar_texto_base(informe_raw)

                    # Presentación en pantalla con títulos en negrita y viñetas
                    st.subheader("📄 Informe (vista previa)")
                    vista_md = []
                    for raw in informe_limpio.splitlines():
                        l = raw.strip()
                        if not l:
                            continue
                        if es_encabezado(l):
                            vista_md.append(f"**{l}**")
                        elif _bullet_regex.match(l):
                            # Mostrar como lista Markdown limpia
                            vista_md.append(f"- {l[_bullet_regex.match(l).end():]}")
                        else:
                            vista_md.append(l)
                    st.markdown("\n\n".join(vista_md))

                    # DOCX
                    word_bytes = generar_word(informe_limpio)
                    st.download_button(
                        "⬇️ Descargar Informe (Word)",
                        data=word_bytes,
                        file_name="informe_predictivo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

                except Exception as e:
                    st.error(f"❌ Error al generar el informe: {e}")

    except Exception as e:
        st.error(f"❌ No se pudo leer el Excel: {e}")

else:
    st.info("Carga un archivo .xlsx para comenzar.")
