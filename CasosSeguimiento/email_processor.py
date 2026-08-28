"""
CasosSeguimiento v2.1
Lectura de correos vía IMAP y descarga segura de adjuntos.
"""

import email
import fnmatch
import imaplib
import logging
from datetime import datetime
from email.header import decode_header
from pathlib import Path

from config_manager import (
    get_email_settings,
    get_filtro_nombre_adjunto,
    get_tipo_archivo,
)
from paths import UPLOAD_DIR, ensure_directories


logger = logging.getLogger(__name__)


# ============================================================
# EXTENSIONES
# ============================================================

def _extensiones_permitidas():

    tipo = get_tipo_archivo()

    if tipo == "csv":
        return [".csv"]

    return [
        ".xlsx",
        ".xls",
    ]


# ============================================================
# NOMBRE ARCHIVO
# ============================================================

def _decodificar_filename(filename):
    if not filename:
        return ""

    try:
        partes = decode_header(filename)

        resultado = ""

        for parte, encoding in partes:

            if isinstance(parte, bytes):
                resultado += parte.decode(
                    encoding or "utf-8",
                    errors="replace",
                )
            else:
                resultado += str(parte)

        return resultado

    except Exception:
        return str(filename)


def _nombre_seguro(filename: str) -> str:

    filename = _decodificar_filename(
        filename
    )

    # Elimina rutas potenciales
    filename = Path(filename).name

    # Caracteres peligrosos
    caracteres = '<>:"/\\|?*'

    for caracter in caracteres:
        filename = filename.replace(
            caracter,
            "_",
        )

    filename = filename.strip()

    if not filename:
        filename = "adjunto"

    # Evitar nombres excesivamente largos
    return filename[:180]


# ============================================================
# FILTRO
# ============================================================

def _coincide_filtro(filename: str) -> bool:

    filtro = get_filtro_nombre_adjunto().strip()

    if not filtro:
        return True

    return fnmatch.fnmatch(
        filename.lower(),
        filtro.lower(),
    )


# ============================================================
# PROCESAMIENTO IMAP
# ============================================================

def check_emails_and_download_excel():

    ensure_directories()

    settings = get_email_settings()

    if not settings:
        logger.warning(
            "No existe configuración de correo."
        )
        return []

    host = settings.get(
        "imap_server",
        "imap.gmail.com",
    )

    port = int(
        settings.get(
            "imap_port",
            993,
        )
    )

    user = settings.get("email")
    password = settings.get("password")

    if not user or not password:
        logger.error(
            "Faltan usuario o contraseña IMAP."
        )
        return []

    extensiones = _extensiones_permitidas()

    downloaded = []

    mail = None

    try:

        mail = imaplib.IMAP4_SSL(
            host,
            port,
            timeout=30,
        )

        mail.login(
            user,
            password,
        )

        status, _ = mail.select(
            "INBOX"
        )

        if status != "OK":
            raise RuntimeError(
                "No se pudo abrir INBOX."
            )

        status, messages = mail.search(
            None,
            "UNSEEN",
        )

        if status != "OK":
            logger.warning(
                "No se pudieron consultar correos."
            )
            return []

        message_ids = messages[0].split()

        for msg_id in message_ids:

            try:

                status, msg_data = mail.fetch(
                    msg_id,
                    "(RFC822)",
                )

                if status != "OK":
                    continue

                raw_message = None

                for item in msg_data:
                    if (
                        isinstance(item, tuple)
                        and len(item) > 1
                    ):
                        raw_message = item[1]
                        break

                if not raw_message:
                    continue

                msg = email.message_from_bytes(
                    raw_message
                )

                for part in msg.walk():

                    if part.get_content_maintype() == "multipart":
                        continue

                    disposition = (
                        part.get(
                            "Content-Disposition"
                        )
                        or ""
                    ).lower()

                    if "attachment" not in disposition:
                        continue

                    filename = part.get_filename()

                    if not filename:
                        continue

                    filename = _decodificar_filename(
                        filename
                    )

                    safe_filename = (
                        _nombre_seguro(
                            filename
                        )
                    )

                    extension = (
                        Path(
                            safe_filename
                        ).suffix.lower()
                    )

                    if extension not in extensiones:
                        continue

                    if not _coincide_filtro(
                        safe_filename
                    ):
                        continue

                    payload = part.get_payload(
                        decode=True
                    )

                    if not payload:
                        continue

                    timestamp = datetime.now().strftime(
                        "%Y%m%d_%H%M%S_%f"
                    )

                    output_name = (
                        f"{timestamp}_"
                        f"{safe_filename}"
                    )

                    filepath = (
                        UPLOAD_DIR
                        / output_name
                    )

                    filepath.write_bytes(
                        payload
                    )

                    downloaded.append(
                        str(filepath)
                    )

                    logger.info(
                        "Adjunto descargado: %s",
                        filepath,
                    )

                # Marcar como leído únicamente después
                # de procesar correctamente el mensaje.
                mail.store(
                    msg_id,
                    "+FLAGS",
                    "\\Seen",
                )

            except Exception as exc:

                logger.exception(
                    "Error procesando mensaje %s: %s",
                    msg_id,
                    exc,
                )

        return downloaded

    except Exception as exc:

        logger.exception(
            "Error IMAP: %s",
            exc,
        )

        return []

    finally:

        if mail:

            try:
                mail.close()
            except Exception:
                pass

            try:
                mail.logout()
            except Exception:
                pass
