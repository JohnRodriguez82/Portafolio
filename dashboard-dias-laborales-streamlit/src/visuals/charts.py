import altair as alt
import streamlit as st
import pandas as pd


def render_charts(df: pd.DataFrame):

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
    # COLORES (IGUAL QUE ANTES)
    # =========================
    color_scale = alt.Scale(
        domain=["Dentro de oportunidad", "Fuera de oportunidad"],
        range=["#1f77b4", "#aec7e8"],
    )

    # =========================
    # BARRAS APILADAS
    # =========================
    barras = alt.Chart(resumen).mark_bar().encode(
        x=alt.X("SECCION:N", title="Sección"),
        y=alt.Y("Total:Q", title="Total de registros"),
        color=alt.Color(
            "Estado:N",
            scale=color_scale,
            legend=alt.Legend(title="Estado"),
        ),
        tooltip=[
            alt.Tooltip("SECCION:N"),
            alt.Tooltip("Estado:N"),
            alt.Tooltip("Total:Q", format=","),
            alt.Tooltip("Porcentaje:Q", format=".1f"),
        ],
    )

    # =========================
    # TEXTO DENTRO DE OPORTUNIDAD 
    # =========================
    texto_dentro = alt.Chart(
        resumen[resumen["Dentro_Oportunidad"] == 1]
    ).mark_text(
        fontSize=14,
        align="center",
        baseline="top",
        dy=6,
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.value("#00FF00"),
    )

    # =========================
    # TEXTO FUERA DE OPORTUNIDAD 
    # =========================
    texto_fuera = alt.Chart(
        resumen[resumen["Dentro_Oportunidad"] == 0]
    ).mark_text(
        fontSize=14,
        align="center",
        baseline="top",
        dy=-6,
    ).encode(
        x="SECCION:N",
        y=alt.Y("Total:Q", stack="center"),
        text="Label:N",
        color=alt.value("#880808"),
    )

    # =========================
    # MOSTRAR
    # =========================
    st.subheader("Cumplimiento por sección")
    st.altair_chart(
        barras + texto_dentro + texto_fuera,
        use_container_width=True,
    )
