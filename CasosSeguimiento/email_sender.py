"""
Envío de alertas e informes vía SMTP.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config_manager import get_email_settings, get_encargado


def _get_smtp_connection():
    settings = get_email_settings()
    host = settings.get("smtp_server", "smtp.gmail.com")
    port = settings.get("smtp_port", 587)
    user = settings.get("email")
    password = settings.get("password")

    server = smtplib.SMTP(host, port)
    server.starttls()
    server.login(user, password)
    return server, user


def enviar_alerta(destinatario: str, asunto: str, cuerpo_html: str):
    try:
        server, remitente = _get_smtp_connection()
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destinatario
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
        server.sendmail(remitente, [destinatario], msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def enviar_resumen_casos(destinatario: str, casos_pendientes: list, casos_vencidos: list, casos_preventiva: list):
    encargado = get_encargado()
    nombre_encargado = encargado.get("nombre", "Encargado")

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background: #1f4e79; color: white; padding: 15px; text-align: center; }}
            .section {{ margin: 20px 0; }}
            .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
            .vencido {{ background: #dc3545; }}
            .preventiva {{ background: #ffc107; color: #333; }}
            .pendiente {{ background: #17a2b8; }}
            table {{ width: 100%%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
            th {{ background: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📊 Resumen de Seguimiento de Casos</h2>
            <p>Generado automáticamente para: <b>{nombre_encargado}</b></p>
            <p style="font-size:12px;">{__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>

        <div class="section">
            <h3>🔴 Casos Vencidos ({len(casos_vencidos)})</h3>
            {tabla_casos(casos_vencidos, "vencido") if casos_vencidos else "<p>No hay casos vencidos.</p>"}
        </div>

        <div class="section">
            <h3>🟡 Casos en Alerta Preventiva - 2 días para vencer ({len(casos_preventiva)})</h3>
            {tabla_casos(casos_preventiva, "preventiva") if casos_preventiva else "<p>No hay casos en alerta preventiva.</p>"}
        </div>

        <div class="section">
            <h3>🔵 Casos Pendientes ({len(casos_pendientes)})</h3>
            {tabla_casos(casos_pendientes, "pendiente") if casos_pendientes else "<p>No hay casos pendientes.</p>"}
        </div>

        <hr>
        <p style="font-size:12px; color:#666;">
            Este correo fue generado automáticamente por la herramienta de seguimiento de casos.<br>
            Para más detalle, consulte el tablero de control.
        </p>
    </body>
    </html>
    """
    return enviar_alerta(destinatario, "📊 Resumen de Casos - Seguimiento", html)


def enviar_alerta_individual(destinatario: str, caso, tipo: str, dias: int):
    color = "#dc3545" if tipo == "VENCIDA" else "#ffc107"
    emoji = "🚨" if tipo == "VENCIDA" else "⚠️"
    titulo = "CASO VENCIDO" if tipo == "VENCIDA" else "ALERTA PREVENTIVA"

    extra_rows = ""
    if caso.campos_extra:
        for k, v in caso.campos_extra.items():
            extra_rows += f"<p><b>{k.replace('_', ' ').title()}:</b> {v}</p>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background:{color}; color:white; padding:15px; text-align:center;">
            <h2>{emoji} {titulo}</h2>
        </div>
        <div style="padding: 20px;">
            <p><b>Número de Caso:</b> {caso.numero_caso}</p>
            <p><b>Profesional:</b> {caso.profesional}</p>
            <p><b>Sede:</b> {caso.sede or 'N/A'}</p>
            <p><b>Sección:</b> {caso.seccion or 'N/A'}</p>
            <p><b>Órgano:</b> {caso.organo or 'N/A'}</p>
            <p><b>Estudios:</b> {caso.estudios or 'N/A'}</p>
            <p><b>Fecha de Ingreso:</b> {caso.fecha_ingreso}</p>
            <p><b>Fecha de Validación:</b> {caso.fecha_validacion or 'Pendiente'}</p>
            <p><b>Días transcurridos:</b> {dias}</p>
            {extra_rows}
            <hr>
            <p style="color:#666; font-size:13px;">
                {'Este caso ha superado el límite de 10 días. Requiere acción inmediata.' if tipo == 'VENCIDA' else 'Este caso vencerá en 2 días (límite: 10 días desde el ingreso).'}
            </p>
        </div>
    </body>
    </html>
    """
    asunto = f"{emoji} {titulo} - Caso {caso.numero_caso}"
    return enviar_alerta(destinatario, asunto, html)


def tabla_casos(casos, tipo_badge):
    filas = ""
    for c in casos:
        estado_badge = {
            "vencido": '<span class="badge vencido">VENCIDO</span>',
            "preventiva": '<span class="badge preventiva">2 DÍAS RESTANTES</span>',
            "pendiente": '<span class="badge pendiente">PENDIENTE</span>'
        }.get(tipo_badge, "")
        filas += f"""
        <tr>
            <td>{c.numero_caso}</td>
            <td>{c.profesional}</td>
            <td>{c.sede or 'N/A'}</td>
            <td>{c.organo or 'N/A'}</td>
            <td>{c.fecha_ingreso}</td>
            <td>{c.fecha_validacion or 'Pendiente'}</td>
            <td>{estado_badge}</td>
        </tr>
        """
    return f"""
    <table>
        <tr>
            <th>Caso</th><th>Profesional</th><th>Sede</th><th>Órgano</th><th>Ingreso</th><th>Validación</th><th>Estado</th>
        </tr>
        {filas}
    </table>
    """
