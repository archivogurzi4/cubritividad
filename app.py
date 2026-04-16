import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP Latino v4", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Inspirado en el estándar Ghostscript para preprensa profesional.")

uploaded_files = st.file_uploader("Subí tus PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Ejecutar Análisis de Precisión", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    fila = {"Página": int(page_num + 1)}

                    # 1. Detectar todas las separaciones (CMYK + Spots)
                    try:
                        seps = page.get_separations()
                        nombres_tinta = [s[0] for s in seps]
                    except:
                        nombres_tinta = []
                    
                    chapas_proceso = ["Cyan", "Magenta", "Yellow", "Black"]
                    todas_las_chapas = chapas_proceso + nombres_tinta

                    # 2. Analizar cada chapa de forma independiente
                    for i, nombre in enumerate(todas_las_chapas):
                        # Forzamos el renderizado de la separación específica 'i'
                        # Usamos colorespace GRAY para medir densidad de chapa única
                        pix = page.get_pixmap(colorspace=fitz.csGRAY, separation=i, dpi=72)
                        
                        # Convertimos a array de NumPy
                        img = np.frombuffer(pix.samples, dtype=np.uint8)
                        
                        # Lógica Crucial: En preprensa 0 es papel (blanco) y 255 es tinta (sólido)
                        # Si el motor lo entrega invertido, esta fórmula lo normaliza:
                        densidad_media = np.mean(img)
                        
                        # Calculamos el porcentaje real basado en la densidad de la chapa
                        porcentaje = (densidad_media / 255) * 100
                        fila[nombre] = porcentaje

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # 3. Presentación de Datos
                if resultados:
                    df = pd.DataFrame(resultados).fillna(0.0)
                    # Ordenar columnas para que CMYK esté primero
                    cols = [c for c in chapas_proceso if c in df.columns] + \
                           [c for c in df.columns if c not in chapas_proceso and c != "Página"]
                    
                    df = df[["Página"] + cols]

                    st.write("### 📊 Resumen de Consumo (Promedio del PDF)")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Cubritividad %")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Detalle por Página")
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)

            except Exception as e:
                st.error(f"Error en el motor: {e}")
