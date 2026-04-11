import streamlit as st
import pandas as pd

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis
from src.visuals.charts import render_charts
from src.utils.export import dataframe_to_excel_bytes
from src.utils.dates import limpiar_fechas

# =========================
# SESSION STATE INICIAL
# =========================
if "df_procesado" not in st.session_state:
    st.session_state.df_procesado = None

if "duracion" not in st.session_state:
    st.session_state.duracion = None

# =========================
# CONFIGURACIÓN INICIAL
# =========================
setup_page()

# =========================
# SIDEBAR Y CARGA DE DATOS
# =========================
df, config = load_sidebar_data()

# =========================
# APLICACIÓN DE FILTROS
# =========================
if df is not None:
    if config["sedes_sel"]:
        df = df[df["NOMBRESEDE"].isin(config["sedes_sel"])]

    if config["seccion_sel"]:
        df = df[df["SECCION"].isin(config["seccion_sel"])]

# =========================
# PROCESAMIENTO (SOLO CUANDO SE PRESIONA PROCESAR)
# =========================
if df is not None and config["procesar"]:

    col_inicio = config.get("col_inicio")
    col_fin = config.get("col_fin")

    if not col_inicio or not col_fin:
        st.warning(
            "⚠️ Debe seleccionar columnas válidas para Fecha inicio y Fecha fin."
        )

    elif col_inicio == col_fin:
        st.warning(
            "⚠️ La columna de Fecha inicio y Fecha fin no pueden ser la misma."
        )

    elif col_inicio not in df.columns or col_fin not in df.columns:
        st.warning(
            "⚠️ Las columnas seleccionadas de fecha no existen en el archivo."
        )

    elif (
        
limpiar_fechas(df[col_inicio]).notna().mean() < 0.7
    or
    limpiar_fechas(df[col_fin]).notna().mean() < 0.7

    ):
        st.warning(
            "⚠️ Una o ambas columnas seleccionadas **no contienen fechas válidas**. "
            "Seleccione columnas que correspondan a fechas."
        )

    else:
        df_procesado, duracion = process_dataframe(df, config)
        df_procesado = aplicar_reglas_negocio(df_procesado)

        st.session_state.df_procesado = df_procesado
        st.session_state.duracion = duracion

# =========================
# MENSAJE INICIAL (SOLO SI NO HAY RESULTADOS)
# =========================
if st.session_state.df_procesado is None:
    st.info("📂 Carga un archivo Excel y configura los filtros para iniciar el análisis.")

# =========================
# MOSTRAR RESULTADOS (SI EXISTEN)
# =========================
if st.session_state.df_procesado is not None:
    df_procesado = st.session_state.df_procesado
    duracion = st.session_state.duracion

    # -------------------------
    # INDICADORES (KPI)
    # -------------------------
    mostrar_kpis(df_procesado, duracion)

    # -------------------------
    # GRÁFICAS
    # -------------------------
    render_charts(df_procesado)

    # -------------------------
    # TABLA FINAL
    # -------------------------
    st.subheader("📂 Datos procesados")
    st.dataframe(df_procesado, use_container_width=True)

    # -------------------------
    # DESCARGA EXCEL
    # -------------------------
    st.subheader("⬇ Descarga de resultados")

    excel_bytes = dataframe_to_excel_bytes(df_procesado)

    st.download_button(
        label="⬇ Descargar Excel",
        data=excel_bytes,
        file_name="resultado_dias_laborales.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
