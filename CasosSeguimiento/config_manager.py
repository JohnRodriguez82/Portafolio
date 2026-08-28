"""
CasosSeguimiento v2.1
Gestión segura de configuración encriptada.

Las credenciales IMAP/SMTP se almacenan cifradas mediante Fernet.
"""

import json
import os
import tempfile
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from paths import CONFIG_FILE, KEY_FILE, ensure_directories


# ============================================================
# CAMPOS POR DEFECTO
# ============================================================

def _campos_default():
    """Campos por defecto del archivo de entrada."""

    return [
        {
            "id": "numero_caso",
            "nombre": "Número de caso",
            "tipo": "texto",
            "obligatorio": True,
            "sinonimos": (
                "numero de caso,número de caso,caso,"
                "no. caso,no caso,id caso,numero_caso"
            ),
            "activo": True,
        },
        {
            "id": "sede",
            "nombre": "Sede",
            "tipo": "texto",
            "obligatorio": False,
            "sinonimos": "sede,ubicación,ubicacion,lugar",
            "activo": True,
        },
        {
            "id": "seccion",
            "nombre": "Sección",
            "tipo": "texto",
            "obligatorio": False,
            "sinonimos": (
                "sección,seccion,area,área,departamento"
            ),
            "activo": True,
        },
        {
            "id": "estudios",
            "nombre": "Estudios",
            "tipo": "texto",
            "obligatorio": False,
            "sinonimos": (
                "estudios,tipo estudio,tipo de estudio,examen"
            ),
            "activo": True,
        },
        {
            "id": "organo",
            "nombre": "Órgano",
            "tipo": "texto",
            "obligatorio": False,
            "sinonimos": (
                "órgano,organo,organos,órganos"
            ),
            "activo": True,
        },
        {
            "id": "fecha_ingreso",
            "nombre": "Fecha de ingreso",
            "tipo": "fecha",
            "obligatorio": True,
            "sinonimos": (
                "fecha de ingreso,fecha ingreso,ingreso,"
                "fecha recepcion,fecha recepción,fecha de recepción"
            ),
            "activo": True,
        },
        {
            "id": "fecha_validacion",
            "nombre": "Fecha de validación",
            "tipo": "fecha",
            "obligatorio": False,
            "sinonimos": (
                "fecha de validación,fecha validacion,"
                "validación,validacion,fecha resolucion,"
                "fecha resolución,fecha cierre"
            ),
            "activo": True,
        },
        {
            "id": "estado",
            "nombre": "Estado",
            "tipo": "texto",
            "obligatorio": False,
            "sinonimos": (
                "estado,status,situacion,situación"
            ),
            "activo": True,
        },
        {
            "id": "profesional",
            "nombre": "Profesional",
            "tipo": "texto",
            "obligatorio": True,
            "sinonimos": (
                "nombre del profesional,profesional,"
                "responsable,encargado,medico,médico"
            ),
            "activo": True,
        },
    ]


# ============================================================
# CLAVE
# ============================================================

def _get_or_create_key() -> bytes:
    ensure_directories()

    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    key = Fernet.generate_key()

    # Escritura de la clave
    KEY_FILE.write_bytes(key)

    # Intento de permisos restrictivos en sistemas que los soportan
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass

    return key


# ============================================================
# GUARDAR
# ============================================================

def save_config(data: dict) -> None:
    """
    Guarda la configuración encriptada.

    Se utiliza un archivo temporal para evitar dejar una
    configuración parcialmente escrita si el proceso falla.
    """

    ensure_directories()

    key = _get_or_create_key()
    fernet = Fernet(key)

    json_bytes = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    encrypted = fernet.encrypt(json_bytes)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(CONFIG_FILE.parent),
            prefix="config_",
            suffix=".tmp",
        ) as tmp:
            tmp.write(encrypted)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = tmp.name

        os.replace(temp_path, CONFIG_FILE)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ============================================================
# CARGAR
# ============================================================

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}

    key = _get_or_create_key()
    fernet = Fernet(key)

    try:
        encrypted = CONFIG_FILE.read_bytes()
        json_bytes = fernet.decrypt(encrypted)
        return json.loads(
            json_bytes.decode("utf-8")
        )

    except InvalidToken as exc:
        raise RuntimeError(
            "No se pudo desencriptar la configuración. "
            "Verifica que data/.secret.key corresponda a data/config.enc."
        ) from exc

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "El archivo de configuración no contiene JSON válido."
        ) from exc


def config_exists() -> bool:
    return CONFIG_FILE.exists()


# ============================================================
# GETTERS
# ============================================================

def get_email_settings() -> dict:
    cfg = load_config()
    return cfg.get("email", {})


def get_profesionales() -> list:
    cfg = load_config()
    return cfg.get("profesionales", [])


def get_encargado() -> dict:
    cfg = load_config()
    return cfg.get("encargado", {})


def get_campos_excel() -> list:
    cfg = load_config()
    return cfg.get(
        "campos_excel",
        _campos_default(),
    )


def get_tipo_archivo() -> str:
    cfg = load_config()
    tipo = cfg.get("tipo_archivo", "excel")

    if tipo not in {"excel", "csv"}:
        return "excel"

    return tipo


def get_filtro_nombre_adjunto() -> str:
    cfg = load_config()
    return str(
        cfg.get("filtro_nombre_adjunto", "")
    ).strip()
