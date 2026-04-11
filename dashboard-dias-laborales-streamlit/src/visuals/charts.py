import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
    resumen = (
        df.groupby(["SECCION", "Dias_Oportunidad"])
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dias_Oportunidad"].map(
        {1: "Dentro de oportunidad", 0: "Fuera de oportunidad"}
    )

    resumen["Porcentaje"] = (
        resumen["Total"] / resumen["Total"].sum() * 100
    ).round(1)

    # -------------------------
    # GRÁFICA DE TORTA (con %)
    # -------------------------
    pie = alt.Chart(resumen).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("Total:Q", stack=True),
        color=alt.Color("Estado:N", legend=alt.Legend(title="Estado")),
        tooltip=["SECCION", "Estado", "Total", "Porcentaje"],
    )

    pie_text = alt.Chart(resumen).mark_text(radius=70, size=12).encode(
        theta=alt.Theta("Total:Q", stack=True),
        text=alt.Text("Porcentaje:Q", format=".1f"),
    )

    # -------------------------
    # BARRA APILADA (con valor)
    # -------------------------
    bar = alt.Chart(resumen).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total de registros"),
        color=alt.Color("Estado:N", legend=None),
        tooltip=["SECCION", "Estado", "Total"],
    )

    bar_text = alt.Chart(resumen).mark_text(
        dy=-5, fontWeight="bold"
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="zero"),
        text="Total:Q",
        detail="Estado:N",
    )

    # -------------------------
    # MOSTRAR EN STREAMLIT
    # -------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥧 Cumplimiento (%)")
        st.altair_chart(pie + pie_text, use_container_width=True)

    with col2:
        st.markdown("### 📊 Total por sección")
        st.altair_chart(bar + bar_text, use_container_width=True)
