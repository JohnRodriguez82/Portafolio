"""
Modelo de base de datos SQLite con SQLAlchemy.
Incluye columna JSON para campos personalizados parametrizables.
"""
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()
ENGINE = create_engine("sqlite:///data/casos.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)


class Caso(Base):
    __tablename__ = "casos"

    id = Column(Integer, primary_key=True, index=True)
    numero_caso = Column(String, unique=True, nullable=False, index=True)
    fecha_ingreso = Column(Date, nullable=False)
    fecha_validacion = Column(Date, nullable=True)
    estado = Column(String, default="PENDIENTE")
    profesional = Column(String, nullable=False)

    # Campos base opcionales (para búsquedas rápidas)
    sede = Column(String)
    seccion = Column(String)
    estudios = Column(String)
    organo = Column(String)

    # Campos personalizados adicionales (JSON flexible)
    campos_extra = Column(JSON, default=dict)

    fecha_registro_db = Column(DateTime, default=datetime.now)
    fecha_ultima_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    alerta_preventiva_enviada = Column(Boolean, default=False)
    alerta_vencido_enviada = Column(Boolean, default=False)


class LogAlerta(Base):
    __tablename__ = "log_alertas"
    id = Column(Integer, primary_key=True)
    caso_id = Column(Integer)
    tipo_alerta = Column(String)
    fecha_envio = Column(DateTime, default=datetime.now)
    destinatario = Column(String)
    contenido = Column(Text)


class LogProcesamiento(Base):
    __tablename__ = "log_procesamiento"
    id = Column(Integer, primary_key=True)
    archivo = Column(String)
    fecha_proceso = Column(DateTime, default=datetime.now)
    insertados = Column(Integer, default=0)
    actualizados = Column(Integer, default=0)
    errores = Column(Integer, default=0)
    detalle = Column(Text)


Base.metadata.create_all(bind=ENGINE)


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
