"""
CasosSeguimiento v2.1
Gestión centralizada de rutas del proyecto.

Todas las rutas dependen de la ubicación real de este archivo,
no del directorio desde el cual se ejecuta Streamlit.
"""

from pathlib import Path


# Directorio raíz de CasosSeguimiento
BASE_DIR = Path(__file__).resolve().parent

# Datos persistentes
DATA_DIR = BASE_DIR / "data"

# Archivos de configuración
DATABASE_FILE = DATA_DIR / "casos.db"
CONFIG_FILE = DATA_DIR / "config.enc"
KEY_FILE = DATA_DIR / ".secret.key"

# Archivos recibidos/subidos
UPLOAD_DIR = DATA_DIR / "uploads"

# Crear directorios automáticamente
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_directories() -> None:
    """Garantiza que las carpetas necesarias existan."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def database_url() -> str:
    """
    Devuelve la URL SQLite compatible con Windows/Linux/macOS.

    Ejemplo Windows:
    sqlite:///D:/Users/Asus/.../CasosSeguimiento/data/casos.db
    """
    ensure_directories()
    return f"sqlite:///{DATABASE_FILE.as_posix()}"