"""
Aplicación principal de Seguimiento de Casos v2.
Soporta: campos parametrizables, Excel/CSV, filtro de nombre de adjunto,
actualización incremental y carga manual.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import get_db, Caso, LogAlerta, LogProcesamiento
from config_manager import (
    config_exists, save_config, load_config,
    get_email_settings, get_encargado, get_profesionales,
    get_campos_excel, get_tipo_archivo, get_filtro_nombre_adjunto,
    _campos_default
)
from email_processor import check_emails_and_download_excel
from excel_parser import procesar_archivo
from email_sender import enviar_resumen_casos, enviar_alerta_individual
from scheduler_service import iniciar_scheduler, detener_scheduler
import os

st.set_page_config(
    page_title="Seguimiento de Casos v2",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .kpi-title { font-size: 14px; opacity: 0.9; }
    .kpi-value { font-size: 32px; font-weight: bold; }
    .alert-vencido { background-color: #ffebee; border-left: 5px solid #f44336; padding: 10px; border-radius: 5px; }
    .alert-preventiva { background-color: #fff8e1; border-left: 5px solid #ffc107; padding: 10px; border-radius: 5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; }
    .campo-card { background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 8px 0; border: 1px solid #dee2e6; }
    .campo-obligatorio { border-left: 4px solid #dc3545; }
    .campo-opcional { border-left: 4px solid #28a745; }
</style>
""", unsafe_allow_html=True)

if "scheduler_started" not in st.session_state:
    if config_exists():
        iniciar_scheduler()
        st.session_state.scheduler_started = True


def calcular_dias(fecha_ingreso):
    if not fecha_ingreso:
        return 0
    return (date.today() - fecha_ingreso).days


def estado_visual(dias, estado_db, fecha_validacion):
    if estado_db == "RESUELTO" or fecha_validacion:
        return "✅ RESUELTO", "green"
    if dias > 10:
        return "🚨 VENCIDO", "red"
    if dias == 8:
        return "⚠️ 2 DÍAS RESTANTES", "orange"
    if dias >= 9:
        return "🔴 CRÍTICO", "red"
    return "🔵 PENDIENTE", "blue"


