import pandas as pd
import numpy as np
import time
import streamlit as st
from src.utils.dates import limpiar_fechas, obtener_festivos

def process_dataframe(df, config):
    start = time.time()

    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    festivos = obtener_festivos() if config["excluir_festivos"] else []

    df["Dias_Laborales"] = np.busday_count(
        df["fecha_inicio"].values.astype("datetime64[D]"),
        df["fecha_fin"].values.astype("datetime64[D]") + np.timedelta64(1, "D"),
        holidays=festivos,
        weekmask=config["weekmask"]
    )

    return df, time.time() - start

ef load_sidebar_data():
    """
    Maneja la UI del sidebar y devuelve el DataFrame y la configuración.
    """
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
