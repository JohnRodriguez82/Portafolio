import pandas as pd
import streamlit as st
import time
import numpy as np

from src.utils.dates import limpiar_fechas, obtener_festivos


def load_sidebar_data():
    """
    Construye el sidebar y retorna:
    - df: DataFrame cargado
    - config: diccionario de configuración del usuario
    """
    with st.sidebar:
        st.header("⚙️ Configuración")

        archivo = st.file_uploader(
            "📂 Cargar archivo Excel",
            type=["xlsx", "xls", "xlsm"],
        )

        st.subheader("📅 Configuración días laborales")

        excluir_sabado = st.checkbox("Excluir sábado", value=True)
        excluir_domingo = st.checkbox("Excluir domingo", value=True)
        excluir_festivos = st.checkbox("Excluir festivos", value=True)

        dias = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if excluir_sabado and "Sat" in dias:
            dias.remove("Sat")
        if excluir_domingo and "Sun" in dias:
            dias.remove("Sun")

        weekmask = " ".join(dias)

        if archivo:
            df = pd.read_excel(archivo)
            columnas = df.columns.tolist()

            # Filtros opcionales
            sedes_sel = []
            seccion_sel = []

            if "NOMBRESEDE" in columnas:
                sedes = df["NOMBRESEDE"].dropna().unique().tolist()
                sedes_sel = st.multiselect("Filtrar por sede", sedes)

            if "SECCION" in columnas:
                secciones = df["SECCION"].dropna().unique().tolist()
                seccion_sel = st.multiselect("Filtrar por sección", secciones)

            col_inicio = st.selectbox("Columna fecha inicio", columnas)
            col_fin = st.selectbox("Columna fecha fin", columnas)

            procesar = st.button("🚀 Procesar")

        else:
            df = None
            col_inicio = None
            col_fin = None
            sedes_sel = []
            seccion_sel = []
            procesar = False

    config = {
        "col_inicio": col_inicio,
        "col_fin": col_fin,
        "excluir_festivos": excluir_festivos,
        "weekmask": weekmask,
        "procesar": procesar,
        "sedes_sel": sedes_sel,
        "seccion_sel": seccion_sel,
    }

    return df, config


def process_dataframe(df: pd.DataFrame, config: dict):
    """
    Procesa el DataFrame:
    - Limpia fechas
    - Calcula días laborales de forma segura
    """
    start_time = time.time()
    df = df.copy()

    # Limpieza de fechas
    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    # Columnas de resultado
    df["Dias_Laborales_num"] = np.nan
    df["Dias_Laborales"] = "Sin dato"

    # Festivos
    festivos = obtener_festivos() if config["excluir_festivos"] else []

    # Filas válidas para cálculo
    mask_validas = (
        df["fecha_inicio"].notna()
        & df["fecha_fin"].notna()
        & (df["fecha_fin"] >= df["fecha_inicio"])
    )

    if mask_validas.any():
        inicio_vals = df.loc[mask_validas, "fecha_inicio"].values.astype("datetime64[D]")
        fin_vals = df.loc[mask_validas, "fecha_fin"].values.astype("datetime64[D]")

        dias = np.busday_count(
            inicio_vals,
            fin_vals + np.timedelta64(1, "D"),
            holidays=festivos,
            weekmask=config["weekmask"],
        )

        # ✅ numérico puro para cálculos
        df.loc[mask_validas, "Dias_Laborales_num"] = dias

        # ✅ texto solo para visualización
        df.loc[mask_validas, "Dias_Laborales"] = dias.astype(str)

    duracion = time.time() - start_time
    return df, duracion
