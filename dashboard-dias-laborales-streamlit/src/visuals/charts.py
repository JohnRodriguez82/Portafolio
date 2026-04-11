import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):

    # =========================
    # RESUMEN GLOBAL (TORTA)
    # =========================
    resumen_global = (
        df.groupby("Dias_Oportunidad")
        .size()
        .reset_index(name="Total")
    )

    resumen_global["Estado"] = resumen_global["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    resumen_global["Porcentaje"] = (
        resumen_global["Total"] / resumen_global["Total"].sum() * 100
    ).round(1)

    torta = alt.Chart(resumen_global).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("Total:Q", stack=True),
        color=alt.Color(
            "Estado:N",
            legend=alt.Legend(title="Estado")
        ),
        tooltip=["Estado", "Total", "Porcentaje"]
    )

    torta_texto = alt.Chart(resumen_global).mark_text(
        radius=90,
        size=14,
        fontWeight="bold"
    ).encode(
        theta=alt.Theta("Total:Q", stack=True),
        text=alt.Text("Porcentaje:Q", format=".1f")
    )

    # =========================
    # RESUMEN POR SECCIÓN (BARRA)
    # =========================
    resumen_seccion = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen_seccion["Estado"] = resumen_seccion["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    barras = alt.Chart(resumen_seccion).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total de registros"),
        color=alt.Color(
            "Estado:N",
            legend=None
        ),
        tooltip=["SECCION", "Estado", "Total"]
    )

    texto_barras = alt.Chart(resumen_seccion).mark_text(
        dy=-5,
        fontSize=12,
        fontWeight="bold"
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text="Total:Q",
        detail="Estado:N"
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥧 Cumplimiento global")
        st.altair_chart(torta + torta_texto, use_container_width=True)

    with col2:
        st.markdown("### 📊 Cumplimiento por sección")
        st.altair_chart(barras + texto_barras, use_container_width=True)
