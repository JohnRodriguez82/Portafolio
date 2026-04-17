import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
    st.subheader("Cumplimiento por sección")
    st.caption(
        "ℹ️ Dos barras por sección: dentro y fuera de la oportunidad. "
        "Los valores corresponden a los datos finales del análisis."
    )

    resumen = (
        df.groupby(["SECCION", "Dentro_Oportunidad"], dropna=False)
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dentro_Oportunidad"].map({
        1: "Dentro de oportunidad",
        0: "Fuera de oportunidad",
    })

    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = (resumen["Total"] / total_seccion * 100).round(1)

    resumen["Etiqueta"] = (
        resumen["Total"].astype(int).astype(str)
        + " / "
        + resumen["Porcentaje"].astype(str)
        + "%"
    )

    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],
    )

    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X(
                "SECCION:N",
                title="Sección",
                axis=alt.Axis(
                    labelAngle=-90,
                    labelColor="#374151",
                    titleColor="#374151",
                ),
            ),
            xOffset="Estado:N",
            y=alt.Y(
                "Total:Q",
                title="Cantidad de registros",
                axis=alt.Axis(
                    labelColor="#374151",
                    titleColor="#374151",
                    gridColor="#9ca3af",
                ),
            ),
            color=alt.Color(
                "Estado:N",
                scale=color_scale,
                legend=alt.Legend(
                    title="Estado",
                    labelColor="#374151",
                    titleColor="#374151",
                ),
            ),
        )
    )

    texto = (
        alt.Chart(resumen)
        .mark_text(
            dy=-6,
            fontSize=12,
            fontWeight="bold",
            color="#111827",  # ✅ visible en claro y oscuro
        )
        .encode(
            x="SECCION:N",
            xOffset="Estado:N",
            y="Total:Q",
            text="Etiqueta:N",
        )
    )

    grafica = (
        barras + texto
    ).configure_view(
        stroke=None
    )

    st.altair_chart(grafica, use_container_width=True)
