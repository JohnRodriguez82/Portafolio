import streamlit as st

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis
from src.visuals.charts import render_charts
from src.utils.export import dataframe_to_excel_bytes

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
# PROCESAMIENTO (SOLO SI SE PRESIONA PROCESAR)
# =========================
if df is not None and config["procesar"]:
    df_procesado, duracion = process_dataframe(df, config)

    # Reglas de negocio
    df_procesado = aplicar_reglas_negocio(df_procesado)

    # Guardar en session_state
    st.session_state.df_procesado = df_procesado
    st.session_state.duracion = duracion

# =========================
# MOSTRAR RESULTADOS (SI EXISTEN EN SESSION_STATE)
# =========================
if st.session_state.df_procesado is not None:
    df_procesado = st.session_state.df_procesado
    duracion = st.session_state.duracion

    # -------------------------
    # INDICADORES (KPI)
    # -------------------------
    mostrar_kpis(df_procesado, duracion)

    # -------------------------
