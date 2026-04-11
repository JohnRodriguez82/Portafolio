import streamlit as st
import pandas as pd


def mostrar_kpis(df: pd.DataFrame, duracion: float):
    st.subheader("📊 Indicadores Generales")
    st.caption(f"⏱ Procesado en {duracion:.2f}s | {len(df):,} registros")

    total = len(df)
    cumplimiento = df["Dias_Oportunidad"].mean() * 100
    promedio = df["Dias_Laborales_num"].mean()
    sin_fecha = (df["Dias_Laborales"] == "Sin dato").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas procesadas", f"{total:,}")
    c2.metric("Cumplimiento global", f"{cumplimiento:.1f}%")
    c3.metric("Promedio días", round(promedio, 2))
    c4.metric("Registros sin fecha final", sin_fecha)
