import streamlit as st
import pandas as pd

from src.config.settings import setup_page
from src.data.processing import load_sidebar_data, process_dataframe
from src.utils.business_rules import aplicar_reglas_negocio
from src.utils.kpis import mostrar_kpis, cumplimiento_global, cumplimiento_por_seccion
from src.visuals.charts import render_charts
from src.utils.export import dataframe_to_excel_bytes
from src.utils.dates import limpiar_fechas
from src.utils.deduplicacion import eliminar_duplicados

# =========================
# SESSION STATE INICIAL
# =========================
if "df_procesado" not in st.session_state:
    st.session_state.df_procesado = None

if "duracion" not in st.session_state:
    st.session_state.duracion = None

# =========================
# CONFIGURACIÓN INICIAL
# =========================
setup_page()

# =========================
# SIDEBAR Y CARGA DE DATOS
# =========================
df, config = load_sidebar_data()

# =========================
# APLICACIÓN DE FILTROS
# =========================
if df is not None:
    if config["sedes_sel"]:
        df = df[df["NOMBRESEDE"].isin(config["sedes_sel"])]

    if config["seccion_sel"]:
        df = df[df["SECCION"].isin(config["seccion_sel"])]

    # ✅ FILTRO POR ESTUDIO (si se seleccionó SLA especial)
    if config.get("estudio_especial") and config["estudio_especial"] != "(Ninguno)":
        df = df[df["ESTUDIO"] == config["estudio_especial"]]

# =========================
# PROCESAMIENTO (SOLO CUANDO SE PRESIONA PROCESAR)
# =========================
if df is not None and config["procesar"]:

    # -------------------------------------
    # ✅ VALIDACIÓN OBLIGATORIA: TIPO DE SLA
    # -------------------------------------
    if config.get("tipo_sla") == "Seleccione una opción":
        st.error(
            "❌ Debe seleccionar un tipo de SLA antes de procesar.\n\n"
            "Seleccione:\n"
            "- SLA específico por ESTUDIO, o\n"
            "- SLA generales."
        )
        st.session_state.df_procesado = None
        st.session_state.duracion = None

    # -------------------------------------
    # VALIDACIONES EXISTENTES
    # -------------------------------------
    else:
        col_inicio = config.get("col_inicio")
        col_fin = config.get("col_fin")

        if not col_inicio or not col_fin:
            st.warning(
                "⚠️ Debe seleccionar columnas válidas para Fecha inicio y Fecha fin."
            )
            st.session_state.df_procesado = None
            st.session_state.duracion = None

        elif col_inicio == col_fin:
            st.warning(
                "⚠️ La columna de Fecha inicio y Fecha fin no pueden ser la misma."
            )
            st.session_state.df_procesado = None
            st.session_state.duracion = None

        elif col_inicio not in df.columns or col_fin not in df.columns:
            st.warning(
                "⚠️ Las columnas seleccionadas de fecha no existen en el archivo."
            )
            st.session_state.df_procesado = None
            st.session_state.duracion = None

        elif (
            limpiar_fechas(df[col_inicio]).notna().mean() < 0.7
            or
            limpiar_fechas(df[col_fin]).notna().mean() < 0.7
        ):
            st.warning(
                "⚠️ Una o ambas columnas seleccionadas "
                "**no contienen fechas válidas**."
            )
            st.session_state.df_procesado = None
            st.session_state.duracion = None

        else:
            # ✅ LIMPIEZA PREVIA (si aplica)
            df_limpio = eliminar_duplicados(df, config)

            if config.get("aplicar_deduplicacion"):
                st.info(
                    f"🧹 Registros originales: {len(df):,}\n"
                    f"✅ Registros después de limpieza: {len(df_limpio):,}"
                )

            # ✅ CÁLCULO
            df_procesado, duracion = process_dataframe(df_limpio, config)

            # ✅ REGLAS DE NEGOCIO
            df_procesado = aplicar_reglas_negocio(df_procesado, config)

            # ✅ GUARDAR RESULTADOS
            st.session_state.df_procesado = df_procesado
            st.session_state.duracion = duracion
            st.session_state.duplicados = len(df) - len(df_limpio)


            #=====================================
            # KPI: Impacto de eliminar duplicados
            # =====================================

            # Escenario SIN eliminar duplicados
            df_sin_dupl, _ = process_dataframe(df, config)
            df_sin_dupl = aplicar_reglas_negocio(df_sin_dupl, config)

            cumplimiento_sin_dupl = cumplimiento_global(df_sin_dupl)

            # Escenario CON eliminación de duplicados
            cumplimiento_con_dupl = cumplimiento_global(df_procesado)

            impacto_duplicados = cumplimiento_con_dupl - cumplimiento_sin_dupl

            # Guardar en session_state
            st.session_state.impacto_duplicados = impacto_duplicados
            st.session_state.cumplimiento_base = cumplimiento_sin_dupl

            # =====================================
            # KPI: Impacto de eliminar duplicados por SECCIÓN
            # =====================================
            
            # Cumplimiento por sección SIN eliminar duplicados
            cumpl_sin_seccion = (
                df_sin_dupl
                .groupby("SECCION")["Dentro_Oportunidad"]
                .mean()
                * 100
            )
            
            # Cumplimiento por sección CON eliminar duplicados
            cumpl_con_seccion = (
                df_procesado
                .groupby("SECCION")["Dentro_Oportunidad"]
                .mean()
                * 100
            )
            
            # Alinear índices por seguridad
            impacto_seccion = cumpl_con_seccion - cumpl_sin_seccion
            
            # Quitar secciones con NaN si alguna no existe en ambos escenarios
            impacto_seccion = impacto_seccion.dropna()
            
            if not impacto_seccion.empty:
                seccion_mayor_impacto = impacto_seccion.abs().idxmax()
                valor_impacto_seccion = impacto_seccion.loc[seccion_mayor_impacto]
            
                st.session_state.impacto_seccion = {
                    "seccion": seccion_mayor_impacto,
                    "delta": valor_impacto_seccion,
                }
            else:
                st.session_state.impacto_seccion = None


