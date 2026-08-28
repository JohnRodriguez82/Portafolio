"""
CasosSeguimiento v2.1
Envío de alertas e informes vía SMTP.
"""

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config_manager import (
    get_email_settings,
    get_encargado,
)


logger = logging.getLogger(__name__)


# ============================================================
# SMTP
# ============================================================

def _get_smtp_connection():

    settings = get_email_settings()

    host = settings.get(
        "smtp_server",
        "smtp.gmail.com",
    )

    port = int(
        settings.get(
            "smtp_port",
            587,
        )
    )

    user = settings.get("email")
    password = settings.get("password")

    if not user or not password:
        raise RuntimeError(
            "Faltan credenciales SMTP."
        )

    server = smtplib.SMTP(
        host,
        port,
        timeout=30,
    )

    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login(
        user,
        password,
    )

    return server, user


# ============================================================
# ENVÍO GENÉRICO
# ============================================================

def enviar_alerta(
    destinatario: str,
    asunto: str,
    cuerpo_html: str,
):

    if not destinatario:
        return False, (
            "No se especificó destinatario."
        )

    server = None

    try:

        server, remitente = (
            _get_smtp_connection()
        )

        msg = MIMEMultipart(
            "alternative"
        )

        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destinatario

        msg.attach(
            MIMEText(
                cuerpo_html,
                "html",
                "utf-8",
            )
        )

        server.sendmail(
            remitente,
            [destinatario],
            msg.as_string(),
        )

        return True, None

    except Exception as exc:

        logger.exception(
            "Error SMTP: %s",
            exc,
        )

        return False, str(exc)

    finally:

        if server:

            try:
                server.quit()
            except Exception:
                pass


# ============================================================
# RESUMEN
# ============================================================

