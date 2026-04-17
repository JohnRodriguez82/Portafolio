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
    # COLORES
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],
    )

    # =========================
    # BARRAS
    # =========================
    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X("SECCION:N", title="Sección"),
            xOffset="Estado:N",
            y=alt.Y("Total:Q", title="Cantidad de registros"),
            color=alt.Color("Estado:N", scale=color_scale, legend=None),
        )
    )

    texto = (
        alt.Chart(resumen)
        .mark_text(dy=-6, fontSize=11, color="#000000")
        .encode(
            x="SECCION:N",
            xOffset="Estado:N",
            y="Total:Q",
            text="Etiqueta:N",
        )
    )

    grafico_principal = barras + texto

    # =========================
    # LEYENDA MANUAL CON FONDO
    # =========================
    leyenda_df = pd.DataFrame({
        "y": [1, 0],
        "color": ["#1f77b4", "#aec7e8"],
        "texto": [
            "Dentro de oportunidad (cantidad / %)",
            "Fuera de oportunidad (cantidad / %)",
        ],
    })

    # Fondo semitransparente (funciona en ambos temas)
    fondo_leyenda = (
        alt.Chart(pd.DataFrame({"x": [0], "y": [0]}))
        .mark_rect(
            fill="#f3f3f3",
            opacity=0.85,
            stroke="#cfcfcf",
            cornerRadius=6
        )
        .properties(width=300, height=90)
    )

    leyenda_color = (
        alt.Chart(leyenda_df)
        .mark_square(size=160)
        .encode(
            y=alt.Y("y:O", axis=None),
            color=alt.Color("color:N", scale=None),
        )
    )

    leyenda_texto = (
        alt.Chart(leyenda_df)
        .mark_text(
            align="left",
            dx=10,
            fontSize=12,
            color="#1a1a1a",
        )
        .encode(
            y=alt.Y("y:O", axis=None),
            text="texto:N",
        )
    )

    leyenda = (
        fondo_leyenda
        + leyenda_color
        + leyenda_texto
    )

    # =========================
    # COMPOSICIÓN FINAL
    # =========================
    grafica = alt.hconcat(
        grafico_principal,
        leyenda
    ).resolve_scale(
        color="independent"
    )

    st.altair_chart(grafica, use_container_width=True)
