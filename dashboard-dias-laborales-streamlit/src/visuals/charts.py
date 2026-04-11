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

    # Texto explícito con símbolo %
    resumen_global["Porcentaje_txt"] = resumen_global["Porcentaje"].astype(str) + "%"

    # Escala de colores (semántica correcta)
    escala_colores = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]  # fuerte / claro
    )

    torta = alt.Chart(resumen_global).mark_arc(
        innerRadius=60,
        stroke="white",
        strokeWidth=1
    ).encode(
        theta=alt.Theta("Total:Q", stack=True),
        color=alt.Color(
            "Estado:N",
            scale=escala_colores,
            legend=alt.Legend(title="Estado")
        ),
        tooltip=[
            alt.Tooltip("Estado:N"),
            alt.Tooltip("Total:Q", format=","),
            alt.Tooltip("Porcentaje:Q", format=".1f")
        ]
    )

    # Texto con fondo y borde (legible en modo oscuro)
    torta_texto = alt.Chart(resumen_global).mark_text(
        radius=85,
        size=14,
        fontWeight="bold",
        fill="#00000080",   # fondo negro semitransparente
        stroke="white",     # borde blanco
        strokeWidth=2
    ).encode(
        theta=alt.Theta("Total:Q", stack=True),
        text="Porcentaje_txt:N",
        color=alt.value("white")
    )

    # =========================
    # RESUMEN POR SECCIÓN (BARRAS)
    # =========================
    resumen_seccion = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen_seccion["Estado"] = resumen_seccion["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    # Solo Fuera de oportunidad
    fuera = resumen_seccion[
        resumen_seccion["Estado"] == "Fuera de oportunidad"
    ].copy()

    # Identificar el mayor valor
    max_val = fuera["Total"].max()
    fuera["Es_Max"] = fuera["Total"] == max_val

    barras = alt.Chart(fuera).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total fuera de oportunidad"),
        color=alt.condition(
