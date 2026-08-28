"""
CasosSeguimiento v2.1
Modelo de base de datos SQLite con SQLAlchemy.

Correcciones:
- Ruta absoluta basada en __file__
- Creación automática de data/
- Sesiones SQLAlchemy correctamente gestionadas
- SQLite configurado para uso local con Streamlit
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from paths import DATABASE_FILE, database_url


Base = declarative_base()


# ============================================================
# ENGINE
# ============================================================

ENGINE = create_engine(
    database_url(),
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=ENGINE,
    autoflush=False,
    autocommit=False,
)


# ============================================================
# MODELOS
# ============================================================

class Caso(Base):
    __tablename__ = "casos"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    numero_caso = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    fecha_ingreso = Column(
        Date,
        nullable=False,
    )

    fecha_validacion = Column(
        Date,
        nullable=True,
    )

    estado = Column(
        String(100),
        nullable=False,
        default="PENDIENTE",
    )

    profesional = Column(
        String(255),
        nullable=False,
    )

    # Campos base opcionales
    sede = Column(String(255))
    seccion = Column(String(255))
    estudios = Column(String(255))
    organo = Column(String(255))

    # Campos parametrizables
    campos_extra = Column(
        JSON,
        default=dict,
    )

    fecha_registro_db = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    fecha_ultima_actualizacion = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    alerta_preventiva_enviada = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    alerta_vencido_enviada = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_casos_profesional",
            "profesional",
        ),
        Index(
            "ix_casos_estado",
            "estado",
        ),
        Index(
            "ix_casos_fecha_ingreso",
            "fecha_ingreso",
        ),
    )


class LogAlerta(Base):
    __tablename__ = "log_alertas"

    id = Column(
        Integer,
        primary_key=True,
    )

    caso_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    tipo_alerta = Column(
        String(50),
        nullable=False,
        index=True,
    )

    fecha_envio = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    destinatario = Column(
        String(255),
        nullable=False,
    )

    contenido = Column(
        Text,
        nullable=True,
    )


class LogProcesamiento(Base):
    __tablename__ = "log_procesamiento"

    id = Column(
        Integer,
        primary_key=True,
    )

    archivo = Column(
        String(1000),
        nullable=False,
    )

    fecha_proceso = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    insertados = Column(
        Integer,
        default=0,
        nullable=False,
    )

    actualizados = Column(
        Integer,
        default=0,
        nullable=False,
    )

    errores = Column(
        Integer,
        default=0,
        nullable=False,
    )

    detalle = Column(
        Text,
        nullable=True,
    )


# ============================================================
# INICIALIZACIÓN
# ============================================================

def init_db() -> None:
    """
    Crea las tablas si no existen.
    No elimina datos existentes.
    """
    Base.metadata.create_all(bind=ENGINE)


# Mantener el comportamiento original:
# al importar database.py, garantizar las tablas.
init_db()


# ============================================================
# SESIONES
# ============================================================

def get_db():
    """
    Devuelve una sesión SQLAlchemy abierta.

    El llamador es responsable de cerrarla:

        db = get_db()
        try:
            ...
        finally:
            db.close()
    """
    return SessionLocal()


def database_info() -> dict:
    """Información útil para diagnóstico."""
    return {
        "database_file": str(DATABASE_FILE),
        "database_exists": DATABASE_FILE.exists(),
    }
