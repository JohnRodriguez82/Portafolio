from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis
from src.visuals.charts import render_charts

setup_page()

df, config = load_sidebar_data()

# Filtros
if df is not None:
    if config["sedes_sel"]:
        df = df[df["NOMBRESEDE"].isin(config["sedes_sel"])]

    if config["seccion_sel"]:
        df = df[df["SECCION"].isin(config["seccion_sel"])]

if df is not None and config["procesar"]:
    df_proc, duracion = process_dataframe(df, config)

    # Reglas de negocio
    df_proc = aplicar_reglas_negocio(df_proc)

    # KPIs
    mostrar_kpis(df_proc, duracion)

    # Gráficas
    render_charts(df_proc)

    # Tabla final
    st.subheader("📂 Datos procesados")
    st.dataframe(df_proc, use_container_width=True)
