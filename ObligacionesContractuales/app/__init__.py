"""
Inicialización principal de la aplicación Flask.

Responsabilidades:
- Crear la aplicación Flask.
- Cargar la configuración.
- Inicializar SQLAlchemy.
- Inicializar Flask-Login.
- Inicializar OAuth.
- Configurar Google OAuth.
- Registrar el user_loader.
- Registrar los Blueprints.
- Inicializar/migrar la base de datos.
- Registrar manejadores de errores.
"""

import os

from flask import (
    Flask
)

from flask_login import (
    LoginManager
)

from authlib.integrations.flask_client import (
    OAuth
)

from config import Config

from models import (
    db,
    Usuario
)


# ============================================================
# EXTENSIONES
# ============================================================

login_manager = LoginManager()

oauth = OAuth()


# ============================================================
# FACTORY DE LA APLICACIÓN
# ============================================================

def create_app():
    """
    Crea y configura la aplicación Flask.

    Retorna:
        Flask: instancia configurada de la aplicación.
    """

    # ========================================================
    # CREAR APLICACIÓN
    # ========================================================

    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    app.config.from_object(
        Config
    )

    # ========================================================
    # CONFIGURACIÓN DE CARPETAS
    # ========================================================

    app.config['UPLOAD_FOLDER'] = (
        Config.UPLOAD_FOLDER
    )

    app.config['PDF_FOLDER'] = (
        Config.PDF_FOLDER
    )

    app.config['MAX_CONTENT_LENGTH'] = (
        Config.MAX_CONTENT_LENGTH
    )

    # ========================================================
    # DATABASE
    # ========================================================

    db.init_app(
        app
    )

    # ========================================================
    # FLASK-LOGIN
    # ========================================================

    login_manager.init_app(
        app
    )

    login_manager.login_view = (
        'autenticacion.login'
    )

    login_manager.login_message = (
        'Por favor inicie sesion para acceder.'
    )

    login_manager.login_message_category = (
        'warning'
    )

    # ========================================================
    # USER LOADER
    # ========================================================

    @login_manager.user_loader
    def load_user(user_id):
        """
        Recupera el usuario almacenado en la sesión.
        """

        try:

            return Usuario.query.get(
                int(user_id)
            )

        except (
            ValueError,
            TypeError
        ):

            return None

    # ========================================================
    # OAUTH
    # ========================================================

    oauth.init_app(
        app
    )

    _configurar_google_oauth()

    # ========================================================
    # BLUEPRINTS
    # ========================================================

    _registrar_blueprints(
        app
    )

    # ========================================================
    # BASE DE DATOS
    # ========================================================

    _inicializar_base_datos(
        app
    )

    # ========================================================
    # MANEJADORES DE ERRORES
    # ========================================================

    _registrar_manejadores_errores(
        app
    )

    # ========================================================
    # RETORNAR APLICACIÓN
    # ========================================================

    return app


# ============================================================
# GOOGLE OAUTH
# ============================================================

def _configurar_google_oauth():
    """
    Registra el cliente OAuth de Google.

    Las credenciales se obtienen desde las variables
    de entorno:

        GOOGLE_CLIENT_ID
        GOOGLE_CLIENT_SECRET
    """

    google_client_id = os.environ.get(
        'GOOGLE_CLIENT_ID',
        ''
    ).strip()

    google_client_secret = os.environ.get(
        'GOOGLE_CLIENT_SECRET',
        ''
    ).strip()

    # ========================================================
    # VALIDAR CREDENCIALES
    # ========================================================

    if (
        not google_client_id
        or
        not google_client_secret
    ):

        print(
            '[ADVERTENCIA] '
            'Credenciales de Google OAuth no configuradas.'
        )

        print(
            '[ADVERTENCIA] '
            'El inicio de sesion con Google NO funcionara.'
        )

        print(
            '[ADVERTENCIA] '
            'Configure GOOGLE_CLIENT_ID y '
            'GOOGLE_CLIENT_SECRET en .env.'
        )

        return

    # ========================================================
    # REGISTRAR CLIENTE GOOGLE
    # ========================================================

    oauth.register(
        name='google',

        client_id=google_client_id,

        client_secret=google_client_secret,

        server_metadata_url=(
            'https://accounts.google.com/'
            '.well-known/openid-configuration'
        ),

        client_kwargs={
            'scope': 'openid email profile'
        }
    )


# ============================================================
# REGISTRO DE BLUEPRINTS
# ============================================================

