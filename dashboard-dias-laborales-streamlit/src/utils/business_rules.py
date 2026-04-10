import numpy as np
import streamlit as st

def calculate_kpis(df, duracion):
    cumplimiento = df["Dias_Oportunidad"].mean() * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros", len(df))
    c2.metric("Cumplimiento", f"{cumplimiento:.1f}%")
    c3.metric("Tiempo", f"{duracion:.2f}s")
