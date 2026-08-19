"""
Servicio principal de carga masiva mensual.

Este módulo funciona como ORQUESTADOR.

No debe contener:
- rutas Flask,
- lógica SSE,
- generación de plantillas,
- control de archivos físicos,
- rate limit de Gemini.

Esas responsabilidades están delegadas
a servicios especializados.
"""

from models import db

from app.services.excel_service import (
    leer_carga_masiva
)

from app.services.evidencia_service import (
    procesar_evidencia
)

from app.services.reporte_service import (
    obtener_o_crear_reporte
)

from app.services.contrato_service import (
    obtener_obligacion
)

from app.services.gemini_service import (
    GeminiService
)

from app.services.archivo_service import (
    limpiar_archivos
)


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_carga_masiva(
    contrato,
    mes,
    anio,
    excel_path,
    imagenes,
    api_key=None,
    actualizar_progreso=None,
    job_id=None
):
    """
    Ejecuta el procesamiento completo de una carga masiva.

    Esta función coordina los diferentes servicios.

    Args:
        contrato:
            Contrato sobre el que se realiza la carga.

        mes:
            Mes del reporte.

        anio:
            Año del reporte.

        excel_path:
            Ruta del Excel.

        imagenes:
            Diccionario nombre -> ruta temporal.

        api_key:
            API Key de Gemini.

        actualizar_progreso:
            Callback para informar progreso.

        job_id:
            Identificador del trabajo.

    Returns:
        dict
    """

    errores = []

    exitosos = 0

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    gemini = GeminiService(
        api_key=api_key
    )

    # --------------------------------------------------------
    # LEER EXCEL
    # --------------------------------------------------------

    filas = leer_carga_masiva(
        excel_path
    )

    total = len(
        filas
    )

    if total == 0:

        raise ValueError(
            'El Excel no contiene filas válidas.'
        )

    # --------------------------------------------------------
    # CACHE DE REPORTES
    # --------------------------------------------------------

    reportes_cache = {}

    # --------------------------------------------------------
    # PROCESAR FILAS
    # --------------------------------------------------------

    for indice, fila in enumerate(
        filas,
        start=1
    ):

        porcentaje = int(
            (
                (indice - 1)
                / total
            )
            * 100
        )

        _actualizar(
            actualizar_progreso,
            job_id,
            'procesando',
            porcentaje,
            (
                f'Procesando fila '
                f'{indice}/{total}...'
            )
        )

        try:

            resultado = _procesar_fila(
                contrato=contrato,
                mes=mes,
                anio=anio,
                fila=fila,
                imagenes=imagenes,
                gemini=gemini,
                reportes_cache=reportes_cache,
                actualizar_progreso=(
                    actualizar_progreso
                ),
                job_id=job_id
            )

            if resultado['exitoso']:

                exitosos += 1

            errores.extend(
                resultado['errores']
            )

        except Exception as exc:

            errores.append(
                (
                    f'Fila {indice}: '
                    f'{str(exc)}'
                )
            )

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    db.session.commit()

    return {
        'exitosos': exitosos,
        'errores': errores,
        'mes': mes,
        'anio': anio
    }


# ============================================================
# PROCESAR FILA
# ============================================================

def _procesar_fila(
    contrato,
    mes,
    anio,
    fila,
    imagenes,
    gemini,
    reportes_cache,
    actualizar_progreso,
    job_id
):
    """
    Procesa una fila individual.
    """

    errores = []

    # --------------------------------------------------------
    # DATOS DEL EXCEL
    # --------------------------------------------------------

    numero_obligacion = (
        fila.get(
            'obligacion_numero'
        )
    )

    anuncio = (
        fila.get(
            'anuncio'
        )
        or ''
    ).strip()

    fecha = fila.get(
        'fecha'
    )

    nombre_imagen = (
        fila.get(
            'nombre_imagen'
        )
        or ''
    ).strip()

    # --------------------------------------------------------
    # OBLIGACIÓN
    # --------------------------------------------------------

    obligacion = obtener_obligacion(
        contrato_id=contrato.id,
        numero=numero_obligacion
    )

    if not obligacion:

        return {
            'exitoso': False,
            'errores': [
                (
                    f'Obligación '
                    f'{numero_obligacion} '
                    'no encontrada.'
                )
            ]
        }

    # --------------------------------------------------------
    # REPORTE
    # --------------------------------------------------------

    cache_key = (
        obligacion.id,
        mes,
        anio
    )

    if cache_key not in reportes_cache:

        reportes_cache[
            cache_key
        ] = obtener_o_crear_reporte(
            obligacion=obligacion,
            mes=mes,
            anio=anio
        )

    reporte = reportes_cache[
        cache_key
    ]

    # --------------------------------------------------------
    # EVIDENCIA
    # --------------------------------------------------------

    try:

        evidencia = procesar_evidencia(
            reporte=reporte,
            obligacion=obligacion,
            anuncio=anuncio,
            fecha=fecha,
            nombre_imagen=nombre_imagen,
            imagenes=imagenes,
            gemini=gemini,
            actualizar_progreso=(
                actualizar_progreso
            ),
            job_id=job_id
        )

    except Exception as exc:

        return {
            'exitoso': False,
            'errores': [
                (
                    f'Error procesando '
                    f'obligación '
                    f'{numero_obligacion}: '
                    f'{str(exc)}'
                )
            ]
        }

    # --------------------------------------------------------
    # ERRORES DE LA EVIDENCIA
    # --------------------------------------------------------

    if evidencia.get(
        'errores'
    ):

        errores.extend(
            evidencia[
                'errores'
            ]
        )

    return {
        'exitoso': evidencia.get(
            'creada',
            False
        ),
        'errores': errores
    }


# ============================================================
# PROGRESO
# ============================================================

def _actualizar(
    callback,
    job_id,
    estado,
    porcentaje,
    mensaje
):
    """
    Ejecuta el callback de progreso si existe.
    """

    if not callback:
        return

    callback(
        job_id,
        estado,
        porcentaje,
        mensaje
    )
