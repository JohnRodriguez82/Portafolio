import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df):

    # ==================================
    # PREPARAR DATOS
    # ==================================
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map({
        1: "Dentro de oportunidad",
        0: "Fuera de oportunidad"
    })

    # Porcentaje por sección
    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = resumen["Total"] / total_seccion * 100

    # Etiqueta Total / %
    resumen["Label"] = (
        resumen["Total"].astype(str)
        + " / "
        + resumen["Porcentaje"].round(1).astype(str)
        + "%"
    )

    # ==================================
    # BARRAS APILADAS
    # ==================================
    barras = alt.Chart(resumen).mark_bar().encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", title="Total de registros"),
        color=alt.Color(
            "Estado:N",
            scale=alt.Scale(
                domain=["Dentro de oportunidad", "Fuera de oportunidad"],
                range=["#1f77b4", "#aec7e8"]
            ),
            legend=alt.Legend(title="Estado")
        ),
        tooltip=["SECCION", "Estado", "Total"]
    )

    # ==================================
    # TEXTO DENTRO DE CADA SEGMENTO
    # ==================================

    texto_dentro = alt.Chart(
    resumen[resumen["Estado"] == "Dentro de oportunidad"]
).mark_text(
    fontSize=10,
    align="center",
    baseline="top",
    dy=12,                  # ⬅ empuja hacia la base del segmento
    stroke="white",
    strokeOpacity=0.7,
    strokeWidth=1
).encode(
    x="SECCION:N",
    y=alt.Y("Total:Q", stack="center"),
    text="Label:N",
    color=alt.value("#666666")
)
    
texto_fuera = alt.Chart(
    resumen[resumen["Estado"] == "Fuera de oportunidad"]
).mark_text(
    fontSize=10,
    align="center",
    baseline="bottom",
    dy=-12,                 # ⬅ clave: lo acerca al final sin tocar borde
    stroke="white",
    strokeOpacity=0.7,
    strokeWidth=1
).encode(
    x="SECCION:N",
    y=alt.Y("Total:Q", stack="center"),
    text="Label:N",
    color=alt.value("#333333")
)

    # ==================================
    # MOSTRAR
    # ==================================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(
        barras + texto_dentro + texto_fuera,
        use_container_width=True
    )
