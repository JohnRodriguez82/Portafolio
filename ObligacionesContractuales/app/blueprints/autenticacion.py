"""
Blueprint de autenticación de usuarios.

Responsabilidades:
- Inicio de sesión con correo y contraseña.
- Registro de nuevos usuarios.
- Cierre de sesión.
- Inicio de sesión con Google OAuth.
- Callback de Google OAuth.
- Carga del usuario para Flask-Login.
"""

import os

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from authlib.integrations.flask_client import OAuth

from models import (
    db,
    Usuario
)


# ============================================================
# BLUEPRINT
# ============================================================

autenticacion_bp = Blueprint(
    'autenticacion',
    __name__
)


# ============================================================
# OAUTH GOOGLE
# ============================================================

oauth = OAuth()

_GOOGLE_CLIENT_ID = os.environ.get(
    'GOOGLE_CLIENT_ID',
    ''
).strip()

_GOOGLE_CLIENT_SECRET = os.environ.get(
    'GOOGLE_CLIENT_SECRET',
    ''
).strip()


# ------------------------------------------------------------
# Advertencia si faltan credenciales
# ------------------------------------------------------------

if (
    not _GOOGLE_CLIENT_ID
    or
    not _GOOGLE_CLIENT_SECRET
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
        'GOOGLE_CLIENT_SECRET en el archivo .env'
    )


# ============================================================
# CONFIGURAR GOOGLE
# ============================================================

google = oauth.register(
    name='google',

    client_id=_GOOGLE_CLIENT_ID,

    client_secret=_GOOGLE_CLIENT_SECRET,

    server_metadata_url=(
        'https://accounts.google.com/'
        '.well-known/openid-configuration'
    ),

    client_kwargs={
        'scope': 'openid email profile'
    }
)


# ============================================================
# USER LOADER
# ============================================================

@autenticacion_bp.record_once
def registrar_user_loader(setup_state):
    """
    Registra el user_loader de Flask-Login una sola vez.

    Se utiliza record_once porque el LoginManager pertenece
    a la aplicación Flask y no al Blueprint.
    """

    login_manager = setup_state.app.extensions.get(
        'login_manager'
    )

    if login_manager is None:
        return

    @login_manager.user_loader
    def load_user(user_id):

        try:

            return Usuario.query.get(
                int(user_id)
            )

        except (
            ValueError,
            TypeError
        ):

            return None


# ============================================================
# LOGIN
# ============================================================

@autenticacion_bp.route(
    '/login',
    methods=['GET', 'POST']
)
def login():
    """
    Inicio de sesión mediante correo y contraseña.
    """

    # --------------------------------------------------------
    # Si ya está autenticado
    # --------------------------------------------------------

    if current_user.is_authenticated:

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == 'POST':

        email = request.form.get(
            'email',
            ''
        ).strip().lower()

        password = request.form.get(
            'password',
            ''
        )

        remember = bool(
            request.form.get(
                'remember'
            )
        )

        # ----------------------------------------------------
        # Validar campos
        # ----------------------------------------------------

        if not email or not password:

            flash(
                'Complete todos los campos.',
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
            )

        # ----------------------------------------------------
        # Buscar usuario
        # ----------------------------------------------------

        usuario = (
            Usuario.query
            .filter_by(
                email=email
            )
            .first()
        )

        # ----------------------------------------------------
        # Validar contraseña
        # ----------------------------------------------------

        if (
            usuario
            and
            usuario.check_password(
                password
            )
        ):

            login_user(
                usuario,
                remember=remember
            )

            # -----------------------------------------------
            # Página solicitada originalmente
            # -----------------------------------------------

            next_page = request.args.get(
                'next'
            )

            flash(
                (
                    'Bienvenido, '
                    f'{usuario.nombre or usuario.email}!'
                ),
                'success'
            )

            return redirect(
                next_page
                or
                url_for(
                    'inicio.inicio'
                )
            )

        # ----------------------------------------------------
        # Credenciales incorrectas
        # ----------------------------------------------------

        flash(
            'Correo o contrasena incorrectos.',
            'danger'
        )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )

    # ========================================================
    # GET
    # ========================================================

    google_configurado = bool(
        _GOOGLE_CLIENT_ID
        and
        _GOOGLE_CLIENT_SECRET
    )

    return render_template(
        'login.html',
        google_configurado=(
            google_configurado
        )
    )


