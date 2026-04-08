import altair as alt

def grafica_barras(df):
    resumen = df.groupby("SECCION")["dias_num"].mean().reset_index()

    chart = alt.Chart(resumen).mark_bar().encode(
        x="SECCION",
        y="dias_num",
        tooltip=["SECCION","dias_num"]
    ).properties(title="Promedio de días por sección")

    return chart
