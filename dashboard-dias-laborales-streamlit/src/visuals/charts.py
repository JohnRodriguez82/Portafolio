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
        0: "Fuera de oportunidad",
    })

    # =========================
    # PORCENTAJE POR SECCIÓN
    # =========================
    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = (resumen["Total"] / total_seccion * 100).round(1)

    # Label: Total / %
    resumen["Label"] = (
        resumen["Total"].map("{:,}".format)
        + " / "
        + resumen["Porcentaje"].astype(str)
        + "%"
    )

    # =========================
    # ESCALA DE COLORES
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],  # fuerte / claro
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
            legend=alt.Legend(title="Estado"),
        ),
        tooltip=[
            alt.Tooltip("SECCION:N", title="Sección"),
            alt.Tooltip("Estado:N", title="Estado"),
            alt.Tooltip("Total:Q", title="Total", format=","),
            alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".1f"),
        ],
    )

    # =========================
    # TEXTO: DENTRO DE OPORTUNIDAD
    # (ligeramente hacia abajo)
    # =========================
    texto_dentro = alt.Chart(
        resumen[resumen["Estado"] == "Dentro de oportunidad"]
    ).mark_text(
        fontSize=13,
        align="center",
        baseline="top",
        dy=-22,
        stroke="white",
        strokeOpacity=0.7,
        strokeWidth=1,
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.value("#666666"),
    )

    # =========================
    # TEXTO: FUERA DE OPORTUNIDAD
    # (ligeramente hacia arriba)
    # =========================
    texto_fuera = alt.Chart(
        resumen[resumen["Estado"] == "Fuera de oportunidad"]
    ).mark_text(
        fontSize=13,
        align="center",
        baseline="bottom",
        dy=12
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.value("#FF6600"),
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(
        barras + texto_dentro + texto_fuera,
        use_container_width=True,
    )
