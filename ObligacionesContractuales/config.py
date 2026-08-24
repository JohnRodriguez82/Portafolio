import os
from pathlib import Path


class Config:
    """Configuración base."""

    BASE_DIR = Path(__file__).resolve().parent

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-cambiar-en-produccion')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "reportes.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    PDF_FOLDER = os.environ.get('PDF_FOLDER', str(BASE_DIR / 'pdfs'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')


class DevelopmentConfig(Config):
    """Configuración de desarrollo."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración de producción."""
    DEBUG = False


class TestingConfig(Config):
    """Configuración de testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
