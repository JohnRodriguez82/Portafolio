import streamlit as st
import pandas as pd
import numpy as np
from utils import limpiar_fechas, calcular_busdays_seguro, obtener_festivos
from config import PAGE_TITLE, ICON, LAYOUT

st.set_page_config(page_title=PAGE_TITLE, page_icon=ICON, layout=LAYOUT)

st.title("📊 Dashboard Analítico de Días Laborales")

# SIDEBAR
with st.sidebar:
    archivo = st.file_uploader("Cargar Excel", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)

    col_inicio = st.selectbox("Fecha inicio", df.columns)
    col_fin = st.selectbox("Fecha fin", df.columns)

    if st.button("Procesar"):
        df["fecha_inicio"] = limpiar_fechas(df[col_inicio])
        df["fecha_fin"] = limpiar_fechas(df[col_fin])

        festivos = obtener_festivos()

        df["dias"] = calcular_busdays_seguro(
            df["fecha_inicio"].values.astype("datetime64[D]"),
            df["fecha_fin"].values.astype("datetime64[D]"),
            festivos,
            "Mon Tue Wed Thu Fri"
        )

        st.dataframe(df)
