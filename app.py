import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="Calculador de Tintas Pro", layout="wide")
st.title("🖨️ Calculador de Cubritividad (Separación Real)")
st.markdown("Análisis de chapas individuales: CMYK + Tintas Planas (Pantones).")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Analizar Separaciones", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # Cargamos el documento
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    fila = {"Página": int(page_num + 1)}

                    # 1. Lista de separaciones técnicas (Pantones)
                    try:
                        spot_list = page.get_separations()
                    except:
                        spot_list = []

                    # 2. Definimos tintas de proceso
                    procesos = ["Cyan", "Magenta", "Yellow", "Black"]
                    total_chapas = 4 + len(spot_list)

                    for i in range(total_chapas):
                        # Asignamos nombre según el ID de chapa
                        if i < 4:
                            nombre_chapa = procesos[i]
                        else:
                            nombre_chapa = spot_list[i-4][0]

                        try:
                            # Renderizamos SOLO la chapa i (Independencia total)
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separation=i, 
                                dpi=72
                            )
                            img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                            
                            # Medimos presencia de tinta en esa chapa específica
                            # (Menos de 250 en escala de grises es tinta)
                            area_tinta = np.count_nonzero(img_data < 250)
                            porcentaje = (area_tinta / img_data.size) * 100
                            fila[nombre_chapa] = porcentaje
                        except:
                            fila[nombre_chapa] = 0.0

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # --- GENERACIÓN DE TABLAS ---
                if resultados:
                    df = pd.DataFrame(resultados)
                    cols_basicas = ["Página", "Cyan", "Magenta", "Yellow", "Black"]
                    cols_extras = [c for c in df.columns if c not in cols_basicas]
                    
                    df = df.reindex(columns=cols_basicas + cols_extras).fillna(0.0)
                    
                    st.write("### 📊 Promedio por Chapa / Separación")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Cubritividad (%)")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Detalle por Página")
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                # Cerramos el bloque de este archivo con un divisor
                st.divider()

            except Exception as e:
                # Este es el bloque que faltaba o estaba mal movido
                st.error(f"Error crítico al analizar el archivo: {e}")
