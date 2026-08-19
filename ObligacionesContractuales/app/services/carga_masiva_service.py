"""
Servicio para procesamiento de cargas masivas mensuales.

Responsabilidades:
- Leer y validar el Excel.
- Procesar las filas de obligaciones.
- Crear o reutilizar reportes mensuales.
- Procesar las imágenes.
- Analizar imágenes con Gemini.
- Crear evidencias.
- Actualizar el progreso del proceso.
- Limpiar archivos temporales.

Este módulo contiene lógica de negocio y no define rutas Flask.
"""

import os
import calendar
import time
import threading

from datetime import datetime, date

from flask import current_app

from werkzeug.utils import secure_filename

from openpyxl import load_workbook

from models import (
    db,
    Obligacion,
    ReporteMensual,
    Evidencia
)

from vision_analyzer import analizar_imagen


# ============================================================
# RATE LIMITER GEMINI
# ============================================================

_gemini_last_call = 0.0

_gemini_lock = threading.Lock()

# Aproximadamente 15 solicitudes por minuto.
# Se deja margen de seguridad.
GEMINI_MIN_INTERVAL = 4.1


def esperar_rate_limit_gemini():
    """
    Espera el tiempo necesario entre llamadas a Gemini.
    """

    global _gemini_last_call

    with _gemini_lock:

        ahora = time.time()

        transcurrido = (
            ahora
            - _gemini_last_call
        )

        if (
            transcurrido
            < GEMINI_MIN_INTERVAL
        ):

            esperar = (
                GEMINI_MIN_INTERVAL
                - transcurrido
            )

            time.sleep(
                esperar
            )

        _gemini_last_call = time.time()


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_carga_masiva_job(
    app,
    job_id,
    contrato,
    obligaciones,
    mes,
    anio,
    excel_path,
    imagenes_subidas,
    api_key,
    actualizar_progreso
):
    """
    Procesa una carga masiva mensual en segundo plano.

    Parámetros:
        app:
            Instancia de Flask.

        job_id:
            Identificador único del proceso.

        contrato:
            Contrato activo.

        obligaciones:
            Obligaciones del contrato.

        mes:
            Mes del reporte.

        anio:
            Año del reporte.

        excel_path:
            Ruta temporal del archivo Excel.

        imagenes_subidas:
            Diccionario:
                nombre_archivo -> ruta_temporal

        api_key:
            API key de Gemini, si está configurada.

        actualizar_progreso:
            Función callback proporcionada por el blueprint
            para actualizar el progreso SSE.
    """

    try:

        with app.app_context():

            # =================================================
            # CARGAR EXCEL
            # =================================================

            wb = load_workbook(
                excel_path
            )

            ws = wb.active

            # =================================================
            # VALIDAR ENCABEZADOS
            # =================================================

            headers = [
                cell.value
                for cell in ws[1]
            ]

            expected = [
                'Obligacion No.',
                'Descripcion Obligacion',
                'Anuncio / Contexto',
                'Fecha de la actividad',
                'Nombre Imagen'
            ]

            if headers[:5] != expected:

                actualizar_progreso(
                    job_id,
                    'error',
                    0,
                    (
                        'Encabezados incorrectos. '
                        f'Esperado: {expected}'
                    )
                )

                return

            # =================================================
            # FILAS VÁLIDAS
            # =================================================

            filas_validas = []

            for idx, row in enumerate(
                ws.iter_rows(
                    min_row=2,
                    values_only=True
                ),
                start=2
            ):

                if (
                    not row[0]
                    and
                    not row[2]
                ):
                    continue

                filas_validas.append(
                    (
                        idx,
                        row
                    )
                )

            total_filas = len(
                filas_validas
            )

            if total_filas == 0:

                actualizar_progreso(
                    job_id,
                    'error',
                    0,
                    'No se encontraron filas válidas en el Excel.'
                )

                return

            # =================================================
            # CONTADORES
            # =================================================

            exitosos = 0

            errores = []

            # =================================================
            # CACHE DE REPORTES
            # =================================================

            reportes_cache = {}

            evidencias_por_reporte = {}

            # =================================================
            # FECHAS DEL MES
            # =================================================

            _, last_day = calendar.monthrange(
                anio,
                mes
            )

            fecha_inicio_mes = date(
                anio,
                mes,
                1
            )

            fecha_fin_mes = date(
                anio,
                mes,
                last_day
            )

            # =================================================
            # IMÁGENES DISPONIBLES
            # =================================================

            imagenes_disponibles = dict(
                imagenes_subidas
            )

            # =================================================
            # PROCESAR FILAS
            # =================================================

            for i, (
                idx,
                row
            ) in enumerate(
                filas_validas
            ):

                porcentaje = int(
                    (
                        i
                        /
                        total_filas
                    )
                    * 100
                )

                actualizar_progreso(
                    job_id,
                    'procesando',
                    porcentaje,
                    (
                        f'Procesando fila '
                        f'{idx} '
                        f'({i + 1}/{total_filas})...'
                    )
                )

                # =================================================
                # DATOS DEL EXCEL
                # =================================================

                obl_num = row[0]

                anuncio = str(
                    row[2] or ''
                ).strip()

                fecha_str = str(
                    row[3] or ''
                ).strip()

                nombre_imagen = str(
                    row[4] or ''
                ).strip()

                # =================================================
                # OBLIGACIÓN
                # =================================================

                try:

                    obl_num_int = int(
                        obl_num
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    errores.append(
                        f'Fila {idx}: '
                        f'Numero de obligacion '
                        f'invalido ({obl_num}).'
                    )

                    continue

                obligacion = (
                    Obligacion.query
                    .filter_by(
                        numero=obl_num_int,
                        contrato_id=contrato.id
                    )
                    .first()
                )

                if not obligacion:

                    errores.append(
                        f'Fila {idx}: '
                        f'Obligacion No. '
                        f'{obl_num_int} '
                        f'no encontrada.'
                    )

                    continue

                # =================================================
                # ANUNCIO
                # =================================================

                if not anuncio:

                    errores.append(
                        f'Fila {idx}: '
                        f'Anuncio vacio.'
                    )

                    continue

                # =================================================
                # FECHA
                # =================================================

                fecha_actividad = (
                    _parsear_fecha(
                        fecha_str
                    )
                )

                if fecha_str and not fecha_actividad:

                    errores.append(
                        f'Fila {idx}: '
                        f'Fecha invalida '
                        f'({fecha_str}).'
                    )

                    continue

                if fecha_actividad:

                    if (
                        fecha_actividad
                        < fecha_inicio_mes
                        or
                        fecha_actividad
                        > fecha_fin_mes
                    ):

                        errores.append(
                            f'Fila {idx}: '
                            f'Fecha {fecha_str} '
                            f'fuera del mes '
                            f'{mes}/{anio}.'
                        )

                        continue

                else:

                    fecha_actividad = date(
                        anio,
                        mes,
                        15
                    )

                # =================================================
                # REPORTE
                # =================================================

                cache_key = (
                    obligacion.id,
                    mes,
                    anio
                )

                if cache_key not in reportes_cache:

                    reporte = (
                        ReporteMensual.query
                        .filter_by(
                            mes=mes,
                            anio=anio,
                            obligacion_id=(
                                obligacion.id
                            )
                        )
                        .first()
                    )

                    if not reporte:

                        reporte = ReporteMensual(
                            mes=mes,
                            anio=anio,
                            fecha_inicio_reporte=(
                                fecha_inicio_mes
                            ),
                            fecha_fin_reporte=(
                                fecha_fin_mes
                            ),
                            obligacion_id=(
                                obligacion.id
                            )
                        )

                        db.session.add(
                            reporte
                        )

                        db.session.commit()

                    reportes_cache[
                        cache_key
                    ] = reporte

                    ultima = (
                        Evidencia.query
                        .filter_by(
                            reporte_id=reporte.id
                        )
                        .order_by(
                            Evidencia
                            .numero_actividad
                            .desc()
                        )
                        .first()
                    )

                    evidencias_por_reporte[
                        reporte.id
                    ] = (
                        ultima.numero_actividad
                        if ultima
                        else 0
                    )

                else:

                    reporte = reportes_cache[
                        cache_key
                    ]

                # =================================================
                # IMAGEN
                # =================================================

                imagen_path = ''

                if nombre_imagen:

                    actualizar_progreso(
                        job_id,
                        'procesando',
                        porcentaje,
                        (
                            f'Fila {idx}: '
                            f'Buscando imagen '
                            f'"{nombre_imagen}"...'
                        )
                    )

                    tmp_src = None

                    if (
                        nombre_imagen
                        in imagenes_disponibles
                    ):

                        tmp_src = (
                            imagenes_disponibles.pop(
                                nombre_imagen
                            )
                        )

                    else:

                        safe_name = (
                            secure_filename(
                                nombre_imagen
                            )
                        )

                        if (
                            safe_name
                            in imagenes_disponibles
                        ):

                            tmp_src = (
                                imagenes_disponibles.pop(
                                    safe_name
                                )
                            )

                    if tmp_src:

                        final_name = secure_filename(
                            (
                                f'evidencia_'
                                f'{reporte.id}_'
                                f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_'
                                f'{nombre_imagen}'
                            )
                        )

                        final_path = os.path.join(
                            current_app.config[
                                'UPLOAD_FOLDER'
                            ],
                            final_name
                        )

                        os.rename(
                            tmp_src,
                            final_path
                        )

                        imagen_path = (
                            final_path
                        )

                    else:

                        errores.append(
                            f'Fila {idx}: '
                            f'Imagen "{nombre_imagen}" '
                            f'no encontrada.'
                        )

                # =================================================
                # NÚMERO DE ACTIVIDAD
                # =================================================

                evidencias_por_reporte[
                    reporte.id
                ] += 1

                numero_actividad = (
                    evidencias_por_reporte[
                        reporte.id
                    ]
                )

                # =================================================
                # CREAR EVIDENCIA
                # =================================================

                evidencia = Evidencia(
                    numero_actividad=(
                        numero_actividad
                    ),
                    imagen_path=(
                        imagen_path
                    ),
                    anuncio_usuario=(
                        anuncio
                    ),
                    descripcion_visual_ia=None,
                    descripcion_actividad='',
                    fecha_actividad=(
                        fecha_actividad
                    ),
                    reporte_id=(
                        reporte.id
                    )
                )

                # =================================================
                # GEMINI
                # =================================================

                if (
                    imagen_path
                    and
                    api_key
                ):

                    actualizar_progreso(
                        job_id,
                        'procesando',
                        porcentaje,
                        (
                            f'Fila {idx}: '
                            f'Analizando con Gemini...'
                        )
                    )

                    esperar_rate_limit_gemini()

                    try:

                        descripcion_visual = (
                            analizar_imagen(
                                imagen_path,
                                api_key
                            )
                        )

                        if descripcion_visual:

                            evidencia.descripcion_visual_ia = (
                                descripcion_visual
                            )

                    except Exception as exc:

                        print(
                            '[CargaMasiva] '
                            f'Error IA fila {idx}: '
                            f'{exc}'
                        )

                        errores.append(
                            f'Fila {idx}: '
                            f'Error al analizar imagen '
                            f'con IA '
                            f'({str(exc)[:60]}).'
                        )

                # =================================================
                # DESCRIPCIÓN AUTOMÁTICA
                # =================================================

                evidencia.descripcion_actividad = (
                    evidencia
                    .generar_descripcion_automatica(
                        obligacion
                    )
                )

                # =================================================
                # AGREGAR
                # =================================================

                db.session.add(
                    evidencia
                )

                exitosos += 1

            # =================================================
            # COMMIT FINAL
            # =================================================

            db.session.commit()

            # =================================================
            # LIMPIAR IMÁGENES
            # =================================================

            _limpiar_archivos_temporales(
                imagenes_disponibles.values()
            )

            # =================================================
            # LIMPIAR EXCEL
            # =================================================

            _limpiar_archivo(
                excel_path
            )

            # =================================================
            # COMPLETADO
            # =================================================

            actualizar_progreso(
                job_id,
                'completado',
                100,
                (
                    f'Proceso finalizado. '
                    f'{exitosos} evidencias cargadas.'
                ),
                resultado={
                    'exitosos': exitosos,
                    'mes': mes,
                    'anio': anio
                },
                errores=errores
            )

    except Exception as exc:

        import traceback

        traceback.print_exc()

        actualizar_progreso(
            job_id,
            'error',
            0,
            (
                'Error inesperado: '
                f'{str(exc)}'
            )
        )


# ============================================================
# FECHAS
# ============================================================

def _parsear_fecha(fecha_str):
    """
    Convierte una fecha del Excel a date.

    Formatos soportados:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - DD-MM-YYYY
    """

    if not fecha_str:
        return None

    formatos = (
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y'
    )

    for formato in formatos:

        try:

            return datetime.strptime(
                fecha_str,
                formato
            ).date()

        except ValueError:

            continue

    return None


# ============================================================
# LIMPIEZA DE ARCHIVOS
# ============================================================

def _limpiar_archivo(
    archivo_path
):
    """
    Elimina un archivo temporal.
    """

    try:

        if (
            archivo_path
            and
            os.path.exists(
                archivo_path
            )
        ):

            os.remove(
                archivo_path
            )

    except Exception:

        pass


def _limpiar_archivos_temporales(
    archivos
):
    """
    Elimina archivos temporales
    que no fueron utilizados.
    """

    for archivo_path in archivos:

        _limpiar_archivo(
            archivo_path
        )