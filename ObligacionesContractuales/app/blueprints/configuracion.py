"""
Blueprint de configuración de la aplicación.

Responsabilidades:
- Mostrar la página de configuración.
- Guardar la API Key de Gemini.
- Obtener la API Key configurada.
- Eliminar la API Key.
- Mantener la configuración independiente de autenticación.

La API Key de Gemini es GLOBAL para todo el sistema.

La API Key:
    - Se almacena en la base de datos.
    - Se almacena cifrada.
    - No se guarda en texto plano.
    - Es compartida por todos los usuarios autenticados.

La clave utilizada para cifrar/desencriptar la API Key
se obtiene desde GEMINI_ENCRYPTION_KEY.
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

from flask_login import login_required

from cryptography.fernet import (
    Fernet,
    InvalidToken
)

from app.models import (
    db,
    ConfiguracionSistema
)


# ============================================================
# BLUEPRINT
# ============================================================

configuracion_bp = Blueprint(
    'configuracion',
    __name__
)


# ============================================================
# CLAVE DE CIFRADO
# ============================================================

def _obtener_clave_cifrado():
    """
    Obtiene la clave maestra utilizada para cifrar
    y descifrar la API Key de Gemini.

    Esta clave NO se almacena en la base de datos.

    Debe existir en:

        GEMINI_ENCRYPTION_KEY

    """

    clave = os.environ.get(
        'GEMINI_ENCRYPTION_KEY',
        ''
    ).strip()

    if not clave:

        raise RuntimeError(
            'No está configurada GEMINI_ENCRYPTION_KEY.'
        )

    try:

        return Fernet(
            clave.encode('utf-8')
        )

    except Exception as exc:

        raise RuntimeError(
            'GEMINI_ENCRYPTION_KEY no tiene '
            'un formato Fernet válido.'
        ) from exc


# ============================================================
# OBTENER CONFIGURACIÓN GLOBAL
# ============================================================

def _obtener_configuracion():
    """
    Obtiene el único registro de configuración del sistema.

    Si no existe, lo crea.
    """

    configuracion = (
        ConfiguracionSistema.query
        .order_by(
            ConfiguracionSistema.id.asc()
        )
        .first()
    )

    if configuracion is None:

        configuracion = (
            ConfiguracionSistema()
        )

        db.session.add(
            configuracion
        )

        db.session.commit()

    return configuracion


# ============================================================
# CIFRAR API KEY
# ============================================================

def _cifrar_api_key(
    api_key
):
    """
    Cifra una API Key utilizando Fernet.
    """

    fernet = (
        _obtener_clave_cifrado()
    )

    return (
        fernet.encrypt(
            api_key.encode('utf-8')
        )
        .decode('utf-8')
    )


# ============================================================
# DESCIFRAR API KEY
# ============================================================

def _descifrar_api_key(
    api_key_cifrada
):
    """
    Descifra una API Key almacenada en la base de datos.

    Retorna:
        str: API Key original.

    Retorna cadena vacía si no existe.
    """

    if not api_key_cifrada:

        return ''

    try:

        fernet = (
            _obtener_clave_cifrado()
        )

        return (
            fernet.decrypt(
                api_key_cifrada.encode('utf-8')
            )
            .decode('utf-8')
            .strip()
        )

    except (
        InvalidToken,
        ValueError,
        TypeError,
        UnicodeDecodeError
    ):

        return ''


# ============================================================
# OBTENER API KEY
# ============================================================

def _obtener_api_key():
    """
    Obtiene la API Key GLOBAL de Gemini.

    La API Key se almacena cifrada en:

        configuracion_sistema.gemini_api_key

    Retorna:
        str: API Key descifrada.

        '' si no existe o no puede descifrarse.
    """

    try:

        configuracion = (
            ConfiguracionSistema.query
            .order_by(
                ConfiguracionSistema.id.asc()
            )
            .first()
        )

        if not configuracion:

            return ''

        return _descifrar_api_key(
            configuracion.gemini_api_key
        )

    except Exception as exc:

        print(
            '[Configuracion] '
            f'No fue posible obtener la API Key: {exc}'
        )

        return ''


# ============================================================
# GUARDAR API KEY
# ============================================================

def _guardar_api_key(
    api_key
):
    """
    Guarda la API Key GLOBAL de Gemini.

    La API Key se cifra antes de almacenarla.
    """

    api_key = (
        api_key or ''
    ).strip()

    if not api_key:

        return False

    try:

        api_key_cifrada = (
            _cifrar_api_key(
                api_key
            )
        )

        configuracion = (
            ConfiguracionSistema.query
            .order_by(
                ConfiguracionSistema.id.asc()
            )
            .first()
        )

        if configuracion is None:

            configuracion = (
                ConfiguracionSistema()
            )

            db.session.add(
                configuracion
            )

        configuracion.gemini_api_key = (
            api_key_cifrada
        )

        db.session.commit()

        return True

    except Exception as exc:

        db.session.rollback()

        print(
            '[Configuracion] '
            f'No fue posible guardar API Key: {exc}'
        )

        return False


# ============================================================
# ELIMINAR API KEY
# ============================================================

def _eliminar_api_key():
    """
    Elimina la API Key GLOBAL de Gemini.

    No elimina el registro de configuración;
    simplemente elimina la clave almacenada.
    """

    try:

        configuracion = (
            ConfiguracionSistema.query
            .order_by(
                ConfiguracionSistema.id.asc()
            )
            .first()
        )

        if configuracion is None:

            return True

        configuracion.gemini_api_key = None

        db.session.commit()

        return True

    except Exception as exc:

        db.session.rollback()

        print(
            '[Configuracion] '
            f'No fue posible eliminar API Key: {exc}'
        )

        return False


# ============================================================
# PÁGINA DE CONFIGURACIÓN
# ============================================================

@configuracion_bp.route(
    '/configuracion',
    methods=['GET', 'POST']
)
@login_required
def configuracion():
    """
    Página principal de configuración.

    GET:
        Muestra el estado de la API Key.

    POST:
        Guarda la API Key global.
    """

    # ========================================================
    # GUARDAR CONFIGURACIÓN
    # ========================================================

    if request.method == 'POST':

        api_key = request.form.get(
            'gemini_api_key',
            ''
        ).strip()

        # ----------------------------------------------------
        # Validar
        # ----------------------------------------------------

        if not api_key:

            flash(
                'Ingrese una API Key de Gemini.',
                'warning'
            )

            return redirect(
                url_for(
                    'configuracion.configuracion'
                )
            )

        # ----------------------------------------------------
        # Guardar
        # ----------------------------------------------------

        if _guardar_api_key(
            api_key
        ):

            flash(
                'API Key de Gemini guardada correctamente.',
                'success'
            )

        else:

            flash(
                (
                    'No fue posible guardar la API Key '
                    'en la base de datos.'
                ),
                'danger'
            )

        return redirect(
            url_for(
                'configuracion.configuracion'
            )
        )

    # ========================================================
    # GET
    # ========================================================

    api_key = (
        _obtener_api_key()
    )

    api_key_configurada = bool(
        api_key
    )

    # --------------------------------------------------------
    # No enviar la clave completa a la plantilla
    # --------------------------------------------------------

    api_key_mostrable = ''

    if api_key:

        if len(api_key) <= 8:

            api_key_mostrable = (
                '*' * len(api_key)
            )

        else:

            api_key_mostrable = (
                api_key[:4]
                +
                '********'
                +
                api_key[-4:]
            )

    return render_template(
        'config.html',
        api_key_configurada=(
            api_key_configurada
        ),
        api_key_mostrable=(
            api_key_mostrable
        )
    )


# ============================================================
# ELIMINAR API KEY
# ============================================================

@configuracion_bp.route(
    '/configuracion/eliminar-api-key',
    methods=['POST']
)
@login_required
def eliminar_api_key():
    """
    Elimina la API Key GLOBAL de Gemini.
    """

    if _eliminar_api_key():

        flash(
            'API Key eliminada correctamente.',
            'success'
        )

    else:

        flash(
            'No fue posible eliminar la API Key.',
            'danger'
        )

    return redirect(
        url_for(
            'configuracion.configuracion'
        )
    )


# ============================================================
# API KEY DISPONIBLE
# ============================================================

def api_key_configurada():
    """
    Indica si existe una API Key configurada.

    Retorna:
        bool
    """

    return bool(
        _obtener_api_key()
    )
