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
La clave maestra NO debe almacenarse en la base de datos.

La API Key antigua almacenada en .env se mantiene como
compatibilidad temporal. Una vez guardada nuevamente desde
Configuración del Sistema, la nueva copia queda almacenada
en la base de datos.
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
    login_required
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

CLAVE_GEMINI = 'GEMINI_API_KEY'

CLAVE_ENCRIPTACION = (
    'GEMINI_CONFIG_ENCRYPTION_KEY'
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
# CLAVE MAESTRA DE ENCRIPTACIÓN
# ============================================================

def _obtener_clave_encriptacion():
    """
    Obtiene la clave maestra utilizada para cifrar y descifrar
    la configuración sensible.

    La clave debe estar en:

        GEMINI_CONFIG_ENCRYPTION_KEY

    Esta clave NO se almacena en la base de datos.

    Retorna:
        bytes: clave Fernet válida.

    Raises:
        RuntimeError:
            Si la clave no está configurada o no es válida.
    """

    clave = os.environ.get(
        CLAVE_ENCRIPTACION,
        ''
    ).strip()

    # --------------------------------------------------------
    # Si no está en el entorno, intentar leer .env
    # --------------------------------------------------------

    if not clave:

        clave = _leer_variable_env(
            CLAVE_ENCRIPTACION
        )

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
        # Validar que sea una clave Fernet válida.
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
# LEER VARIABLE DESDE .ENV
# ============================================================

def _leer_variable_env(
    nombre_variable
):
    """
    Lee una variable específica desde .env.

    Se utiliza únicamente como compatibilidad/respaldo.

    Args:
        nombre_variable:
            Nombre de la variable.

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

                    # ----------------------------------------
                    # Eliminar comillas
                    # ----------------------------------------

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
# ENCRIPTAR
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
            Valor cifrado.
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
# DESENCRIPTAR
# ============================================================

def _desencriptar_valor(
    valor_encriptado
):
    """
    Descifra un valor previamente almacenado mediante Fernet.

    Args:
        valor_encriptado:
            Texto cifrado.

    Returns:
        str:
            Valor original.

    Raises:
        RuntimeError:
            Si el valor no puede ser descifrado.
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
# BUSCAR CONFIGURACIÓN
# ============================================================

def _obtener_configuracion(
    clave
):
    """
    Busca una configuración global por su nombre.

    Args:
        clave:
            Nombre de la configuración.

    Returns:
        ConfiguracionSistema | None
    """

    try:

        return ConfiguracionSistema.query.filter_by(
            clave=clave
        ).first()

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
            API Key o cadena vacía si no está configurada.
    """

    # ========================================================
    # BASE DE DATOS
    # ========================================================

    try:

        configuracion = _obtener_configuracion(
            CLAVE_GEMINI
        )

        if configuracion:

            valor_encriptado = (
                configuracion.valor_encriptado
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
    # COMPATIBILIDAD CON ENTORNO
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
    Guarda la API Key global de Gemini en la base de datos.

    La API Key se almacena cifrada mediante Fernet.

    Args:
        api_key:
            API Key de Gemini.

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
        # CIFRAR
        # ====================================================

        valor_encriptado = _encriptar_valor(
            api_key
        )

        if not valor_encriptado:

            return False

        # ====================================================
        # BUSCAR CONFIGURACIÓN EXISTENTE
        # ====================================================

        configuracion = _obtener_configuracion(
            CLAVE_GEMINI
        )

        # ====================================================
        # CREAR O ACTUALIZAR
        # ====================================================

        if configuracion is None:

            configuracion = (
                ConfiguracionSistema(
                    clave=CLAVE_GEMINI,
                    valor_encriptado=(
                        valor_encriptado
                    )
                )
            )

            db.session.add(
                configuracion
            )

        else:

            configuracion.valor_encriptado = (
                valor_encriptado
            )

        # ====================================================
        # GUARDAR
        # ====================================================

        db.session.commit()

        # ====================================================
        # ACTUALIZAR ENTORNO EN MEMORIA
        #
        # Esto permite que partes antiguas de la aplicación
        # que todavía consulten GEMINI_API_KEY sigan
        # funcionando durante la transición.
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

    También elimina la variable de entorno de la memoria
    del proceso actual.

    No modifica el archivo .env.

    Returns:
        bool:
            True si la operación fue exitosa.
    """

    try:

        configuracion = _obtener_configuracion(
            CLAVE_GEMINI
        )

        if configuracion:

            db.session.delete(
                configuracion
            )

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

    # ========================================================
    # GUARDAR CONFIGURACIÓN
    # ========================================================

    if request.method == 'POST':

        api_key = request.form.get(
            'gemini_api_key',
            ''
        ).strip()

        # ----------------------------------------------------
        # Validar API Key
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

    # --------------------------------------------------------
    # No enviar la clave completa a la plantilla.
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
