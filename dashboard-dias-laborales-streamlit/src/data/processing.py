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
        archivo = st.file_uploader("📂 Cargar archivo Excel")
        st.caption("ℹ️ Formatos permitidos: .xls, .xlsx, .xlsm")

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

        # -------------------------------------
        # ✅ Validación temprana del archivo
        # -------------------------------------
        if archivo is None:
            st.info("ℹ️ Cargue un archivo Excel para continuar.")
            st.stop()
        
        if archivo.size == 0:
            st.error(
                "❌ El archivo cargado no es un Excel válido.\n\n"
                "📌 Formatos permitidos:\n"
                "- .xls\n"
                "- .xlsx\n"
                "- .xlsm"
            )
            st.stop()
        
        nombre = archivo.name.lower()
        
        if not nombre.endswith((".xls", ".xlsx", ".xlsm")):
            st.error(
                "❌ El archivo cargado no es un Excel válido.\n\n"
                "📌 Formatos permitidos:\n"
                "- .xls\n"
                "- .xlsx\n"
                "- .xlsm"
            )
            st.stop()

        # =====================================
        # 2. Validar archivo cargado
        # =====================================
        if archivo is None:
            st.session_state.pop("archivo_validado_id", None)
            st.info("ℹ️ Cargue un archivo Excel para continuar.")
            st.stop()

        # -------------------------------------
        # ✅ Validación: archivo inválido (Word, PDF, etc.)
        # -------------------------------------
        if archivo.size == 0:
            st.error(
                "❌ El archivo cargado no es un Excel válido.\n\n"
                "📌 Formatos permitidos:\n"
                "- .xls\n"
                "- .xlsx\n"
                "- .xlsm\n\n"
                "Por favor cargue un archivo Excel correcto."
            )
            st.stop()

        nombre = archivo.name.lower()

        # Validar extensión
        if not nombre.endswith((".xls", ".xlsx", ".xlsm")):
            st.error(
                "❌ Archivo no válido\n\n"
                "El archivo cargado **no es un Excel**.\n\n"
                "✅ Formatos permitidos:\n"
                "- .xls\n"
                "- .xlsx\n"
                "- .xlsm\n\n"
                "📌 Por favor cargue un archivo Excel válido."
            )
            st.stop()

        # Intentar abrir el Excel
        try:
            if nombre.endswith(".xls"):
                xls = pd.ExcelFile(archivo, engine="xlrd")
            else:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
        except Exception as e:
            st.error(
                "❌ No se pudo abrir el archivo Excel.\n\n"
                "📌 Verifique que:\n"
                "- El archivo no esté dañado\n"
                "- No esté protegido con contraseña\n"
                "- Sea un Excel válido\n\n"
                f"Detalle técnico: {e}"
            )
            st.stop()

        # ✅ Feedback positivo 
        archivo_id = f"{archivo.name}_{archivo.size}"

        if st.session_state.get("archivo_validado_id") != archivo_id:
            st.toast("✅ Archivo Excel válido y cargado", icon="✅")
            st.session_state["archivo_validado_id"] = archivo_id

        # =====================================
        # 3. Seleccionar hoja
        # =====================================
        hoja = st.selectbox(
            "📄 Seleccione la hoja del Excel",
            xls.sheet_names
        )

        df = pd.read_excel(xls, sheet_name=hoja)
        columnas = df.columns.tolist()

        # =====================================
        # Limpieza de registros duplicados (opcional)
        # =====================================
        st.subheader("🧹 Limpieza de registros (opcional)")
        
        aplicar_deduplicacion = st.checkbox(
            "Eliminar registros duplicados antes del cálculo",
            value=False
        )
        
        columna_duplicados = None
        columna_fecha_dedup = None
        
        if aplicar_deduplicacion:
            st.caption("Se conservará el registro con la fecha más reciente")
        
            columna_duplicados = st.selectbox(
                "Columna identificadora de duplicados",
                columnas
            )
        
            columna_fecha_dedup = st.selectbox(
                "Columna de fecha para conservar el registro más reciente",
                columnas
            )

        # -------------------------------------
        # ✅ Validación: la columna seleccionada debe ser fecha
        # -------------------------------------
        if columna_fecha_dedup is not None:
        
            # Intentar convertir la columna seleccionada a datetime
            fechas_parseadas = pd.to_datetime(
                df[columna_fecha_dedup],
                errors="coerce",
                dayfirst=True
            )
        
            porcentaje_valido = fechas_parseadas.notna().mean()
        
            if porcentaje_valido < 0.7:  # umbral recomendado (70%)
                st.error(
                    "❌ La columna seleccionada NO es una columna de fecha válida.\n\n"
                    "📌 Requisitos:\n"
                    "- Debe contener fechas reconocibles\n"
                    "- No debe ser texto libre o códigos\n\n"
                    "👉 Por favor seleccione una columna de fecha válida."
                )
        
                # ❌ Bloquear procesamiento
                aplicar_deduplicacion = False
                columna_fecha_dedup = None
        
                st.stop()
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
        # 6. Selección del tipo de SLA
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

        # -------------------------------------
        # ✅ Validación: tipo de SLA obligatorio
        # -------------------------------------
        if tipo_sla == "Seleccione una opción":
            st.warning(
                "⚠️ Debe seleccionar un tipo de SLA para poder procesar los datos."
            )

        if tipo_sla == "SLA específico por ESTUDIO" and "ESTUDIO" in columnas:
            st.subheader("🎯 SLA específico por ESTUDIO")

            estudios = sorted(df["ESTUDIO"].dropna().unique().tolist())
            estudio_especial = st.selectbox("Seleccione un ESTUDIO", estudios)

            sla_estudio_especial = st.number_input(
                f"Días de oportunidad para {estudio_especial}",
                min_value=1,
                max_value=120,
                value=10,
                step=1,
            )

        elif tipo_sla == "SLA generales":
            st.subheader("⏱️ Días de oportunidad (SLA generales)")

            sla_quirurgico = st.number_input("Especimen quirúrgico (días)", 1, 60, 10)
            sla_citologia = st.number_input("Citología de líquidos (días)", 1, 60, 6)
            sla_hematopatologia = st.number_input("Hematopatología (días)", 1, 60, 10)
            sla_autopsia = st.number_input("Autopsia (días)", 1, 120, 30)

        else:
            st.info("ℹ️ Seleccione el tipo de SLA para continuar.")

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

        # =====================================
        # 8. Procesar
        # =====================================
        procesar = st.button("🚀 Procesar")

        # -------------------------------------
        # ❌ Bloquear procesamiento sin SLA
        # -------------------------------------
        if procesar and tipo_sla == "Seleccione una opción":
            st.error(
                "❌ No es posible procesar.\n\n"
                "Debe seleccionar un tipo de SLA antes de continuar."
            )
            procesar = False
        
            # =====================================
            # Config final
            # =====================================

    config = {
         # Configuración existente
        "col_inicio": col_inicio,
        "col_fin": col_fin,
        "excluir_festivos": excluir_festivos,
        "weekmask": weekmask,
        "procesar": procesar,
        "sedes_sel": sedes_sel,
        "seccion_sel": seccion_sel,
    
        # SLA existentes
        "sla_quirurgico": sla_quirurgico,
        "sla_citologia": sla_citologia,
        "sla_hematopatologia": sla_hematopatologia,
        "sla_autopsia": sla_autopsia,
    
        # SLA por estudio
        "estudio_especial": estudio_especial,
        "sla_estudio_especial": sla_estudio_especial,
    
        # Deduplicación
        "aplicar_deduplicacion": aplicar_deduplicacion,
        "columna_duplicados": columna_duplicados,
        "columna_fecha_dedup": columna_fecha_dedup,  
    }

    return df, config

