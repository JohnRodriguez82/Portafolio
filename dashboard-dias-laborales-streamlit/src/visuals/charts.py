import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):
    """
    Gráfico de Cumplimiento por sección.
    Utiliza exclusivamente el DataFrame final procesado
    (con o sin deduplicación, según configuración del usuario).
    """

    st.subheader("Cumplimiento por sección")
    st.caption(
        "ℹ️ La gráfica representa el cumplimiento calculado "
        "sobre los datos finales utilizados en el análisis."
    )

    # =========================
    # RESUMEN POR SECCIÓN
    # =========================
    resumen = (
        df.groupby(
            ["SECCION", "Dentro_Oportunidad"],
            dropna=False
        )
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
    # PORCENTAJE POR SECCIÓN
    # =========================
    total_seccion = resumen.groupby("SECCION")["Total"].transform("sum")
    resumen["Porcentaje"] = (resumen["Total"] / total_seccion * 100).round(1)

    resumen["Label"] = (
        resumen["Total"].map("{:,}".format)
        + " / "
        + resumen["Porcentaje"].astype(str)
        + "%"
    )

    # =========================
    # ORDEN EXPLÍCITO DE CATEGORÍAS
    # =========================
    resumen["Estado"] = pd.Categorical(
        resumen["Estado"],
        categories=[
            "Dentro de oportunidad",
            "Fuera de oportunidad",
        ],
        ordered=True
    )

    # =========================
    # ESCALA DE COLORES EXPLÍCITA
    # =========================
    color_scale = alt.Scale(
        domain=[
            "Dentro de oportunidad",
            "Fuera de oportunidad",
        ],
        range=[
            "#1f77b4",  # Azul fuerte → Dentro
            "#aec7e8",  # Azul claro  → Fuera
        ],
    )

    # =========================
    # BARRAS APILADAS
    # =========================
    barras = (
        alt.Chart(resumen)
        .mark_bar()
        .encode(
            x=alt.X("SECCION:N", title="Sección"),
            y=alt.Y("Total:Q", title="Total de registros"),
            color=alt.Color(
                "Estado:N",
                scale=color_scale,
                legend=alt.Legend(title="Estado"),
            ),
            tooltip=[
                alt.Tooltip("SECCION:N", title="Sección"),
                alt.Tooltip("Estado:N", title="Estado"),
                alt.Tooltip("Total:Q", title="Total", format=","),
                alt.Tooltip("Porcentaje:Q", title="% participación", format=".1f"),
            ],
        )
    )

    # =========================
    # TEXTO DENTRO DE OPORTUNIDAD
    # =========================
    texto_dentro = (
        alt.Chart(resumen[resumen["Dentro_Oportunidad"] == 1])
        .mark_text(
            fontSize=12,
            align="center",
            baseline="bottom",
            dy=-4,
            color="#1f77b4",
        )
        .encode(
            x="SECCION:N",
            y=alt.Y("Total:Q", stack="center"),
            text="Label:N",
        )
    )

    # =========================
    # TEXTO FUERA DE OPORTUNIDAD
    # =========================
    texto_fuera = (
        alt.Chart(resumen[resumen["Dentro_Oportunidad"] == 0])
        .mark_text(
            fontSize=12,
            align="center",
            baseline="top",
            dy=4,
            color="#000000",
        )
        .encode(
            x="SECCION:N",
            y=alt.Y("Total:Q", stack="center"),
            text="Label:N",
        )
    )

    # =========================
    # MOSTRAR GRÁFICA
    # =========================
    st.altair_chart(
        barras + texto_dentro + texto_fuera,
        use_container_width=True,
    )
