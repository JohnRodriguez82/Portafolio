import streamlit as st
from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.visuals.charts import render_charts
from src.utils.business_rules import calculate_kpis

setup_page()

df, config = load_sidebar_data()

if df is not None and config["procesar"]:
    df_procesado, duracion = process_dataframe(df, config)
    calculate_kpis(df_procesado, duracion)
    render_charts(df_procesado)
    st.dataframe(df_procesado, use_container_width=True)
