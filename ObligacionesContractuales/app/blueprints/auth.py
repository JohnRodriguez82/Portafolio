"""
Blueprint de autenticación.

Incluye:
- Login tradicional
- Registro
- Logout
- Inicio de sesión con Google
- Callback de Google
"""

import os

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

from authlib.integrations.flask_client import OAuth

from models import db, Usuario


auth_bp = Blueprint(
    'auth',
    __name__
)


# ============================================================
# CONFIGURACIÓN GOOGLE OAUTH
# ============================================================

_GOOGLE_CLIENT_ID = os.environ.get(
    'GOOGLE_CLIENT_ID',
    ''
).strip()

_GOOGLE_CLIENT_SECRET = os.environ.get(
    'GOOGLE_CLIENT_SECRET',
    ''
).strip()


def configurar_google(oauth):
    """
    Registra el cliente de Google OAuth.

    La instancia OAuth será creada posteriormente
    por la aplicación principal.
    """

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

    return google


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route(
    '/login',
    methods=['GET', 'POST']
)
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for('inicio.inicio')
        )

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
            request.form.get('remember')
        )

        if not email or not password:

            flash(
                'Complete todos los campos.',
                'danger'
            )

            return redirect(
                url_for('auth.login')
            )

        usuario = Usuario.query.filter_by(
            email=email
        ).first()

        if usuario and usuario.check_password(
            password
        ):

            login_user(
                usuario,
                remember=remember
            )

            next_page = request.args.get(
                'next'
            )

            flash(
                f'Bienvenido, '
                f'{usuario.nombre or usuario.email}!',
                'success'
            )

            return redirect(
                next_page or
                url_for('inicio.inicio')
            )

        flash(
            'Correo o contrasena incorrectos.',
            'danger'
        )

        return redirect(
            url_for('auth.login')
        )

    google_configurado = bool(
        _GOOGLE_CLIENT_ID and
        _GOOGLE_CLIENT_SECRET
    )

    return render_template(
        'login.html',
        google_configurado=google_configurado
    )


# ============================================================
# REGISTRO
# ============================================================

@auth_bp.route(
    '/registro',
    methods=['GET', 'POST']
)
def registro():

    if current_user.is_authenticated:
        return redirect(
            url_for('inicio.inicio')
        )

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

        if not nombre or not email or not password:

            flash(
                'Complete todos los campos obligatorios.',
                'danger'
            )

            return redirect(
                url_for('auth.registro')
            )

        if password != confirmar:

            flash(
                'Las contrasenas no coinciden.',
                'danger'
            )

            return redirect(
                url_for('auth.registro')
            )

        if len(password) < 6:

            flash(
                'La contrasena debe tener al menos '
                '6 caracteres.',
                'danger'
            )

            return redirect(
                url_for('auth.registro')
            )

        existente = Usuario.query.filter_by(
            email=email
        ).first()

        if existente:

            flash(
                'Ya existe una cuenta con este correo.',
                'danger'
            )

            return redirect(
                url_for('auth.registro')
            )

        nuevo = Usuario(
            email=email,
            nombre=nombre
        )

        nuevo.set_password(password)

        db.session.add(nuevo)
        db.session.commit()

        flash(
            'Cuenta creada exitosamente. '
            'Inicie sesion.',
            'success'
        )

        return redirect(
            url_for('auth.login')
        )

    google_configurado = bool(
        _GOOGLE_CLIENT_ID and
        _GOOGLE_CLIENT_SECRET
    )

    return render_template(
        'registro.html',
        google_configurado=google_configurado
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route('/logout')
@login_required
def logout():

    logout_user()

    session.clear()

    flash(
        'Sesion cerrada.',
        'info'
    )

    return redirect(
        url_for('auth.login')
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@auth_bp.route('/auth/google')
def auth_google():

    google = configurar_google(
        auth_bp.oauth
    )

    redirect_uri = url_for(
        'auth.auth_google_callback',
        _external=True
    )

    return google.authorize_redirect(
        redirect_uri
    )


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@auth_bp.route(
    '/auth/google/callback'
)
def auth_google_callback():

    google = configurar_google(
        auth_bp.oauth
    )

    try:

        token = google.authorize_access_token()

        resp = google.get(
            'https://www.googleapis.com/oauth2/v3/userinfo'
        )

        user_info = resp.json()

        email = user_info.get(
            'email',
            ''
        ).lower()

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

        if not email:

            flash(
                'No se pudo obtener el correo de Google.',
                'danger'
            )

            return redirect(
                url_for('auth.login')
            )

        usuario = Usuario.query.filter_by(
            email=email
        ).first()

        if not usuario:

            usuario = Usuario(
                email=email,
                nombre=nombre,
                auth_google=True,
                google_id=google_id,
                avatar_url=avatar
            )

            db.session.add(usuario)
            db.session.commit()

        else:

            if not usuario.auth_google:

                usuario.auth_google = True
                usuario.google_id = google_id
                usuario.avatar_url = avatar

                db.session.commit()

        login_user(usuario)

        flash(
            f'Bienvenido, '
            f'{usuario.nombre or usuario.email}!',
            'success'
        )

        return redirect(
            url_for('inicio.inicio')
        )

    except Exception as e:

        error_msg = str(e)

        if 'invalid_client' in error_msg.lower():

            flash(
                'Error: El Client Secret de Google '
                'es invalido. Verifique las credenciales.',
                'danger'
            )

        elif 'redirect_uri' in error_msg.lower():

            flash(
                'Error: La URI de redireccionamiento '
                'no coincide con la configuracion de Google.',
                'danger'
            )

        elif 'unauthorized_client' in error_msg.lower():

            flash(
                'Error: El Client ID no es valido '
                'para aplicaciones web.',
                'danger'
            )

        else:

            flash(
                f'Error al autenticar con Google: '
                f'{error_msg}',
                'danger'
            )

        return redirect(
            url_for('auth.login')
        )