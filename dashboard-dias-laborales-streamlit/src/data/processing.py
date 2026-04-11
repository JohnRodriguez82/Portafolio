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
            type=["xlsx", "xls", "xlsm"],
        )

        excluir_festivos = st.checkbox("Excluir festivos", value=True)

        dias = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        weekmask = " ".join(dias)

        if archivo:
            df = pd.read_excel(archivo)
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
        "procesar": procesar,
    }

    return df, config


def process_dataframe(df, config):
    start_time = time.time()

    df = df.copy()
    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    df["Dias_Laborales"] = "OK"

    duracion = time.time() - start_time
    return df, duracion
