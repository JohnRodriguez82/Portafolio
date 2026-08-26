from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import zlib
import re

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    auth_google = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    es_admin = db.Column(db.Boolean, default=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    contratos = db.relationship('Contrato', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.email}>'


class ConfiguracionSistema(db.Model):
    __tablename__ = 'configuracion_sistema'
    id = db.Column(db.Integer, primary_key=True)
    gemini_api_key_encriptada = db.Column(db.Text, nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ConfiguracionSistema {self.id}>'


class Contrato(db.Model):
    __tablename__ = 'contrato'
    id = db.Column(db.Integer, primary_key=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    contratista = db.Column(db.String(200), nullable=True)
    numero_contrato = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    etapa = db.Column(db.String(50), default='Reporte en Proceso')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    obligaciones = db.relationship('Obligacion', backref='contrato', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Contrato {self.numero_contrato}>'


class Obligacion(db.Model):
    __tablename__ = 'obligacion'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    reportes = db.relationship('ReporteMensual', backref='obligacion', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Obligacion {self.numero}>'


class ReporteMensual(db.Model):
    __tablename__ = 'reporte_mensual'
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    fecha_inicio_reporte = db.Column(db.Date, nullable=False)
    fecha_fin_reporte = db.Column(db.Date, nullable=False)
    cerrado = db.Column(db.Boolean, default=False, nullable=False)
    obligacion_id = db.Column(db.Integer, db.ForeignKey('obligacion.id'), nullable=False)
    evidencias = db.relationship('Evidencia', backref='reporte', lazy=True, cascade='all, delete-orphan')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nombre_mes(self):
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[self.mes]

    def __repr__(self):
        return f'<ReporteMensual {self.mes}-{self.anio}>'


class Evidencia(db.Model):
    __tablename__ = 'evidencia'
    id = db.Column(db.Integer, primary_key=True)
    numero_actividad = db.Column(db.Integer, nullable=False)
    imagen_path = db.Column(db.String(500), nullable=False)
    anuncio_usuario = db.Column(db.Text, nullable=False)
    descripcion_visual_ia = db.Column(db.Text, nullable=True)
    descripcion_actividad = db.Column(db.Text, nullable=False)
    fecha_actividad = db.Column(db.Date, nullable=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reporte_mensual.id'), nullable=False)
    fecha_carga = db.Column(db.DateTime, default=datetime.utcnow)

    def _extraer_contenido_funcional(self, anuncio, visual):
        from vision_analyzer import _limpiar_texto
        anuncio_limpio = _limpiar_texto(anuncio)
        visual_limpio = _limpiar_texto(visual) if visual else ''
        # Si la descripcion visual ya esta contenida en el anuncio, no duplicar
        if visual_limpio and visual_limpio.lower() in anuncio_limpio.lower():
            visual_limpio = ''
        return anuncio_limpio, visual_limpio

    def generar_descripcion_automatica(self, obligacion, visual=None):
    anuncio = (self.anuncio_usuario or "").strip()
    visual = (visual or "").strip()

    contenido = self._extraer_contenido_funcional(
        anuncio,
        visual
    )

    if not contenido:
        contenido = anuncio or "la actividad contractual prevista"

    templates = [
        (
            f"Durante el periodo reportado se adelantó {contenido}. "
            f"Esta actividad se desarrolló en el marco de la obligación "
            f"contractual y contribuye al avance de las actividades "
            f"previstas para el cumplimiento del objeto contractual."
        ),
        (
            f"En el marco de la obligación contractual, se llevó a cabo "
            f"{contenido}. La actividad permitió avanzar en la "
            f"estructuración, desarrollo y consolidación de los componentes "
            f"requeridos, de acuerdo con las necesidades identificadas "
            f"durante el periodo reportado."
        ),
        (
            f"Como parte de las actividades programadas, se realizó "
            f"{contenido}. Esta gestión permitió fortalecer el desarrollo "
            f"de los componentes asociados a la obligación y dar "
            f"continuidad a las acciones técnicas y funcionales previstas "
            f"para el periodo."
        ),
        (
            f"Durante el periodo se desarrolló {contenido}. La labor "
            f"realizada representa un avance en la ejecución de las "
            f"actividades contractuales, contribuyendo a la implementación "
            f"y consolidación de los resultados previstos."
        ),
    ]

    return random.choice(templates)


    def __repr__(self):
        return f'<Evidencia {self.numero_actividad}>'