def enviar_resumen_casos(
    destinatario: str,
    casos_pendientes: list,
    casos_vencidos: list,
    casos_preventiva: list,
):

    encargado = get_encargado()

    nombre_encargado = html.escape(
        str(
            encargado.get(
                "nombre",
                "Encargado",
            )
        )
    )

    html_body = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #333;
            }}

            .header {{
                background: #1f4e79;
                color: white;
                padding: 15px;
                text-align: center;
            }}

            .section {{
                margin: 20px 0;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 13px;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 6px;
                text-align: left;
            }}

            th {{
                background: #f2f2f2;
            }}

            .vencido {{
                color: #dc3545;
                font-weight: bold;
            }}

            .preventiva {{
                color: #b8860b;
                font-weight: bold;
            }}
        </style>
    </head>

    <body>

        <div class="header">
            <h2>📊 Resumen de Seguimiento de Casos</h2>

            <p>
                Generado automáticamente para:
                <b>{nombre_encargado}</b>
            </p>
        </div>

        <div class="section">

            <h3>
                🔴 Casos Vencidos
                ({len(casos_vencidos)})
            </h3>

            {
                tabla_casos(
                    casos_vencidos,
                    "vencido"
                )
                if casos_vencidos
                else "<p>No hay casos vencidos.</p>"
            }

        </div>

        <div class="section">

            <h3>
                🟡 Casos en Alerta Preventiva
                ({len(casos_preventiva)})
            </h3>

            {
                tabla_casos(
                    casos_preventiva,
                    "preventiva"
                )
                if casos_preventiva
                else "<p>No hay casos en alerta preventiva.</p>"
            }

        </div>

        <div class="section">

            <h3>
                🔵 Casos Pendientes
                ({len(casos_pendientes)})
            </h3>

            {
                tabla_casos(
                    casos_pendientes,
                    "pendiente"
                )
                if casos_pendientes
                else "<p>No hay casos pendientes.</p>"
            }

        </div>

        <hr>

        <p style="font-size:12px;color:#666;">
            Este correo fue generado automáticamente
            por CasosSeguimiento v2.1.
        </p>

    </body>
    </html>
    """

    return enviar_alerta(
        destinatario,
        "📊 Resumen de Casos - Seguimiento",
        html_body,
    )


# ============================================================
# ALERTA INDIVIDUAL
# ============================================================

def enviar_alerta_individual(
    destinatario: str,
    caso,
    tipo: str,
    dias: int,
):

    es_vencida = (
        tipo.upper() == "VENCIDA"
    )

    color = (
        "#dc3545"
        if es_vencida
        else "#ffc107"
    )

    emoji = (
        "🚨"
        if es_vencida
        else "⚠️"
    )

    titulo = (
        "CASO VENCIDO"
        if es_vencida
        else "ALERTA PREVENTIVA"
    )

    extra_rows = ""

    if caso.campos_extra:

        for key, value in (
            caso.campos_extra.items()
        ):

            extra_rows += (
                "<p>"
                f"<b>{html.escape(str(key).replace('_', ' ').title())}:</b> "
                f"{html.escape(str(value))}"
                "</p>"
            )

    numero_caso = html.escape(
        str(caso.numero_caso)
    )

    profesional = html.escape(
        str(caso.profesional or "N/A")
    )

    sede = html.escape(
        str(caso.sede or "N/A")
    )

    seccion = html.escape(
        str(caso.seccion or "N/A")
    )

    organo = html.escape(
        str(caso.organo or "N/A")
    )

    estudios = html.escape(
        str(caso.estudios or "N/A")
    )

    fecha_ingreso = html.escape(
        str(caso.fecha_ingreso)
    )

    fecha_validacion = html.escape(
        str(
            caso.fecha_validacion
            or "Pendiente"
        )
    )

    mensaje = (
        "Este caso ha superado el límite "
        "de 10 días. Requiere acción inmediata."
        if es_vencida
        else
        "Este caso se encuentra en alerta preventiva."
    )

    html_body = f"""
    <html>
    <body
        style="
            font-family:Arial,sans-serif;
            color:#333;
        "
    >

        <div
            style="
                background:{color};
                color:white;
                padding:15px;
                text-align:center;
            "
        >
            <h2>
                {emoji} {titulo}
            </h2>
        </div>

        <div style="padding:20px;">

            <p>
                <b>Número de Caso:</b>
                {numero_caso}
            </p>

            <p>
                <b>Profesional:</b>
                {profesional}
            </p>

            <p>
                <b>Sede:</b>
                {sede}
            </p>

            <p>
                <b>Sección:</b>
                {seccion}
            </p>

            <p>
                <b>Órgano:</b>
                {organo}
            </p>

            <p>
                <b>Estudios:</b>
                {estudios}
            </p>

            <p>
                <b>Fecha de Ingreso:</b>
                {fecha_ingreso}
            </p>

            <p>
                <b>Fecha de Validación:</b>
                {fecha_validacion}
            </p>

            <p>
                <b>Días transcurridos:</b>
                {dias}
            </p>

            {extra_rows}

            <hr>

            <p
                style="
                    color:#666;
                    font-size:13px;
                "
            >
                {mensaje}
            </p>

        </div>

    </body>
    </html>
    """

    asunto = (
        f"{emoji} {titulo} - "
        f"Caso {numero_caso}"
    )

    return enviar_alerta(
        destinatario,
        asunto,
        html_body,
    )


# ============================================================
# TABLA
# ============================================================

def tabla_casos(
    casos,
    tipo_badge,
):

    filas = ""

    for caso in casos:

        if tipo_badge == "vencido":
            estado = (
                '<span style="color:#dc3545;'
                'font-weight:bold;">VENCIDO</span>'
            )

        elif tipo_badge == "preventiva":
            estado = (
                '<span style="color:#b8860b;'
                'font-weight:bold;">'
                '2 DÍAS RESTANTES'
                '</span>'
            )

        else:
            estado = (
                '<span style="color:#17a2b8;'
                'font-weight:bold;">PENDIENTE</span>'
            )

        filas += f"""
        <tr>
            <td>{html.escape(str(caso.numero_caso))}</td>
            <td>{html.escape(str(caso.profesional or 'N/A'))}</td>
            <td>{html.escape(str(caso.sede or 'N/A'))}</td>
            <td>{html.escape(str(caso.organo or 'N/A'))}</td>
            <td>{html.escape(str(caso.fecha_ingreso))}</td>
            <td>{html.escape(str(caso.fecha_validacion or 'Pendiente'))}</td>
            <td>{estado}</td>
        </tr>
        """

    return f"""
    <table>
        <tr>
            <th>Caso</th>
            <th>Profesional</th>
            <th>Sede</th>
            <th>Órgano</th>
            <th>Ingreso</th>
            <th>Validación</th>
            <th>Estado</th>
        </tr>

        {filas}

    </table>
    """