# =========================================================
# PANTALLA DE CONFIGURACIÓN INICIAL
# =========================================================
def pantalla_configuracion():
    st.title("🔧 Configuración Inicial del Sistema")
    st.info("Complete todos los pasos. Los datos se guardarán encriptados en el disco.")

    step = st.radio("Paso", ["1. Correo y Encargado", "2. Campos del Archivo", "3. Tipo de Archivo y Adjunto", "4. Profesionales"], horizontal=True)

    if step == "1. Correo y Encargado":
        with st.form("config_paso1"):
            st.subheader("📧 Configuración del Correo (IMAP/SMTP)")
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Correo electrónico", placeholder="seguimiento@empresa.com")
                password = st.text_input("Contraseña / App Password", type="password",
                                         help="Gmail: usa 'App Password' (no tu contraseña normal).")
            with col2:
                imap_server = st.text_input("Servidor IMAP", value="imap.gmail.com")
                smtp_server = st.text_input("Servidor SMTP", value="smtp.gmail.com")
            col3, col4 = st.columns(2)
            with col3:
                imap_port = st.number_input("Puerto IMAP", value=993, step=1)
            with col4:
                smtp_port = st.number_input("Puerto SMTP", value=587, step=1)

            st.divider()
            st.subheader("👤 Encargado de Seguimiento")
            nombre_encargado = st.text_input("Nombre completo")
            st.caption(f"El correo de alertas será el mismo configurado arriba: {email}")

            if st.form_submit_button("Guardar y continuar ➡️", type="primary"):
                if not all([email, password, nombre_encargado]):
                    st.error("Todos los campos son obligatorios.")
                else:
                    cfg = load_config()
                    cfg["email"] = {"email": email, "password": password, "imap_server": imap_server,
                                    "smtp_server": smtp_server, "imap_port": int(imap_port), "smtp_port": int(smtp_port)}
                    cfg["encargado"] = {"nombre": nombre_encargado, "email": email}
                    save_config(cfg)
                    st.success("Paso 1 guardado. Selecciona el paso 2 arriba.")

    elif step == "2. Campos del Archivo":
        st.subheader("📋 Configurar Campos del Archivo de Entrada")
        st.info("Define qué columnas esperas en el Excel/CSV. Puedes agregar, quitar o modificar campos.")

        cfg = load_config()
        campos = cfg.get("campos_excel", _campos_default())

        with st.form("config_campos"):
            campos_editados = []
            for i, campo in enumerate(campos):
                cols = st.columns([2, 2, 2, 1, 1, 1])
                with cols[0]:
                    cid = st.text_input(f"ID campo {i+1}", value=campo["id"], key=f"cid_{i}")
                with cols[1]:
                    cname = st.text_input(f"Nombre {i+1}", value=campo["nombre"], key=f"cname_{i}")
                with cols[2]:
                    csin = st.text_input(f"Sinónimos {i+1}", value=campo.get("sinonimos", ""), key=f"csin_{i}",
                                         help="Separados por coma. Ej: sede,ubicación,lugar")
                with cols[3]:
                    ctipo = st.selectbox(f"Tipo {i+1}", ["texto", "fecha", "numero"], 
                                         index=["texto", "fecha", "numero"].index(campo.get("tipo", "texto")), key=f"ctipo_{i}")
                with cols[4]:
                    coblig = st.checkbox(f"Obligatorio {i+1}", value=campo.get("obligatorio", False), key=f"coblig_{i}")
                with cols[5]:
                    cactivo = st.checkbox(f"Activo {i+1}", value=campo.get("activo", True), key=f"cactivo_{i}")

                if cactivo:
                    campos_editados.append({"id": cid, "nombre": cname, "tipo": ctipo, 
                                            "obligatorio": coblig, "sinonimos": csin, "activo": True})

            st.divider()
            st.subheader("➕ Agregar nuevo campo")
            cols_new = st.columns([2, 2, 2, 1, 1])
            with cols_new[0]:
                new_id = st.text_input("ID del nuevo campo", key="new_id", placeholder="ej: observacion")
            with cols_new[1]:
                new_name = st.text_input("Nombre visible", key="new_name", placeholder="ej: Observación")
            with cols_new[2]:
                new_sin = st.text_input("Sinónimos", key="new_sin", placeholder="observacion,nota,comentario")
            with cols_new[3]:
                new_tipo = st.selectbox("Tipo", ["texto", "fecha", "numero"], key="new_tipo")
            with cols_new[4]:
                new_oblig = st.checkbox("Obligatorio", key="new_oblig")

            if st.form_submit_button("💾 Guardar Configuración de Campos", type="primary"):
                if new_id and new_name:
                    campos_editados.append({"id": new_id, "nombre": new_name, "tipo": new_tipo,
                                            "obligatorio": new_oblig, "sinonimos": new_sin, "activo": True})
                cfg["campos_excel"] = campos_editados
                save_config(cfg)
                st.success(f"Campos guardados: {len(campos_editados)} campos activos.")
                st.balloons()

    elif step == "3. Tipo de Archivo y Adjunto":
        with st.form("config_archivo"):
            st.subheader("📁 Tipo de Archivo y Filtro de Adjunto")
            tipo_archivo = st.radio("Formato de archivo a procesar", ["excel", "csv"], horizontal=True,
                                    index=0 if get_tipo_archivo() == "excel" else 1)

            st.divider()
            st.subheader("🔍 Filtro de nombre del archivo adjunto")
            filtro = st.text_input("Patrón del nombre de archivo (opcional)", 
                                   value=get_filtro_nombre_adjunto(),
                                   placeholder="ej: reporte_casos*  o  *.xlsx  o  dejar vacío para cualquiera",
                                   help="Usa * como comodín. Ej: 'reporte*' captura 'reporte_enero.xlsx', 'reporte_febrero.csv', etc.")

            st.info("Si dejas el filtro vacío, se aceptará cualquier archivo del tipo seleccionado.")

            if st.form_submit_button("💾 Guardar", type="primary"):
                cfg = load_config()
                cfg["tipo_archivo"] = tipo_archivo
                cfg["filtro_nombre_adjunto"] = filtro.strip()
                save_config(cfg)
                st.success("Configuración de archivo guardada.")

    elif step == "4. Profesionales":
        with st.form("config_profesionales"):
            st.subheader("👨‍⚕️ Profesionales a Monitorear")
            st.caption("Ingresa los nombres separados por comas.")
            profesionales_input = st.text_area("Lista de profesionales", height=100,
                                               placeholder="Dr. Pérez, Dra. López, Dr. Martínez")

            if st.form_submit_button("✅ Finalizar Configuración", type="primary"):
                if not profesionales_input:
                    st.error("Debes ingresar al menos un profesional.")
                else:
                    profesionales_list = [p.strip() for p in profesionales_input.split(",") if p.strip()]
                    cfg = load_config()
                    cfg["profesionales"] = [{"nombre": p, "especialidad": ""} for p in profesionales_list]
                    cfg["tiempo_resolucion_dias"] = 10
                    cfg["dias_alerta_previa"] = 2
                    save_config(cfg)
                    st.success("🎉 ¡Configuración completada! Recarga la página (F5) para entrar al dashboard.")
                    st.balloons()