def process_dataframe(df: pd.DataFrame, config: dict):
    """
    Calcula días laborales SIN modificar las columnas originales del archivo.
    Usa columnas auxiliares técnicas para el cálculo.
    """
    start_time = time.time()
    df = df.copy()

    # ✅ Columnas auxiliares (NO tocar FECHA ni FECHAVALIDO)
    df["__fecha_inicio_calc__"] = limpiar_fechas(df[config["col_inicio"]])
    df["__fecha_fin_calc__"] = limpiar_fechas(df[config["col_fin"]])

    df["Dias_Laborales_num"] = np.nan
    df["Dias_Laborales"] = "Sin dato"

    festivos = obtener_festivos() if config["excluir_festivos"] else []

    # ✅ Máscara correcta (Python real, sin HTML)
    mask_validas = (
        df["__fecha_inicio_calc__"].notna()
        & df["__fecha_fin_calc__"].notna()
        & (df["__fecha_fin_calc__"] >= df["__fecha_inicio_calc__"])
    )

    if mask_validas.any():
        inicio_vals = (
            df.loc[mask_validas, "__fecha_inicio_calc__"]
            .values
            .astype("datetime64[D]")
        )

        fin_vals = (
            df.loc[mask_validas, "__fecha_fin_calc__"]
            .values
            .astype("datetime64[D]")
        )

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
