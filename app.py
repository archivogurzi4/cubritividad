import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="Calculador de Tintas", layout="wide")
st.title("🖨️ Calculador de Cubritividad (CMYK + Pantones)")
st.markdown("Sube tus PDFs para analizar el consumo de tinta real.")

uploaded_files = st.file_uploader("Arrastrá tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Calcular Cubritividad", type="primary"):
        for uploaded_file in uploaded_files:
            st.subheader(f"📄 Archivo: {uploaded_file.name}")
            
            try:
                # Leemos el archivo
                file_bytes = uploaded_file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                resultados = []
                progress_bar = st.progress(0)
                
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    
                    # 1. Intentamos obtener separaciones de forma segura
                    try:
                        seps = page.get_separations()
                        # Si existen separaciones (Pantones), las usamos
                        if seps:
                            nombres = [s[0] for s in seps]
                            usar_sep = True
                        else:
                            # Si no hay, forzamos CMYK estándar
                            nombres = ["Cyan", "Magenta", "Yellow", "Black"]
                            usar_sep = False
                    except:
                        nombres = ["Cyan", "Magenta", "Yellow", "Black"]
                        usar_sep = False

                    res_pag = {"Página": page_index + 1}
                    
                    for i, nombre in enumerate(nombres):
                        try:
                            # Renderizado en alta precisión (escala de grises de la chapa)
                            # separation=i le dice al motor: "Mostrame solo esta chapa"
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separation=i if usar_sep else None,
                                # Si no hay separaciones, forzamos el canal CMYK i (0=C, 1=M, 2=Y, 3=K)
                            )
                            
                            # Si no se usó separación forzada, extraemos el canal CMYK manualmente
                            if not usar_sep:
                                pix = page.get_pixmap(colorspace=fitz.csCMYK)
                                img_full = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
                                canal_data = img_full[:, :, i]
                                # En CMYK de PyMuPDF, los valores altos (255) suelen ser 100% tinta
                                cubritividad = (np.sum(canal_data > 2) / canal_data.size) * 100
                            else:
                                img = np.frombuffer(pix.samples, dtype=np.uint8)
                                # En escala de grises, los oscuros (<250) son tinta
                                cubritividad = (np.sum(img < 250) / len(img)) * 100
                                
                            res_pag[nombre] = cubritividad
                        except:
                            res_pag[nombre] = 0.0
                    
                    resultados.append(res_pag)
                    progress_bar.progress((page_index + 1) / len(doc))

                # Generar reporte
                df = pd.DataFrame(resultados).fillna(0)
                columnas = [c for c in df.columns if c != "Página"]
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write("**PROMEDIO POR TINTA**")
                    display_df = df[columnas].mean().to_frame("Total").round(2)
                    st.table(display_df.style.format("{:.2f}%"))
                
                with col2:
                    st.write("**DETALLE PÁGINA A PÁGINA**")
                    st.dataframe(df.style.format({col: "{:.2f}%" for col in columnas}), use_container_width=True)
                
                st.divider()
                
            except Exception as e:
                st.error(f"Error crítico: {e}")
