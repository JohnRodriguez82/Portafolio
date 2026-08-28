"""
Gestión de configuración encriptada.
El mismo correo se usa para IMAP (recibir archivos) y SMTP (enviar alertas).
"""
import json
import os
from cryptography.fernet import Fernet

CONFIG_FILE = "data/config.enc"
KEY_FILE = "data/.secret.key"


def _get_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    os.makedirs("data", exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def save_config(data: dict):
    key = _get_or_create_key()
    fernet = Fernet(key)
    json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
    encrypted = fernet.encrypt(json_bytes)
    with open(CONFIG_FILE, "wb") as f:
        f.write(encrypted)


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    key = _get_or_create_key()
    fernet = Fernet(key)
    with open(CONFIG_FILE, "rb") as f:
        encrypted = f.read()
    json_bytes = fernet.decrypt(encrypted)
    return json.loads(json_bytes.decode("utf-8"))


def config_exists() -> bool:
    return os.path.exists(CONFIG_FILE)


def get_email_settings():
    cfg = load_config()
    return cfg.get("email", {})


def get_profesionales():
    cfg = load_config()
    return cfg.get("profesionales", [])


def get_encargado():
    cfg = load_config()
    return cfg.get("encargado", {})


def get_campos_excel():
    """Retorna la lista de campos parametrizados del archivo."""
    cfg = load_config()
    return cfg.get("campos_excel", _campos_default())


def get_tipo_archivo():
    cfg = load_config()
    return cfg.get("tipo_archivo", "excel")  # "excel" o "csv"


def get_filtro_nombre_adjunto():
    cfg = load_config()
    return cfg.get("filtro_nombre_adjunto", "")  # vacío = cualquier nombre


def _campos_default():
    """Campos por defecto si no hay configuración personalizada."""
    return [
        {"id": "numero_caso", "nombre": "Número de caso", "tipo": "texto", "obligatorio": True, "sinonimos": "numero de caso,número de caso,caso,no. caso,id caso"},
        {"id": "sede", "nombre": "Sede", "tipo": "texto", "obligatorio": False, "sinonimos": "sede,ubicación,ubicacion,lugar"},
        {"id": "seccion", "nombre": "Sección", "tipo": "texto", "obligatorio": False, "sinonimos": "sección,seccion,area,área,departamento"},
        {"id": "estudios", "nombre": "Estudios", "tipo": "texto", "obligatorio": False, "sinonimos": "estudios,tipo estudio,tipo de estudio,examen"},
        {"id": "organo", "nombre": "Órgano", "tipo": "texto", "obligatorio": False, "sinonimos": "órgano,organo,organos,órganos"},
        {"id": "fecha_ingreso", "nombre": "Fecha de ingreso", "tipo": "fecha", "obligatorio": True, "sinonimos": "fecha de ingreso,fecha ingreso,ingreso,fecha recepcion,fecha recepción"},
        {"id": "fecha_validacion", "nombre": "Fecha de validación", "tipo": "fecha", "obligatorio": False, "sinonimos": "fecha de validación,fecha validacion,validación,validacion,fecha resolucion,fecha resolución,fecha cierre"},
        {"id": "estado", "nombre": "Estado", "tipo": "texto", "obligatorio": False, "sinonimos": "estado,status,situacion,situación"},
        {"id": "profesional", "nombre": "Profesional", "tipo": "texto", "obligatorio": True, "sinonimos": "nombre del profesional,profesional,responsable,encargado,medico,médico"},
    ]