# ============================================================
# REGISTRO
# ============================================================

@autenticacion_bp.route(
    '/registro',
    methods=['GET', 'POST']
)
def registro():
    """
    Registro de nuevos usuarios.
    """

    # --------------------------------------------------------
    # Usuario ya autenticado
    # --------------------------------------------------------

    if current_user.is_authenticated:

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == 'POST':

        nombre = request.form.get(
            'nombre',
            ''
        ).strip()

        email = request.form.get(
            'email',
            ''
        ).strip().lower()

        password = request.form.get(
            'password',
            ''
        )

        confirmar = request.form.get(
            'confirmar_password',
            ''
        )

        # ----------------------------------------------------
        # Campos obligatorios
        # ----------------------------------------------------

        if (
            not nombre
            or
            not email
            or
            not password
        ):

            flash(
                'Complete todos los campos obligatorios.',
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.registro'
                )
            )

        # ----------------------------------------------------
        # Confirmación
        # ----------------------------------------------------

        if password != confirmar:

            flash(
                'Las contrasenas no coinciden.',
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.registro'
                )
            )

        # ----------------------------------------------------
        # Longitud mínima
        # ----------------------------------------------------

        if len(password) < 6:

            flash(
                (
                    'La contrasena debe tener '
                    'al menos 6 caracteres.'
                ),
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.registro'
                )
            )

        # ----------------------------------------------------
        # Verificar correo existente
        # ----------------------------------------------------

        existente = (
            Usuario.query
            .filter_by(
                email=email
            )
            .first()
        )

        if existente:

            flash(
                'Ya existe una cuenta con este correo.',
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.registro'
                )
            )

        # ----------------------------------------------------
        # Crear usuario
        # ----------------------------------------------------

        nuevo = Usuario(
            email=email,
            nombre=nombre
        )

        nuevo.set_password(
            password
        )

        db.session.add(
            nuevo
        )

        db.session.commit()

        flash(
            (
                'Cuenta creada exitosamente. '
                'Inicie sesion.'
            ),
            'success'
        )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )

    # ========================================================
    # GET
    # ========================================================

    google_configurado = bool(
        _GOOGLE_CLIENT_ID
        and
        _GOOGLE_CLIENT_SECRET
    )

    return render_template(
        'registro.html',

        google_configurado=(
            google_configurado
        )
    )


# ============================================================
# LOGOUT
# ============================================================

