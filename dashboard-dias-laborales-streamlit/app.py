import streamlit as st

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis
from src.visuals.charts import render_charts
from src.utils.export import dataframe_to_excel_bytes

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
# PROCESAMIENTO PRINCIPAL
# =========================
if df is not None and config["procesar"]:
    df_procesado, duracion = process_dataframe(df, config)

    # -------------------------
    # REGLAS DE NEGOCIO
    # -------------------------
    df_procesado = aplicar_reglas_negocio(df_procesado)

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

else:
    st.info("📂 Carga un archivo Excel y configura los filtros para iniciar el análisis.")
