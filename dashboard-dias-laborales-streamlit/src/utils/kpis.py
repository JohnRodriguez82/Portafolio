import streamlit as st
import pandas as pd


def mostrar_kpis(df: pd.DataFrame, duracion: float):
    st.subheader("📊 Indicadores Generales")
    st.caption(f"⏱ Procesado en {duracion:.2f}s | {len(df):,} registros")

    total = len(df)
    cumplimiento = df["Dentro_Oportunidad"].mean() * 100
    promedio = df["Dias_Laborales_num"].mean()
    sin_fecha = (df["Dias_Laborales"] == "Sin dato").sum()

    duplicados = st.session_state.get("duplicados")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Filas procesadas", f"{total:,}")
    c2.metric("Cumplimiento global", f"{cumplimiento:.1f}%")
    c3.metric("Promedio días", round(promedio, 2))
    c4.metric("Registros sin fecha final", sin_fecha)

    # KPI de duplicados SOLO si aplica
    if duplicados is not None:
        c5.metric("🧹 Duplicados eliminados", f"{duplicados:,}")


def cumplimiento_global(df: pd.DataFrame) -> float:
    """
    Calcula el cumplimiento global (% Dentro_Oportunidad)
    """
    if df.empty or "Dentro_Oportunidad" not in df.columns:
        return 0.0

    return df["Dentro_Oportunidad"].mean() * 100


def cumplimiento_por_seccion(df: pd.DataFrame) -> pd.Series:
    """
    Calcula el cumplimiento (% Dentro_Oportunidad) por sección
    """
    return (
        df.groupby("SECCION")["Dentro_Oportunidad"]
        .mean()
        * 100
    )
