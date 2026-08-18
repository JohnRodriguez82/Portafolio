"""
Blueprint de autenticación.

Incluye:
- Login tradicional
- Registro
- Logout
- Inicio de sesión con Google
- Callback de Google

La instancia OAuth es administrada por app/__init__.py.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from models import (
    db,
    Usuario
)

from app import oauth


# ============================================================
# BLUEPRINT
# ============================================================

autenticacion_bp = Blueprint(
    'autenticacion',
    __name__
)


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
            # URL solicitada originalmente
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

    google_configurado = _google_configurado()

    return render_template(
        'login.html',
        google_configurado=google_configurado
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
        # Confirmación de contraseña
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

    google_configurado = _google_configurado()

    return render_template(
        'registro.html',
        google_configurado=google_configurado
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

    # --------------------------------------------------------
    # Limpiar información de sesión
    # --------------------------------------------------------

    session.clear()

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
    Inicia el proceso de autenticación con Google.
    """

    # --------------------------------------------------------
    # Verificar configuración
    # --------------------------------------------------------

    if not _google_configurado():

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

    try:

        # ----------------------------------------------------
        # URL de retorno
        # ----------------------------------------------------

        redirect_uri = url_for(
            'autenticacion.auth_google_callback',
            _external=True
        )

        # ----------------------------------------------------
        # Cliente Google
        # ----------------------------------------------------

        google = oauth.create_client(
            'google'
        )

        if google is None:

            flash(
                (
                    'No fue posible inicializar '
                    'Google OAuth.'
                ),
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
            )

        # ----------------------------------------------------
        # Redireccionar a Google
        # ----------------------------------------------------

        return google.authorize_redirect(
            redirect_uri
        )

    except Exception as e:

        flash(
            (
                'Error al iniciar la autenticacion '
                f'con Google: {str(e)}'
            ),
            'danger'
        )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@autenticacion_bp.route(
    '/auth/google/callback'
)
def auth_google_callback():
    """
    Procesa la respuesta de Google después de la
    autenticación.
    """

    try:

        # ====================================================
        # CLIENTE GOOGLE
        # ====================================================

        google = oauth.create_client(
            'google'
        )

        if google is None:

            flash(
                (
                    'No fue posible inicializar '
                    'Google OAuth.'
                ),
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
            )

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
        # EXTRAER DATOS
        # ====================================================

        email = (
            user_info
            .get(
                'email',
                ''
            )
            .strip()
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
                (
                    'No se pudo obtener el correo '
                    'de Google.'
                ),
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
            )

        # ====================================================
        # BUSCAR USUARIO
        # ========================================================

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
        # ACTUALIZAR USUARIO EXISTENTE
        # ====================================================

        else:

            cambios = False

            # ------------------------------------------------
            # Marcar autenticación Google
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
            # Guardar
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
            error_msg.lower()
        )

        # ----------------------------------------------------
        # invalid_client
        # ----------------------------------------------------

        if 'invalid_client' in error_lower:

            flash(
                (
                    'Error: El Client Secret de Google '
                    'es invalido. Verifique las credenciales '
                    'configuradas en el archivo .env.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # redirect_uri
        # ----------------------------------------------------

        elif 'redirect_uri' in error_lower:

            flash(
                (
                    'Error: La URI de redireccionamiento '
                    'no coincide con la configuracion '
                    'de Google.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # unauthorized_client
        # ----------------------------------------------------

        elif 'unauthorized_client' in error_lower:

            flash(
                (
                    'Error: El Client ID no es valido '
                    'para una aplicacion web.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # access_denied
        # ----------------------------------------------------

        elif 'access_denied' in error_lower:

            flash(
                (
                    'La autenticacion con Google '
                    'fue cancelada.'
                ),
                'warning'
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


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _google_configurado():
    """
    Verifica si las credenciales de Google OAuth
    están disponibles.

    Se consulta el entorno en el momento de utilizar
    la función para mantener compatibilidad con .env.
    """

    import os

    client_id = os.environ.get(
        'GOOGLE_CLIENT_ID',
        ''
    ).strip()

    client_secret = os.environ.get(
        'GOOGLE_CLIENT_SECRET',
        ''
    ).strip()

    return bool(
        client_id
        and
        client_secret
    )