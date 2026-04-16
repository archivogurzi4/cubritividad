import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="Calculador de Tintas", layout="wide")
st.title("🖨️ Calculador de Cubritividad (CMYK + Pantones)")
st.markdown("Sube tus PDFs para analizar el consumo de tinta de cada chapa.")

uploaded_files = st.file_uploader("Arrastrá tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Calcular Cubritividad", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                resultados = []
                progress_bar = st.progress(0)
                
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    
                    # --- SISTEMA ANTIFALLOS PARA LECTURA DE CHAPAS ---
                    lista_colores = None
                    try:
                        # Intento 1: Método moderno
                        lista_colores = page.get_separation_names()
                    except:
                        try:
                            # Intento 2: Método clásico
                            seps = page.get_separations()
                            if seps:
                                lista_colores = [s[0] for s in seps]
                        except:
                            # Intento 3: Si todo falla, forzar CMYK
                            lista_colores = None
                    # -------------------------------------------------

                    res_pag = {"Página": page_index + 1}
                    
                    if lista_colores:
                        nombres = lista_colores
                        usar_separacion = True
                    else:
                        nombres = ["Cyan", "Magenta", "Yellow", "Black"]
                        usar_separacion = False

                    for i, nombre in enumerate(nombres):
                        try:
                            pix = page.get_pixmap(colorspace=fitz.csGRAY, separation=i if usar_separacion else None)
                            img = np.frombuffer(pix.samples, dtype=np.uint8)
                            cubritividad = (np.sum(img < 252) / len(img)) * 100
                            res_pag[nombre] = cubritividad
                        except:
                            res_pag[nombre] = 0.0
                    
                    resultados.append(res_pag)
                    progress_bar.progress((page_index + 1) / len(doc))

                df = pd.DataFrame(resultados).fillna(0)
                columnas = [c for c in df.columns if c != "Página"]
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.write("**PROMEDIO TOTAL (%)**")
                    resumen = df[columnas].mean().to_frame("Promedio").round(2)
                    st.table(resumen.style.format("{:.2f}%"))
                    
                with col2:
                    st.write("**DETALLE POR PÁGINA (%)**")
                    st.dataframe(df.style.format({col: "{:.2f}%" for col in columnas}), use_container_width=True)
                
                st.divider()
                
            except Exception as e:
                st.error(f"Error procesando el archivo: {e}")
