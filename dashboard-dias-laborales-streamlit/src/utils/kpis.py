import streamlit as st
import pandas as pd


def mostrar_kpis(df: pd.DataFrame, duracion: float):
    """
    Muestra los indicadores principales del dashboard
    """

    st.subheader("📊 Indicadores Generales")
    st.caption(f"⏱️ Procesado en {duracion:.2f}s | {len(df):,} registros")

    total = len(df)

    cumplimiento = (
        df["Dias_Oportunidad"].mean() * 100
        if "Dias_Oportunidad" in df.columns
        else 0
    )

    promedio_dias = (
        df["Dias_Laborales_num"].mean()
        if "Dias_Laborales_num" in df.columns
        else 0
    )

    sin_fecha = (
        (df["Dias_Laborales"] == "Sin dato").sum()
        if "Dias_Laborales" in df.columns
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas procesadas", f"{total:,}")
    c2.metric("Cumplimiento global", f"{cumplimiento:.1f}%")
    c3.metric("Promedio días", round(promedio_dias, 2))
    c4.metric("Registros sin fecha final", sin_fecha)
