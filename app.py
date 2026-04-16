import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP Latino v5", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Análisis de separaciones reales (CMYK + Pantones).")

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

                    # 1. Obtener nombres de las separaciones
                    try:
                        seps_list = page.get_separations()
                        nombres_spot = [s[0] for s in seps_list]
                    except:
                        nombres_spot = []
                    
                    chapas_base = ["Cyan", "Magenta", "Yellow", "Black"]
                    todas_las_chapas = chapas_base + nombres_spot

                    # 2. Analizar cada chapa
                    for i, nombre in enumerate(todas_las_chapas):
                        try:
                            # 'separations' en plural es el estándar actual
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separations=i, 
                                dpi=72
                            )
                            
                            img = np.frombuffer(pix.samples, dtype=np.uint8)
                            
                            # LÓGICA DE PREPRENSA:
                            # En escala de grises, 255 es Blanco (Papel) y 0 es Negro (Tinta).
                            # Calculamos cuánta tinta (oscuridad) hay:
                            tinta_detectada = 255 - np.mean(img)
                            porcentaje = (max(0, tinta_detectada) / 255) * 100
                            fila[nombre] = porcentaje
                        except:
                            fila[nombre] = 0.0

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # 3. Mostrar tablas
                if resultados:
                    df = pd.DataFrame(resultados).fillna(0.0)
                    # Asegurar orden de columnas
                    cols_presentes = [c for c in chapas_base if c in df.columns]
                    cols_extras = [c for c in df.columns if c not in chapas_base and c != "Página"]
                    df = df[["Página"] + cols_presentes + cols_extras]

                    st.write("### 📊 Cubritividad Promedio")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Total %")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Detalle por Página")
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)

            except Exception as e:
                st.error(f"Error en el motor: {e}")