# =========================================================
# DASHBOARD
# =========================================================
def dashboard():
    st.title("📊 Tablero de Control - Seguimiento de Casos")

    db = get_db()
    try:
        casos = db.query(Caso).all()
    finally:
        db.close()

    if not casos:
        st.warning("📭 No hay casos registrados. Sube un archivo manualmente o espera al correo.")
        return

    data = []
    for c in casos:
        dias = calcular_dias(c.fecha_ingreso)
        estado_str, color = estado_visual(dias, c.estado, c.fecha_validacion)
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
            "Última Actualización": c.fecha_ultima_actualizacion,
        }
        # Agregar campos extra al dataframe
        if c.campos_extra:
            for k, v in c.campos_extra.items():
                row[k.replace("_", " ").title()] = v
        data.append(row)

    df = pd.DataFrame(data)

    total = len(df)
    resueltos = len(df[df["Estado DB"] == "RESUELTO"])
    vencidos = len(df[df["Color"] == "red"])
    preventiva = len(df[df["Color"] == "orange"])
    pendientes = total - resueltos - vencidos - preventiva

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL CASOS</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="kpi-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"><div class="kpi-title">RESUELTOS</div><div class="kpi-value">{resueltos}</div></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="kpi-card" style="background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);"><div class="kpi-title">PENDIENTES</div><div class="kpi-value">{pendientes}</div></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="kpi-card" style="background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);"><div class="kpi-title">ALERTA 2 DÍAS</div><div class="kpi-value">{preventiva}</div></div>', unsafe_allow_html=True)
    with kpi5:
        st.markdown(f'<div class="kpi-card" style="background: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%);"><div class="kpi-title">VENCIDOS</div><div class="kpi-value">{vencidos}</div></div>', unsafe_allow_html=True)

    st.divider()

    if vencidos > 0:
        st.markdown(f'<div class="alert-vencido">🚨 <b>ATENCIÓN:</b> {vencidos} casos VENCIDOS.</div>', unsafe_allow_html=True)
    if preventiva > 0:
        st.markdown(f'<div class="alert-preventiva">⚠️ {preventiva} casos vencen en 2 días.</div>', unsafe_allow_html=True)

    st.divider()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_prof = st.multiselect("Filtrar por Profesional", options=sorted(df["Profesional"].unique()), default=[])
    with col_f2:
        filtro_estado = st.multiselect("Filtrar por Estado", options=sorted(df["Estado Visual"].unique()), default=[])
    with col_f3:
        sedes = [s for s in df["Sede"].dropna().unique() if s]
        filtro_sede = st.multiselect("Filtrar por Sede", options=sorted(sedes), default=[])

    df_filtered = df.copy()
    if filtro_prof:
        df_filtered = df_filtered[df_filtered["Profesional"].isin(filtro_prof)]
    if filtro_estado:
        df_filtered = df_filtered[df_filtered["Estado Visual"].isin(filtro_estado)]
    if filtro_sede:
        df_filtered = df_filtered[df_filtered["Sede"].isin(filtro_sede)]

    st.subheader("📋 Listado de Casos")
    display_df = df_filtered.drop(columns=["Color", "Estado DB"])

    def color_rows(row):
        if row["Color"] == "red":
            return ["background-color: #ffebee"] * len(row)
        elif row["Color"] == "orange":
            return ["background-color: #fff8e1"] * len(row)
        elif row["Color"] == "green":
            return ["background-color: #e8f5e9"] * len(row)
        return [""] * len(row)

    st.dataframe(display_df.style.apply(color_rows, axis=1), use_container_width=True, height=450)

    st.divider()
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📈 Casos por Profesional")
        prof_counts = df[df["Estado DB"] != "RESUELTO"]["Profesional"].value_counts()
        if not prof_counts.empty:
            st.bar_chart(prof_counts)
    with col_g2:
        st.subheader("🥧 Distribución de Estados")
        estado_counts = df["Estado Visual"].value_counts()
        if not estado_counts.empty:
            try:
                import plotly.express as px
                fig = px.pie(values=estado_counts.values, names=estado_counts.index, color=estado_counts.index,
                             color_discrete_map={"✅ RESUELTO": "#38ef7d", "🔵 PENDIENTE": "#6dd5ed",
                                                "⚠️ 2 DÍAS RESTANTES": "#ffd200", "🔴 CRÍTICO": "#ff6b6b", "🚨 VENCIDO": "#ef473a"})
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.bar_chart(estado_counts)


