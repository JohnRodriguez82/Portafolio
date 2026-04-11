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

    # 🔑 Texto explícito con símbolo %
    resumen_global["Porcentaje_txt"] = resumen_global["Porcentaje"].astype(str) + "%"

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

    torta_texto = alt.Chart(resumen_global).mark_text(
        radius=85,
        size=14,
        fontWeight="bold"
    ).encode(
        theta=alt.Theta("Total:Q", stack=True),
        text="Porcentaje_txt:N",
        color=alt.condition(
            alt.datum.Estado == "Dentro de oportunidad",
            alt.value("white"),
            alt.value("black")
        )
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
    fuera = resumen_seccion[resumen_seccion["Estado"] == "Fuera de oportunidad"].copy()

    # 🔑 Identificar el mayor valor
    max_val = fuera["Total"].max()
    fuera["Es_Max"] = fuera["Total"] == max_val

    barras = alt.Chart(fuera).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total fuera de oportunidad"),
        color=alt.condition(
            "datum.Es_Max",
            alt.value("#1f77b4"),   # 🔵 fuerte = mayor
            alt.value("#aec7e8")    # 🔹 claro = resto
        ),
        tooltip=[
            alt.Tooltip("SECCION:N"),
            alt.Tooltip("Total:Q", format=",")
        ]
    )

    texto_barras = alt.Chart(fuera).mark_text(
        dy=-5,
        fontSize=12,
        fontWeight="bold"
    ).encode(
        x="SECCION:N",
        y="Total:Q",
        text=alt.Text("Total:Q", format=","),
        color=alt.condition(
            "datum.Es_Max",
            alt.value("black"),
            alt.value("gray")
        )
    )

    # =========================
    # MOSTRAR EN STREAMLIT
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥧 Cumplimiento global")
        st.altair_chart(torta + torta_texto, use_container_width=True)

    with col2:
        st.markdown("### 📊 Fuera de oportunidad por sección")
        st.altair_chart(barras + texto_barras, use_container_width=True)
