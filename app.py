import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP Latino v7", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Análisis de chapas reales (CMYK + Pantones).")

uploaded_files = st.file_uploader("Subí tus PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Ejecutar Análisis de Precisión", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # 1. Cargar el documento
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                
                if len(doc) == 0:
                    st.error("Archivo vacío.")
                    continue

                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    fila = {"Página": int(page_num + 1)}

                    # 2. Detectar nombres de tintas
                    try:
                        seps = page.get_separations()
                        nombres_spot = [s[0] for s in seps]
                    except:
                        nombres_spot = []
                    
                    chapas_proceso = ["Cyan", "Magenta", "Yellow", "Black"]
                    todas_las_chapas = chapas_proceso + nombres_spot

                    # 3. Analizar cada canal
                    for i, nombre in enumerate(todas_las_chapas):
                        try:
                            # Renderizamos la chapa específica
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separations=i, 
                                dpi=72
                            )
                            img = np.frombuffer(pix.samples, dtype=np.uint8)
                            
                            # CÁLCULO DE DENSIDAD (Para evitar el 0% constante)
                            # En preimpresión 255=Papel, 0=Tinta. 
                            # Invertimos para obtener la carga real.
                            carga_tinta = 255 - np.mean(img)
                            porcentaje = (max(0, carga_tinta) / 255) * 100
                            fila[nombre] = porcentaje
                        except:
                            fila[nombre] = 0.0

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # 4. Mostrar Resultados
                if resultados:
                    df = pd.DataFrame(resultados).fillna(0.0)
                    
                    # Ordenar columnas
                    cols_presentes = [c for c in chapas_proceso if c in df.columns]
                    cols_extra = [c for c in df.columns if c not in chapas_proceso and c != "Página"]
                    df = df[["Página"] + cols_presentes + cols_extra]

                    st.write("### 📊 Promedio por Tinta")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Cubritividad (%)")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Detalle por Página")
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico: {e}")
