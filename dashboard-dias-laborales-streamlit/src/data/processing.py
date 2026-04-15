import pandas as pd
import streamlit as st
import time
import numpy as np

from src.utils.dates import limpiar_fechas, obtener_festivos


def load_sidebar_data():
    """
    Construye el sidebar y retorna:
    - df: DataFrame cargado
    - config: diccionario de configuración del usuario
    """
    with st.sidebar:
        st.header("⚙️ Configuración")

        # =====================================
        # 1. Cargar archivo
        # =====================================
        archivo = st.file_uploader(
            "📂 Cargar archivo Excel",
            type=["xlsx", "xlsm", "xls"],
        )

        st.caption("ℹ️ Archivos soportados: .xlsx, .xlsm y .xls")

        # Inicialización segura
        df = None
        columnas = []
        col_inicio = None
        col_fin = None
        sedes_sel = []
        seccion_sel = []
        procesar = False

        estudio_especial = None
        sla_estudio_especial = None

        # SLA generales (defaults)
        sla_quirurgico = 10
        sla_citologia = 6
        sla_hematopatologia = 10
        sla_autopsia = 30

        excluir_sabado = True
        excluir_domingo = True
        excluir_festivos = True
        weekmask = "Mon Tue Wed Thu Fri"

        # =====================================
        # 2. Validar y abrir archivo
        # =====================================
        if archivo is not None:
            nombre = archivo.name.lower()

            try:
                if nombre.endswith(".xls"):
                    xls = pd.ExcelFile(archivo, engine="xlrd")
                else:
                    xls = pd.ExcelFile(archivo, engine="openpyxl")
            except Exception as e:
                st.error(
                    "❌ El archivo no es un Excel válido o está dañado.\n\n"
                    f"Detalle técnico: {e}"
                )
                return None, {
                    "procesar": False,
                    "col_inicio": None,
                    "col_fin": None,
                    "excluir_festivos": True,
                    "weekmask": weekmask,
                    "sedes_sel": [],
                    "seccion_sel": [],
                    "sla_quirurgico": sla_quirurgico,
                    "sla_citologia": sla_citologia,
                    "sla_hematopatologia": sla_hematopatologia,
                    "sla_autopsia": sla_autopsia,
                    "estudio_especial": None,
                    "sla_estudio_especial": None,
                }

            # =====================================
            # 3. Seleccionar hoja
            # =====================================
            hoja = st.selectbox("📄 Seleccione la hoja del Excel", xls.sheet_names)
            df = pd.read_excel(xls, sheet_name=hoja)
            columnas = df.columns.tolist()

            # =====================================
            # 4. Columnas de fecha
            # =====================================
            st.subheader("📅 Columnas de fecha")
            col_inicio = st.selectbox("Columna fecha inicio", columnas)
            col_fin = st.selectbox("Columna fecha fin", columnas)

            # =====================================
            # 5. Configuración días laborales
            # =====================================
            st.subheader("📅 Configuración días laborales")

            excluir_sabado = st.checkbox("Excluir sábado", value=True)
            excluir_domingo = st.checkbox("Excluir domingo", value=True)
            excluir_festivos = st.checkbox("Excluir festivos", value=True)

            dias = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if excluir_sabado:
                dias.remove("Sat")
            if excluir_domingo:
                dias.remove("Sun")

            weekmask = " ".join(dias)

            # =====================================
            # 6. Selección del tipo de SLA (PASO 1 REAL)
            # =====================================
            st.subheader("⏱️ Configuración de SLA")

            tipo_sla = st.selectbox(
                "Seleccione el tipo de SLA a aplicar",
                [
                    "Seleccione una opción",
                    "SLA específico por ESTUDIO",
                    "SLA generales",
                ]
            )

            if tipo_sla == "SLA específico por ESTUDIO" and "ESTUDIO" in columnas:
                st.subheader("🎯 SLA específico por ESTUDIO")
                estudios = sorted(df["ESTUDIO"].dropna().unique().tolist())
                estudio_especial = st.selectbox("Seleccione un ESTUDIO", estudios)

                sla_estudio_especial = st.number_input(
                    f"Días de oportunidad para {estudio_especial}",
                    min_value=1,
                    max_value=120,
                    value=10
                )

            elif tipo_sla == "SLA generales":
                st.subheader("⏱️ Días de oportunidad (SLA generales)")

                sla_quirurgico = st.number_input("Especimen quirúrgico (días)", 1, 60, 10)
                sla_citologia = st.number_input("Citología de líquidos (días)", 1, 60, 6)
                sla_hematopatologia = st.number_input("Hematopatología (días)", 1, 60, 10)
                sla_autopsia = st.number_input("Autopsia (días)", 1, 120, 30)

            else:
                st.info("ℹ️ Seleccione un tipo de SLA para continuar.")

            # =====================================
            # 7. Filtros de negocio
            # =====================================
            st.subheader("🏢 Filtros de negocio")

            if "NOMBRESEDE" in columnas:
                sedes = df["NOMBRESEDE"].dropna().unique().tolist()
                sedes_sel = st.multiselect("Filtrar por sede", sedes)

            if "SECCION" in columnas:
                secciones = df["SECCION"].dropna().unique().tolist()
                seccion_sel = st.multiselect("Filtrar por sección", secciones)

            procesar = st.button("🚀 Procesar")

    config = {
        "col_inicio": col_inicio,
        "col_fin": col_fin,
        "excluir_festivos": excluir_festivos,
        "weekmask": weekmask,
        "procesar": procesar,
        "sedes_sel": sedes_sel,
        "seccion_sel": seccion_sel,
        "sla_quirurgico": sla_quirurgico,
        "sla_citologia": sla_citologia,
        "sla_hematopatologia": sla_hematopatologia,
        "sla_autopsia": sla_autopsia,
        "estudio_especial": estudio_especial,
        "sla_estudio_especial": sla_estudio_especial,
    }

    return df, config


def process_dataframe(df: pd.DataFrame, config: dict):
    """
    Limpia fechas y calcula días laborales
    """
    start_time = time.time()
    df = df.copy()

    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    df["Dias_Laborales_num"] = np.nan
    df["Dias_Laborales"] = "Sin dato"

    festivos = obtener_festivos() if config["excluir_festivos"] else []

    mask_validas = (
        df["fecha_inicio"].notna()
        & df["fecha_fin"].notna()
        & (df["fecha_fin"] >= df["fecha_inicio"])
    )

    if mask_validas.any():
        inicio_vals = df.loc[mask_validas, "fecha_inicio"].values.astype("datetime64[D]")
        fin_vals = df.loc[mask_validas, "fecha_fin"].values.astype("datetime64[D]")

        dias = np.busday_count(
            inicio_vals,
            fin_vals + np.timedelta64(1, "D"),
            holidays=festivos,
            weekmask=config["weekmask"],
        )

        df.loc[mask_validas, "Dias_Laborales_num"] = dias
        df.loc[mask_validas, "Dias_Laborales"] = dias.astype(str)

    duracion = time.time() - start_time
    return df, duracion
``
