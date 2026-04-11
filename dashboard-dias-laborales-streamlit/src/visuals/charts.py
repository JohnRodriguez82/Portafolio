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
    # CAPA 1: ARCO
    # =========================
    pie = alt.Chart(resumen).mark_arc(
        innerRadius=45,
        stroke="white",
        strokeWidth=1
    ).encode(
        theta="Total:Q",
        color=alt.Color(
            "Estado:N",
            scale=alt.Scale(
                domain=["Dentro de oportunidad", "Fuera de oportunidad"],
                range=["#1f77b4", "#aec7e8"]
            ),
            legend=alt.Legend(title="Estado")
        ),
        tooltip=[
            alt.Tooltip("SECCION:N"),
            alt.Tooltip("Estado:N"),
            alt.Tooltip("Total:Q", format=","),
            alt.Tooltip("Porcentaje:Q", format=".1f")
        ],
        column=alt.Column(
            "SECCION:N",
            title="",
            header=alt.Header(labelOrient="bottom")
        )
    )

    # =========================
    # CAPA 2: TEXTO
    # =========================
    pie_text = alt.Chart(resumen).mark_text(
        radius=65,
        size=12,
        fontWeight="bold",
        stroke="white",
        strokeWidth=0.7
    ).encode(
        theta="Total:Q",
        text="Porcentaje_txt:N",
        color=alt.value("white"),
        column="SECCION:N"
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(pie + pie_text, use_container_width=True)