def _registrar_blueprints(app):
    """
    Importa y registra todos los Blueprints.
    """

    # ========================================================
    # AUTENTICACIÓN
    # ========================================================

    from app.blueprints.autenticacion import (
        autenticacion_bp
    )

    # ========================================================
    # INICIO
    # ========================================================

    from app.blueprints.inicio import (
        inicio_bp
    )

    # ========================================================
    # CONTRATOS
    # ========================================================

    from app.blueprints.contratos import (
        contratos_bp
    )

    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    from app.blueprints.configuracion import (
        configuracion_bp
    )

    # ========================================================
    # REPORTES
    # ========================================================

    from app.blueprints.reportes import (
        reportes_bp
    )

    # ========================================================
    # CARGAS
    # ========================================================

    from app.blueprints.cargas import (
        cargas_bp
    )

    # ========================================================
    # REGISTRAR BLUEPRINTS
    # ========================================================

    app.register_blueprint(
        autenticacion_bp
    )

    app.register_blueprint(
        inicio_bp
    )

    app.register_blueprint(
        contratos_bp
    )

    app.register_blueprint(
        configuracion_bp
    )

    app.register_blueprint(
        reportes_bp
    )

    app.register_blueprint(
        cargas_bp
    )


# ============================================================
# INICIALIZAR BASE DE DATOS
# ============================================================

def _inicializar_base_datos(app):
    """
    Inicializa las tablas y conserva las migraciones
    básicas utilizadas por la aplicación existente.

    Esta función permite mantener compatibilidad con la
    base de datos SQLite existente durante la transición
    a la nueva estructura de Blueprints.
    """

    with app.app_context():

        # ====================================================
        # INSPECTOR
        # ====================================================

        inspector = db.inspect(
            db.engine
        )

        tables = (
            inspector.get_table_names()
        )

        # ====================================================
        # CREAR TABLAS
        # ====================================================

        if 'usuario' not in tables:

            db.create_all()

            return

        # ====================================================
        # TABLA CONTRATO
        # ====================================================

        if 'contrato' in tables:

            columns = [
                column['name']
                for column in
                inspector.get_columns(
                    'contrato'
                )
            ]

            with db.engine.connect() as conn:

                # ------------------------------------------------
                # user_id
                # ------------------------------------------------

                if 'user_id' not in columns:

                    conn.execute(
                        db.text(
                            """
                            ALTER TABLE contrato
                            ADD COLUMN user_id INTEGER
                            """
                        )
                    )

                    conn.commit()

                # ------------------------------------------------
                # contratista
                # ------------------------------------------------

                if 'contratista' not in columns:

                    conn.execute(
                        db.text(
                            """
                            ALTER TABLE contrato
                            ADD COLUMN contratista
                            VARCHAR(200)
                            """
                        )
                    )

                    conn.commit()

                # ------------------------------------------------
                # numero_contrato
                # ------------------------------------------------

                if 'numero_contrato' not in columns:

                    conn.execute(
                        db.text(
                            """
                            ALTER TABLE contrato
                            ADD COLUMN numero_contrato
                            VARCHAR(100)
                            """
                        )
                    )

                    conn.commit()

                # ------------------------------------------------
                # etapa
                # ------------------------------------------------

                if 'etapa' not in columns:

                    conn.execute(
                        db.text(
                            """
                            ALTER TABLE contrato
                            ADD COLUMN etapa
                            VARCHAR(50)
                            DEFAULT 'Reporte en Proceso'
                            """
                        )
                    )

                    conn.execute(
                        db.text(
                            """
                            UPDATE contrato
                            SET etapa = 'Reporte en Proceso'
                            WHERE etapa IS NULL
                            """
                        )
                    )

                    conn.commit()

        # ====================================================
        # TABLA USUARIO
        # ====================================================

        if 'usuario' in tables:

            usuario_columns = [
                column['name']
                for column in
                inspector.get_columns(
                    'usuario'
                )
            ]

            # ------------------------------------------------
            # ELIMINAR ETAPA DE USUARIO
            # ------------------------------------------------

            if 'etapa' in usuario_columns:

                with db.engine.connect() as conn:

                    try:

                        conn.execute(
                            db.text(
                                """
                                ALTER TABLE usuario
                                DROP COLUMN etapa
                                """
                            )
                        )

                        conn.commit()

                    except Exception as exc:

                        print(
                            '[ADVERTENCIA] '
                            'No se pudo eliminar la columna '
                            'etapa de usuario: '
                            f'{exc}'
                        )


# ============================================================
# MANEJADORES DE ERRORES
# ============================================================

def _registrar_manejadores_errores(app):
    """
    Registra manejadores básicos de errores de la aplicación.
    """

    # ========================================================
    # ARCHIVO DEMASIADO GRANDE
    # ========================================================

    @app.errorhandler(413)
    def archivo_demasiado_grande(error):

        from flask import (
            flash,
            redirect,
            url_for
        )

        flash(
            (
                'El archivo supera el tamaño máximo '
                'permitido.'
            ),
            'danger'
        )

        return redirect(
            url_for(
                'inicio.index'
            )
        )
