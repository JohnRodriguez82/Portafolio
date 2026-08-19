"""
Blueprint de autenticación de usuarios.

Responsabilidades:
- Inicio de sesión con correo y contraseña.
- Registro de nuevos usuarios.
- Cierre de sesión.
- Inicio de sesión con Google OAuth.
- Callback de Google OAuth.

La configuración de Flask-Login y OAuth pertenece a:
    app/__init__.py
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

    # ========================================================
    # USUARIO YA AUTENTICADO
    # ========================================================

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
        # VALIDAR CAMPOS
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
        # BUSCAR USUARIO
        # ----------------------------------------------------

        usuario = (
            Usuario.query
            .filter_by(
                email=email
            )
            .first()
        )

        # ----------------------------------------------------
        # VALIDAR CONTRASEÑA
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
        # CREDENCIALES INCORRECTAS
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

    # ========================================================
    # USUARIO YA AUTENTICADO
    # ========================================================

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
        # CAMPOS OBLIGATORIOS
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
        # CONFIRMAR CONTRASEÑA
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
        # LONGITUD MÍNIMA
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
        # VERIFICAR USUARIO EXISTENTE
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
        # CREAR USUARIO
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

    # ========================================================
    # OBTENER CLIENTE GOOGLE
    # ========================================================

    google = oauth.create_client(
        'google'
    )

    if google is None:

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

    # ========================================================
    # CALLBACK
    # ========================================================

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
    Procesa la respuesta de Google después de la autenticación.
    """

    # ========================================================
    # OBTENER CLIENTE GOOGLE
    # ========================================================

    google = oauth.create_client(
        'google'
    )

    if google is None:

        flash(
            (
                'El inicio de sesion con Google '
                'no esta configurado.'
            ),
            'danger'
        )

        return redirect(
            url_for(
                'autenticacion.login'
            )
        )

    # ========================================================
    # PROCESAR AUTENTICACIÓN
    # ========================================================

    try:

        token = google.authorize_access_token()

        if not token:

            flash(
                (
                    'No fue posible obtener el token '
                    'de autenticacion de Google.'
                ),
                'danger'
            )

            return redirect(
                url_for(
                    'autenticacion.login'
                )
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
            # ACTIVAR GOOGLE
            # ------------------------------------------------

            if not usuario.auth_google:

                usuario.auth_google = True

                cambios = True

            # ------------------------------------------------
            # GOOGLE ID
            # ------------------------------------------------

            if (
                google_id
                and
                usuario.google_id != google_id
            ):

                usuario.google_id = google_id

                cambios = True

            # ------------------------------------------------
            # AVATAR
            # ------------------------------------------------

            if (
                avatar
                and
                usuario.avatar_url != avatar
            ):

                usuario.avatar_url = avatar

                cambios = True

            # ------------------------------------------------
            # NOMBRE
            # ------------------------------------------------

            if (
                nombre
                and
                not usuario.nombre
            ):

                usuario.nombre = nombre

                cambios = True

            # ------------------------------------------------
            # GUARDAR CAMBIOS
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

    except Exception as exc:

        error_msg = str(
            exc
        )

        error_lower = (
            error_msg.lower()
        )

        # ----------------------------------------------------
        # INVALID CLIENT
        # ----------------------------------------------------

        if 'invalid_client' in error_lower:

            flash(
                (
                    'Error: El Client Secret de Google '
                    'es invalido. Verifique las credenciales.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # REDIRECT URI
        # ----------------------------------------------------

        elif 'redirect_uri' in error_lower:

            flash(
                (
                    'Error: La URI de redireccionamiento '
                    'no coincide con la configuracion de Google.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # UNAUTHORIZED CLIENT
        # ----------------------------------------------------

        elif 'unauthorized_client' in error_lower:

            flash(
                (
                    'Error: El Client ID no es valido '
                    'para aplicaciones web.'
                ),
                'danger'
            )

        # ----------------------------------------------------
        # OTRO ERROR
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
    Determina si el cliente de Google fue registrado
    correctamente por app/__init__.py.

    Retorna:
        bool: True si Google OAuth está disponible.
    """

    try:

        google = oauth.create_client(
            'google'
        )

        return google is not None

    except Exception:

        return False