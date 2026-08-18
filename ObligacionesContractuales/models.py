from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import random

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
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    gemini_api_key = db.Column(db.String(500), nullable=True)
    contratos = db.relationship('Contrato', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.email}>'


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
        return f'<Contrato {self.fecha_inicio} - {self.fecha_fin}>'


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
    obligacion_id = db.Column(db.Integer, db.ForeignKey('obligacion.id'), nullable=False)
    evidencias = db.relationship('Evidencia', backref='reporte', lazy=True, cascade='all, delete-orphan')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nombre_mes(self):
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[self.mes]

    def __repr__(self):
        return f'<Reporte {self.nombre_mes} {self.anio}>'


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
        import re
        texto = anuncio
        if visual and visual.lower() not in anuncio.lower():
            visual_limpio = self._limpiar_referencias_visuales(visual)
            if visual_limpio:
                texto = f"{anuncio}. {visual_limpio}"
        return self._limpiar_referencias_visuales(texto)

    def _limpiar_referencias_visuales(self, texto):
        import re
        frases_a_eliminar = [
            r'[Ee]n la imagen[^.]*\.',
            r'[Ss]e observa[^.]*\.',
            r'[Ss]e visualiza[^.]*\.',
            r'[Ll]a imagen muestra[^.]*\.',
            r'[Cc]omo se ve en[^.]*\.',
            r'[Pp]antallazo de[^.]*\.',
            r'[Ff]otografia de[^.]*\.',
            r'[Cc]aptura de[^.]*\.',
            r'[Ss]creenshot de[^.]*\.',
            r'[Dd]ocumento que muestra[^.]*\.',
            r'[Aa]rchivo que contiene[^.]*\.',
            r'[Ee]videncia fotografica[^.]*\.',
            r'[Ss]oporte grafico[^.]*\.',
            r'[Ll]a evidencia adjunta[^.]*\.',
            r'[Ss]e adjunta[^.]*\.',
            r'[Ll]a imagen anexa[^.]*\.',
            r'[Ee]l soporte fotografico[^.]*\.',
            r'[Ss]e presenta la correspondiente evidencia[^.]*\.',
            r'[Ee]sta accion se documenta con la evidencia[^.]*\.',
            r'[Ll]a presente evidencia certifica[^.]*\.',
            r'[Ss]e adjunta evidencia documental[^.]*\.',
            r'[Ee]videnciado en la imagen[^,]*,\s*',
            r'[Dd]onde se observa[^.]*\.',
            r'[Ss]e observa[^.]*\.',
            r'[Ll]a imagen muestra[^.]*\.',
            r'[Cc]omo se ve en[^.]*\.',
            r'[Pp]antallazo de[^,]*,\s*',
            r'[Ff]otografia de[^,]*,\s*',
        ]
        resultado = texto
        for patron in frases_a_eliminar:
            resultado = re.sub(patron, ' ', resultado)
        resultado = re.sub(r'\s+', ' ', resultado)
        resultado = re.sub(r'\.\.', '.', resultado)
        resultado = re.sub(r'\.\s*\.', '.', resultado)
        resultado = resultado.strip()
        if resultado and not resultado.endswith('.'):
            resultado += '.'
        return resultado

    def generar_descripcion_automatica(self, obligacion):
        anuncio = self.anuncio_usuario.strip()
        visual = (self.descripcion_visual_ia or "").strip()
        contenido = self._extraer_contenido_funcional(anuncio, visual)

        templates = [
            f"Durante el periodo reportado se adelanto {contenido} Esta accion contribuye al cumplimiento de la obligacion contractual y fortalece el avance del objeto del contrato.",
            f"Se ejecuto {contenido} como parte de las actividades programadas para el mes. El desarrollo de esta tarea responde a los compromisos establecidos en el contrato y aporta al logro de los resultados esperados.",
            f"Como parte del plan de trabajo contractual, se realizo {contenido} Esta labor se desarrollo conforme a lo planeado y dentro de los terminos pactados, garantizando la continuidad operativa del proyecto.",
            f"En el marco de la obligacion contractual, se llevo a cabo {contenido} La actividad fue desarrollada de manera oportuna y contribuye al seguimiento de los indicadores de gestion definidos.",
            f"Se efectuo {contenido} durante el periodo de reporte. Esta accion representa un avance significativo en el cumplimiento de los compromisos contractuales y aporta al cumplimiento de las metas establecidas.",
            f"Dentro del plan operativo del contrato, se desarrollo {contenido} La ejecucion de esta actividad se realizo en cumplimiento de las obligaciones pactadas y contribuye al cumplimiento de los objetivos del proyecto.",
            f"Se adelanto {contenido} como parte del seguimiento a las actividades contractuales. El resultado de esta labor se consolida dentro del marco de los entregables definidos y contribuye al cumplimiento mensual.",
            f"En cumplimiento de la obligacion contractual, se realizo {contenido} Esta actividad fue ejecutada durante el periodo reportado y se encuentra alineada con los objetivos y alcance definidos en el contrato.",
            f"Se gestiono y ejecuto {contenido} durante el mes reportado. Esta labor forma parte de las acciones contractuales planificadas y contribuye al cumplimiento de los entregables pactados.",
            f"Como parte del desarrollo de las actividades contractuales, se adelanto {contenido} Esta accion se ejecuto conforme a la programacion establecida y aporta al seguimiento de los compromisos del contrato."
        ]
        return random.choice(templates)

    def __repr__(self):
        return f'<Evidencia Act.{self.numero_actividad}>'
