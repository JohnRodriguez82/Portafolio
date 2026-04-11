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
    # CALCULAR PORCENTAJES
    # =========================
    resumen["Total_Seccion"] = resumen.groupby("SECCION")["Total"].transform("sum")

    resumen["Porcentaje"] = (
        resumen["Total"] / resumen["Total_Seccion"] * 100
    )

    # Solo fuera de oportunidad
    fuera = resumen[resumen["Estado"] == "Fuera de oportunidad"].copy()

    fuera["Porcentaje_txt"] = fuera["Porcentaje"].round(1).astype(str) + "%"

    # Marcar el mayor fuera de oportunidad
    max_val = fuera["Total"].max()
    fuera["Es_Max"] = fuera["Total"] == max_val

    # =========================
    # ESCALA DE COLORES
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
    # TEXTO: TOTAL (principal)
    # =========================
    texto_total = alt.Chart(fuera).mark_text(
        dy=-10,
        fontSize=12,
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
    # TEXTO: PORCENTAJE (secundario)
    # =========================
    texto_pct = alt.Chart(fuera).mark_text(
        dy=6,
        fontSize=10,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.4
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text="Porcentaje_txt:N",
        color=alt.value("#555555")
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(barras + texto_total + texto_pct, use_container_width=True)