# =========================================================
# PESTAÑA: PROCESAR DATOS
# =========================================================
def pestaña_procesar():
    st.header("📥 Procesamiento de Datos")
    tipo = get_tipo_archivo()
    ext_label = "Excel (.xlsx, .xls)" if tipo == "excel" else "CSV (.csv)"
    ext_accept = [".xlsx", ".xls"] if tipo == "excel" else [".csv"]

    st.info(f"Modo configurado: **{ext_label}**. Filtro de adjunto: '{get_filtro_nombre_adjunto() or 'Cualquier nombre'}'")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1️⃣ Revisar correo electrónico")
        if st.button("🔄 Revisar correo ahora", use_container_width=True, type="primary"):
            with st.spinner("Conectando al servidor de correo..."):
                files = check_emails_and_download_excel()
            if files:
                st.success(f"📎 {len(files)} archivo(s) encontrado(s).")
                for f in files:
                    with st.spinner(f"Procesando {os.path.basename(f)}..."):
                        res = procesar_archivo(f)
                    if res["ok"]:
                        st.success(f"✅ `{os.path.basename(f)}`: {res['insertados']} insertados, {res['actualizados']} actualizados.")
                        if res.get("cambios"):
                            with st.expander(f"Ver {len(res['cambios'])} cambios detectados"):
                                for c in res["cambios"]:
                                    st.text(f"• {c}")
                        with st.expander("Columnas detectadas"):
                            st.json(res["columnas_detectadas"])
                    else:
                        st.error(f"❌ Error: {res.get('error')}")
            else:
                st.info("📭 No se encontraron correos nuevos con adjuntos que coincidan.")

    with col2:
        st.subheader("2️⃣ Subir archivo manualmente")
        uploaded = st.file_uploader(f"Selecciona un archivo {ext_label}", type=ext_accept)
        if uploaded:
            ext = ".xlsx" if tipo == "excel" else ".csv"
            tmp_path = f"data/uploads/manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded.name}"
            with open(tmp_path, "wb") as f:
                f.write(uploaded.getvalue())
            with st.spinner("Procesando archivo..."):
                res = procesar_archivo(tmp_path)
            if res["ok"]:
                st.success(f"✅ Procesado: {res['insertados']} insertados, {res['actualizados']} actualizados.")
                if res.get("cambios"):
                    with st.expander(f"Cambios detectados ({len(res['cambios'])})"):
                        for c in res["cambios"]:
                            st.text(f"• {c}")
                if res["errores"]:
                    with st.expander(f"Errores ({len(res['errores'])})"):
                        for e in res["errores"]:
                            st.text(e)
            else:
                st.error(f"❌ Error: {res.get('error')}")


