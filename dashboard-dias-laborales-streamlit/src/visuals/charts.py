import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    # Torta
    pie = alt.Chart(resumen).mark_arc(innerRadius=50).encode(
        theta="Total:Q",
        color="Estado:N",
        tooltip=["SECCION", "Estado", "Total"],
    )

    # Barra apilada
    bar = alt.Chart(resumen).mark_bar().encode(
        x="SECCION:N",
        y="Total:Q",
        color="Estado:N",
        tooltip=["SECCION", "Estado", "Total"],
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🥧 Torta de cumplimiento")
        st.altair_chart(pie, use_container_width=True)

    with col2:
        st.markdown("#### 📊 Barra apilada")
        st.altair_chart(bar, use_container_width=True)
