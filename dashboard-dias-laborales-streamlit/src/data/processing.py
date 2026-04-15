def load_sidebar_data():
    """
    Construye el sidebar y retorna:
    - df: DataFrame cargado
    - config: diccionario de configuración del usuario
    """
    with st.sidebar:
        st.header("⚙️ Configuración")

        # -----------------------------
        # 1. Cargar archivo
        # -----------------------------
        archivo = st.file_uploader(
            "📂 Cargar archivo Excel",
            type=["xlsx", "xlsm", "xls"],
        )

        st.caption("ℹ️ Archivos soportados: .xlsx, .xlsm y .xls")

        # Inicialización segura
        df = None
        col_inicio = None
        col_fin = None
        sedes_sel = []
        seccion_sel = []
        procesar = False

        estudio_especial = None
        sla_estudio_especial = None

        # SLA generales (valores por defecto)
        sla_quirurgico = 10
        sla_citologia = 6
        sla_hematopatologia = 6
        sla_autopsia = 30

        # -----------------------------
        # 2. Seleccionar hoja del Excel
        # -----------------------------
        if archivo is not None:
            nombre = archivo.name.lower()

            if nombre.endswith(".xls"):
                xls = pd.ExcelFile(archivo, engine="xlrd")
            else:
                xls = pd.ExcelFile(archivo, engine="openpyxl")

            hoja = st.selectbox(
                "📄 Seleccione la hoja del Excel",
                xls.sheet_names
            )

            df = pd.read_excel(xls, sheet_name=hoja)
            columnas = df.columns.tolist()

            # -----------------------------
            # 3. Columnas de fecha (MOVIDO AQUÍ)
            # -----------------------------
            st.subheader("📅 Columnas de fecha")
            col_inicio = st.selectbox("Columna fecha inicio", columnas)
            col_fin = st.selectbox("Columna fecha fin", columnas)

            # -----------------------------
            # 4. Configuración días laborales
            # -----------------------------
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

            # -----------------------------
            # 5. Tipo de SLA (selección previa)
            # -----------------------------
            st.subheader("⏱️ Configuración de SLA")

            tipo_sla = st.selectbox(
                "Seleccione el tipo de SLA a aplicar",
                [
                    "Seleccione una opción",
                    "SLA específico por ESTUDIO",
                    "SLA generales",
                ]
            )

            # -----------------------------
            # 5A. SLA específico por ESTUDIO
            # -----------------------------
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

            # -----------------------------
            # 5B. SLA generales
            # -----------------------------
            elif tipo_sla == "SLA generales":
                st.subheader("⏱️ Días de oportunidad (SLA generales)")

                sla_quirurgico = st.number_input(
                    "Especimen quirúrgico (días)",
                    min_value=1, max_value=60, value=10
                )
                sla_citologia = st.number_input(
                    "Citología de líquidos (días)",
                    min_value=1, max_value=60, value=6
                )
                sla_hematopatologia = st.number_input(
                    "Hematopatología (días)",
                    min_value=1, max_value=60, value=6
                )
                sla_autopsia = st.number_input(
                    "Autopsia (días)",
                    min_value=1, max_value=120, value=30
                )
            else:
                st.info("ℹ️ Seleccione un tipo de SLA para continuar.")

            # -----------------------------
            # 6. Filtros de negocio
            # -----------------------------
            st.subheader("🏢 Filtros de negocio")

            if "NOMBRESEDE" in columnas:
                sedes = df["NOMBRESEDE"].dropna().unique().tolist()
                sedes_sel = st.multiselect("Filtrar por sede", sedes)

            if "SECCION" in columnas:
                secciones = df["SECCION"].dropna().unique().tolist()
                seccion_sel = st.multiselect("Filtrar por sección", secciones)

            # -----------------------------
            # 7. Procesar
            # -----------------------------
            procesar = st.button("🚀 Procesar")

        else:
            excluir_sabado = True
            excluir_domingo = True
            excluir_festivos = True
            weekmask = "Mon Tue Wed Thu Fri"

    # -----------------------------
    # Config final
    # -----------------------------
    config = {
        "col_inicio": col_inicio,
        "col_fin": col_fin,
        "excluir_festivos": excluir_festivos,
        "weekmask": weekmask,
        "procesar": procesar,
        "sedes_sel": sedes_sel,
        "seccion_sel": seccion_sel,

        # SLA generales
        "sla_quirurgico": sla_quirurgico,
        "sla_citologia": sla_citologia,
        "sla_hematopatologia": sla_hematopatologia,
        "sla_autopsia": sla_autopsia,

        # SLA por ESTUDIO
        "estudio_especial": estudio_especial,
        "sla_estudio_especial": sla_estudio_especial,
    }

    return df, config
