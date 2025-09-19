from fpdf import FPDF
import streamlit as st

def generar_pdf(informe: str) -> bytes:
    class PDF(FPDF):
        def header(self):
            self.set_font("DejaVu", "", 12)
            self.cell(0, 10, "Gemini Assist – Informe de Mantenimiento Predictivo", align="C", ln=True)

        def footer(self):
            self.set_y(-15)
            self.set_font("DejaVu", "I", 8)
            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    pdf = PDF()
    pdf.add_page()

    # 🔹 Asegúrate de que las fuentes DejaVu están en tu repo
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)

    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 10, informe)

    # Guardar en memoria en lugar de archivo físico
    return pdf.output(dest="S").encode("latin1")


# =======================
# Dentro del flujo de Streamlit
# =======================

if st.button("Generar Informe PDF"):
    try:
        pdf_bytes = generar_pdf(informe)
        st.success("✅ Informe generado correctamente")

        # Botón de descarga
        st.download_button(
            label="📥 Descargar Informe en PDF",
            data=pdf_bytes,
            file_name="Informe_GeminiAssist.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"❌ Error al generar el PDF: {e}")
