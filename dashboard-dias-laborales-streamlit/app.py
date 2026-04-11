import streamlit as st

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe

# Configuración inicial
setup_page()

# Sidebar y carga de datos
df, config = load_sidebar_data()

# Aplicación de filtros
if df is not None:
    if config["sedes_sel"]:
        df = df[df["NOMBRESEDE"].isin(config["sedes_sel"])]

    if config["seccion_sel"]:
        df = df[df["SECCION"].isin(config["seccion_sel"])]

# Procesamiento
if df is not None and config["procesar"]:
    df_procesado, duracion = process_dataframe(df, config)

    st.subheader("📊 Resultados")
    st.caption(f"⏱ Procesado en {duracion:.2f} segundos")

    st.dataframe(df_procesado, use_container_width=True)
else:
    st.info("📂 Carga un archivo Excel y configura los filtros para iniciar el análisis.")
