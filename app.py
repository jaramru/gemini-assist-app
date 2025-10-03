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

# -----------------------------
# Configuración de página
# -----------------------------
st.set_page_config(page_title="Gemini Assist – Informe Predictivo", layout="wide")

# Logo (opcional)
LOGO_PATH = "images/logo.png"
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=140)

st.title("🔧 Gemini Assist – Informe Predictivo de Mantenimiento")

# -----------------------------
# API KEY (secrets / envvar)
# -----------------------------
api_key = None
try:
    api_key = st.secrets["GOOGLE_API_KEY"]  # Streamlit Cloud -> Settings -> Secrets
except Exception:
    api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error(
        "❌ No se encontró la API KEY. "
        "Configúrala en *Streamlit Cloud → Settings → Secrets* con:\n\n"
        "```\nGOOGLE_API_KEY=\"tu_clave\"\n```"
    )
    st.stop()

# Configurar SDK
genai.configure(api_key=api_key)

# -----------------------------
# Instrucciones del sistema
# -----------------------------
SYSTEM_INSTRUCTIONS = """
Eres Gemini Assist, un asistente experto en mantenimiento hospitalario.
Objetivo: generar un informe ejecutivo, claro y profesional (neutro, blanco y negro),
a partir de una tabla Excel de activos hospitalarios.

Estructura del informe:
1. Acciones preventivas para los 3 activos más críticos
   - Explica brevemente por qué son críticos (tipo, coste, horas de parada).
   - Propón acciones preventivas concretas y justificadas.
2. Estimación de ahorro en € y horas (si se aplican las medidas)
   - Totales y, cuando proceda, por activo.
3. Panel de alertas (clasificar cada activo: Bajo / Medio / Alto).
4. Informe ejecutivo (máx. 5 líneas) para Dirección.

Reglas de estilo:
- Español neutro, sin emojis ni símbolos llamativos.
- Nada de **asteriscos** de Markdown; usa frases limpias.
- Títulos y subtítulos claros (puedes usar mayúsculas iniciales).
- Texto normal justificado (lo aplicaré en la exportación).
- Cuando listes elementos, usa viñetas (•) o numeración.
- Evita duplicar numeraciones como “1. 1.”.

Si el usuario pide cambios (“itera”), reescribe el informe completo incorporando los cambios.
"""

# Crear modelo con instrucciones del sistema
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTIONS
)

# -----------------------------
# Utilidades
# -----------------------------
def limpiar_texto(texto: str) -> str:
    """Quita marcas típicas de Markdown (negritas, bullets '*') para evitar asteriscos en Word."""
    if not texto:
        return ""
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)              # **negrita**
    t = re.sub(r"(?m)^\*\s+", "", t)                       # líneas que empiezan con "* "
    t = re.sub(r"(?m)^-\s+", "", t)                        # líneas que empiezan con "- "
    t = t.replace("**", "")                                # restos de **
    t = t.replace("•", "• ")                               # asegurar espacio tras bullet
    return t.strip()

def generar_word(informe: str) -> BytesIO:
    """Crea un DOCX sencillo y limpio con portada + contenido."""
    doc = Document()

    # Márgenes
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Portada
    if os.path.exists(LOGO_PATH):
        p = doc.add_paragraph()
        run = p.add_run()
        run.add_picture(LOGO_PATH, width=Inches(2.2))
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    ttl = doc.add_paragraph("Gemini Assist")
    ttl.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = ttl.runs[0]
    run.font.size = Pt(26)
    run.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)

    sub = doc.add_paragraph("Informe Predictivo de Mantenimiento Hospitalario")
    sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = sub.runs[0]
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(90, 90, 90)

    fecha = doc.add_paragraph(datetime.now().strftime("%d/%m/%Y"))
    fecha.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = fecha.runs[0]
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # Cuerpo
    texto = limpiar_texto(informe)
    lines = [ln.strip() for ln in texto.split("\n")]

    # Heurística simple para headings: líneas terminadas en ":" o líneas muy cortas a modo de título
    for ln in lines:
        if not ln:
            continue

        # Encabezados “claros”
        if ln.endswith(":") or len(ln) <= 60 and ln.lower().startswith(("acciones preventivas", "estimación de ahorro", "panel de alertas", "informe ejecutivo")):
            p = doc.add_paragraph(ln.rstrip(":"))
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            r = p.runs[0]
            r.bold = True
            r.font.size = Pt(14)
            continue

        # Viñetas con "• " o "- "
        if ln.startswith("• ") or ln.startswith("- "):
            p = doc.add_paragraph(ln[2:], style="List Bullet")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            r = p.runs[0]
            r.font.size = Pt(11)
            continue

        # Listas numeradas "1. ...", "2. ..."
        if re.match(r"^\d+\.\s", ln):
            p = doc.add_paragraph(ln, style="List Number")
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            r = p.runs[0]
            r.font.size = Pt(11)
            continue

        # Párrafo normal
        p = doc.add_paragraph(ln)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        r = p.runs[0]
        r.font.size = Pt(11)

    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out

