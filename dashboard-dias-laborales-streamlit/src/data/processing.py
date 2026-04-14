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
            type=["xlsx", "xlsm", "xls"],
        )

        st.caption("ℹ️ Archivos soportados: .xlsx, .xlsm y .xls")

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

        if archivo is not None:
            # ✅ Elegir engine según extensión
            if archivo.name.endswith(".xls"):
                df = pd.read_excel(archivo, engine="xlrd")
            else:
                df = pd.read_excel(archivo, engine="openpyxl")

            columnas = df.columns.tolist()

            st.subheader("📅 Columnas de fecha")
            col_inicio = st.selectbox("Columna fecha inicio", columnas)
            col_fin = st.selectbox("Columna fecha fin", columnas)

            st.subheader("🏢 Filtros de negocio")
            sedes_sel = []
            seccion_sel = []

            if "NOMBRESEDE" in columnas:
                sedes = df["NOMBRESEDE"].dropna().unique().tolist()
                sedes_sel = st.multiselect("Filtrar por sede", sedes)

            if "SECCION" in columnas:
                secciones = df["SECCION"].dropna().unique().tolist()
                seccion_sel = st.multiselect("Filtrar por sección", secciones)

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