@autenticacion_bp.route(
    '/logout'
)
@login_required
def logout():
    """
    Cierra la sesión del usuario actual.
    """

    logout_user()

    flash(
        'Sesion cerrada.',
        'info'
    )

    return redirect(
        url_for(
            'autenticacion.login'
        )
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@autenticacion_bp.route(
    '/auth/google'
)
def auth_google():
    """
    Inicia el flujo de autenticación con Google.
    """

    # --------------------------------------------------------
    # Verificar configuración
    # --------------------------------------------------------

    if (
        not _GOOGLE_CLIENT_ID
        or
        not _GOOGLE_CLIENT_SECRET
    ):

        flash(
            (
                'El inicio de sesion con Google '
                'no esta configurado.'
            ),
            'warning'
        )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )

    # --------------------------------------------------------
    # URI callback
    # --------------------------------------------------------

    redirect_uri = url_for(
        'autenticacion.auth_google_callback',
        _external=True
    )

    return google.authorize_redirect(
        redirect_uri
    )


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@autenticacion_bp.route(
    '/auth/google/callback'
)
def auth_google_callback():
    """
    Procesa la respuesta enviada por Google después
    de la autenticación.
    """

    try:

        # ====================================================
        # OBTENER TOKEN
        # ====================================================

        token = (
            google.authorize_access_token()
        )

        # ====================================================
        # INFORMACIÓN DEL USUARIO
        # ====================================================

        resp = google.get(
            'https://www.googleapis.com/oauth2/v3/userinfo'
        )

        user_info = resp.json()

        # ====================================================
        # DATOS
        # ====================================================

        email = (
            user_info
            .get(
                'email',
                ''
            )
            .lower()
        )

        google_id = user_info.get(
            'sub'
        )

        nombre = user_info.get(
            'name',
            email
        )

        avatar = user_info.get(
            'picture',
            ''
        )

        # ====================================================
        # VALIDAR EMAIL
        # ====================================================

        if not email:

            flash(
                'No se pudo obtener el correo de Google.',
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
            )

        # ====================================================
        # BUSCAR USUARIO
        # ====================================================

        usuario = (
            Usuario.query
            .filter_by(
                email=email
            )
            .first()
        )

        # ====================================================
        # CREAR USUARIO
        # ====================================================

        if not usuario:

            usuario = Usuario(
                email=email,
                nombre=nombre,
                auth_google=True,
                google_id=google_id,
                avatar_url=avatar
            )

            db.session.add(
                usuario
            )

            db.session.commit()

        # ====================================================
        # USUARIO EXISTENTE
        # ====================================================

        else:

            cambios = False

            # ------------------------------------------------
            # Activar Google
            # ------------------------------------------------

            if not usuario.auth_google:

                usuario.auth_google = True

                cambios = True

            # ------------------------------------------------
            # Google ID
            # ------------------------------------------------

            if (
                google_id
                and
                usuario.google_id != google_id
            ):

                usuario.google_id = google_id

                cambios = True

            # ------------------------------------------------
            # Avatar
            # ------------------------------------------------

            if (
                avatar
                and
                usuario.avatar_url != avatar
            ):

                usuario.avatar_url = avatar

                cambios = True

            # ------------------------------------------------
            # Nombre
            # ------------------------------------------------

            if (
                nombre
                and
                not usuario.nombre
            ):

                usuario.nombre = nombre

                cambios = True

            # ------------------------------------------------
            # Guardar cambios
            # ------------------------------------------------

            if cambios:

                db.session.commit()

        # ====================================================
        # INICIAR SESIÓN
        # ====================================================

        login_user(
            usuario
        )

        flash(
            (
                'Bienvenido, '
                f'{usuario.nombre or usuario.email}!'
            ),
            'success'
        )

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # ========================================================
    # ERRORES
    # ========================================================

    except Exception as e:

        error_msg = str(
            e
        )

        error_lower = (
            error_msg
            .lower()
        )

        # ----------------------------------------------------
        # invalid_client
        # ----------------------------------------------------

        if (
            'invalid_client'
            in error_lower
        ):

            flash(
                (
                    'Error: El Client Secret de Google '
                    'es invalido. '
                    'Verifique que haya copiado el valor '
                    'correcto de "Secreto de cliente" '
                    '(no el ID de cliente). '
                    'Ejecute: '
                    'python diagnostico_google.py'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # redirect_uri
        # ----------------------------------------------------

        elif (
            'redirect_uri'
            in error_lower
        ):

            flash(
                (
                    'Error: La URI de redireccionamiento '
                    'no coincide. '
                    'Verifique en Google Cloud Console '
                    'que la URI configurada sea exactamente '
                    'la utilizada por la aplicacion.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # unauthorized_client
        # ----------------------------------------------------

        elif (
            'unauthorized_client'
            in error_lower
        ):

            flash(
                (
                    'Error: El Client ID no es valido '
                    'para aplicaciones web. '
                    'Cree un ID de cliente OAuth 2.0 '
                    'de tipo "Aplicacion web" '
                    'en Google Cloud Console.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # Otro error
        # ----------------------------------------------------

        else:

            flash(
                (
                    'Error al autenticar con Google: '
                    f'{error_msg}'
                ),
                'danger'
            )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )