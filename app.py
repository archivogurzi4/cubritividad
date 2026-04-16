import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP de Bolsillo Pro", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Análisis de separaciones reales para preprensa e imprenta.")

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

                    # --- GESTIÓN DE SEPARACIONES ---
                    # Creamos el objeto de control de chapas
                    seps = fitz.Separations(page)
                    nombres_spot = [page.get_separations()[i][0] for i in range(len(page.get_separations()))]
                    
                    # --- PASO A: CMYK PROCESO (Sin contaminación de Pantones) ---
                    # Desactivamos todos los Pantones para que no sumen al CMYK
                    for i in range(4, seps.count):
                        seps.set_status(i, 0) # 0 = Desactivado

                    # Renderizamos la página en CMYK usando solo las chapas de proceso
                    pix_cmyk = page.get_pixmap(colorspace=fitz.csCMYK, separations=seps, dpi=72)
                    img_cmyk = np.frombuffer(pix_cmyk.samples, dtype=np.uint8).reshape(pix_cmyk.height, pix_cmyk.width, 4)
                    
                    nombres_cmyk = ["Cyan", "Magenta", "Yellow", "Black"]
                    for idx, nombre in enumerate(nombres_cmyk):
                        canal = img_cmyk[:, :, idx]
                        # Cálculo de cubritividad real por densidad de chapa
                        fila[nombre] = (np.mean(canal) / 255) * 100

                    # --- PASO B: PANTÓNES (Chapas independientes) ---
                    for i in range(len(nombres_spot)):
                        nombre_p = nombres_spot[i]
                        # Creamos un render donde SOLO esté activo este Pantone
                        seps_p = fitz.Separations(page)
                        for j in range(seps_p.count):
                            # Apagamos todo menos el Pantone actual (que empieza en el índice 4)
                            seps_p.set_status(j, 1 if j == (i + 4) else 0)
                        
                        # Renderizamos en escala de grises para medir la chapa única
                        pix_p = page.get_pixmap(colorspace=fitz.csGRAY, separations=seps_p, dpi=72)
                        img_p = np.frombuffer(pix_p.samples, dtype=np.uint8)
                        
                        # En chapas individuales de PyMuPDF, el valor suele ser invertido (0=tinta)
                        # Aplicamos corrección de polaridad si es necesario
                        tinta_promedio = 255 - np.mean(img_p) 
                        fila[nombre_p] = (max(0, tinta_promedio) / 255) * 100

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # --- MOSTRAR RESULTADOS ---
                if resultados:
                    df = pd.DataFrame(resultados)
                    # Limpieza y orden de columnas
                    cols_fijas = ["Página", "Cyan", "Magenta", "Yellow", "Black"]
                    cols_spots = [c for c in df.columns if c not in cols_fijas]
                    df = df.reindex(columns=cols_fijas + cols_spots).fillna(0.0)
                    
                    st.write("### 📊 Totales de Cubritividad (%)")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Promedio Total")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Desglose por Página")
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico: {e}")
