import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):

    # =========================
    # PREPARAR DATOS
    # =========================
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    resumen["Porcentaje"] = (
        resumen.groupby("SECCION")["Total"]
        .transform(lambda x: x / x.sum() * 100)
        .round(1)
    )

    resumen["Porcentaje_txt"] = resumen["Porcentaje"].astype(str) + "%"

    # =========================
    # COLORES POR SECCIÓN
    # =========================
    secciones = resumen["SECCION"].unique().tolist()

    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c",
        "#d62728", "#9467bd", "#8c564b",
        "#e377c2", "#7f7f7f"
    ][: len(secciones)]

    color_scale = alt.Scale(domain=secciones, range=palette)

    # =========================
    # LAYER: TORTA + TEXTO
    # =========================
    pie = alt.Chart(resumen).mark_arc(
        innerRadius=45,
        stroke="white",
        strokeWidth=1
    ).encode(
        theta="Total:Q",
        color=alt.Color("SECCION:N", scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip("SECCION:N"),
            alt.Tooltip("Estado:N"),
            alt.Tooltip("Total:Q", format=","),
            alt.Tooltip("Porcentaje:Q", format=".1f")
        ]
    )

    pie_text = alt.Chart(resumen).mark_text(
        radius=70,
        size=12,
        fontWeight="bold",
        stroke="white",
        strokeWidth=0.7
    ).encode(
        theta="Total:Q",
        text="Porcentaje_txt:N",
        color=alt.value("white")
    )

    pie_layer = pie + pie_text

    # =========================
    # FACET POR SECCIÓN
    # =========================
    pie_facet = pie_layer.facet(
        facet=alt.Facet("SECCION:N", columns=3, title=None)
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(pie_facet, use_container_width=True)
