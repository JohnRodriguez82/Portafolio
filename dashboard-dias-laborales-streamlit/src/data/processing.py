import pandas as pd
import streamlit as st
import time
import numpy as np

from src.utils.dates import limpiar_fechas, obtener_festivos


def load_sidebar_data():
    with st.sidebar:
        st.header("⚙️ Configuración")

        archivo = st.file_uploader(
            "📂 Cargar archivo Excel",
            type=["xlsx", "xls", "xlsm"]
        )

        st.subheader("📅 Configuración días laborales")

        excluir_sabado = st.checkbox("Excluir sábado", value=True)
        excluir_domingo = st.checkbox("Excluir domingo", value=True)
        excluir_festivos = st.checkbox("Excluir festivos", value=True)

        dias = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if excluir_sabado:
            dias.remove("Sat")
        if excluir_domingo:
            dias.remove("Sun")

        weekmask = " ".join(dias)

        if archivo:
            xls = pd.ExcelFile(archivo)
            hoja = st.selectbox("Seleccionar hoja", xls.sheet_names)
            df = pd.read_excel(xls, sheet_name=hoja)

            columnas = df.columns.tolist()
            col_inicio = st.selectbox("Columna fecha inicio", columnas)
            col_fin = st.selectbox("Columna fecha fin", columnas)

            procesar = st.button("🚀 Procesar")
        else:
            df = None
            col_inicio = None
            col_fin = None
            procesar = False

    config = {
        "col_inicio": col_inicio,
        "col_fin": col_fin,
        "excluir_festivos": excluir_festivos,
        "weekmask": weekmask,
        "procesar": procesar
    }

    return df, config


def process_dataframe(df, config):
    start_time = time.time()

    df = df.copy()

    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    if config["excluir_festivos"]:
        festivos = obtener_festivos()
    else:
        festivos = []

    inicio_vals = df["fecha_inicio"].values.astype("datetime64[D]")
    fin_vals = df["fecha_fin"].values.astype("datetime64[D]")

    df["Dias_Laborales"] = np.busday_count(
        inicio_vals,
        fin_vals + np.timedelta64(1, "D"),
        holidays=festivos,
        weekmask=config["weekmask"]
    )

    duracion = time.time() - start_time
    return df, duracion