# =========================================================
# PESTAÑA: CONFIGURACIÓN / PROFESIONALES / CAMPOS
# =========================================================
def pestaña_configuracion():
    st.header("⚙️ Configuración del Sistema")

    cfg = load_config()
    tabs = st.tabs(["📧 Correo", "📋 Campos del Archivo", "📁 Tipo de Archivo", "👨‍⚕️ Profesionales", "📜 Logs"])

    with tabs[0]:
        email_cfg = cfg.get("email", {})
        st.subheader("Configuración de Correo")
        st.json({k: ("***" if k == "password" else v) for k, v in email_cfg.items()})
        st.caption("Para modificar, elimina `data/config.enc` y reinicia la app.")

    with tabs[1]:
        st.subheader("Campos Parametrizados del Archivo")
        campos = get_campos_excel()
        for c in campos:
            oblig = "🔴 Obligatorio" if c.get("obligatorio") else "🟢 Opcional"
            st.markdown(f"""
            <div class="campo-card {'campo-obligatorio' if c.get('obligatorio') else 'campo-opcional'}">
                <b>{c['nombre']}</b> (ID: <code>{c['id']}</code>) | Tipo: {c.get('tipo','texto')} | {oblig}<br>
                <small>Sinónimos: {c.get('sinonimos','N/A')}</small>
            </div>
            """, unsafe_allow_html=True)

    with tabs[2]:
        st.subheader("Tipo de Archivo y Filtro")
        st.write(f"**Formato:** {get_tipo_archivo().upper()}")
        st.write(f"**Filtro de nombre:** {get_filtro_nombre_adjunto() or 'Cualquier nombre'}")

    with tabs[3]:
        st.subheader("Profesionales Monitoreados")
        profesionales = get_profesionales()
        if profesionales:
            st.dataframe(pd.DataFrame(profesionales), use_container_width=True)
        enc = get_encargado()
        st.write(f"**Encargado:** {enc.get('nombre', 'N/A')} ({enc.get('email', 'N/A')})")

    with tabs[4]:
        st.subheader("📜 Historial de Procesamiento")
        db = get_db()
        try:
            logs = db.query(LogProcesamiento).order_by(LogProcesamiento.fecha_proceso.desc()).limit(30).all()
            if logs:
                df_logs = pd.DataFrame([{
                    "Fecha": l.fecha_proceso,
                    "Archivo": os.path.basename(l.archivo),
                    "Insertados": l.insertados,
                    "Actualizados": l.actualizados,
                    "Errores": l.errores,
                    "Detalle": l.detalle[:100] + "..." if l.detalle and len(l.detalle) > 100 else (l.detalle or "")
                } for l in logs])
                st.dataframe(df_logs, use_container_width=True)
            else:
                st.info("No hay logs de procesamiento aún.")
        finally:
            db.close()


# =========================================================
# PESTAÑA: ALERTAS
# =========================================================
def pestaña_alertas():
    st.header("📤 Alertas e Informes por Correo")

    db = get_db()
    try:
        casos = db.query(Caso).all()
    finally:
        db.close()

    hoy = date.today()
    vencidos = []
    preventivos = []
    pendientes = []

    for c in casos:
        if c.estado == "RESUELTO" or not c.fecha_ingreso:
            continue
        dias = (hoy - c.fecha_ingreso).days
        pendientes.append(c)
        if dias > 10:
            vencidos.append(c)
        elif dias == 8:
            preventivos.append(c)

    col1, col2, col3 = st.columns(3)
    col1.metric("Vencidos", len(vencidos))
    col2.metric("Preventiva (2 días)", len(preventivos))
    col3.metric("Pendientes", len(pendientes))

    st.divider()

    enc = get_encargado()
    destino = enc.get("email", "")

    st.subheader("📨 Enviar Resumen de Estado")
    st.write(f"Destinatario: **{destino}**")
    if st.button("📧 Enviar Resumen Ahora", type="primary", use_container_width=True):
        with st.spinner("Enviando correo..."):
            ok, err = enviar_resumen_casos(destino, pendientes, vencidos, preventivos)
        if ok:
            st.success("✅ Resumen enviado correctamente.")
        else:
            st.error(f"❌ Error: {err}")

    st.divider()
    st.subheader("📜 Historial de Alertas Enviadas")
    db = get_db()
    try:
        logs = db.query(LogAlerta).order_by(LogAlerta.fecha_envio.desc()).limit(50).all()
        if logs:
            df_logs = pd.DataFrame([{
                "Fecha": l.fecha_envio,
                "Tipo": l.tipo_alerta,
                "Caso ID": l.caso_id,
                "Destinatario": l.destinatario,
                "Contenido": l.contenido,
            } for l in logs])
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No se han enviado alertas aún.")
    finally:
        db.close()


# =========================================================
# MAIN
# =========================================================
def main():
    if not config_exists():
        pantalla_configuracion()
        return

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2920/2920277.png", width=80)
        st.title("📋 Seguimiento de Casos")
        st.caption("v2.0 - Campos parametrizables | Excel/CSV | Actualización incremental")
        st.divider()

        enc = get_encargado()
        st.write(f"**Encargado:** {enc.get('nombre', 'N/A')}")
        st.write(f"**Correo:** {enc.get('email', 'N/A')}")
        st.write(f"**Archivo:** {get_tipo_archivo().upper()}")
        st.divider()

        if st.button("🔄 Recargar datos", use_container_width=True):
            st.rerun()

        st.divider()
        st.caption("Automatización activa (correo cada 5 min, alertas cada hora)")

    tab_dashboard, tab_procesar, tab_config, tab_alertas = st.tabs([
        "📊 Dashboard", "📥 Procesar Datos", "⚙️ Configuración", "📤 Alertas"
    ])

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
