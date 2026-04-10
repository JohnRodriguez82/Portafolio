import altair as alt
import streamlit as st

def render_charts(df):
    resumen = df.groupby(["SECCION", "Dias_Oportunidad"]).size().reset_index(name="Total")

    chart = alt.Chart(resumen).mark_bar().encode(
        x="SECCION:N",
        y="Total:Q",
        color="Dias_Oportunidad:N"
    )

    st.altair_chart(chart, use_container_width=True)
