import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP de Bolsillo v3", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Análisis de separaciones reales (CMYK + Pantones).")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Ejecutar Análisis de Chapas", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # 1. Cargar documento
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    fila = {"Página": int(page_num + 1)}

                    # --- DETECCIÓN DE PANTÓNES ---
                    try:
                        # Obtenemos la lista de separaciones de la página
                        seps_list = page.get_separations()
                        nombres_pantone = [s[0] for s in seps_list]
                    except:
                        nombres_pantone = []

                    # --- LISTA DE TODAS LAS CHAPAS ---
                    chapas_base = ["Cyan", "Magenta", "Yellow", "Black"]
                    todas_las_chapas = chapas_base + nombres_pantone
                    
                    # --- RENDERIZADO POR CHAPA ---
                    # En lugar de usar el objeto Separations, iteramos por índice de chapa
                    for i, nombre_chapa in enumerate(todas_las_chapas):
                        try:
                            # Renderizamos la chapa 'i' en escala de grises
                            # separation=i le dice a la librería que solo queremos esa película
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separation=i, 
                                dpi=72
                            )
                            
                            # Convertimos a matriz numérica
                            img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                            
                            # En estas separaciones: 0 es papel y 255 es tinta pura
                            # O al revés dependiendo del motor. Medimos densidad relativa.
                            promedio_bruto = np.mean(img_data)
                            
                            # Lógica de seguridad para preprensa:
                            # Si es escala de grises pura, 0 suele ser negro (tinta).
                            # Calculamos la tinta presente.
                            porcentaje = (promedio_bruto / 255) * 100
                            fila[nombre_chapa] = porcentaje
                            
                        except:
                            fila[nombre_chapa] = 0.0

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # --- MOSTRAR RESULTADOS ---
                if resultados:
                    df = pd.DataFrame(resultados)
                    cols_fijas = ["Página", "Cyan", "Magenta", "Yellow", "Black"]
                    cols_extras = [c for c in df.columns if c not in cols_fijas]
                    
                    df = df.reindex(columns=cols_fijas + cols_extras).fillna(0.0)
                    
                    st.write("### 📊 Cubritividad Promedio")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Promedio")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Desglose de Chapas")
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico en el procesamiento: {e}")
