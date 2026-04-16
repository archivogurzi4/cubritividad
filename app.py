import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="Calculador de Tintas Pro", layout="wide")
st.title("🖨️ Calculador de Cubritividad (CMYK + Pantones)")
st.markdown("Herramienta técnica para preprensa y presupuestación.")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Calcular Cubritividad Real", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # 1. Cargar el documento
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    res_pag = {"Página": page_num + 1}

                    # --- MÉTODO 1: CMYK DE PROCESO (RENDERIZADO DIRECTO) ---
                    # Renderizamos la página en espacio de color CMYK (4 canales)
                    pix = page.get_pixmap(colorspace=fitz.csCMYK, dpi=72) # 72 dpi sobra para cubritividad
                    # Convertimos a matriz numérica (Alto, Ancho, 4 canales)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
                    
                    # En PyMuPDF CMYK: 0 = sin tinta, 255 = 100% tinta
                    # Calculamos cada canal del CMYK
                    canales_nombres = ["Cyan", "Magenta", "Yellow", "Black"]
                    for i, nombre in enumerate(canales_nombres):
                        canal = img[:, :, i]
                        # Contamos píxeles con al menos un 1% de tinta (valor > 2)
                        porcentaje = (np.count_nonzero(canal > 2) / canal.size) * 100
                        res_pag[nombre] = porcentaje

                    # --- MÉTODO 2: BÚSQUEDA DE PANTONES (SPOT COLORS) ---
                    try:
                        # Intentamos extraer nombres de tintas planas
                        seps = page.get_separations()
                        if seps:
                            for i, sep in enumerate(seps):
                                nombre_pantone = sep[0]
                                # Para cada Pantone, renderizamos su chapa específica
                                # La chapa de separación suele venir en escala de grises (oscuro = tinta)
                                pix_sep = page.get_pixmap(colorspace=fitz.csGRAY, separation=i)
                                img_sep = np.frombuffer(pix_sep.samples, dtype=np.uint8)
                                # En escala de grises: 255 es blanco, < 250 es presencia de tinta
                                perc_sep = (np.sum(img_sep < 250) / img_sep.size) * 100
                                res_pag[nombre_pantone] = perc_sep
                    except:
                        pass # Si no hay Pantones o falla la lectura, seguimos con CMYK

                    resultados.append(res_pag)
                    bar.progress((page_num + 1) / len(doc))

                # --- MOSTRAR RESULTADOS ---
                df = pd.DataFrame(resultados).fillna(0)
                # Reordenar columnas: Página primero, luego el resto
                cols = ["Página"] + [c for c in df.columns if c != "Página"]
                df = df[cols]
                
                # Resumen de totales
                st.write("### 📊 Promedios de consumo (Toda la tirada)")
                resumen = df.drop(columns=["Página"]).mean().to_frame("Promedio Total (%)")
                st.table(resumen.style.format("{:.2f}%"))

                # Tabla detallada
                st.write("### 📄 Detalle por página")
                st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico al procesar: {e}")
