"""
Inicialización principal de la aplicación Flask.
"""

import os
from pathlib import Path
from flask import Flask

from app.extensions import db, login_manager, oauth
from app.models import Usuario, ConfiguracionSistema


def create_app():
    """
    Crea y configura la aplicación Flask.
    """

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent / "static")
    )

    # Configuración
    app.config.from_object('config.Config')

    # Carpetas
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
    app.config['PDF_FOLDER'] = os.environ.get('PDF_FOLDER', 'pdfs')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # Extensiones
    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return Usuario.query.get(int(user_id))
        except (ValueError, TypeError):
            return None

    # OAuth
    _configurar_google_oauth()

    # Blueprints
    _registrar_blueprints(app)

    # Base de datos
    _inicializar_base_datos(app)

    # Manejadores de errores
    _registrar_manejadores_errores(app)

    return app


def _configurar_google_oauth():
    """Registra el cliente OAuth de Google."""

    google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

    if not google_client_id or not google_client_secret:
        print('[ADVERTENCIA] Credenciales de Google OAuth no configuradas.')
        return

    oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )


def _registrar_blueprints(app):
    """Importa y registra todos los Blueprints."""

    from app.blueprints.autenticacion import autenticacion_bp
    from app.blueprints.inicio import inicio_bp
    from app.blueprints.contratos import contratos_bp
    from app.blueprints.configuracion import configuracion_bp
    from app.blueprints.reportes import reportes_bp
    from app.blueprints.cargas import cargas_bp

    app.register_blueprint(autenticacion_bp)
    app.register_blueprint(inicio_bp)
    app.register_blueprint(contratos_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(cargas_bp)


def _inicializar_base_datos(app):
    """Inicializa las tablas y conserva migraciones básicas."""

    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        # Configuración del sistema
        if 'configuracion_sistema' not in tables:
            ConfiguracionSistema.__table__.create(bind=db.engine, checkfirst=True)
            print('[INFO] Tabla configuracion_sistema creada.')

        # Crear tablas si no existen
        if 'usuario' not in tables:
            db.create_all()
            return

        # Migraciones de contrato
        if 'contrato' in tables:
            columns = [c['name'] for c in inspector.get_columns('contrato')]
            with db.engine.connect() as conn:
                if 'user_id' not in columns:
                    conn.execute(db.text("ALTER TABLE contrato ADD COLUMN user_id INTEGER"))
                    conn.commit()
                if 'contratista' not in columns:
                    conn.execute(db.text("ALTER TABLE contrato ADD COLUMN contratista VARCHAR(200)"))
                    conn.commit()
                if 'numero_contrato' not in columns:
                    conn.execute(db.text("ALTER TABLE contrato ADD COLUMN numero_contrato VARCHAR(100)"))
                    conn.commit()
                if 'etapa' not in columns:
                    conn.execute(db.text("ALTER TABLE contrato ADD COLUMN etapa VARCHAR(50) DEFAULT 'Reporte en Proceso'"))
                    conn.execute(db.text("UPDATE contrato SET etapa = 'Reporte en Proceso' WHERE etapa IS NULL"))
                    conn.commit()

        # Eliminar etapa de usuario
        if 'usuario' in tables:
            usuario_columns = [c['name'] for c in inspector.get_columns('usuario')]
            if 'etapa' in usuario_columns:
                with db.engine.connect() as conn:
                    try:
                        conn.execute(db.text("ALTER TABLE usuario DROP COLUMN etapa"))
                        conn.commit()
                    except Exception as exc:
                        print(f'[ADVERTENCIA] No se pudo eliminar columna etapa: {exc}')


def _registrar_manejadores_errores(app):
    """Registra manejadores básicos de errores."""

    @app.errorhandler(413)
    def archivo_demasiado_grande(error):
        from flask import flash, redirect, url_for
        flash('El archivo supera el tamaño máximo permitido.', 'danger')
        return redirect(url_for('inicio.index'))
