import streamlit as st
import pandas as pd
from processing import procesar_datos
from visuals import grafica_barras

st.set_page_config(page_title="Dashboard", layout="wide")

st.title("📊 Dashboard Días Laborales")

# Sidebar
with st.sidebar:
    archivo = st.file_uploader("Cargar Excel", type=["xlsx"])

    excluir_sabado = st.checkbox("Excluir sábado", True)
    excluir_domingo = st.checkbox("Excluir domingo", True)
    excluir_festivos = st.checkbox("Excluir festivos", True)

    dias = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    if excluir_sabado: dias.remove("Sat")
    if excluir_domingo: dias.remove("Sun")

    config = {
        "weekmask": " ".join(dias),
        "festivos": excluir_festivos
    }

# App
if archivo:
    df = pd.read_excel(archivo)

    col_inicio = st.selectbox("Fecha inicio", df.columns)
    col_fin = st.selectbox("Fecha fin", df.columns)

    if st.button("Procesar"):
        df = procesar_datos(df, col_inicio, col_fin, config)

        # KPIs
        st.metric("Registros", len(df))
        st.metric("Promedio días", round(df["dias_num"].mean(),2))

        # Gráfica
        st.altair_chart(grafica_barras(df), use_container_width=True)

        # Tabla
        st.dataframe(df)
