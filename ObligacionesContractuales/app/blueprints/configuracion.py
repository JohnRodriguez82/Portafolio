"""
Blueprint de configuración de la aplicación.

Responsabilidades:
- Mostrar la página de configuración.
- Guardar la API Key de Gemini.
- Obtener la API Key configurada.
- Eliminar la API Key.
- Mantener la configuración independiente de autenticación.

La autenticación y Google OAuth pertenecen exclusivamente
al Blueprint autenticacion.py.
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


# ============================================================
# BLUEPRINT
# ============================================================

configuracion_bp = Blueprint(
    'configuracion',
    __name__
)


# ============================================================
# CONFIGURACIÓN
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
# OBTENER API KEY
# ============================================================

def _obtener_api_key():
    """
    Obtiene la API Key de Gemini.

    Primero intenta obtenerla desde las variables de entorno.
    Si no existe, intenta leerla desde el archivo .env.

    Retorna:
        str: API Key o cadena vacía si no está configurada.
    """

    # ========================================================
    # VARIABLES DE ENTORNO
    # ========================================================

    api_key = os.environ.get(
        'GEMINI_API_KEY',
        ''
    ).strip()

    if api_key:
        return api_key

    # ========================================================
    # ARCHIVO .ENV
    # ========================================================

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

                # ------------------------------------------------
                # Buscar GEMINI_API_KEY
                # ------------------------------------------------

                if linea.startswith(
                    'GEMINI_API_KEY='
                ):

                    valor = linea.split(
                        '=',
                        1
                    )[1].strip()

                    # --------------------------------------------
                    # Eliminar comillas
                    # --------------------------------------------

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
# GUARDAR API KEY
# ============================================================

def _guardar_api_key(
    api_key
):
    """
    Guarda o actualiza la API Key de Gemini en .env.

    También actualiza os.environ para que la nueva clave
    esté disponible inmediatamente sin reiniciar la aplicación.

    Parámetros:
        api_key (str): API Key de Gemini.

    Retorna:
        bool: True si se guardó correctamente.
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
        # LEER .ENV EXISTENTE
        # ====================================================

        lineas = []

        if os.path.exists(
            _ENV_FILE
        ):

            with open(
                _ENV_FILE,
                'r',
                encoding='utf-8'
            ) as archivo:

                lineas = archivo.readlines()

        # ====================================================
        # ACTUALIZAR VARIABLE
        # ====================================================

        encontrada = False

        nuevas_lineas = []

        for linea in lineas:

            linea_sin_espacios = (
                linea.strip()
            )

            if linea_sin_espacios.startswith(
                'GEMINI_API_KEY='
            ):

                nuevas_lineas.append(
                    f'GEMINI_API_KEY={api_key}\n'
                )

                encontrada = True

            else:

                nuevas_lineas.append(
                    linea
                )

        # ====================================================
        # AGREGAR SI NO EXISTÍA
        # ====================================================

        if not encontrada:

            nuevas_lineas.append(
                f'GEMINI_API_KEY={api_key}\n'
            )

        # ====================================================
        # ESCRIBIR .ENV
        # ====================================================

        with open(
            _ENV_FILE,
            'w',
            encoding='utf-8'
        ) as archivo:

            archivo.writelines(
                nuevas_lineas
            )

        # ====================================================
        # ACTUALIZAR ENTORNO
        # ====================================================

        os.environ[
            'GEMINI_API_KEY'
        ] = api_key

        return True

    except (
        OSError,
        UnicodeError
    ):

        return False


# ============================================================
# ELIMINAR API KEY
# ============================================================

def _eliminar_api_key():
    """
    Elimina GEMINI_API_KEY del archivo .env y del entorno.

    Retorna:
        bool: True si la operación fue exitosa.
    """

    try:

        # ====================================================
        # LEER .ENV
        # ====================================================

        lineas = []

        if os.path.exists(
            _ENV_FILE
        ):

            with open(
                _ENV_FILE,
                'r',
                encoding='utf-8'
            ) as archivo:

                lineas = archivo.readlines()

        # ====================================================
        # ELIMINAR VARIABLE
        # ====================================================

        nuevas_lineas = []

        for linea in lineas:

            if linea.strip().startswith(
                'GEMINI_API_KEY='
            ):

                continue

            nuevas_lineas.append(
                linea
            )

        # ====================================================
        # ESCRIBIR .ENV
        # ====================================================

        with open(
            _ENV_FILE,
            'w',
            encoding='utf-8'
        ) as archivo:

            archivo.writelines(
                nuevas_lineas
            )

        # ====================================================
        # ELIMINAR DEL ENTORNO
        # ====================================================

        os.environ.pop(
            'GEMINI_API_KEY',
            None
        )

        return True

    except (
        OSError,
        UnicodeError
    ):

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
        Guarda la API Key proporcionada.
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
                'API Key de Gemini guardada correctamente.',
                'success'
            )

        else:

            flash(
                (
                    'No fue posible guardar la API Key. '
                    'Verifique los permisos del archivo .env.'
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
    Elimina la API Key de Gemini.
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
        bool: True si existe una API Key.
    """

    return bool(
        _obtener_api_key()
    )