import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df):

    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map({
        1: "Dentro de oportunidad",
        0: "Fuera de oportunidad"
    })

    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = resumen["Total"] / total_seccion * 100

    resumen["Label"] = (
        resumen["Total"].astype(str)
        + " / "
        + resumen["Porcentaje"].round(1).astype(str)
        + "%"
    )

    barras = alt.Chart(resumen).mark_bar().encode(
        x="SECCION:N",
        y="Total:Q",
        color="Estado:N",
        tooltip=["SECCION", "Estado", "Total"]
    )


texto = alt.Chart(resumen).mark_text(
    fontSize=11,
    fontWeight="normal",
    dy=0,                  # ⬅ sin desplazamiento extra
    align="center",
    baseline="middle",
    stroke="white",
    strokeOpacity=0.7,
    strokeWidth=1
).encode(
    x="SECCION:N",
    y=alt.Y("Total:Q", stack="center"),  # ⬅ CLAVE: centro del segmento
    text="Label:N",
    color=alt.value("#333333")
)

    st.subheader("Cumplimiento por sección")
    st.altair_chart(barras + texto, use_container_width=True)
