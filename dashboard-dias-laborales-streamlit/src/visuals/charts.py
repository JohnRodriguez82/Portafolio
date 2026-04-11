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
    # ESCALA DE COLORES (SEMÁNTICA)
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]  # azul fuerte / azul claro
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
            alt.Tooltip("SECCION:N", title="Sección"),
            alt.Tooltip("Estado:N", title="Estado"),
            alt.Tooltip("Total:Q", title="Total", format=",")
        ]
    )

    # =========================
    # TEXTO PARA FUERA DE OPORTUNIDAD
    # =========================
    texto_fuera = alt.Chart(
        resumen[resumen["Estado"] == "Fuera de oportunidad"]
    ).mark_text(
        dy=-6,
        fontSize=11,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.6
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text=alt.Text("Total:Q", format=","),
        color=alt.value("#333333")
    )

    # =========================
    # TEXTO PARA DENTRO DE OPORTUNIDAD
    # =========================
    texto_dentro = alt.Chart(
        resumen[resumen["Estado"] == "Dentro de oportunidad"]
    ).mark_text(
        dy=12,
        fontSize=10,
        fontWeight="normal",
        stroke="white",
        strokeWidth=0.4
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text=alt.Text("Total:Q", format=","),
        color=alt.value("#666666")
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(
        barras + texto_fuera + texto_dentro,
        use_container_width=True
    )