def prompt_para_datos(df: pd.DataFrame) -> str:
    """Genera el prompt de datos para el modelo (el grueso de reglas ya va en SYSTEM_INSTRUCTIONS)."""
    tabla_txt = df.to_string(index=False)
    return (
        "Analiza la siguiente tabla y genera el informe completo con los apartados previstos.\n\n"
        f"{tabla_txt}\n\n"
        "Recuerda: no uses asteriscos; usa viñetas o numeración normales y títulos claros."
    )

# -----------------------------
# UI: subir Excel
# -----------------------------
uploaded = st.file_uploader("📎 Sube el archivo de activos (Excel)", type=["xlsx"])
if not uploaded:
    st.info("Carga un archivo .xlsx para comenzar.")
    st.stop()

# Cargar tabla
try:
    df = pd.read_excel(uploaded)
    st.success("✅ Archivo cargado correctamente")
    st.dataframe(df, use_container_width=True, height=360)
except Exception as e:
    st.error(f"❌ No se pudo leer el Excel: {e}")
    st.stop()

# -----------------------------
# Estado de sesión
# -----------------------------
if "draft" not in st.session_state:
    st.session_state.draft = ""  # último borrador
if "tabla_cargada" not in st.session_state:
    st.session_state.tabla_cargada = df.copy()

# -----------------------------
# Botón: Generar informe directo (un clic)
# -----------------------------
st.markdown("### 🚀 Acciones")
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if st.button("⚡ Generar informe directo", type="primary", use_container_width=True):
        try:
            with st.spinner("Generando informe con Gemini..."):
                prompt = prompt_para_datos(df)
                resp = model.generate_content(prompt)
                texto = resp.text or ""
                st.session_state.draft = texto

            if not st.session_state.draft.strip():
                st.error("El modelo no devolvió texto. Prueba con menos filas/columnas o revisa los datos.")
            else:
                st.success("✅ Informe generado.")
        except Exception as e:
            st.error(f"❌ Error al generar el informe: {e}")

with col2:
    if st.button("🧠 Generar borrador con Gemini (para iterar)", use_container_width=True):
        try:
            with st.spinner("Creando borrador inicial..."):
                prompt = prompt_para_datos(df)
                resp = model.generate_content(prompt)
                st.session_state.draft = resp.text or ""
            st.success("✅ Borrador creado. Puedes pedir cambios abajo y luego exportar a Word.")
        except Exception as e:
            st.error(f"❌ Error creando el borrador: {e}")

# -----------------------------
# Vista previa + Iteración opcional
# -----------------------------
if st.session_state.draft:
    st.subheader("📄 Vista previa del informe")
    st.text_area("Contenido", st.session_state.draft, height=360, key="vista_prev", label_visibility="collapsed")

    with st.expander("💬 Afinar con una instrucción (opcional)"):
        user_msg = st.text_area("Indica los cambios que quieres (p.ej., 'convierte el panel de alertas en viñetas y resume el ejecutivo en 3 líneas'):", height=120)
        if st.button("Aplicar cambios", type="secondary"):
            if not user_msg.strip():
                st.warning("Escribe una instrucción antes de aplicar cambios.")
            else:
                try:
                    with st.spinner("Reescribiendo informe..."):
                        prompt_iter = (
                            "Reescribe el informe completo incorporando estos cambios del usuario.\n\n"
                            f"Solicitado por el usuario: {user_msg}\n\n"
                            "Informe actual:\n"
                            f"{st.session_state.draft}"
                        )
                        resp = model.generate_content(prompt_iter)
                        st.session_state.draft = resp.text or st.session_state.draft
                    st.success("✅ Cambios aplicados.")
                except Exception as e:
                    st.error(f"❌ Error iterando el informe: {e}")

    # Descargar Word
    st.divider()
    try:
        word_bytes = generar_word(st.session_state.draft)
        st.download_button(
            "⬇️ Descargar Informe Word",
            data=word_bytes,
            file_name="informe_predictivo.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Error generando el Word: {e}")
else:
    st.info("Pulsa **⚡ Generar informe directo** o **🧠 Generar borrador** para crear el informe.")
