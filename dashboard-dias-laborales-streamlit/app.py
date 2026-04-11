import streamlit as st

from io import BytesIO
import pandas as pd

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis
from src.visuals.charts import render_charts

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

    # Reglas de negocio
    df_procesado = aplicar_reglas_negocio(df_procesado)

    # Indicadores
    mostrar_kpis(df_procesado, duracion)

    # Gráficas
    render_charts(df_procesado)

    # Tabla final
    st.subheader("📂 Datos procesados")
    st.dataframe(df_procesado, use_container_width=True)
else:
    st.info("📂 Carga un archivo Excel y configura los filtros para iniciar el análisis.")
