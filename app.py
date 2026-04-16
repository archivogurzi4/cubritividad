import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP de Bolsillo Pro", layout="wide")
st.title("🖨️ Calculador de Cubritividad (CMYK + Pantones)")
st.markdown("Herramienta técnica de alta precisión para preprensa.")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Calcular Cubritividad Real", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # 1. Cargar el documento de forma segura
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                
                if len(doc) == 0:
                    st.error("El archivo parece estar vacío o protegido.")
                    continue

                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # La fila de datos siempre empieza con la página
                    fila = {"Página": int(page_num + 1)}

                    # --- CMYK: RENDERIZADO DIRECTO ---
                    # Renderizamos a 72 DPI para velocidad, espacio CMYK (4 canales)
                    pix = page.get_pixmap(colorspace=fitz.csCMYK, dpi=72)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
                    
                    canales_cmyk = ["Cyan", "Magenta", "Yellow", "Black"]
                    for i, nombre in enumerate(canales_cmyk):
                        canal = img[:, :, i]
                        # Contamos píxeles con tinta (valor > 2 para ignorar ruido)
                        fila[nombre] = (np.count_nonzero(canal > 2) / canal.size) * 100

                    # --- PANTONES: SEPARACIONES TÉCNICAS ---
                    try:
                        seps = page.get_separations()
                        if seps:
                            for i, sep in enumerate(seps):
                                nombre_tinta = sep[0]
                                # Renderizamos solo esa chapa de separación
                                pix_s = page.get_pixmap(colorspace=fitz.csGRAY, separation=i, dpi=72)
                                img_s = np.frombuffer(pix_s.samples, dtype=np.uint8)
                                # En escala de grises, el negro (tinta) es valor bajo
                                fila[nombre_tinta] = (np.count_nonzero(img_s < 250) / img_s.size) * 100
                    except:
                        pass # Si falla un Pantone, al menos tenemos el CMYK

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # --- PROCESAMIENTO DE LA TABLA ---
                if len(resultados) > 0:
                    # Convertimos a DataFrame y limpiamos
                    df = pd.DataFrame(resultados)
                    
                    # Reordenar columnas para que 'Página' esté primero
                    columnas_fijas = ["Página", "Cyan", "Magenta", "Yellow", "Black"]
                    # Buscamos qué Pantones se encontraron en total
                    columnas_pantone = [c for c in df.columns if c not in columnas_fijas]
                    
                    # Armamos el orden final y llenamos huecos con 0.0
                    orden_final = columnas_fijas + columnas_pantone
                    df = df.reindex(columns=orden_final).fillna(0.0)
                    
                    # Mostrar Totales
                    st.write("### 📊 Consumo Promedio")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Cubritividad (%)")
                    st.table(resumen.style.format("{:.2f}%"))

                    # Mostrar Detalle
                    st.write("### 📄 Detalle por Pliego / Página")
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error en el proceso: {e}")
