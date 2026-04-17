import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
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
    # COLORES FIJOS
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],
    )

    # =========================
    # BARRAS AGRUPADAS (SIN LEYENDA AUTOMÁTICA)
    # =========================
    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X("SECCION:N", title="Sección"),
            xOffset="Estado:N",
            y=alt.Y("Total:Q", title="Cantidad de registros"),
            color=alt.Color("Estado:N", scale=color_scale, legend=None),
            tooltip=[
                alt.Tooltip("SECCION:N", title="Sección"),
                alt.Tooltip("Estado:N", title="Estado"),
                alt.Tooltip("Total:Q", title="Cantidad", format=","),
                alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".1f"),
            ],
        )
    )

    # =========================
    # TEXTO SOBRE BARRAS
    # =========================
    texto = (
        alt.Chart(resumen)
        .mark_text(dy=-6, color="white", fontSize=11)
        .encode(
            x="SECCION:N",
            xOffset="Estado:N",
            y="Total:Q",
            text="Etiqueta:N",
        )
    )

    # =========================
    # LEYENDA MANUAL (ROBUSTA)
    # =========================
    leyenda_df = pd.DataFrame({
        "y": [1, 0],
        "Color": ["#1f77b4", "#aec7e8"],
        "Texto": [
            "Dentro de oportunidad  (cantidad / %)",
            "Fuera de oportunidad   (cantidad / %)",
        ],
    })

    leyenda_color = (
        alt.Chart(leyenda_df)
        .mark_square(size=180)
        .encode(
            y=alt.Y("y:O", axis=None),
            color=alt.Color("Color:N", scale=None),
        )
        .properties(width=20)
    )

    leyenda_texto = (
        alt.Chart(leyenda_df)
        .mark_text(
            align="left",
            dx=10,
            fontSize=12,
            color="white"
        )
        .encode(
            y=alt.Y("y:O", axis=None),
            text="Texto:N",
        )
        .properties(width=260)
    )

    # =========================
    # COMPOSICIÓN FINAL CORRECTA
    # =========================
    grafica = alt.hconcat(
        barras + texto,
        leyenda_color + leyenda_texto
    ).resolve_scale(
        color="independent"
    )

    st.altair_chart(grafica, use_container_width=True
