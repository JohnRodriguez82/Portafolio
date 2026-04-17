import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
    """
    Gráfica de cumplimiento por sección.
    Usa colores de barras fijos y deja que Streamlit maneje
    el contraste de textos y leyendas para tema claro y oscuro.
    """

    st.subheader("Cumplimiento por sección")
    st.caption(
        "ℹ️ Dos barras por sección: dentro y fuera de la oportunidad. "
        "Los valores corresponden a los datos finales del análisis."
    )

    # =========================
    # RESUMEN POR SECCIÓN
    # =========================
    resumen = (
        df.groupby(["SECCION", "Dentro_Oportunidad"], dropna=False)
        .size()
        .reset_index(name="Total")
    )

    resumen["Estado"] = resumen["Dentro_Oportunidad"].map(
        {
            1: "Dentro de oportunidad",
            0: "Fuera de oportunidad",
        }
    )

    # =========================
    # PORCENTAJES
    # =========================
    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = (resumen["Total"] / total_seccion * 100).round(1)

    resumen["Etiqueta"] = (
        resumen["Total"].astype(int).astype(str)
        + " / "
        + resumen["Porcentaje"].astype(str)
        + "%"
    )

    # =========================
    # COLORES DE BARRAS
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=[
            "#1f77b4",  # Azul oscuro → Dentro
            "#aec7e8",  # Azul claro  → Fuera
        ],
    )

    # =========================
    # BARRAS AGRUPADAS
    # =========================
    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X("SECCION:N", title="Sección"),
            xOffset="Estado:N",
            y=alt.Y("Total:Q", title="Cantidad de registros"),
            color=alt.Color(
                "Estado:N",
                scale=color_scale,
                legend=alt.Legend(title="Estado"),
            ),
            tooltip=[
                alt.Tooltip("SECCION:N", title="Sección"),
                alt.Tooltip("Estado:N", title="Estado"),
                alt.Tooltip("Total:Q", title="Cantidad", format=","),
                alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".1f"),
            ],
        )
    )

    # =========================
    # TEXTO SOBRE LAS BARRAS
    # =========================
    texto = (
        alt.Chart(resumen)
        .mark_text(
            dy=-5,
            fontSize=12,            
            color="#e5e7eb",         
        )
        .encode(
            x="SECCION:N",
            xOffset="Estado:N",
            y="Total:Q",
            text="Etiqueta:N",
        )
    )

    # =========================
    # MOSTRAR GRÁFICA
    # =========================
    st.altair_chart(barras + texto, use_container_width=True)
