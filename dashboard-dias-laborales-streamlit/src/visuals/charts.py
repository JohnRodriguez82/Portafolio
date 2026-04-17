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
    # RESUMEN
    # =========================
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

    # =========================
    # COLORES DE BARRAS (SE MANTIENEN)
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],  # azul oscuro / azul claro
    )

    # =========================
    # BARRAS AGRUPADAS
    # =========================
    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X(
                "SECCION:N",
                title="Sección",
                axis=alt.Axis(labelAngle=-90)
            ),
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
    # TEXTO SOBRE BARRAS (CON COLOR ADAPTABLE)
    # =========================
    texto = (
        alt.Chart(resumen)
        .mark_text(
            dy=-6,
            fontSize=12,
            fontWeight="bold",
            color="#374151"  # gris oscuro, visible en ambos temas
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
    ).configure_axis(
        labelColor="#4b5563",
        titleColor="#4b5563",
        gridColor="#9ca3af",
    ).configure_legend(
        labelColor="#4b5563",
        titleColor="#4b5563",
    ).configure_view(
        stroke=None
    )

    st.altair_chart(grafica, use_container_width=True)
