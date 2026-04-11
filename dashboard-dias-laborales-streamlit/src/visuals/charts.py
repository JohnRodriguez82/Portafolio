import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df):

    # =========================
    # RESUMEN POR SECCIÓN
    # =========================
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map({
        1: "Dentro de oportunidad",
        0: "Fuera de oportunidad"
    })

    # =========================
    # PORCENTAJE POR SECCIÓN
    # =========================
    resumen["Total_Seccion"] = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = resumen["Total"] / resumen["Total_Seccion"] * 100

    # Label: Total / %
    resumen["Label"] = (
        resumen["Total"].astype(str)
        + " / "
        + resumen["Porcentaje"].round(1).astype(str)
        + "%"
    )

    # =========================
    # COLORES SEMÁNTICOS
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
            alt.Tooltip("SECCION:N", title="Sección"),
            alt.Tooltip("Estado:N", title="Estado"),
            alt.Tooltip("Total:Q", title="Total", format=","),
            alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".1f")
        ]
    )

    # =========================
    # TEXTO CENTRADO DENTRO DE LAS BARRAS
    # =========================
    texto = alt.Chart(resumen).mark_text(
        fontSize=11,
        fontWeight="normal",
        align="center",
        baseline="middle",
        stroke="white",
        strokeOpacity=0.7,
        strokeWidth=1
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.condition(
            alt.datum.Estado == "Fuera de oportunidad",
            alt.value("#333333"),
            alt.value("#666666")
        )
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(barras + texto, use_container_width=True)
