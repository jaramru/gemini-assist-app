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


# ======================================
# Configuración general (sin diagnóstico)
# ======================================
st.set_page_config(page_title="Gemini Assist – Informe Predictivo", layout="wide")

# Cabecera con logo
try:
    st.image("images/logo.png", width=150)
except Exception:
    pass

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")


# ==============================
# Lectura simple de API key
# (mantiene compatibilidad con tu setup previo)
# ==============================
def get_api_key() -> str | None:
    try:
        if "GOOGLE_API_KEY" in st.secrets and str(st.secrets["GOOGLE_API_KEY"]).strip():
            return str(st.secrets["GOOGLE_API_KEY"]).strip()
        if "API_KEY" in st.secrets and str(st.secrets["API_KEY"]).strip():
            return str(st.secrets["API_KEY"]).strip()
    except Exception:
        pass
    # Fallback variables de entorno si ejecutas local
    for name in ("GOOGLE_API_KEY", "API_KEY", "GEMINI_API_KEY"):
        v = os.getenv(name, "").strip()
        if v:
            return v
    return None


# ==============================
# Limpieza y formato del texto del modelo
# ==============================
_bullet_regex = re.compile(r"^\s*[-•]\s*")

def normaliza_numeracion(linea: str) -> str:
    # '1. 1. Título' -> '1. Título'
    return re.sub(r"^(\s*\d+\.\s+)(\d+\.\s+)+", r"\1", linea)

def limpiar_texto_base(texto: str) -> str:
    # quita **negritas** markdown y asteriscos sueltos;
    # homogeneiza viñetas a "• "
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    lineas = []
    for raw in texto.splitlines():
        l = raw.rstrip()
        l = normaliza_numeracion(l)
        if re.match(r"^\s*[\*\-]\s+", l):
            l = re.sub(r"^\s*[\*\-]\s+", "• ", l)
        if "*" in l:
            l = l.replace("*", "")
        # guiones raros a guion normal
        l = l.replace("–", "-").replace("—", "-")
        lineas.append(l)
    return "\n".join(lineas).strip()

def es_encabezado(linea: str) -> bool:
    if re.match(r"^\d+\.\s", linea.strip()):
        return True
    patrones = [
        "Acciones Preventivas", "Acciones preventivas",
        "Estimación de ahorro", "Estimacion de ahorro",
        "Panel de alertas", "Informe ejecutivo",
    ]
    return any(pat.lower() in linea.lower() for pat in patrones)


# ==============================
# Generación DOCX (sin resumen)
# ==============================
def generar_word(informe: str) -> BytesIO:
    doc = Document()

    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)

    # Portada
    try:
        p_logo = doc.add_paragraph()
        r_logo = p_logo.add_run()
        r_logo.add_picture("images/logo.png", width=Inches(2))
        p_logo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    except Exception:
        pass

    tit = doc.add_paragraph("Gemini Assist")
    tit.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rt = tit.runs[0]; rt.bold = True; rt.font.size = Pt(26)

    subt = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    subt.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rs = subt.runs[0]; rs.font.size = Pt(13); rs.font.color.rgb = RGBColor(90, 90, 90)

    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rf = fecha.runs[0]; rf.font.size = Pt(11); rf.font.color.rgb = RGBColor(90, 90, 90)

    doc.add_page_break()

    # Contenido (solo informe detallado)
    texto = limpiar_texto_base(informe)
    for raw in texto.splitlines():
        l = raw.strip()
        if not l:
            continue

        if es_encabezado(l):
            p = doc.add_paragraph()
            r = p.add_run(l)
            r.bold = True
            r.font.size = Pt(13)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            continue

        if _bullet_regex.match(l):
            p = doc.add_paragraph(l[_bullet_regex.match(l).end():], style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            for run in p.runs:
                run.font.size = Pt(11)
            continue

        p = doc.add_paragraph(l)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        for run in p.runs:
            run.font.size = Pt(11)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ==============================
# Modelo + System Instructions
# ==============================
MODEL_ID = "gemini-1.5-flash"  # ajusta si usas otro (p.ej. "gemini-2.5-flash")

SYSTEM_INSTRUCTIONS = """
Eres Gemini Assist, un sistema experto en mantenimiento hospitalario.

Reglas de estilo:
- Estilo neutro, profesional y en blanco y negro.
- No uses asteriscos (*) ni emojis.
- Usa títulos claros (ej. '1. Acciones preventivas...') y listas con viñetas (•) cuando corresponda.
- Redacción clara y concisa, justificada.

Estructura obligatoria del informe (en este orden):
1) Acciones preventivas para los 3 activos más críticos.
2) Estimación de ahorro en € y horas si se aplican esas medidas.
3) Panel de alertas clasificando cada activo en: Bajo, Medio o Alto.
4) Informe ejecutivo final (máximo 5 líneas).

Notas:
- No incluyas Markdown decorativo (##, ###) ni negritas con ** **.
- Evita símbolos raros (✔, ❌, etc.).
- No repitas numeración (nada de '1. 1.').
"""


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
                    api_key = get_api_key()
                    if not api_key:
                        st.error(
                            "❌ No se encontró la API KEY. Configúrala en Streamlit Cloud → Settings → Secrets con:\n\n"
                            'GOOGLE_API_KEY="tu_clave"  (o API_KEY)'
                        )
                        st.stop()

                    # Configurar Gemini aquí (solo cuando hace falta)
                    genai.configure(api_key=api_key)

                    # Crear modelo con system instructions (nuevo)
                    model = genai.GenerativeModel(
                        model=MODEL_ID,
                        system_instruction=SYSTEM_INSTRUCTIONS
                    )

                    # Prompt solo con datos y petición
                    tabla_texto = df.to_string(index=False)
                    prompt = f"""
Analiza la siguiente tabla de activos hospitalarios (texto) y genera el informe siguiendo estrictamente las instrucciones del sistema.

TABLA:
{tabla_texto}
"""

                    resp = model.generate_content(prompt)
                    informe_raw = (resp.text or "").strip()

                    # Limpieza/normalización
                    informe_limpio = limpiar_texto_base(informe_raw)

                    # Vista previa con títulos en negrita y viñetas
                    st.subheader("📄 Informe (vista previa)")
                    vista = []
                    for raw in informe_limpio.splitlines():
                        l = raw.strip()
                        if not l:
                            continue
                        if es_encabezado(l):
                            vista.append(f"**{l}**")
                        elif _bullet_regex.match(l):
                            vista.append(f"- {l[_bullet_regex.match(l).end():]}")
                        else:
                            vista.append(l)
                    st.markdown("\n\n".join(vista))

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
