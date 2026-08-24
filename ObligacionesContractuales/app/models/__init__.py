"""
Modelos de la aplicación.

Todos los modelos SQLAlchemy se importan desde aquí
para mantener compatibilidad con el código existente.
"""

from app.extensions import db

from .user import Usuario
from .config_system import ConfiguracionSistema
from .contract import Contrato
from .obligation import Obligacion
from .report import ReporteMensual
from .evidence import Evidencia

__all__ = [
    'db',
    'Usuario',
    'ConfiguracionSistema',
    'Contrato',
    'Obligacion',
    'ReporteMensual',
    'Evidencia',
]