# =========================
# MENSAJE INICIAL (SOLO SI NO HAY RESULTADOS)
# =========================
if st.session_state.df_procesado is None:
    st.info("📂 Carga un archivo Excel y configura los filtros para iniciar el análisis.")

# =========================
# MOSTRAR RESULTADOS (SI EXISTEN)
# =========================
if st.session_state.df_procesado is not None:
    df_procesado = st.session_state.df_procesado
    duracion = st.session_state.duracion

    # -------------------------
    # INDICADORES (KPI)
    # -------------------------
    mostrar_kpis(df_procesado, duracion)
    
    # -------------------------
    # KPI: Impacto de eliminar duplicados (GLOBAL)
    # -------------------------
    impacto_global = st.session_state.get("impacto_duplicados")
    
    if impacto_global is not None:
        st.metric(
            label="Impacto de eliminar duplicados",
            value=" ",
            delta=f"{impacto_global:+.1f} %",
            delta_color="inverse"
        )
    
    # -------------------------
    # KPI: Sección con mayor impacto por duplicados
    # -------------------------
    impacto_seccion = st.session_state.get("impacto_seccion")
    
    if impacto_seccion:
        st.metric(
            label="Sección con mayor impacto por duplicados",
            value=impacto_seccion["seccion"],
            delta=f"{impacto_seccion['delta']:+.1f} %",
            delta_color="inverse"
        )

    # -------------------------
    # GRÁFICAS
    # -------------------------
    render_charts(df_procesado)

    # -------------------------
    # TABLA FINAL
    # -------------------------
    st.subheader("📂 Datos procesados")
    st.dataframe(df_procesado, use_container_width=True)

    # -------------------------
    # DESCARGA EXCEL
    # -------------------------
    st.subheader("⬇ Descarga de resultados")

    excel_bytes = dataframe_to_excel_bytes(df_procesado)

    st.download_button(
        label="⬇ Descargar Excel",
        data=excel_bytes,
        file_name="resultado_dias_laborales.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
