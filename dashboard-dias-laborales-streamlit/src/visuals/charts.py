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
    # CÁLCULO DE PORCENTAJES
    # =========================
    resumen["Total_Seccion"] = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = resumen["Total"] / resumen["Total_Seccion"] * 100

    # Texto combinado: Total / %
    resumen["Label"] = (
        resumen["Total"].map(lambda x: f"{x:,}")
        + " / "
        + resumen["Porcentaje"].round(1).astype(str)
        + "%"
    )

    # =========================
    # ESCALA DE COLORES
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]  # fuerte / claro
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
            alt.Tooltip("SECCION:N", title="Sección"),
            alt.Tooltip("Estado:N", title="Estado"),
            alt.Tooltip("Total:Q", title="Total", format=","),
            alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".1f")
        ]
    )

    # =========================
    # TEXTO PARA FUERA DE OPORTUNIDAD
    # =========================
    texto_fuera = alt.Chart(
        resumen[resumen["Estado"] == "Fuera de oportunidad"]
    ).mark_text(
        dy=-6,
        fontSize=10,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.4
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text="Label:N",
        color=alt.value("#333333")
    )

    # =========================
    # TEXTO PARA DENTRO DE OPORTUNIDAD
    # =========================
    texto_dentro = alt.Chart(
        resumen[resumen["Estado"] == "Dentro de oportunidad"]
    ).mark_text(
        dy=12,
        fontSize=9,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.3
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text="Label:N",
        color=alt.value("#666666")
    )

    # =========================
