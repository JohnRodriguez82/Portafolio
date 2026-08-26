from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import zlib

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

    def generar_descripcion_automatica(self, obligacion):
        import re
        import zlib

        anuncio = self.anuncio_usuario.strip()
        visual = (self.descripcion_visual_ia or "").strip()
        anuncio_limpio, visual_limpio = self._extraer_contenido_funcional(anuncio, visual)

        if not anuncio_limpio:
            anuncio_limpio = "Actividad contractual realizada durante el periodo reportado."

        oraciones = []

        # Oracion 1: accion principal (el anuncio del usuario, que YA es una oracion completa)
        if not anuncio_limpio.endswith(('.', '!', '?')):
            anuncio_limpio += '.'
        oraciones.append(anuncio_limpio)

        # Oracion 2: enriquecimiento con lo que vio la IA (si existe y es diferente)
        if visual_limpio:
            if not visual_limpio.endswith(('.', '!', '?')):
                visual_limpio += '.'
            # Conectores fluidos; el hash garantiza variedad pero determinismo
            conectores = [
                "Asimismo, se evidencia que {}",
                "De igual manera, {}",
                "En consecuencia, {}",
                "Adicionalmente, {}",
                "De manera complementaria, {}",
            ]
            idx = zlib.crc32(visual_limpio.encode('utf-8')) % len(conectores)
            # Adaptar la visual al conector (primera letra minuscula porque el conector ya inicia la oracion)
            visual_adaptada = visual_limpio[0].lower() + visual_limpio[1:] if visual_limpio else ''
            oracion2 = conectores[idx].format(visual_adaptada)
            oracion2 = oracion2.replace('..', '.').replace('. .', '.').strip()
            oraciones.append(oracion2)

        # Oracion 3: cierre contractual (contexto de la obligacion)
        cierres = [
            "Esta accion contribuye al cumplimiento de la obligacion contractual y fortalece el avance del objeto del contrato.",
            "El desarrollo de esta tarea responde a los compromisos establecidos en el contrato y aporta al logro de los resultados esperados.",
            "Esta labor se desarrollo conforme a lo planeado y dentro de los terminos pactados, garantizando la continuidad operativa del proyecto.",
            "La actividad fue ejecutada de manera oportuna y contribuye al seguimiento de los indicadores de gestion definidos.",
            "Dicha accion representa un avance significativo en el cumplimiento de los compromisos contractuales y aporta al cumplimiento de las metas establecidas.",
        ]
        idx = zlib.crc32((anuncio_limpio + obligacion.descripcion).encode('utf-8')) % len(cierres)
        oraciones.append(cierres[idx])

        # Unir y capitalizar correctamente despues de cada punto
        parrafo = ' '.join(oraciones)
        def _cap(match):
            return match.group(1) + match.group(2).upper()
        parrafo = re.sub(r'(^|[.!?]\s+)([a-záéíóúñ])', _cap, parrafo)

        return parrafo

    def __repr__(self):
        return f'<Evidencia {self.numero_actividad}>'
