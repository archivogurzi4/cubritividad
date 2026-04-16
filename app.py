import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="Calculador de Tintas Pro", layout="wide")
st.title("🖨️ Calculador de Cubritividad (CMYK + Pantones)")
st.markdown("Herramienta técnica de precisión para preprensa.")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Calcular Cubritividad Real", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # Cargar el documento
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                resultados = []
                bar = st.progress(0)

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # Inicializamos la fila siempre con el número de página
                    res_pag = {"Página": int(page_num + 1)}

                    # --- 1. CMYK (RENDERIZADO) ---
                    pix = page.get_pixmap(colorspace=fitz.csCMYK, dpi=72)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
                    
                    canales_cmyk = ["Cyan", "Magenta", "Yellow", "Black"]
                    for i, nombre in enumerate(canales_cmyk):
                        canal = img[:, :, i]
                        # Umbral de sensibilidad para evitar 'ruido'
                        res_pag[nombre] = (np.count_nonzero(canal > 2) / canal.size) * 100

                    # --- 2. PANTONES / SPOT COLORS ---
                    try:
                        # Buscamos las chapas de tintas planas
                        seps = page.get_separations()
                        if seps:
                            for i, sep in enumerate(seps):
                                # sep[0] es el nombre de la tinta (ej. PANTONE 485 C)
                                nombre_spot = sep[0]
                                # Renderizamos la chapa específica
                                pix_sep = page.get_pixmap(colorspace=fitz.csGRAY, separation=i)
                                img_sep = np.frombuffer(pix_sep.samples, dtype=np.uint8)
                                # En escala de grises: 255=blanco, <250=tinta
                                res_pag[nombre_spot] = (np.count_nonzero(img_sep < 250) / img_sep.size) * 100
                    except:
                        pass # Si falla el spot, al menos ya tenemos el CMYK

                    resultados.append(res_pag)
                    bar.progress((page_num + 1) / len(doc))

                # --- PROCESAMIENTO DE TABLAS ---
                if resultados:
                    df = pd.DataFrame(resultados)
                    
                    # Aseguramos que 'Página' sea la primera columna
                    cols = ["Página"] + [c for c in df.columns if c != "Página"]
                    df = df[cols].fillna(0)
                    
                    # Totales
                    st.write("### 📊 Promedios de consumo")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Total (%)")
                    st.table(resumen.style.format("{:.2f}%"))

                    # Detalle
                    st.write("### 📄 Detalle por página")
                    # Convertimos página a entero para que no se vea como 1.0
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                else:
                    st.warning("No se pudieron extraer datos del archivo.")
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico: {e}")
