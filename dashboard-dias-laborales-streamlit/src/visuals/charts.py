import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):

    # =========================
    # RESUMEN POR SECCIÓN
    # =========================
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    # =========================
    # COLORES SEMÁNTICOS
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]  # fuerte / claro
    )

    # =========================
    # BARRA APILADA
    # =========================
    barras = alt.Chart(resumen).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total de registros"),
        color=alt.Color(
            "Estado:N",
            scale=color_scale,
            legend=alt.Legend(title="Estado")
        ),
        tooltip=[
            alt.Tooltip("SECCION:N"),
            alt.Tooltip("Estado:N"),
            alt.Tooltip("Total:Q", format=",")
        ]
    )

    # =========================
    # TEXTO SOLO PARA FUERA
    # =========================
    fuera = resumen[resumen["Estado"] == "Fuera de oportunidad"]

    max_val = fuera["Total"].max()
    fuera["Es_Max"] = fuera["Total"] == max_val

    texto = alt.Chart(fuera).mark_text(
        dy=-5,
        fontSize=11,
        fontWeight="bold",
        stroke="white",
        strokeWidth=0.6
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text=alt.Text("Total:Q", format=","),
        color=alt.condition(
            "datum.Es_Max",
            alt.value("#1f77b4"),
            alt.value("#333333")
        )
    )

    # =========================
    # MOSTRAR
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(barras + texto, use_container_width=True)
