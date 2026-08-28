"""
CasosSeguimiento v2.1
Aplicación principal Streamlit.

Características:
- Dashboard de casos.
- Excel / CSV.
- Actualización incremental.
- Configuración parametrizable.
- Procesamiento manual.
- Procesamiento IMAP.
- Alertas SMTP.
- Logs.

IMPORTANTE:
El scheduler automático se ejecuta mediante:

    python scheduler_runner.py

No se inicia dentro de Streamlit para evitar múltiples schedulers
cuando Streamlit crea/recrea sesiones.
"""

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config_manager import (
    _campos_default,
    config_exists,
    get_campos_excel,
    get_encargado,
    get_filtro_nombre_adjunto,
    get_profesionales,
    get_tipo_archivo,
    load_config,
    save_config,
)
from database import (
    Caso,
    LogAlerta,
    LogProcesamiento,
    get_db,
)
from email_processor import (
    check_emails_and_download_excel,
)
from email_sender import (
    enviar_resumen_casos,
)
from excel_parser import (
    procesar_archivo,
)
from paths import (
    DATABASE_FILE,
    UPLOAD_DIR,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "casos_seguimiento.app"
)


st.set_page_config(
    page_title="Seguimiento de Casos v2.1",
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
            background:
                linear-gradient(
                    135deg,
                    #667eea 0%,
                    #764ba2 100%
                );

            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;

            box-shadow:
                0 4px 6px rgba(0,0,0,0.1);
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

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ESTADOS
# ============================================================

def calcular_dias(
    fecha_ingreso,
):
    if not fecha_ingreso:
        return 0

    return (
        date.today()
        - fecha_ingreso
    ).days


def estado_visual(
    dias,
    estado_db,
    fecha_validacion,
):

    estado_normalizado = (
        str(
            estado_db or ""
        )
        .strip()
        .upper()
    )

    if (
        estado_normalizado == "RESUELTO"
        or fecha_validacion
    ):
        return "✅ RESUELTO", "green"

    if dias > 10:
        return "🚨 VENCIDO", "red"

    if dias == 10:
        return "🔴 VENCE HOY", "red"

    if dias == 8:
        return (
            "⚠️ 2 DÍAS RESTANTES",
            "orange",
        )

    if dias >= 9:
        return "🔴 CRÍTICO", "red"

    return "🔵 PENDIENTE", "blue"


# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

def pantalla_configuracion():

    st.title(
        "🔧 Configuración Inicial "
        "CasosSeguimiento v2.1"
    )

    st.info(
        "Complete los cuatro pasos. "
        "Las credenciales de correo se almacenarán "
        "encriptadas."
    )

    step = st.radio(
        "Paso",
        [
            "1. Correo y Encargado",
            "2. Campos del Archivo",
            "3. Tipo de Archivo y Adjunto",
            "4. Profesionales",
        ],
        horizontal=True,
    )

    # --------------------------------------------------------
    # PASO 1
    # --------------------------------------------------------

    if step == "1. Correo y Encargado":

        with st.form(
            "config_paso1"
        ):

            st.subheader(
                "📧 Configuración del Correo"
            )

            col1, col2 = st.columns(2)

            with col1:

                email = st.text_input(
                    "Correo electrónico",
                    placeholder=(
                        "seguimiento@empresa.com"
                    ),
                )

                password = st.text_input(
                    "Contraseña / App Password",
                    type="password",
                    help=(
                        "Gmail: utiliza una App Password."
                    ),
                )

            with col2:

                imap_server = st.text_input(
                    "Servidor IMAP",
                    value="imap.gmail.com",
                )

                smtp_server = st.text_input(
                    "Servidor SMTP",
                    value="smtp.gmail.com",
                )

            col3, col4 = st.columns(2)

            with col3:

                imap_port = st.number_input(
                    "Puerto IMAP",
                    value=993,
                    min_value=1,
                    step=1,
                )

            with col4:

                smtp_port = st.number_input(
                    "Puerto SMTP",
                    value=587,
                    min_value=1,
                    step=1,
                )

            st.divider()

            st.subheader(
                "👤 Encargado"
            )

            nombre_encargado = st.text_input(
                "Nombre completo"
            )

            if st.form_submit_button(
                "Guardar y continuar ➡️",
                type="primary",
            ):

                if not all(
                    [
                        email.strip(),
                        password,
                        nombre_encargado.strip(),
                    ]
                ):

                    st.error(
                        "Todos los campos son obligatorios."
                    )

                else:

                    cfg = load_config()

                    cfg["email"] = {
                        "email": email.strip(),
                        "password": password,
                        "imap_server": imap_server.strip(),
                        "smtp_server": smtp_server.strip(),
                        "imap_port": int(imap_port),
                        "smtp_port": int(smtp_port),
                    }

                    cfg["encargado"] = {
                        "nombre": (
                            nombre_encargado.strip()
                        ),
                        "email": email.strip(),
                    }

                    save_config(cfg)

                    st.success(
                        "Paso 1 guardado."
                    )

    # --------------------------------------------------------
    # PASO 2
    # --------------------------------------------------------

    elif step == "2. Campos del Archivo":

        st.subheader(
            "📋 Campos del Archivo"
        )

        st.info(
            "Configure las columnas esperadas "
            "del Excel/CSV."
        )

        cfg = load_config()

        campos = cfg.get(
            "campos_excel",
            _campos_default(),
        )

        with st.form(
            "config_campos"
        ):

            campos_editados = []

            for i, campo in enumerate(
                campos
            ):

                cols = st.columns(
                    [
                        2,
                        2,
                        3,
                        1,
                        1,
                        1,
                    ]
                )

                with cols[0]:

                    cid = st.text_input(
                        f"ID {i + 1}",
                        value=campo["id"],
                        key=f"cid_{i}",
                    )

                with cols[1]:

                    cname = st.text_input(
                        f"Nombre {i + 1}",
                        value=campo["nombre"],
                        key=f"cname_{i}",
                    )

                with cols[2]:

                    csin = st.text_input(
                        f"Sinónimos {i + 1}",
                        value=campo.get(
                            "sinonimos",
                            "",
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
                        "texto",
                    )

                    index_tipo = (
                        tipos.index(tipo_actual)
                        if tipo_actual in tipos
                        else 0
                    )

                    ctipo = st.selectbox(
                        f"Tipo {i + 1}",
                        tipos,
                        index=index_tipo,
                        key=f"ctipo_{i}",
                    )

                with cols[4]:

                    coblig = st.checkbox(
                        "Obligatorio",
                        value=campo.get(
                            "obligatorio",
                            False,
                        ),
                        key=f"coblig_{i}",
                    )

                with cols[5]:

                    cactivo = st.checkbox(
                        "Activo",
                        value=campo.get(
                            "activo",
                            True,
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
                "➕ Agregar campo"
            )

            cols_new = st.columns(
                [2, 2, 3, 1, 1]
            )

            with cols_new[0]:

                new_id = st.text_input(
                    "ID",
                    key="new_id",
                    placeholder="observacion",
                )

            with cols_new[1]:

                new_name = st.text_input(
                    "Nombre visible",
                    key="new_name",
                    placeholder="Observación",
                )

            with cols_new[2]:

                new_sin = st.text_input(
                    "Sinónimos",
                    key="new_sin",
                    placeholder=(
                        "observacion,nota,comentario"
                    ),
                )

            with cols_new[3]:

                new_tipo = st.selectbox(
                    "Tipo",
                    [
                        "texto",
                        "fecha",
                        "numero",
                    ],
                    key="new_tipo",
                )

            with cols_new[4]:

                new_oblig = st.checkbox(
                    "Obligatorio",
                    key="new_oblig",
                )

            if st.form_submit_button(
                "💾 Guardar Campos",
                type="primary",
            ):

                ids_existentes = {
                    c["id"]
                    for c in campos_editados
                }

                if new_id and new_name:

                    if new_id.strip() in ids_existentes:

                        st.error(
                            "El ID del nuevo campo ya existe."
                        )

                        return

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

                campos_editados = [
                    c
                    for c in campos_editados
                    if c["id"] and c["nombre"]
                ]

                cfg["campos_excel"] = (
                    campos_editados
                )

                save_config(cfg)

                st.success(
                    f"Campos guardados: "
                    f"{len(campos_editados)}."
                )

    # --------------------------------------------------------
    # PASO 3
    # --------------------------------------------------------

    elif step == "3. Tipo de Archivo y Adjunto":

        with st.form(
            "config_archivo"
        ):

            st.subheader(
                "📁 Tipo de Archivo"
            )

            tipo_archivo = st.radio(
                "Formato",
                [
                    "excel",
                    "csv",
                ],
                horizontal=True,
                index=(
                    0
                    if get_tipo_archivo()
                    == "excel"
                    else 1
                ),
            )

            st.divider()

            filtro = st.text_input(
                "Filtro del nombre del adjunto",
                value=get_filtro_nombre_adjunto(),
                placeholder=(
                    "reporte_casos*.xlsx"
                ),
                help=(
                    "Ejemplo: reporte_casos*.xlsx"
                ),
            )

            if st.form_submit_button(
                "💾 Guardar",
                type="primary",
            ):

                cfg = load_config()

                cfg[
                    "tipo_archivo"
                ] = tipo_archivo

                cfg[
                    "filtro_nombre_adjunto"
                ] = filtro.strip()

                save_config(cfg)

                st.success(
                    "Configuración guardada."
                )

    # --------------------------------------------------------
    # PASO 4
    # --------------------------------------------------------

    else:

        with st.form(
            "config_profesionales"
        ):

            st.subheader(
                "👨‍⚕️ Profesionales"
            )

            profesionales_input = (
                st.text_area(
                    "Nombres separados por comas",
                    height=120,
                    placeholder=(
                        "Dr. Pérez, Dra. López"
                    ),
                )
            )

            if st.form_submit_button(
                "✅ Finalizar Configuración",
                type="primary",
            ):

                profesionales = [
                    p.strip()
                    for p
                    in profesionales_input.split(",")
                    if p.strip()
                ]

                if not profesionales:

                    st.error(
                        "Ingrese al menos un profesional."
                    )

                    return

                cfg = load_config()

                cfg[
                    "profesionales"
                ] = [
                    {
                        "nombre": p,
                        "especialidad": "",
                    }
                    for p in profesionales
                ]

                cfg[
                    "tiempo_resolucion_dias"
                ] = 10

                cfg[
                    "dias_alerta_previa"
                ] = 2

                save_config(cfg)

                st.success(
                    "🎉 Configuración completada."
                )

                st.info(
                    "Recargue la página para entrar "
                    "al dashboard."
                )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    st.title(
        "📊 Tablero de Control"
    )

    db = get_db()

    try:

        casos = (
            db.query(Caso)
            .order_by(
                Caso.fecha_ingreso.asc()
            )
            .all()
        )

    finally:

        db.close()

    if not casos:

        st.warning(
            "📭 No hay casos registrados."
        )

        return

    data = []

    for caso in casos:

        dias = calcular_dias(
            caso.fecha_ingreso
        )

        estado_str, color = (
            estado_visual(
                dias,
                caso.estado,
                caso.fecha_validacion,
            )
        )

        row = {
            "ID": caso.id,
            "Número Caso": caso.numero_caso,
            "Sede": caso.sede,
            "Sección": caso.seccion,
            "Estudios": caso.estudios,
            "Órgano": caso.organo,
            "Fecha Ingreso": caso.fecha_ingreso,
            "Fecha Validación": caso.fecha_validacion,
            "Profesional": caso.profesional,
            "Estado DB": caso.estado,
            "Días": dias,
            "Estado Visual": estado_str,
            "Color": color,
            "Última Actualización": (
                caso.fecha_ultima_actualizacion
            ),
        }

        if caso.campos_extra:

            for key, value in (
                caso.campos_extra.items()
            ):

                row[
                    key.replace(
                        "_",
                        " ",
                    ).title()
                ] = value

        data.append(row)

    df = pd.DataFrame(data)

    total = len(df)

    resueltos = len(
        df[
            df["Estado Visual"]
            == "✅ RESUELTO"
        ]
    )

    vencidos = len(
        df[
            df["Color"] == "red"
        ]
    )

    preventiva = len(
        df[
            df["Color"] == "orange"
        ]
    )

    pendientes = (
        total
        - resueltos
        - vencidos
        - preventiva
    )

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:

        st.metric(
            "TOTAL",
            total,
        )

    with k2:

        st.metric(
            "RESUELTOS",
            resueltos,
        )

    with k3:

        st.metric(
            "PENDIENTES",
            pendientes,
        )

    with k4:

        st.metric(
            "ALERTA PREVENTIVA",
            preventiva,
        )

    with k5:

        st.metric(
            "VENCIDOS",
            vencidos,
        )

    if vencidos:

        st.markdown(
            f"""
            <div class="alert-vencido">
                🚨 <b>ATENCIÓN:</b>
                {vencidos} casos requieren atención.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if preventiva:

        st.markdown(
            f"""
            <div class="alert-preventiva">
                ⚠️ {preventiva}
                casos están en alerta preventiva.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        profesionales = sorted(
            [
                x
                for x in df[
                    "Profesional"
                ].dropna().unique()
                if str(x).strip()
            ]
        )

        filtro_prof = st.multiselect(
            "Profesional",
            profesionales,
        )

    with col2:

        estados = sorted(
            [
                x
                for x in df[
                    "Estado Visual"
                ].dropna().unique()
            ]
        )

        filtro_estado = st.multiselect(
            "Estado",
            estados,
        )

    with col3:

        sedes = sorted(
            [
                x
                for x in df[
                    "Sede"
                ].dropna().unique()
                if str(x).strip()
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
        "📋 Listado de Casos"
    )

    def color_rows(row):

        color = row.get(
            "Color",
            "",
        )

        if color == "red":

            return [
                "background-color:#ffebee"
            ] * len(row)

        if color == "orange":

            return [
                "background-color:#fff8e1"
            ] * len(row)

        if color == "green":

            return [
                "background-color:#e8f5e9"
            ] * len(row)

        return [""] * len(row)

    # Se estiliza ANTES de eliminar Color.
    styled_df = (
        df_filtered
        .style
        .apply(
            color_rows,
            axis=1,
        )
    )

    display_df = df_filtered.drop(
        columns=[
            "Color",
            "Estado DB",
        ],
        errors="ignore",
    )

    # El estilo se aplica sobre la copia que sí contiene Color.
    styled_display = (
        df_filtered
        .style
        .apply(
            color_rows,
            axis=1,
        )
    )

    st.dataframe(
        styled_display,
        use_container_width=True,
        height=450,
    )

    st.divider()

    col_g1, col_g2 = st.columns(2)

    with col_g1:

        st.subheader(
            "📈 Casos por Profesional"
        )

        prof_counts = (
            df[
                df["Estado Visual"]
                != "✅ RESUELTO"
            ]["Profesional"]
            .value_counts()
        )

        if not prof_counts.empty:

            st.bar_chart(
                prof_counts
            )

    with col_g2:

        st.subheader(
            "🥧 Distribución de Estados"
        )

        estado_counts = (
            df[
                "Estado Visual"
            ].value_counts()
        )

        if not estado_counts.empty:

            try:

                import plotly.express as px

                fig = px.pie(
                    values=estado_counts.values,
                    names=estado_counts.index,
                    color=estado_counts.index,
                    color_discrete_map={
                        "✅ RESUELTO": "#38ef7d",
                        "🔵 PENDIENTE": "#6dd5ed",
                        "⚠️ 2 DÍAS RESTANTES": "#ffd200",
                        "🔴 CRÍTICO": "#ff6b6b",
                        "🔴 VENCE HOY": "#ff6b6b",
                        "🚨 VENCIDO": "#ef473a",
                    },
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
# PROCESAR DATOS
# ============================================================

def pestaña_procesar():

    st.header(
        "📥 Procesamiento de Datos"
    )

    tipo = get_tipo_archivo()

    if tipo == "excel":

        ext_label = (
            "Excel (.xlsx, .xls)"
        )

        ext_accept = [
            "xlsx",
            "xls",
        ]

    else:

        ext_label = "CSV (.csv)"

        ext_accept = [
            "csv"
        ]

    st.info(
        f"Modo: **{ext_label}**. "
        f"Filtro: "
        f"`{get_filtro_nombre_adjunto() or 'Cualquier nombre'}`"
    )

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # CORREO
    # --------------------------------------------------------

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

            if not files:

                st.info(
                    "📭 No se encontraron "
                    "archivos nuevos."
                )

            else:

                st.success(
                    f"📎 {len(files)} "
                    "archivo(s) encontrado(s)."
                )

                for filepath in files:

                    with st.spinner(
                        f"Procesando "
                        f"{Path(filepath).name}..."
                    ):

                        resultado = (
                            procesar_archivo(
                                filepath
                            )
                        )

                    if resultado["ok"]:

                        st.success(
                            f"✅ "
                            f"{Path(filepath).name}: "
                            f"{resultado['insertados']} "
                            "insertados, "
                            f"{resultado['actualizados']} "
                            "actualizados."
                        )

                        if resultado.get(
                            "errores"
                        ):

                            with st.expander(
                                "Ver errores"
                            ):

                                for error in (
                                    resultado[
                                        "errores"
                                    ]
                                ):

                                    st.text(
                                        error
                                    )

                        if resultado.get(
                            "cambios"
                        ):

                            with st.expander(
                                "Ver cambios"
                            ):

                                for cambio in (
                                    resultado[
                                        "cambios"
                                    ]
                                ):

                                    st.text(
                                        cambio
                                    )

                    else:

                        st.error(
                            resultado.get(
                                "error",
                                "Error desconocido",
                            )
                        )

    # --------------------------------------------------------
    # MANUAL
    # --------------------------------------------------------

    with col2:

        st.subheader(
            "2️⃣ Subir archivo manualmente"
        )

        uploaded = st.file_uploader(
            f"Selecciona {ext_label}",
            type=ext_accept,
        )

        if uploaded:

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )

            safe_name = Path(
                uploaded.name
            ).name

            filepath = (
                UPLOAD_DIR
                / f"manual_{timestamp}_{safe_name}"
            )

            try:

                filepath.write_bytes(
                    uploaded.getvalue()
                )

                with st.spinner(
                    "Procesando archivo..."
                ):

                    resultado = (
                        procesar_archivo(
                            str(filepath)
                        )
                    )

                if resultado["ok"]:

                    st.success(
                        "✅ Archivo procesado."
                    )

                    st.write(
                        f"**Insertados:** "
                        f"{resultado['insertados']}"
                    )

                    st.write(
                        f"**Actualizados:** "
                        f"{resultado['actualizados']}"
                    )

                    if resultado.get(
                        "errores"
                    ):

                        with st.expander(
                            f"Errores "
                            f"({len(resultado['errores'])})"
                        ):

                            for error in (
                                resultado[
                                    "errores"
                                ]
                            ):

                                st.text(
                                    error
                                )

                    if resultado.get(
                        "cambios"
                    ):

                        with st.expander(
                            f"Cambios "
                            f"({len(resultado['cambios'])})"
                        ):

                            for cambio in (
                                resultado[
                                    "cambios"
                                ]
                            ):

                                st.text(
                                    cambio
                                )

                else:

                    st.error(
                        resultado.get(
                            "error",
                            "Error desconocido",
                        )
                    )

            except Exception as exc:

                logger.exception(
                    "Error procesando archivo manual."
                )

                st.error(
                    f"Error: {exc}"
                )


# ============================================================
# CONFIGURACIÓN
# ============================================================

def pestaña_configuracion():

    st.header(
        "⚙️ Configuración"
    )

    cfg = load_config()

    tabs = st.tabs(
        [
            "📧 Correo",
            "📋 Campos",
            "📁 Archivo",
            "👨‍⚕️ Profesionales",
            "📜 Logs",
            "💾 Sistema",
        ]
    )

    # --------------------------------------------------------
    # CORREO
    # --------------------------------------------------------

    with tabs[0]:

        st.subheader(
            "Configuración de Correo"
        )

        email_cfg = cfg.get(
            "email",
            {},
        )

        safe_cfg = dict(
            email_cfg
        )

        if "password" in safe_cfg:

            safe_cfg["password"] = "***"

        st.json(
            safe_cfg
        )

        st.caption(
            "Para modificar las credenciales, "
            "utilice nuevamente la configuración inicial "
            "o gestione data/config.enc."
        )

    # --------------------------------------------------------
    # CAMPOS
    # --------------------------------------------------------

    with tabs[1]:

        st.subheader(
            "Campos Parametrizados"
        )

        for campo in get_campos_excel():

            obligatorio = (
                "🔴 Obligatorio"
                if campo.get(
                    "obligatorio"
                )
                else "🟢 Opcional"
            )

            st.markdown(
                f"""
                <div class="
                    campo-card
                    {
                        'campo-obligatorio'
                        if campo.get('obligatorio')
                        else 'campo-opcional'
                    }
                ">
                    <b>{campo['nombre']}</b>
                    <br>
                    ID:
                    <code>{campo['id']}</code>
                    <br>
                    Tipo:
                    {campo.get('tipo', 'texto')}
                    <br>
                    {obligatorio}
                    <br>
                    Sinónimos:
                    {campo.get('sinonimos', 'N/A')}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------
    # ARCHIVO
    # --------------------------------------------------------

    with tabs[2]:

        st.subheader(
            "Tipo de Archivo"
        )

        st.write(
            f"**Formato:** "
            f"{get_tipo_archivo().upper()}"
        )

        st.write(
            f"**Filtro:** "
            f"{get_filtro_nombre_adjunto() or 'Cualquiera'}"
        )

    # --------------------------------------------------------
    # PROFESIONALES
    # --------------------------------------------------------

    with tabs[3]:

        st.subheader(
            "Profesionales"
        )

        profesionales = (
            get_profesionales()
        )

        if profesionales:

            st.dataframe(
                pd.DataFrame(
                    profesionales
                ),
                use_container_width=True,
            )

        encargado = get_encargado()

        st.write(
            f"**Encargado:** "
            f"{encargado.get('nombre', 'N/A')}"
        )

        st.write(
            f"**Correo:** "
            f"{encargado.get('email', 'N/A')}"
        )

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    with tabs[4]:

        st.subheader(
            "📜 Historial de Procesamiento"
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

            if logs:

                df_logs = pd.DataFrame(
                    [
                        {
                            "Fecha": log.fecha_proceso,
                            "Archivo": Path(
                                log.archivo
                            ).name,
                            "Insertados": log.insertados,
                            "Actualizados": log.actualizados,
                            "Errores": log.errores,
                            "Detalle": (
                                log.detalle[:200]
                                + "..."
                                if log.detalle
                                and len(log.detalle) > 200
                                else (
                                    log.detalle
                                    or ""
                                )
                            ),
                        }
                        for log in logs
                    ]
                )

                st.dataframe(
                    df_logs,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No hay logs todavía."
                )

        finally:

            db.close()

    # --------------------------------------------------------
    # SISTEMA
    # --------------------------------------------------------

    with tabs[5]:

        st.subheader(
            "💾 Información del Sistema"
        )

        st.write(
            f"**Base de datos:** "
            f"`{DATABASE_FILE}`"
        )

        st.write(
            f"**Existe:** "
            f"{'Sí' if DATABASE_FILE.exists() else 'No'}"
        )

        st.write(
            f"**Uploads:** "
            f"`{UPLOAD_DIR}`"
        )

        st.info(
            "El scheduler automático se ejecuta "
            "como proceso independiente mediante "
            "`python scheduler_runner.py`."
        )


# ============================================================
# ALERTAS
# ============================================================

def pestaña_alertas():

    st.header(
        "📤 Alertas e Informes"
    )

    db = get_db()

    try:

        casos = (
            db.query(Caso)
            .all()
        )

    finally:

        db.close()

    hoy = date.today()

    vencidos = []
    preventivos = []
    pendientes = []

    for caso in casos:

        if (
            caso.estado == "RESUELTO"
            or caso.fecha_validacion
            or not caso.fecha_ingreso
        ):
            continue

        dias = (
            hoy - caso.fecha_ingreso
        ).days

        pendientes.append(caso)

        if dias > 10:

            vencidos.append(caso)

        elif dias == 8:

            preventivos.append(caso)

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Vencidos",
        len(vencidos),
    )

    c2.metric(
        "Preventiva",
        len(preventivos),
    )

    c3.metric(
        "Pendientes",
        len(pendientes),
    )

    st.divider()

    encargado = get_encargado()

    destino = (
        encargado.get(
            "email",
            "",
        )
    )

    st.subheader(
        "📨 Enviar Resumen"
    )

    st.write(
        f"Destinatario: **{destino or 'No configurado'}**"
    )

    if st.button(
        "📧 Enviar Resumen Ahora",
        type="primary",
        use_container_width=True,
    ):

        if not destino:

            st.error(
                "No existe destinatario configurado."
            )

        else:

            with st.spinner(
                "Enviando..."
            ):

                ok, error = (
                    enviar_resumen_casos(
                        destino,
                        pendientes,
                        vencidos,
                        preventivos,
                    )
                )

            if ok:

                st.success(
                    "✅ Resumen enviado."
                )

            else:

                st.error(
                    f"❌ {error}"
                )

    st.divider()

    st.subheader(
        "📜 Historial de Alertas"
    )

    db = get_db()

    try:

        logs = (
            db.query(
                LogAlerta
            )
            .order_by(
                LogAlerta.fecha_envio.desc()
            )
            .limit(50)
            .all()
        )

        if logs:

            df_logs = pd.DataFrame(
                [
                    {
                        "Fecha": log.fecha_envio,
                        "Tipo": log.tipo_alerta,
                        "Caso ID": log.caso_id,
                        "Destinatario": log.destinatario,
                        "Contenido": log.contenido,
                    }
                    for log in logs
                ]
            )

            st.dataframe(
                df_logs,
                use_container_width=True,
            )

        else:

            st.info(
                "No se han enviado alertas."
            )

    finally:

        db.close()


# ============================================================
# MAIN
# ============================================================

def main():

    if not config_exists():

        pantalla_configuracion()

        return

    with st.sidebar:

        st.title(
            "📋 CasosSeguimiento"
        )

        st.caption(
            "v2.1"
        )

        st.divider()

        encargado = get_encargado()

        st.write(
            f"**Encargado:** "
            f"{encargado.get('nombre', 'N/A')}"
        )

        st.write(
            f"**Correo:** "
            f"{encargado.get('email', 'N/A')}"
        )

        st.write(
            f"**Archivo:** "
            f"{get_tipo_archivo().upper()}"
        )

        st.divider()

        if st.button(
            "🔄 Recargar datos",
            use_container_width=True,
        ):

            st.rerun()

        st.divider()

        st.caption(
            "📅 Scheduler independiente"
        )

        st.caption(
            "Correo: cada 5 min"
        )

        st.caption(
            "Alertas: cada hora"
        )

    tab_dashboard, tab_procesar, tab_config, tab_alertas = (
        st.tabs(
            [
                "📊 Dashboard",
                "📥 Procesar Datos",
                "⚙️ Configuración",
                "📤 Alertas",
            ]
        )
    )

    with tab_dashboard:

        dashboard()

    with tab_procesar:

        pestaña_procesar()

    with tab_config:

        pestaña_configuracion()

    with tab_alertas:

        pestaña_alertas()


if __name__ == "__main__":
    main()
