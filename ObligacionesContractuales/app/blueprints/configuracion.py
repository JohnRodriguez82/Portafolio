"""
Blueprint de configuración de la aplicación.

Responsabilidades:
- Mostrar la página de configuración.
- Guardar la API Key de Gemini.
- Obtener la API Key configurada.
- Eliminar la API Key.
- Mantener la configuración independiente de autenticación.

La API Key de Gemini se almacena:
    - En la base de datos.
    - Cifrada mediante Fernet.
    - Como configuración GLOBAL de la aplicación.

La clave maestra de cifrado se obtiene desde:

    GEMINI_CONFIG_ENCRYPTION_KEY

IMPORTANTE:
La clave maestra NO se almacena en la base de datos.

Compatibilidad temporal:
    GEMINI_API_KEY puede permanecer en .env.
    Si existe allí y todavía no hay una API Key almacenada
    en la base de datos, será utilizada como respaldo.
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
    login_required,
    current_user
)

from cryptography.fernet import (
    Fernet,
    InvalidToken
)

from models import (
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
# CONSTANTES
# ============================================================

CLAVE_GEMINI = (
    'GEMINI_API_KEY'
)

CLAVE_ENCRIPTACION = (
    'APP_ENCRYPTION_KEY'
)


# ============================================================
# ARCHIVO .ENV
# ============================================================

_ENV_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    ),
    '.env'
)


# ============================================================
# LEER VARIABLE DESDE .ENV
# ============================================================

def _leer_variable_env(
    nombre_variable
):
    """
    Lee una variable específica desde el archivo .env.

    Args:
        nombre_variable:
            Nombre de la variable que se desea obtener.

    Returns:
        str:
            Valor encontrado o cadena vacía.
    """

    if not os.path.exists(
        _ENV_FILE
    ):

        return ''

    try:

        with open(
            _ENV_FILE,
            'r',
            encoding='utf-8'
        ) as archivo:

            for linea in archivo:

                linea = linea.strip()

                # ------------------------------------------------
                # Ignorar comentarios y líneas vacías
                # ------------------------------------------------

                if (
                    not linea
                    or
                    linea.startswith('#')
                ):

                    continue

                prefijo = (
                    f'{nombre_variable}='
                )

                if linea.startswith(
                    prefijo
                ):

                    valor = linea.split(
                        '=',
                        1
                    )[1].strip()

                    # ------------------------------------------------
                    # Eliminar comillas
                    # ------------------------------------------------

                    if (
                        len(valor) >= 2
                        and
                        valor[0] == valor[-1]
                        and
                        valor[0] in (
                            '"',
                            "'"
                        )
                    ):

                        valor = valor[1:-1]

                    return valor.strip()

    except (
        OSError,
        UnicodeError
    ):

        return ''

    return ''


# ============================================================
# OBTENER CLAVE MAESTRA DE ENCRIPTACIÓN
# ============================================================

def _obtener_clave_encriptacion():
    """
    Obtiene la clave maestra utilizada por Fernet.

    Prioridad:

        1. Variable de entorno.
        2. Archivo .env.

    La clave maestra NO se almacena en la base de datos.

    Returns:
        bytes:
            Clave Fernet válida.

    Raises:
        RuntimeError:
            Si la clave no está configurada o no es válida.
    """

    # ========================================================
    # VARIABLES DE ENTORNO
    # ========================================================

    clave = os.environ.get(
        CLAVE_ENCRIPTACION,
        ''
    ).strip()

    # ========================================================
    # ARCHIVO .ENV
    # ========================================================

    if not clave:

        clave = _leer_variable_env(
            CLAVE_ENCRIPTACION
        )

    # ========================================================
    # VALIDAR EXISTENCIA
    # ========================================================

    if not clave:

        raise RuntimeError(
            'No está configurada la clave maestra '
            f'{CLAVE_ENCRIPTACION}. '
            'Debe configurarse en el entorno o en el archivo .env.'
        )

    try:

        clave_bytes = clave.encode(
            'utf-8'
        )

        # ----------------------------------------------------
        # Validar clave Fernet
        # ----------------------------------------------------

        Fernet(
            clave_bytes
        )

        return clave_bytes

    except (
        ValueError,
        TypeError
    ) as exc:

        raise RuntimeError(
            f'La variable {CLAVE_ENCRIPTACION} '
            'no contiene una clave Fernet válida.'
        ) from exc


# ============================================================
# ENCRIPTAR VALOR
# ============================================================

def _encriptar_valor(
    valor
):
    """
    Encripta un valor utilizando Fernet.

    Args:
        valor:
            Texto que se desea cifrar.

    Returns:
        str:
            Texto cifrado.
    """

    if valor is None:

        return ''

    valor = str(
        valor
    ).strip()

    if not valor:

        return ''

    clave = _obtener_clave_encriptacion()

    fernet = Fernet(
        clave
    )

    valor_encriptado = (
        fernet.encrypt(
            valor.encode(
                'utf-8'
            )
        )
    )

    return valor_encriptado.decode(
        'utf-8'
    )


# ============================================================
# DESENCRIPTAR VALOR
# ============================================================

def _desencriptar_valor(
    valor_encriptado
):
    """
    Descifra un valor almacenado mediante Fernet.

    Args:
        valor_encriptado:
            Texto cifrado.

    Returns:
        str:
            Valor original.

    Raises:
        RuntimeError:
            Si no se puede descifrar.
    """

    if not valor_encriptado:

        return ''

    clave = _obtener_clave_encriptacion()

    fernet = Fernet(
        clave
    )

    try:

        valor = fernet.decrypt(
            valor_encriptado.encode(
                'utf-8'
            )
        )

        return valor.decode(
            'utf-8'
        ).strip()

    except (
        InvalidToken,
        ValueError,
        TypeError
    ) as exc:

        raise RuntimeError(
            'No fue posible descifrar la configuración '
            'almacenada en la base de datos.'
        ) from exc


# ============================================================
# OBTENER CONFIGURACIÓN GLOBAL
# ============================================================

def _obtener_configuracion():
    """
    Obtiene la configuración global del sistema.

    La aplicación utiliza una única fila de configuración.

    Returns:
        ConfiguracionSistema | None
    """

    try:

        return ConfiguracionSistema.query.first()

    except Exception as exc:

        raise RuntimeError(
            'No fue posible consultar la configuración '
            'del sistema.'
        ) from exc


# ============================================================
# OBTENER API KEY
# ============================================================

def _obtener_api_key():
    """
    Obtiene la API Key global de Gemini.

    Prioridad:

        1. Base de datos.
        2. Variable de entorno.
        3. Archivo .env.

    La API Key almacenada en la base de datos está cifrada.

    Returns:
        str:
            API Key o cadena vacía.
    """

    # ========================================================
    # BASE DE DATOS
    # ========================================================

    try:

        configuracion = _obtener_configuracion()

        if configuracion:

            valor_encriptado = (
                configuracion.gemini_api_key_encriptada
            )

            if valor_encriptado:

                try:

                    api_key = _desencriptar_valor(
                        valor_encriptado
                    )

                    if api_key:

                        return api_key

                except RuntimeError as exc:

                    print(
                        '[ADVERTENCIA] '
                        'No fue posible descifrar la API Key '
                        f'de Gemini: {exc}'
                    )

    except RuntimeError as exc:

        print(
            '[ADVERTENCIA] '
            f'{exc}'
        )

    # ========================================================
    # COMPATIBILIDAD CON VARIABLE DE ENTORNO
    # ========================================================

    api_key = os.environ.get(
        CLAVE_GEMINI,
        ''
    ).strip()

    if api_key:

        return api_key

    # ========================================================
    # COMPATIBILIDAD CON .ENV
    # ========================================================

    api_key = _leer_variable_env(
        CLAVE_GEMINI
    )

    if api_key:

        return api_key

    return ''


# ============================================================
# GUARDAR API KEY
# ============================================================

def _guardar_api_key(
    api_key
):
    """
    Guarda la API Key global de Gemini.

    La API Key se cifra mediante Fernet antes de almacenarla
    en la base de datos.

    Utiliza:

        ConfiguracionSistema.gemini_api_key_encriptada

    Returns:
        bool:
            True si se guardó correctamente.
    """

    api_key = (
        api_key or ''
    ).strip()

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    if not api_key:

        return False

    try:

        # ====================================================
        # CIFRAR API KEY
        # ====================================================

        valor_encriptado = _encriptar_valor(
            api_key
        )

        if not valor_encriptado:

            return False

        # ====================================================
        # OBTENER CONFIGURACIÓN EXISTENTE
        # ====================================================

        configuracion = _obtener_configuracion()

        # ====================================================
        # CREAR CONFIGURACIÓN
        # ====================================================

        if configuracion is None:

            configuracion = ConfiguracionSistema(
                gemini_api_key_encriptada=(
                    valor_encriptado
                )
            )

            db.session.add(
                configuracion
            )

        # ====================================================
        # ACTUALIZAR CONFIGURACIÓN
        # ====================================================

        else:

            configuracion.gemini_api_key_encriptada = (
                valor_encriptado
            )

        # ====================================================
        # GUARDAR
        # ====================================================

        db.session.commit()

        # ====================================================
        # ACTUALIZAR ENTORNO EN MEMORIA
        #
        # Esto mantiene compatibilidad con código antiguo
        # que todavía consulte GEMINI_API_KEY.
        # ====================================================

        os.environ[
            CLAVE_GEMINI
        ] = api_key

        return True

    except Exception as exc:

        db.session.rollback()

        print(
            '[ERROR] '
            'No fue posible guardar la API Key de Gemini '
            f'en la base de datos: {exc}'
        )

        return False


# ============================================================
# ELIMINAR API KEY
# ============================================================

def _eliminar_api_key():
    """
    Elimina la API Key global de la base de datos.

    También elimina GEMINI_API_KEY del entorno del proceso
    actual.

    No modifica el archivo .env.

    Returns:
        bool:
            True si la operación fue exitosa.
    """

    try:

        configuracion = _obtener_configuracion()

        if configuracion:

            configuracion.gemini_api_key_encriptada = None

            db.session.commit()

        # ====================================================
        # ELIMINAR DE MEMORIA
        # ====================================================

        os.environ.pop(
            CLAVE_GEMINI,
            None
        )

        return True

    except Exception as exc:

        db.session.rollback()

        print(
            '[ERROR] '
            'No fue posible eliminar la API Key '
            f'de Gemini: {exc}'
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
        Guarda la API Key global en la base de datos.
    """

    # --------------------------------------------------------
    # Solo administrador puede gestionar la API Key global
    # --------------------------------------------------------

    if not getattr(current_user, 'es_admin', False):
        flash(
            'Solo el administrador del sistema puede '
            'gestionar la API Key de Gemini.',
            'warning'
        )
        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # ========================================================
    # GUARDAR
    # ========================================================

    if request.method == 'POST':

        api_key = request.form.get(
            'gemini_api_key',
            ''
        ).strip()

        # ----------------------------------------------------
        # VALIDAR
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
        # GUARDAR
        # ----------------------------------------------------

        if _guardar_api_key(
            api_key
        ):

            flash(
                (
                    'API Key de Gemini guardada '
                    'correctamente en la configuración '
                    'global del sistema.'
                ),
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

    api_key = _obtener_api_key()

    api_key_configurada = bool(
        api_key
    )

    # ========================================================
    # MÁSCARA DE API KEY
    # ========================================================

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

    # ========================================================
    # PLANTILLA
    # ========================================================

    return render_template(
        'config.html',
        api_key_configurada=api_key_configurada,
        api_key_mostrable=api_key_mostrable
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
    Elimina la API Key global de Gemini.
    """

    # --------------------------------------------------------
    # Solo administrador puede eliminar la API Key
    # --------------------------------------------------------

    if not getattr(current_user, 'es_admin', False):
        flash(
            'Solo el administrador puede eliminar la API Key.',
            'warning'
        )
        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    if _eliminar_api_key():

        flash(
            'API Key de Gemini eliminada correctamente.',
            'success'
        )

    else:

        flash(
            (
                'No fue posible eliminar la API Key '
                'de Gemini.'
            ),
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

    Returns:
        bool:
            True si existe una API Key.
    """

    return bool(
        _obtener_api_key()
    )
