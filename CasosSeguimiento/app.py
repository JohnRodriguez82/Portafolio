"""
CasosSeguimiento v2.1
Sistema de seguimiento de casos profesionales.

Cambios principales:
- Configuración inicial guiada por pasos.
- La configuración queda editable después de finalizar.
- Menú principal permanente.
- Separación entre Configuración y Seguimiento.
- Profesionales editables en cualquier momento.
- Parámetros de seguimiento editables.
- No es necesario eliminar config.enc para modificar la configuración.
"""

import os
from datetime import datetime, date

import pandas as pd
import streamlit as st

from database import get_db, Caso, LogAlerta, LogProcesamiento

from config_manager import (
    config_exists,
    save_config,
    load_config,
    get_email_settings,
    get_encargado,
    get_profesionales,
    get_campos_excel,
    get_tipo_archivo,
    get_filtro_nombre_adjunto,
    _campos_default,
)

from email_processor import check_emails_and_download_excel
from excel_parser import procesar_archivo
from email_sender import enviar_resumen_casos
from scheduler_service import iniciar_scheduler


# ============================================================
# CONFIGURACIÓN DE STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Casos Seguimiento v2.1",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>

    .kpi-card {
        background: linear-gradient(
            135deg,
            #667eea 0%,
            #764ba2 100%
        );
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .kpi-title {
        font-size: 14px;
        opacity: 0.9;
    }

    .kpi-value {
        font-size: 32px;
        font-weight: bold;
    }

    .alert-vencido {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 10px;
        border-radius: 5px;
    }

    .alert-preventiva {
        background-color: #fff8e1;
        border-left: 5px solid #ffc107;
        padding: 10px;
        border-radius: 5px;
    }

    .campo-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 8px 0;
        border: 1px solid #dee2e6;
    }

    .campo-obligatorio {
        border-left: 4px solid #dc3545;
    }

    .campo-opcional {
        border-left: 4px solid #28a745;
    }

    .menu-card {
        background: linear-gradient(
            135deg,
            #f8f9fa 0%,
            #e9ecef 100%
        );
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #dee2e6;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SCHEDULER
# ============================================================

if "scheduler_started" not in st.session_state:

    if config_exists():

        try:
            iniciar_scheduler()
        except Exception:
            pass

        st.session_state.scheduler_started = True


# ============================================================
# NAVEGACIÓN
# ============================================================

def inicializar_navegacion():

    if "pagina" not in st.session_state:

        if config_exists():

            st.session_state.pagina = "inicio"

        else:

            st.session_state.pagina = "configuracion_inicial"

    if "config_step" not in st.session_state:

        st.session_state.config_step = (
            "1. Correo y Encargado"
        )


inicializar_navegacion()


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def calcular_dias(fecha_ingreso):

    if not fecha_ingreso:
        return 0

    return (date.today() - fecha_ingreso).days


def estado_visual(
    dias,
    estado_db,
    fecha_validacion
):

    if estado_db == "RESUELTO" or fecha_validacion:

        return "✅ RESUELTO", "green"

    if dias > 10:

        return "🚨 VENCIDO", "red"

    if dias == 8:

        return "⚠️ 2 DÍAS RESTANTES", "orange"

    if dias >= 9:

        return "🔴 CRÍTICO", "red"

    return "🔵 PENDIENTE", "blue"


def guardar_y_mostrar_mensaje(
    cfg,
    mensaje="Configuración guardada correctamente."
):

    save_config(cfg)

    st.success(mensaje)

    st.session_state.config_saved = True


# ============================================================
# PASO 1 - CORREO Y ENCARGADO
# ============================================================

def configurar_correo():

    cfg = load_config()

    email_cfg = cfg.get("email", {})
    encargado_cfg = cfg.get("encargado", {})

    st.subheader("📧 Correo y encargado")

    st.info(
        "Configure el correo utilizado para recibir archivos "
        "y enviar alertas."
    )

    with st.form("config_correo"):

        col1, col2 = st.columns(2)

        with col1:

            email = st.text_input(
                "Correo electrónico",
                value=email_cfg.get("email", ""),
                placeholder="seguimiento@empresa.com",
            )

            password = st.text_input(
                "Contraseña / App Password",
                value=email_cfg.get("password", ""),
                type="password",
                help=(
                    "Para Gmail se recomienda utilizar "
                    "una App Password."
                ),
            )

        with col2:

            imap_server = st.text_input(
                "Servidor IMAP",
                value=email_cfg.get(
                    "imap_server",
                    "imap.gmail.com"
                ),
            )

            smtp_server = st.text_input(
                "Servidor SMTP",
                value=email_cfg.get(
                    "smtp_server",
                    "smtp.gmail.com"
                ),
            )

        col3, col4 = st.columns(2)

        with col3:

            imap_port = st.number_input(
                "Puerto IMAP",
                value=int(
                    email_cfg.get(
                        "imap_port",
                        993
                    )
                ),
                step=1,
            )

        with col4:

            smtp_port = st.number_input(
                "Puerto SMTP",
                value=int(
                    email_cfg.get(
                        "smtp_port",
                        587
                    )
                ),
                step=1,
            )

        st.divider()

        st.subheader(
            "👤 Encargado de seguimiento"
        )

        nombre_encargado = st.text_input(
            "Nombre completo",
            value=encargado_cfg.get(
                "nombre",
                ""
            ),
        )

        guardar = st.form_submit_button(
            "💾 Guardar cambios",
            type="primary",
            use_container_width=True,
        )

        if guardar:

            if not all(
                [
                    email.strip(),
                    password.strip(),
                    nombre_encargado.strip(),
                ]
            ):

                st.error(
                    "Todos los campos son obligatorios."
                )

            else:

                cfg["email"] = {
                    "email": email.strip(),
                    "password": password,
                    "imap_server": imap_server.strip(),
                    "smtp_server": smtp_server.strip(),
                    "imap_port": int(imap_port),
                    "smtp_port": int(smtp_port),
                }

                cfg["encargado"] = {
                    "nombre": nombre_encargado.strip(),
                    "email": email.strip(),
                }

                guardar_y_mostrar_mensaje(
                    cfg,
                    "✅ Datos de correo y encargado guardados."
                )


# ============================================================
# PASO 2 - CAMPOS
# ============================================================

def configurar_campos():

    cfg = load_config()

    campos = cfg.get(
        "campos_excel",
        _campos_default()
    )

    st.subheader(
        "📋 Campos del archivo"
    )

    st.info(
        "Puede activar, desactivar o modificar "
        "los campos que se utilizan para procesar "
        "los archivos."
    )

    with st.form("config_campos"):

        campos_editados = []

        for i, campo in enumerate(campos):

            cols = st.columns(
                [2, 2, 3, 1, 1, 1]
            )

            with cols[0]:

                cid = st.text_input(
                    f"ID {i + 1}",
                    value=campo.get("id", ""),
                    key=f"cid_{i}",
                )

            with cols[1]:

                cname = st.text_input(
                    f"Nombre {i + 1}",
                    value=campo.get(
                        "nombre",
                        ""
                    ),
                    key=f"cname_{i}",
                )

            with cols[2]:

                csin = st.text_input(
                    f"Sinónimos {i + 1}",
                    value=campo.get(
                        "sinonimos",
                        ""
                    ),
                    key=f"csin_{i}",
                )

            with cols[3]:

                tipos = [
                    "texto",
                    "fecha",
                    "numero",
                ]

                tipo_actual = campo.get(
                    "tipo",
                    "texto"
                )

                if tipo_actual not in tipos:
                    tipo_actual = "texto"

                ctipo = st.selectbox(
                    f"Tipo {i + 1}",
                    tipos,
                    index=tipos.index(
                        tipo_actual
                    ),
                    key=f"ctipo_{i}",
                )

            with cols[4]:

                coblig = st.checkbox(
                    "Obligatorio",
                    value=campo.get(
                        "obligatorio",
                        False
                    ),
                    key=f"coblig_{i}",
                )

            with cols[5]:

                cactivo = st.checkbox(
                    "Activo",
                    value=campo.get(
                        "activo",
                        True
                    ),
                    key=f"cactivo_{i}",
                )

            if cactivo:

                campos_editados.append(
                    {
                        "id": cid.strip(),
                        "nombre": cname.strip(),
                        "tipo": ctipo,
                        "obligatorio": coblig,
                        "sinonimos": csin.strip(),
                        "activo": True,
                    }
                )

        st.divider()

        st.subheader(
            "➕ Agregar nuevo campo"
        )

        cols = st.columns(
            [2, 2, 3, 1, 1]
        )

        with cols[0]:

            new_id = st.text_input(
                "ID nuevo",
                placeholder="observacion",
            )

        with cols[1]:

            new_name = st.text_input(
                "Nombre visible",
                placeholder="Observación",
            )

        with cols[2]:

            new_sin = st.text_input(
                "Sinónimos",
                placeholder=(
                    "observacion,nota,comentario"
                ),
            )

        with cols[3]:

            new_tipo = st.selectbox(
                "Tipo nuevo",
                [
                    "texto",
                    "fecha",
                    "numero",
                ],
            )

        with cols[4]:

            new_oblig = st.checkbox(
                "Obligatorio nuevo"
            )

        guardar = st.form_submit_button(
            "💾 Guardar campos",
            type="primary",
            use_container_width=True,
        )

        if guardar:

            if new_id.strip() and new_name.strip():

                campos_editados.append(
                    {
                        "id": new_id.strip(),
                        "nombre": new_name.strip(),
                        "tipo": new_tipo,
                        "obligatorio": new_oblig,
                        "sinonimos": new_sin.strip(),
                        "activo": True,
                    }
                )

            if not campos_editados:

                st.error(
                    "Debe existir al menos un campo activo."
                )

            else:

                cfg["campos_excel"] = campos_editados

                guardar_y_mostrar_mensaje(
                    cfg,
                    (
                        f"✅ Se guardaron "
                        f"{len(campos_editados)} campos activos."
                    ),
                )


# ============================================================
# PASO 3 - ARCHIVO
# ============================================================

def configurar_archivo():

    cfg = load_config()

    tipo_actual = cfg.get(
        "tipo_archivo",
        "excel"
    )

    filtro_actual = cfg.get(
        "filtro_nombre_adjunto",
        ""
    )

    st.subheader(
        "📁 Tipo de archivo y adjunto"
    )

    with st.form("config_archivo"):

        tipo_archivo = st.radio(
            "Formato de archivo",
            ["excel", "csv"],
            horizontal=True,
            index=(
                0 if tipo_actual == "excel"
                else 1
            ),
        )

        filtro = st.text_input(
            "Filtro del nombre del archivo",
            value=filtro_actual,
            placeholder=(
                "reporte_casos*"
            ),
            help=(
                "Puede utilizar * como comodín. "
                "Deje vacío para aceptar cualquier archivo."
            ),
        )

        guardar = st.form_submit_button(
            "💾 Guardar configuración",
            type="primary",
            use_container_width=True,
        )

        if guardar:

            cfg["tipo_archivo"] = tipo_archivo

            cfg["filtro_nombre_adjunto"] = (
                filtro.strip()
            )

            guardar_y_mostrar_mensaje(
                cfg,
                "✅ Configuración del archivo guardada."
            )


# ============================================================
# PASO 4 - PROFESIONALES
# ============================================================

def configurar_profesionales():

    cfg = load_config()

    profesionales = cfg.get(
        "profesionales",
        []
    )

    nombres_actuales = [
        p.get("nombre", "")
        for p in profesionales
        if p.get("nombre")
    ]

    st.subheader(
        "👨‍⚕️ Profesionales a monitorear"
    )

    st.info(
        "Seleccione los profesionales que deben "
        "ser incluidos en el seguimiento."
    )

    profesionales_input = st.text_area(
        "Profesionales",
        value=", ".join(nombres_actuales),
        height=150,
        placeholder=(
            "Dr. Pérez, Dra. López, "
            "Dr. Martínez"
        ),
        help=(
            "Ingrese los nombres separados por comas."
        ),
    )

    with st.form(
        "config_profesionales"
    ):

        guardar = st.form_submit_button(
            "💾 Guardar profesionales",
            type="primary",
            use_container_width=True,
        )

        if guardar:

            lista = [
                p.strip()
                for p in profesionales_input.split(",")
                if p.strip()
            ]

            # Eliminar duplicados
            lista = list(
                dict.fromkeys(lista)
            )

            if not lista:

                st.error(
                    "Debe seleccionar al menos "
                    "un profesional."
                )

            else:

                cfg["profesionales"] = [
                    {
                        "nombre": nombre,
                        "especialidad": "",
                    }
                    for nombre in lista
                ]

                if "tiempo_resolucion_dias" not in cfg:

                    cfg[
                        "tiempo_resolucion_dias"
                    ] = 10

                if "dias_alerta_previa" not in cfg:

                    cfg[
                        "dias_alerta_previa"
                    ] = 2

                guardar_y_mostrar_mensaje(
                    cfg,
                    (
                        f"✅ Se guardaron "
                        f"{len(lista)} profesionales."
                    ),
                )


# ============================================================
# PARÁMETROS DE SEGUIMIENTO
# ============================================================

def configurar_parametros():

    cfg = load_config()

    st.subheader(
        "⏱️ Parámetros de seguimiento"
    )

    with st.form("config_parametros"):

        dias_resolucion = st.number_input(
            "Días máximos para resolver un caso",
            min_value=1,
            max_value=365,
            value=int(
                cfg.get(
                    "tiempo_resolucion_dias",
                    10
                )
            ),
        )

        dias_alerta = st.number_input(
            "Días de anticipación para alerta",
            min_value=0,
            max_value=100,
            value=int(
                cfg.get(
                    "dias_alerta_previa",
                    2
                )
            ),
        )

        guardar = st.form_submit_button(
            "💾 Guardar parámetros",
            type="primary",
            use_container_width=True,
        )

        if guardar:

            cfg[
                "tiempo_resolucion_dias"
            ] = int(dias_resolucion)

            cfg[
                "dias_alerta_previa"
            ] = int(dias_alerta)

            guardar_y_mostrar_mensaje(
                cfg,
                "✅ Parámetros de seguimiento guardados."
            )


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

def pagina_configuracion():

    st.title(
        "⚙️ Configuración general"
    )

    st.caption(
        "Todos los cambios quedan almacenados "
        "y pueden modificarse posteriormente."
    )

    tabs = st.tabs(
        [
            "📧 Correo y encargado",
            "📋 Campos",
            "📁 Archivo",
            "👨‍⚕️ Profesionales",
            "⏱️ Parámetros",
            "📜 Logs",
        ]
    )

    with tabs[0]:

        configurar_correo()

    with tabs[1]:

        configurar_campos()

    with tabs[2]:

        configurar_archivo()

    with tabs[3]:

        configurar_profesionales()

    with tabs[4]:

        configurar_parametros()

    with tabs[5]:

        mostrar_logs()


# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

def pantalla_configuracion_inicial():

    st.title(
        "🔧 Configuración inicial"
    )

    st.info(
        "Complete los cuatro pasos para dejar "
        "CasosSeguimiento listo para operar."
    )

    pasos = [
        "1. Correo y Encargado",
        "2. Campos del Archivo",
        "3. Tipo de Archivo y Adjunto",
        "4. Profesionales",
    ]

    if (
        st.session_state.config_step
        not in pasos
    ):

        st.session_state.config_step = pasos[0]

    step = st.radio(
        "Paso de configuración",
        pasos,
        index=pasos.index(
            st.session_state.config_step
        ),
        horizontal=True,
    )

    st.session_state.config_step = step

    st.divider()

    if step == pasos[0]:

        configurar_correo()

    elif step == pasos[1]:

        configurar_campos()

    elif step == pasos[2]:

        configurar_archivo()

    elif step == pasos[3]:

        configurar_profesionales()

        cfg = load_config()

        tiene_correo = bool(
            cfg.get("email", {}).get("email")
        )

        tiene_encargado = bool(
            cfg.get("encargado", {}).get("nombre")
        )

        tiene_profesionales = bool(
            cfg.get("profesionales")
        )

        if (
            tiene_correo
            and tiene_encargado
            and tiene_profesionales
        ):

            st.divider()

            if st.button(
                "🚀 Finalizar configuración y abrir menú principal",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.pagina = "inicio"
                st.session_state.pop(
                    "config_step",
                    None
                )

                st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    st.title(
        "📊 Tablero de Control"
    )

    db = get_db()

    try:

        casos = db.query(Caso).all()

    finally:

        db.close()

    if not casos:

        st.warning(
            "📭 No hay casos registrados. "
            "Puede subir un archivo desde "
            "'Procesar datos'."
        )

        return

    data = []

    for c in casos:

        dias = calcular_dias(
            c.fecha_ingreso
        )

        estado_str, color = estado_visual(
            dias,
            c.estado,
            c.fecha_validacion,
        )

        row = {
            "ID": c.id,
            "Número Caso": c.numero_caso,
            "Sede": c.sede,
            "Sección": c.seccion,
            "Estudios": c.estudios,
            "Órgano": c.organo,
            "Fecha Ingreso": c.fecha_ingreso,
            "Fecha Validación": c.fecha_validacion,
            "Profesional": c.profesional,
            "Estado DB": c.estado,
            "Días": dias,
            "Estado Visual": estado_str,
            "Color": color,
            "Última Actualización":
                c.fecha_ultima_actualizacion,
        }

        if c.campos_extra:

            for k, v in c.campos_extra.items():

                row[
                    k.replace(
                        "_",
                        " "
                    ).title()
                ] = v

        data.append(row)

    df = pd.DataFrame(data)

    total = len(df)

    resueltos = len(
        df[
            df["Estado DB"]
            == "RESUELTO"
        ]
    )

    vencidos = len(
        df[
            df["Color"]
            == "red"
        ]
    )

    preventiva = len(
        df[
            df["Color"]
            == "orange"
        ]
    )

    pendientes = (
        total
        - resueltos
        - vencidos
        - preventiva
    )

    kpi1, kpi2, kpi3, kpi4, kpi5 = (
        st.columns(5)
    )

    with kpi1:

        st.metric(
            "TOTAL CASOS",
            total
        )

    with kpi2:

        st.metric(
            "RESUELTOS",
            resueltos
        )

    with kpi3:

        st.metric(
            "PENDIENTES",
            pendientes
        )

    with kpi4:

        st.metric(
            "ALERTA PREVENTIVA",
            preventiva
        )

    with kpi5:

        st.metric(
            "VENCIDOS",
            vencidos
        )

    st.divider()

    if vencidos:

        st.markdown(
            f"""
            <div class="alert-vencido">
            🚨 <b>ATENCIÓN:</b>
            {vencidos} casos vencidos.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if preventiva:

        st.markdown(
            f"""
            <div class="alert-preventiva">
            ⚠️ {preventiva} casos requieren
            atención preventiva.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        profesionales = sorted(
            [
                p
                for p in df[
                    "Profesional"
                ].dropna().unique()
                if p
            ]
        )

        filtro_prof = st.multiselect(
            "Profesional",
            profesionales,
        )

    with col2:

        filtro_estado = st.multiselect(
            "Estado",
            sorted(
                df[
                    "Estado Visual"
                ].unique()
            ),
        )

    with col3:

        sedes = sorted(
            [
                s
                for s in df[
                    "Sede"
                ].dropna().unique()
                if s
            ]
        )

        filtro_sede = st.multiselect(
            "Sede",
            sedes,
        )

    df_filtered = df.copy()

    if filtro_prof:

        df_filtered = df_filtered[
            df_filtered[
                "Profesional"
            ].isin(filtro_prof)
        ]

    if filtro_estado:

        df_filtered = df_filtered[
            df_filtered[
                "Estado Visual"
            ].isin(filtro_estado)
        ]

    if filtro_sede:

        df_filtered = df_filtered[
            df_filtered[
                "Sede"
            ].isin(filtro_sede)
        ]

    st.subheader(
        "📋 Listado de casos"
    )

    columnas_ocultar = [
        "Color",
        "Estado DB",
    ]

    display_df = df_filtered.drop(
        columns=[
            c
            for c in columnas_ocultar
            if c in df_filtered.columns
        ]
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=450,
    )

    st.divider()

    col_g1, col_g2 = st.columns(2)

    with col_g1:

        st.subheader(
            "📈 Casos por profesional"
        )

        prof_counts = (
            df[
                df["Estado DB"]
                != "RESUELTO"
            ]["Profesional"]
            .value_counts()
        )

        if not prof_counts.empty:

            st.bar_chart(
                prof_counts
            )

    with col_g2:

        st.subheader(
            "🥧 Distribución de estados"
        )

        estado_counts = (
            df["Estado Visual"]
            .value_counts()
        )

        if not estado_counts.empty:

            try:

                import plotly.express as px

                fig = px.pie(
                    values=estado_counts.values,
                    names=estado_counts.index,
                )

                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            except Exception:

                st.bar_chart(
                    estado_counts
                )


# ============================================================
# PROCESAMIENTO
# ============================================================

def pagina_procesar():

    st.header(
        "📥 Procesamiento de datos"
    )

    tipo = get_tipo_archivo()

    if tipo == "excel":

        ext_label = "Excel (.xlsx, .xls)"
        ext_accept = [
            "xlsx",
            "xls",
        ]

    else:

        ext_label = "CSV (.csv)"
        ext_accept = ["csv"]

    st.info(
        f"Modo: **{ext_label}** | "
        f"Filtro: "
        f"'{get_filtro_nombre_adjunto() or 'Cualquiera'}'"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "1️⃣ Revisar correo"
        )

        if st.button(
            "🔄 Revisar correo ahora",
            use_container_width=True,
            type="primary",
        ):

            with st.spinner(
                "Conectando al servidor..."
            ):

                files = (
                    check_emails_and_download_excel()
                )

            if files:

                st.success(
                    f"📎 {len(files)} archivo(s) encontrado(s)."
                )

                for f in files:

                    with st.spinner(
                        f"Procesando {os.path.basename(f)}..."
                    ):

                        res = procesar_archivo(f)

                    if res["ok"]:

                        st.success(
                            f"✅ {os.path.basename(f)}: "
                            f"{res['insertados']} insertados, "
                            f"{res['actualizados']} actualizados."
                        )

                    else:

                        st.error(
                            f"❌ {res.get('error')}"
                        )

            else:

                st.info(
                    "📭 No se encontraron "
                    "archivos nuevos."
                )

    with col2:

        st.subheader(
            "2️⃣ Cargar archivo manualmente"
        )

        uploaded = st.file_uploader(
            f"Selecciona {ext_label}",
            type=ext_accept,
        )

        if uploaded:

            upload_dir = "data/uploads"

            os.makedirs(
                upload_dir,
                exist_ok=True
            )

            tmp_path = os.path.join(
                upload_dir,
                (
                    "manual_"
                    + datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )
                    + "_"
                    + uploaded.name
                ),
            )

            with open(
                tmp_path,
                "wb"
            ) as f:

                f.write(
                    uploaded.getvalue()
                )

            with st.spinner(
                "Procesando archivo..."
            ):

                res = procesar_archivo(
                    tmp_path
                )

            if res["ok"]:

                st.success(
                    f"✅ Procesado: "
                    f"{res['insertados']} insertados, "
                    f"{res['actualizados']} actualizados."
                )

            else:

                st.error(
                    f"❌ {res.get('error')}"
                )


# ============================================================
# LOGS
# ============================================================

def mostrar_logs():

    st.subheader(
        "📜 Historial de procesamiento"
    )

    db = get_db()

    try:

        logs = (
            db.query(
                LogProcesamiento
            )
            .order_by(
                LogProcesamiento.fecha_proceso.desc()
            )
            .limit(50)
            .all()
        )

        if not logs:

            st.info(
                "No hay logs registrados."
            )

            return

        df_logs = pd.DataFrame(
            [
                {
                    "Fecha": l.fecha_proceso,
                    "Archivo": os.path.basename(
                        l.archivo
                    ),
                    "Insertados": l.insertados,
                    "Actualizados": l.actualizados,
                    "Errores": l.errores,
                    "Detalle": (
                        l.detalle[:150]
                        + "..."
                        if l.detalle
                        and len(l.detalle) > 150
                        else (
                            l.detalle
                            or ""
                        )
                    ),
                }
                for l in logs
            ]
        )

        st.dataframe(
            df_logs,
            use_container_width=True,
        )

    finally:

        db.close()


# ============================================================
# ALERTAS
# ============================================================

def pagina_alertas():

    st.header(
        "📤 Alertas e informes"
    )

    db = get_db()

    try:

        casos = db.query(Caso).all()

    finally:

        db.close()

    hoy = date.today()

    vencidos = []
    preventivos = []
    pendientes = []

    cfg = load_config()

    dias_resolucion = int(
        cfg.get(
            "tiempo_resolucion_dias",
            10
        )
    )

    dias_alerta = int(
        cfg.get(
            "dias_alerta_previa",
            2
        )
    )

    for c in casos:

        if (
            c.estado == "RESUELTO"
            or not c.fecha_ingreso
        ):

            continue

        dias = (
            hoy - c.fecha_ingreso
        ).days

        pendientes.append(c)

        if dias > dias_resolucion:

            vencidos.append(c)

        elif (
            dias
            >= dias_resolucion
            - dias_alerta
        ):

            preventivos.append(c)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Vencidos",
        len(vencidos)
    )

    col2.metric(
        "Preventivos",
        len(preventivos)
    )

    col3.metric(
        "Pendientes",
        len(pendientes)
    )

    st.divider()

    enc = get_encargado()

    destino = enc.get(
        "email",
        ""
    )

    st.subheader(
        "📨 Enviar resumen"
    )

    st.write(
        f"Destinatario: **{destino}**"
    )

    if st.button(
        "📧 Enviar resumen ahora",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner(
            "Enviando correo..."
        ):

            ok, err = enviar_resumen_casos(
                destino,
                pendientes,
                vencidos,
                preventivos,
            )

        if ok:

            st.success(
                "✅ Resumen enviado correctamente."
            )

        else:

            st.error(
                f"❌ Error: {err}"
            )

    st.divider()

    st.subheader(
        "📜 Alertas enviadas"
    )

    db = get_db()

    try:

        logs = (
            db.query(LogAlerta)
            .order_by(
                LogAlerta.fecha_envio.desc()
            )
            .limit(50)
            .all()
        )

        if logs:

            df = pd.DataFrame(
                [
                    {
                        "Fecha":
                            l.fecha_envio,
                        "Tipo":
                            l.tipo_alerta,
                        "Caso":
                            l.caso_id,
                        "Destinatario":
                            l.destinatario,
                        "Contenido":
                            l.contenido,
                    }
                    for l in logs
                ]
            )

            st.dataframe(
                df,
                use_container_width=True,
            )

        else:

            st.info(
                "No se han enviado alertas."
            )

    finally:

        db.close()


# ============================================================
# INICIO
# ============================================================

def pagina_inicio():

    st.title(
        "📋 Casos Seguimiento"
    )

    st.subheader(
        "Menú principal"
    )

    st.write(
        "Seleccione la operación que desea realizar."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            <div class="menu-card">

            <h2>⚙️ Configuración general</h2>

            <p>
            Modifique el correo, encargado,
            campos, tipo de archivo,
            profesionales y parámetros
            de seguimiento.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "⚙️ Abrir configuración",
            use_container_width=True,
        ):

            st.session_state.pagina = (
                "configuracion"
            )

            st.rerun()

    with col2:

        st.markdown(
            """
            <div class="menu-card">

            <h2>📊 Realizar seguimiento</h2>

            <p>
            Consulte el tablero, procese
            nuevos archivos y revise
            las alertas.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "📊 Abrir seguimiento",
            use_container_width=True,
            type="primary",
        ):

            st.session_state.pagina = (
                "seguimiento"
            )

            st.rerun()

    st.divider()

    cfg = load_config()

    profesionales = cfg.get(
        "profesionales",
        []
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Profesionales configurados",
            len(profesionales)
        )

    with col2:

        st.metric(
            "Tipo de archivo",
            get_tipo_archivo().upper()
        )

    with col3:

        st.metric(
            "Días de resolución",
            cfg.get(
                "tiempo_resolucion_dias",
                10
            )
        )


# ============================================================
# SEGUIMIENTO
# ============================================================

def pagina_seguimiento():

    st.title(
        "📊 Realizar seguimiento"
    )

    tabs = st.tabs(
        [
            "📊 Tablero",
            "📥 Procesar datos",
            "📤 Alertas",
        ]
    )

    with tabs[0]:

        dashboard()

    with tabs[1]:

        pagina_procesar()

    with tabs[2]:

        pagina_alertas()


# ============================================================
# SIDEBAR
# ============================================================

def mostrar_sidebar():

    with st.sidebar:

        st.title(
            "📋 Casos Seguimiento"
        )

        st.caption(
            "Versión 2.1"
        )

        st.divider()

        if config_exists():

            enc = get_encargado()

            nombre = enc.get(
                "nombre",
                "No configurado"
            )

            email = enc.get(
                "email",
                "No configurado"
            )

            st.write(
                f"**Encargado:** {nombre}"
            )

            st.write(
                f"**Correo:** {email}"
            )

            st.divider()

            if st.button(
                "🏠 Inicio",
                use_container_width=True,
            ):

                st.session_state.pagina = (
                    "inicio"
                )

                st.rerun()

            if st.button(
                "⚙️ Configuración general",
                use_container_width=True,
            ):

                st.session_state.pagina = (
                    "configuracion"
                )

                st.rerun()

            if st.button(
                "📊 Realizar seguimiento",
                use_container_width=True,
                type="primary",
            ):

                st.session_state.pagina = (
                    "seguimiento"
                )

                st.rerun()

            st.divider()

            if st.button(
                "🔄 Recargar aplicación",
                use_container_width=True,
            ):

                st.rerun()

        else:

            st.info(
                "La configuración inicial "
                "aún no ha terminado."
            )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # PRIMERA EJECUCIÓN
    # --------------------------------------------------------

    if not config_exists():

        st.session_state.pagina = (
            "configuracion_inicial"
        )

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    if config_exists():

        mostrar_sidebar()

    # --------------------------------------------------------
    # PÁGINA ACTUAL
    # --------------------------------------------------------

    pagina = st.session_state.get(
        "pagina",
        "inicio"
    )

    if pagina == "configuracion_inicial":

        pantalla_configuracion_inicial()

    elif pagina == "inicio":

        pagina_inicio()

    elif pagina == "configuracion":

        pagina_configuracion()

    elif pagina == "seguimiento":

        pagina_seguimiento()

    else:

        st.session_state.pagina = (
            "inicio"
        )

        st.rerun()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    main()
