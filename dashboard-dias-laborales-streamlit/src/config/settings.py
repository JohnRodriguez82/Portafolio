import streamlit as st


def setup_page():
    st.set_page_config(
        page_title="Dashboard Días Laborales",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Dashboard Analítico de Días Laborales")
    st.markdown(
        "Análisis de tiempos de proceso por **sede** y **sección**, "
        "considerando festivos y reglas de días laborales."
    )
