import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):

    # =========================
    # RESUMEN GLOBAL - PIE
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

    resumen_global["Porcentaje_txt"] = (
        resumen_global["Porcentaje"].astype(str) + "%"
    )

    escala_colores = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"]
    )

    pie = alt.Chart(resumen_global).mark_arc(
        innerRadius=60,
        stroke="white",
        strokeWidth=1
    ).encode(
        theta="Total:Q",
        color=alt.Color("Estado:N", scale=escala_colores),
        tooltip=["Estado:N", alt.Tooltip("Total:Q", format=","), "Porcentaje:Q"]
    )
    
pie_text = alt.Chart(resumen_global).mark_text(
    radius=80,
    size=13,
    fontWeight="bold",
    stroke="white",
    strokeWidth=0.8
).encode(
    theta="Total:Q",
    text="Porcentaje_txt:N",
    color=alt.value("white")
)


    # =========================
    # BARRAS - FUERA DE OPORTUNIDAD
    # =========================
    resumen_seccion = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen_seccion["Estado"] = resumen_seccion["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    fuera = resumen_seccion[
        resumen_seccion["Estado"] == "Fuera de oportunidad"
    ].copy()

    max_val = fuera["Total"].max()
    fuera["Es_Max"] = fuera["Total"] == max_val

    bars = alt.Chart(fuera).mark_bar().encode(
        x="SECCION:N",
        y="Total:Q",
        color=alt.condition(
            "datum.Es_Max",
            alt.value("#1f77b4"),
            alt.value("#aec7e8")
        ),
        tooltip=["SECCION:N", alt.Tooltip("Total:Q", format=",")]
    )
    
bars_text = alt.Chart(fuera).mark_text(
    dy=-8,
    fontSize=11,
    fontWeight="bold",
    stroke="white",
    strokeWidth=0.6
).encode(
    x="SECCION:N",
    y="Total:Q",
    text=alt.Text("Total:Q", format=","),
    color=alt.value("#333333")
)


    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cumplimiento global")
        st.altair_chart(pie + pie_text, use_container_width=True)

    with col2:
        st.subheader("Fuera de oportunidad por sección")
        st.altair_chart(bars + bars_text, use_container_width=True)
