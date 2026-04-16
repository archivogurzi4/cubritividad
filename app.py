import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import pandas as pd

st.set_page_config(page_title="RIP Latino v6", layout="wide")
st.title("🖨️ Calculador de Cubritividad Técnica")
st.markdown("Análisis de separaciones reales (CMYK + Pantones).")

uploaded_files = st.file_uploader("Subí tus PDFs aquí", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Ejecutar Análisis de Precisión", type="primary"):
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
                    fila = {"Página": int(page_num + 1)}

                    # --- CMYK + PANTÓNES ---
                    # Obtenemos la lista de todas las tintas presentes
                    try:
                        seps = page.get_separations()
                        nombres_spot = [s[0] for s in seps]
                    except:
                        nombres_spot = []
                    
                    chapas_proceso = ["Cyan", "Magenta", "Yellow", "Black"]
                    todas_las_chapas = chapas_proceso + nombres_spot

                    # Analizamos cada canal por su índice absoluto en el PDF
                    for i, nombre in enumerate(todas_las_chapas):
                        try:
                            # Renderizamos la chapa 'i' (0-3 es CMYK, 4+ son Spots)
                            # 'separations' en plural es el estándar actual
                            pix = page.get_pixmap(
                                colorspace=fitz.csGRAY, 
                                separations=i, 
                                dpi=72
                            )
                            
                            img = np.frombuffer(pix.samples, dtype=np.uint8)
                            
                            # LÓGICA DE PREPRENSA:
                            # 255 es Blanco (Papel) y 0 es Tinta pura.
                            # Calculamos la densidad media de la chapa.
                            tinta_detectada = 255 - np.mean(img)
                            porcentaje = (max(0, tinta_detectada) / 255) * 100
                            fila[nombre] = porcentaje
                        except:
                            fila[nombre] = 0.0

                    resultados.append(fila)
                    bar.progress((page_num + 1) / len(doc))

                # --- PROCESAMIENTO DE LA TABLA ---
                if resultados:
                    df = pd.DataFrame(resultados).fillna(0.0)
                    
                    # Reordenar para que CMYK esté al principio
                    cols_base = [c for c in chapas_proceso if c in df.columns]
                    cols_pantone = [c for c in df.columns if c not in chapas_proceso and c != "Página"]
                    
                    df = df[["Página"] + cols_base + cols_pantone]
                    
                    st.write("### 📊 Consumo Promedio")
                    resumen = df.drop(columns=["Página"]).mean().to_frame("Cubritividad (%)")
                    st.table(resumen.style.format("{:.2f}%"))

                    st.write("### 📄 Detalle por Pliego / Página")
                    df["Página"] = df["Página"].astype(int)
                    st.dataframe(df.style.format({c: "{:.2f}%" for c in df.columns if c != "Página"}), use_container_width=True)
                
                st.divider()

            except Exception as e:
                st.error(f"Error técnico en el procesamiento: {e}")
