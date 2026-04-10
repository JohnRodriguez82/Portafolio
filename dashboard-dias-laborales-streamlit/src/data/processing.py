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
