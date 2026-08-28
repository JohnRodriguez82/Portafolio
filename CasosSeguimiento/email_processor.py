"""
Lectura de correos vía IMAP y descarga de adjuntos según configuración.
"""
import imaplib
import email
from email.header import decode_header
import os
import re
from datetime import datetime
from config_manager import get_email_settings, get_tipo_archivo, get_filtro_nombre_adjunto

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _extensiones_permitidas():
    tipo = get_tipo_archivo()
    if tipo == "csv":
        return [".csv"]
    return [".xlsx", ".xls"]


def _coincide_filtro(filename: str) -> bool:
    filtro = get_filtro_nombre_adjunto().strip()
    if not filtro:
        return True
    # Soporta comodín * y regex simple
    patron = filtro.replace(".", r"\.").replace("*", ".*")
    return bool(re.search(patron, filename, re.IGNORECASE))


def check_emails_and_download_excel():
    settings = get_email_settings()
    if not settings:
        return []

    host = settings.get("imap_server", "imap.gmail.com")
    port = settings.get("imap_port", 993)
    user = settings.get("email")
    password = settings.get("password")

    extensiones = _extensiones_permitidas()
    downloaded = []
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            return []

        for msg_id in messages[0].split():
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get("Content-Disposition") is None:
                    continue

                filename = part.get_filename()
                if not filename:
                    continue

                ext_ok = any(filename.lower().endswith(ext) for ext in extensiones)
                nombre_ok = _coincide_filtro(filename)

                if ext_ok and nombre_ok:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = f"{ts}_{filename}"
                    filepath = os.path.join(UPLOAD_DIR, safe_name)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    downloaded.append(filepath)

            mail.store(msg_id, "+FLAGS", "\\Seen")

    except Exception as e:
        print(f"[ERROR IMAP] {e}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    return downloaded
