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
    # PORCENTAJE POR SECCIÓN
    # =========================
    resumen["Total_Seccion"] = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = resumen["Total"] / resumen["Total_Seccion"] * 100

    resumen["Label"] = (
        resumen["Total"].map(lambda x: f"{x:,}")
        + " / "
        + resumen["Porcentaje"].round(1).astype(str)
        + "%"
    )

    # =========================
    # COLORES
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]
    )

    # =========================
    # BARRAS APILADAS
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
            alt.Tooltip("Total:Q", format=","),
            alt.Tooltip("Porcentaje:Q", format=".1f")
        ]
    )

    # =========================
    # TEXTO CENTRADO POR SEGMENTO
    # =========================
    texto = alt.Chart(resumen).mark_text(
        fontSize=10,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.4
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.condition(
            alt.datum.Estado == "Fuera de oportunidad",
            alt.value("#333333"),
            alt.value("#666666")
