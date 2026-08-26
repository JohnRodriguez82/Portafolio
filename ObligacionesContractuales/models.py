from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import zlib
import re

db = SQLAlchemy()


# ============================================================
# USUARIO
# ============================================================

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    nombre = db.Column(
        db.String(100),
        nullable=True
    )

    password_hash = db.Column(
        db.String(256),
        nullable=True
    )

    auth_google = db.Column(
        db.Boolean,
        default=False
    )

    google_id = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    avatar_url = db.Column(
        db.String(500),
        nullable=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    es_admin = db.Column(
        db.Boolean,
        default=False
    )

    fecha_registro = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    contratos = db.relationship(
        'Contrato',
        backref='usuario',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f'<Usuario {self.email}>'


# ============================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================

class ConfiguracionSistema(db.Model):
    __tablename__ = 'configuracion_sistema'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    gemini_api_key_encriptada = db.Column(
        db.Text,
        nullable=True
    )

    fecha_actualizacion = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f'<ConfiguracionSistema {self.id}>'


# ============================================================
# CONTRATO
# ============================================================

class Contrato(db.Model):
    __tablename__ = 'contrato'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    fecha_inicio = db.Column(
        db.Date,
        nullable=False
    )

    fecha_fin = db.Column(
        db.Date,
        nullable=False
    )

    contratista = db.Column(
        db.String(200),
        nullable=True
    )

    numero_contrato = db.Column(
        db.String(100),
        nullable=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    etapa = db.Column(
        db.String(50),
        default='Reporte en Proceso'
    )

    fecha_creacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('usuario.id'),
        nullable=True
    )

    obligaciones = db.relationship(
        'Obligacion',
        backref='contrato',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Contrato {self.numero_contrato}>'


# ============================================================
# OBLIGACIÓN
# ============================================================

class Obligacion(db.Model):
    __tablename__ = 'obligacion'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    numero = db.Column(
        db.Integer,
        nullable=False
    )

    descripcion = db.Column(
        db.Text,
        nullable=False
    )

    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey('contrato.id'),
        nullable=False
    )

    reportes = db.relationship(
        'ReporteMensual',
        backref='obligacion',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Obligacion {self.numero}>'


# ============================================================
# REPORTE MENSUAL
# ============================================================

class ReporteMensual(db.Model):
    __tablename__ = 'reporte_mensual'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mes = db.Column(
        db.Integer,
        nullable=False
    )

    anio = db.Column(
        db.Integer,
        nullable=False
    )

    fecha_inicio_reporte = db.Column(
        db.Date,
        nullable=False
    )

    fecha_fin_reporte = db.Column(
        db.Date,
        nullable=False
    )

    cerrado = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    obligacion_id = db.Column(
        db.Integer,
        db.ForeignKey('obligacion.id'),
        nullable=False
    )

    evidencias = db.relationship(
        'Evidencia',
        backref='reporte',
        lazy=True,
        cascade='all, delete-orphan'
    )

    fecha_creacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    @property
    def nombre_mes(self):

        meses = [
            '',
            'Enero',
            'Febrero',
            'Marzo',
            'Abril',
            'Mayo',
            'Junio',
            'Julio',
            'Agosto',
            'Septiembre',
            'Octubre',
            'Noviembre',
            'Diciembre'
        ]

        return meses[self.mes]

    def __repr__(self):
        return f'<ReporteMensual {self.mes}-{self.anio}>'


# ============================================================
# EVIDENCIA
# ============================================================

class Evidencia(db.Model):
    __tablename__ = 'evidencia'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    numero_actividad = db.Column(
        db.Integer,
        nullable=False
    )

    imagen_path = db.Column(
        db.String(500),
        nullable=False
    )

    # --------------------------------------------------------
    # Texto original suministrado por el usuario
    # --------------------------------------------------------

    anuncio_usuario = db.Column(
        db.Text,
        nullable=False
    )

    # --------------------------------------------------------
    # Texto generado directamente por Gemini al analizar
    # la evidencia visual.
    #
    # Este campo corresponde a:
    #
    # "IA vio:"
    # --------------------------------------------------------

    descripcion_visual_ia = db.Column(
        db.Text,
        nullable=True
    )

    # --------------------------------------------------------
    # Texto principal que aparece como:
    #
    # "Actividad realizada"
    #
    # Este texto se construye utilizando:
    #
    # anuncio + análisis IA + contexto contractual
    # --------------------------------------------------------

    descripcion_actividad = db.Column(
        db.Text,
        nullable=False
    )

    fecha_actividad = db.Column(
        db.Date,
        nullable=True
    )

    reporte_id = db.Column(
        db.Integer,
        db.ForeignKey('reporte_mensual.id'),
        nullable=False
    )

    fecha_carga = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ========================================================
    # LIMPIEZA DE TEXTO
    # ========================================================

    @staticmethod
    def _limpiar_texto_seguro(texto):

        if not texto:
            return ''

        try:
            from vision_analyzer import _limpiar_texto

            resultado = _limpiar_texto(
                str(texto)
            )

        except Exception:

            resultado = str(
                texto
            ).strip()

            resultado = re.sub(
                r'\s+',
                ' ',
                resultado
            )

        return resultado.strip()

    # ========================================================
    # EXTRAER CONTENIDO FUNCIONAL
    # ========================================================

    def _extraer_contenido_funcional(
        self,
        anuncio,
        visual
    ):
        """
        Obtiene por separado el anuncio y la descripción
        generada por IA.

        NO concatena directamente los textos porque ambos
        tienen funciones diferentes.
        """

        anuncio_limpio = (
            self._limpiar_texto_seguro(
                anuncio
            )
        )

        visual_limpio = (
            self._limpiar_texto_seguro(
                visual
            )
            if visual
            else ''
        )

        return (
            anuncio_limpio,
            visual_limpio
        )

    # ========================================================
    # GENERAR DESCRIPCIÓN DE ACTIVIDAD
    # ========================================================

    def generar_descripcion_automatica(
        self,
        obligacion,
        visual=None
    ):
        """
        Genera el texto principal de "Actividad realizada".

        IMPORTANTE:

        - anuncio_usuario:
          corresponde al contexto original reportado.

        - descripcion_visual_ia:
          corresponde a lo que Gemini interpretó de la
          evidencia.

        - descripcion_actividad:
          es una redacción profesional que integra ambos
          elementos y los relaciona con la obligación.

        No reemplaza "IA vio" por el texto principal.
        """

        anuncio = (
            self.anuncio_usuario
            or ''
        ).strip()

        visual = (
            visual
            or self.descripcion_visual_ia
            or ''
        ).strip()

        anuncio_limpio, visual_limpio = (
            self._extraer_contenido_funcional(
                anuncio,
                visual
            )
        )

        # ----------------------------------------------------
        # Si no existe ninguna información
        # ----------------------------------------------------

        if not anuncio_limpio and not visual_limpio:

            return (
                'Durante el periodo reportado se adelantaron '
                'actividades relacionadas con la obligación '
                'contractual, dando continuidad a las acciones '
                'previstas para su cumplimiento.'
            )

        # ----------------------------------------------------
        # Solo existe anuncio
        # ----------------------------------------------------

        if anuncio_limpio and not visual_limpio:

            return (
                f'Durante el periodo reportado, '
                f'{self._normalizar_inicio(anuncio_limpio)} '
                f'Esta actividad se desarrolló en el marco de '
                f'la obligación contractual y contribuye al '
                f'avance de las acciones previstas para el '
                f'cumplimiento del objeto contractual.'
            )

        # ----------------------------------------------------
        # Solo existe análisis IA
        # ----------------------------------------------------

        if not anuncio_limpio and visual_limpio:

            return (
                f'Durante el periodo reportado, '
                f'{self._normalizar_inicio(visual_limpio)} '
                f'La actividad se relaciona con el desarrollo '
                f'de las acciones técnicas y funcionales '
                f'previstas en el marco de la obligación '
                f'contractual.'
            )

        # ----------------------------------------------------
        # Existen ambos textos
        # ----------------------------------------------------

        anuncio_final = (
            self._normalizar_inicio(
                anuncio_limpio
            )
        )

        visual_final = (
            self._normalizar_inicio(
                visual_limpio
            )
        )

        # ----------------------------------------------------
        # Evitar repetir exactamente el mismo texto
        # ----------------------------------------------------

        if (
            anuncio_final.lower()
            == visual_final.lower()
        ):

            return (
                f'Durante el periodo reportado, '
                f'{anuncio_final} '
                f'Esta actividad permitió avanzar en la '
                f'implementación y consolidación de los '
                f'componentes asociados a la obligación '
                f'contractual, dando continuidad a las '
                f'acciones previstas para su cumplimiento.'
            )

        # ----------------------------------------------------
        # Construcción del párrafo enriquecido
        # ----------------------------------------------------

        return (
            f'Durante el periodo reportado, '
            f'{anuncio_final} '
            f'De manera complementaria, '
            f'{visual_final} '
            f'Estos avances contribuyen al desarrollo y '
            f'consolidación de las actividades previstas '
            f'en el marco de la obligación contractual, '
            f'fortaleciendo la implementación de los '
            f'componentes requeridos para el cumplimiento '
            f'de los compromisos establecidos.'
        )

    # ========================================================
    # NORMALIZAR INICIO DE FRASE
    # ========================================================

    @staticmethod
    def _normalizar_inicio(texto):

        if not texto:
            return ''

        texto = texto.strip()

        if not texto:
            return ''

        # Quitar punto final para poder continuar
        # construyendo el párrafo de forma natural.
        texto = texto.rstrip()

        if texto.endswith('.'):
            texto = texto[:-1]

        # La primera letra debe quedar en minúscula cuando
        # el texto se inserta después de una coma o conector.
        if texto:

            texto = (
                texto[0].lower()
                +
                texto[1:]
            )

        return texto + '.'

    # ========================================================
    # REPRESENTACIÓN
    # ========================================================

    def __repr__(self):
        return (
            f'<Evidencia '
            f'{self.numero_actividad}>'
        )
