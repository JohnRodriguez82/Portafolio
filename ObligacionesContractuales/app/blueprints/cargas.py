"""
Blueprint de cargas masivas.

Responsabilidades:
- Carga masiva de evidencias desde Excel.
- Carga masiva de evidencias por mes.
- Procesamiento en segundo plano.
- Progreso mediante Server-Sent Events (SSE).
- Rate limiter para Gemini.
- Generación de plantilla Excel por reporte.
- Generación de plantilla Excel para carga masiva mensual.
"""

import os
import io
import calendar
import threading
import time
import uuid
import json

from datetime import datetime, date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    Response,
    jsonify,
    current_app
)

from flask_login import (
    login_required,
    current_user
)

from werkzeug.utils import secure_filename

from openpyxl import load_workbook

from models import (
    db,
    Contrato,
    Obligacion,
    ReporteMensual,
    Evidencia
)

from vision_analyzer import (
    analizar_imagen
)

from app.blueprints.configuracion import (
    _obtener_api_key
)


# ============================================================
# BLUEPRINT
# ============================================================

cargas_bp = Blueprint(
    'cargas',
    __name__
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg',
    'gif',
    'bmp',
    'webp'
}


def allowed_file(filename):
    """
    Verifica si un archivo tiene una extensión de imagen
    permitida.
    """

    return (
        '.'
        in filename
        and
        filename.rsplit(
            '.',
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# GENERAR MESES DEL CONTRATO
# ============================================================

def generar_meses_contrato(
    fecha_inicio,
    fecha_fin
):
    """
    Genera los meses comprendidos entre las fechas
    de inicio y fin del contrato.
    """

    meses = []

    current = date(
        fecha_inicio.year,
        fecha_inicio.month,
        1
    )

    end = date(
        fecha_fin.year,
        fecha_fin.month,
        1
    )

    nombres_meses = [
        '',
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre'
    ]

    while current <= end:

        meses.append(
            (
                current.month,
                current.year,
                nombres_meses[
                    current.month
                ]
            )
        )

        if current.month == 12:

            current = date(
                current.year + 1,
                1,
                1
            )

        else:

            current = date(
                current.year,
                current.month + 1,
                1
            )

    return meses


# ============================================================
# ESTADO GLOBAL DE JOBS
# ============================================================

jobs_lock = threading.Lock()

jobs_progreso = {}


# ============================================================
# RATE LIMITER GEMINI
# ============================================================

_gemini_last_call = 0.0

_gemini_lock = threading.Lock()

# Aproximadamente 15 solicitudes por minuto.
# Se deja margen de seguridad.
GEMINI_MIN_INTERVAL = 4.1


def _esperar_rate_limit_gemini():
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
# ACTUALIZAR JOB
# ============================================================

def _actualizar_job(
    job_id,
    estado,
    porcentaje,
    mensaje,
    resultado=None,
    errores=None
):
    """
    Actualiza de manera thread-safe el estado de un
    proceso de carga masiva.
    """

    with jobs_lock:

        if job_id not in jobs_progreso:

            jobs_progreso[
                job_id
            ] = {}

        jobs_progreso[
            job_id
        ].update(
            {
                'estado': estado,
                'porcentaje': porcentaje,
                'mensaje': mensaje,
                'timestamp': time.time()
            }
        )

        if resultado is not None:

            jobs_progreso[
                job_id
            ]['resultado'] = resultado

        if errores is not None:

            jobs_progreso[
                job_id
            ]['errores'] = errores


# ============================================================
# PROCESAMIENTO DE CARGA MASIVA
# ============================================================

def _procesar_carga_masiva_job(
    job_id,
    contrato,
    obligaciones,
    mes,
    anio,
    excel_path,
    imagenes_subidas,
    api_key
):
    """
    Procesa la carga masiva en segundo plano.

    El proceso:

    1. Lee Excel.
    2. Valida encabezados.
    3. Busca obligaciones.
    4. Valida fechas.
    5. Crea o reutiliza reportes.
    6. Busca imágenes.
    7. Analiza imágenes con Gemini.
    8. Crea evidencias.
    9. Guarda los cambios.
    10. Actualiza el progreso SSE.
    """

    try:

        # ----------------------------------------------------
        # IMPORTANTE
        #
        # El thread está fuera de la petición HTTP original.
        # Por eso necesitamos un application context.
        # ----------------------------------------------------

        with current_app.app_context():

            # ------------------------------------------------
            # Cargar Excel
            # ------------------------------------------------

            wb = load_workbook(
                excel_path
            )

            ws = wb.active

            # ------------------------------------------------
            # Validar encabezados
            # ------------------------------------------------

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

                _actualizar_job(
                    job_id,
                    'error',
                    0,
                    (
                        'Encabezados incorrectos. '
                        f'Esperado: {expected}'
                    )
                )

                return

            # ------------------------------------------------
            # Filas válidas
            # ------------------------------------------------

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

                _actualizar_job(
                    job_id,
                    'error',
                    0,
                    'No se encontraron filas válidas en el Excel.'
                )

                return

            # ------------------------------------------------
            # Contadores
            # ------------------------------------------------

            exitosos = 0

            errores = []

            # ------------------------------------------------
            # Cache de reportes
            # ------------------------------------------------

            reportes_cache = {}

            # ------------------------------------------------
            # Contador de evidencias por reporte
            # ------------------------------------------------

            evidencias_por_reporte = {}

            # ------------------------------------------------
            # Fechas del mes
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Copia del diccionario
            # ------------------------------------------------

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

                _actualizar_job(
                    job_id,
                    'procesando',
                    porcentaje,
                    (
                        f'Procesando fila '
                        f'{idx} '
                        f'({i + 1}/{total_filas})...'
                    )
                )

                # ------------------------------------------------
                # Valores del Excel
                # ------------------------------------------------

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

                fecha_actividad = None

                if fecha_str:

                    formatos = (
                        '%Y-%m-%d',
                        '%d/%m/%Y',
                        '%d-%m-%Y'
                    )

                    for fmt in formatos:

                        try:

                            fecha_actividad = (
                                datetime.strptime(
                                    fecha_str,
                                    fmt
                                ).date()
                            )

                            break

                        except ValueError:

                            continue

                    if fecha_actividad is None:

                        errores.append(
                            f'Fila {idx}: '
                            f'Fecha invalida '
                            f'({fecha_str}).'
                        )

                        continue

                    # ------------------------------------------------
                    # Fecha debe pertenecer al mes
                    # ------------------------------------------------

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

                    # ------------------------------------------------
                    # Fecha por defecto
                    # ------------------------------------------------

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
                            obligacion_id=obligacion.id
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

                    # --------------------------------------------
                    # Última actividad existente
                    # --------------------------------------------

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

                    _actualizar_job(
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

                    # --------------------------------------------
                    # Coincidencia exacta
                    # --------------------------------------------

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

                        # ----------------------------------------
                        # Coincidencia con nombre seguro
                        # ----------------------------------------

                        safe_name = secure_filename(
                            nombre_imagen
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

                    # --------------------------------------------
                    # Mover imagen
                    # --------------------------------------------

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
                # ANALIZAR IMAGEN CON GEMINI
                # =================================================

                if (
                    imagen_path
                    and
                    api_key
                ):

                    _actualizar_job(
                        job_id,
                        'procesando',
                        porcentaje,
                        (
                            f'Fila {idx}: '
                            f'Analizando con Gemini '
                            f'(esperando rate limit)...'
                        )
                    )

                    _esperar_rate_limit_gemini()

                    _actualizar_job(
                        job_id,
                        'procesando',
                        porcentaje,
                        (
                            f'Fila {idx}: '
                            f'Analizando imagen con IA...'
                        )
                    )

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

                    except Exception as e:

                        print(
                            '[CargaMasiva] '
                            f'Error IA fila {idx}: '
                            f'{e}'
                        )

                        errores.append(
                            f'Fila {idx}: '
                            f'Error al analizar imagen '
                            f'con IA '
                            f'({str(e)[:60]}).'
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
            # LIMPIAR IMÁGENES TEMPORALES
            # =================================================

            for tmp_path in (
                imagenes_disponibles.values()
            ):

                try:

                    if os.path.exists(
                        tmp_path
                    ):

                        os.remove(
                            tmp_path
                        )

                except Exception:

                    pass

            # =================================================
            # LIMPIAR EXCEL TEMPORAL
            # =================================================

            try:

                if os.path.exists(
                    excel_path
                ):

                    os.remove(
                        excel_path
                    )

            except Exception:

                pass

            # =================================================
            # JOB COMPLETADO
            # =================================================

            _actualizar_job(
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

    except Exception as e:

        import traceback

        traceback.print_exc()

        _actualizar_job(
            job_id,
            'error',
            0,
            (
                'Error inesperado: '
                f'{str(e)}'
            )
        )


# ============================================================
# CARGA MASIVA PARA UN REPORTE
# ============================================================

@cargas_bp.route(
    '/reporte/<int:id>/carga-masiva',
    methods=['GET', 'POST']
)
@login_required
def carga_masiva_evidencias(id):
    """
    Carga masiva de actividades mediante Excel
    para un reporte específico.
    """

    reporte = (
        ReporteMensual.query
        .get_or_404(id)
    )

    obligacion = (
        reporte.obligacion
    )

    contrato = (
        Contrato.query
        .get(
            obligacion.contrato_id
        )
    )

    # --------------------------------------------------------
    # Seguridad
    # --------------------------------------------------------

    if (
        not contrato
        or
        contrato.user_id != current_user.id
    ):

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # --------------------------------------------------------
    # Contrato cerrado
    # --------------------------------------------------------

    if contrato.etapa == 'Reporte Cerrado':

        flash(
            'Este contrato esta finalizado '
            '(Reporte Cerrado). '
            'No se pueden agregar mas evidencias.',
            'warning'
        )

        return redirect(
            url_for(
                'reportes.ver_reporte',
                id=id
            )
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == 'POST':

        # ----------------------------------------------------
        # Excel
        # ----------------------------------------------------

        if 'archivo_excel' not in request.files:

            flash(
                'No se selecciono el archivo Excel.',
                'danger'
            )

            return redirect(
                url_for(
                    'cargas.carga_masiva_evidencias',
                    id=id
                )
            )

        archivo_excel = request.files[
            'archivo_excel'
        ]

        if archivo_excel.filename == '':

            flash(
                'No se selecciono archivo Excel.',
                'danger'
            )

            return redirect(
                url_for(
                    'cargas.carga_masiva_evidencias',
                    id=id
                )
            )

        # ----------------------------------------------------
        # Validar extensión
        # ----------------------------------------------------

        if not archivo_excel.filename.lower().endswith(
            (
                '.xlsx',
                '.xls'
            )
        ):

            flash(
                'El archivo debe ser Excel '
                '(.xlsx o .xls).',
                'danger'
            )

            return redirect(
                url_for(
                    'cargas.carga_masiva_evidencias',
                    id=id
                )
            )

        # ====================================================
        # LEER EXCEL
        # ====================================================

        try:

            wb = load_workbook(
                archivo_excel
            )

            ws = wb.active

            headers = [
                cell.value
                for cell in ws[1]
            ]

            expected = [
                'Anuncio / Contexto',
                'Fecha de la actividad'
            ]

            if headers[:2] != expected:

                flash(
                    (
                        'Encabezados incorrectos. '
                        f'Se esperaba: {expected}. '
                        f'Encontrado: {headers[:2]}'
                    ),
                    'danger'
                )

                return redirect(
                    url_for(
                        'cargas.carga_masiva_evidencias',
                        id=id
                    )
                )

            api_key = _obtener_api_key()

            exitosos = 0

            errores = []

            # =================================================
            # FILAS
            # =================================================

            for idx, row in enumerate(
                ws.iter_rows(
                    min_row=2,
                    values_only=True
                ),
                start=2
            ):

                anuncio = str(
                    row[0] or ''
                ).strip()

                fecha_str = str(
                    row[1] or ''
                ).strip()

                if not anuncio:

                    errores.append(
                        f'Fila {idx}: '
                        f'Anuncio vacio.'
                    )

                    continue

                if not fecha_str:

                    errores.append(
                        f'Fila {idx}: '
                        f'Fecha vacia.'
                    )

                    continue

                # ------------------------------------------------
                # Fecha
                # ------------------------------------------------

                try:

                    fecha_actividad = (
                        datetime.strptime(
                            fecha_str,
                            '%Y-%m-%d'
                        ).date()
                    )

                except ValueError:

                    try:

                        fecha_actividad = (
                            datetime.strptime(
                                fecha_str,
                                '%d/%m/%Y'
                            ).date()
                        )

                    except ValueError:

                        errores.append(
                            f'Fila {idx}: '
                            f'Fecha invalida '
                            f'({fecha_str}). '
                            f'Use YYYY-MM-DD '
                            f'o DD/MM/YYYY.'
                        )

                        continue

                # ------------------------------------------------
                # Validar período
                # ------------------------------------------------

                if (
                    fecha_actividad
                    < reporte.fecha_inicio_reporte
                    or
                    fecha_actividad
                    > reporte.fecha_fin_reporte
                ):

                    errores.append(
                        f'Fila {idx}: '
                        f'Fecha {fecha_str} '
                        f'fuera del periodo del reporte.'
                    )

                    continue

                # ------------------------------------------------
                # Número actividad
                # ------------------------------------------------

                ultima_evidencia = (
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

                numero_actividad = (
                    ultima_evidencia
                    .numero_actividad + 1
                    if ultima_evidencia
                    else 1
                )

                # ------------------------------------------------
                # Crear evidencia
                # ------------------------------------------------

                evidencia = Evidencia(
                    numero_actividad=(
                        numero_actividad
                    ),

                    imagen_path='',

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

                # ------------------------------------------------
                # Generar descripción
                # ------------------------------------------------

                evidencia.descripcion_actividad = (
                    evidencia
                    .generar_descripcion_automatica(
                        obligacion
                    )
                )

                db.session.add(
                    evidencia
                )

                exitosos += 1

            db.session.commit()

            # ----------------------------------------------------
            # Resultado
            # ----------------------------------------------------

            if exitosos:

                flash(
                    f'{exitosos} actividades '
                    f'cargadas exitosamente.',
                    'success'
                )

            if errores:

                flash(
                    'Se encontraron errores: '
                    +
                    ' | '.join(
                        errores[:5]
                    ),
                    'warning'
                )

            return redirect(
                url_for(
                    'reportes.ver_reporte',
                    id=id
                )
            )

        except Exception as e:

            flash(
                f'Error procesando Excel: {str(e)}',
                'danger'
            )

            return redirect(
                url_for(
                    'cargas.carga_masiva_evidencias',
                    id=id
                )
            )

    # ========================================================
    # GET
    # ========================================================

    return render_template(
        'carga_masiva.html',

        reporte=reporte,

        obligacion=obligacion,

        contrato=contrato
    )


# ============================================================
# GENERAR PLANTILLA MASIVA POR MES
# ============================================================

def generar_plantilla_masiva(
    contrato,
    obligaciones,
    mes,
    anio
):
    """
    Genera una plantilla Excel para cargar evidencias
    de todas las obligaciones de un mes.
    """

    from openpyxl import Workbook

    from openpyxl.styles import (
        Font,
        PatternFill,
        Alignment,
        Border,
        Side
    )

    # --------------------------------------------------------
    # Crear workbook
    # --------------------------------------------------------

    wb = Workbook()

    ws = wb.active

    ws.title = (
        f'Carga_{mes:02d}_{anio}'
    )

    # --------------------------------------------------------
    # Encabezados
    # --------------------------------------------------------

    headers = [
        'Obligacion No.',
        'Descripcion Obligacion',
        'Anuncio / Contexto',
        'Fecha de la actividad',
        'Nombre Imagen'
    ]

    ws.append(
        headers
    )

    # --------------------------------------------------------
    # Estilos
    # --------------------------------------------------------

    header_font = Font(
        bold=True,
        color='FFFFFF',
        size=11
    )

    header_fill = PatternFill(
        start_color='2c3e50',
        end_color='2c3e50',
        fill_type='solid'
    )

    header_align = Alignment(
        horizontal='center',
        vertical='center',
        wrap_text=True
    )

    thin_border = Border(
        left=Side(
            style='thin'
        ),
        right=Side(
            style='thin'
        ),
        top=Side(
            style='thin'
        ),
        bottom=Side(
            style='thin'
        )
    )

    for cell in ws[1]:

        cell.font = (
            header_font
        )

        cell.fill = (
            header_fill
        )

        cell.alignment = (
            header_align
        )

        cell.border = (
            thin_border
        )

    # --------------------------------------------------------
    # Obligaciones
    # --------------------------------------------------------

    for obligacion in obligaciones:

        ws.append(
            [
                obligacion.numero,

                obligacion.descripcion,

                '',

                f'{anio}-{mes:02d}-15',

                ''
            ]
        )

    # --------------------------------------------------------
    # Anchos
    # --------------------------------------------------------

    ws.column_dimensions[
        'A'
    ].width = 16

    ws.column_dimensions[
        'B'
    ].width = 55

    ws.column_dimensions[
        'C'
    ].width = 55

    ws.column_dimensions[
        'D'
    ].width = 22

    ws.column_dimensions[
        'E'
    ].width = 28

    ws.freeze_panes = 'A2'

    # ========================================================
    # HOJA DE INSTRUCCIONES
    # ========================================================

    ws_instr = wb.create_sheet(
        'Instrucciones'
    )

    instrucciones = [

        [
            'INSTRUCCIONES DE CARGA MASIVA POR MES'
        ],

        [''],

        [
            '1. NO modifique los encabezados '
            'de columna (fila 1).'
        ],

        [
            '2. NO modifique las columnas A y B '
            '(Obligacion No. y Descripcion).'
        ],

        [
            '3. En la columna C escriba el anuncio '
            'o contexto de la actividad '
            '(solo para el sistema).'
        ],

        [
            '4. En la columna D indique la fecha '
            'en formato YYYY-MM-DD o DD/MM/YYYY.'
        ],

        [
            '5. En la columna E escriba el nombre '
            'EXACTO del archivo de imagen, '
            'incluyendo extension '
            '(ej: evidencia1.jpg).'
        ],

        [
            '6. Puede INSERTAR mas filas para la '
            'misma obligacion si tiene multiples evidencias.'
        ],

        [
            '7. Puede ELIMINAR las filas de obligaciones '
            'que no tengan evidencias este mes.'
        ],

        [
            '8. Las imagenes deben cargarse JUNTO '
            'con el Excel en el formulario web '
            '(campo de archivos multiples).'
        ],

        [''],

        [
            'REGLAS IMPORTANTES:'
        ],

        [
            '- La fecha debe pertenecer al mes '
            'y año seleccionados.'
        ],

        [
            '- El nombre de imagen en el Excel '
            'debe coincidir EXACTAMENTE con el archivo subido.'
        ],

        [
            '- Si no adjunta imagen, deje la columna E vacia; '
            'se creara la actividad sin evidencia visual.'
        ],

        [
            '- El sistema creara automaticamente '
            'los reportes mensuales por obligacion '
            'si no existen.'
        ],

        [
            '- Si tiene API key de Gemini configurada, '
            'analizara automaticamente cada imagen.'
        ],

        [
            '- NOTA: El tier gratuito de Gemini '
            'permite 15 imagenes/minuto. '
            'Si sube mas, el sistema las procesara '
            'automaticamente con pausas.'
        ]
    ]

    for row in instrucciones:

        ws_instr.append(
            row
        )

    ws_instr.column_dimensions[
        'A'
    ].width = 100

    # --------------------------------------------------------
    # Memoria
    # --------------------------------------------------------

    output = io.BytesIO()

    wb.save(
        output
    )

    output.seek(0)

    # --------------------------------------------------------
    # Nombre
    # --------------------------------------------------------

    filename = (
        f'Plantilla_CargaMasiva_'
        f'{mes:02d}_{anio}_'
        f'{contrato.contratista or "Contrato"}.xlsx'
    )

    return send_file(
        output,

        mimetype=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),

        as_attachment=True,

        download_name=filename
    )


# ============================================================
# CARGA MASIVA POR MES
# ============================================================

@cargas_bp.route(
    '/carga-masiva-mes',
    methods=['GET', 'POST']
)
@login_required
def carga_masiva_mes():
    """
    Carga masiva de evidencias para TODAS las obligaciones
    del contrato activo en un mes determinado.
    """

    # --------------------------------------------------------
    # Contrato activo
    # --------------------------------------------------------

    contrato = (
        Contrato.query
        .filter_by(
            activo=True,
            user_id=current_user.id
        )
        .first()
    )

    if not contrato:

        flash(
            'No hay contrato activo configurado.',
            'danger'
        )

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # --------------------------------------------------------
    # Contrato cerrado
    # --------------------------------------------------------

    if contrato.etapa == 'Reporte Cerrado':

        flash(
            'El contrato activo esta finalizado '
            '(Reporte Cerrado). '
            'No se pueden agregar mas evidencias.',
            'warning'
        )

        return redirect(
            url_for(
                'reportes.reportes'
            )
        )

    # --------------------------------------------------------
    # Obligaciones
    # --------------------------------------------------------

    obligaciones = (
        Obligacion.query
        .filter_by(
            contrato_id=contrato.id
        )
        .order_by(
            Obligacion.numero
        )
        .all()
    )

    # --------------------------------------------------------
    # Meses
    # --------------------------------------------------------

    meses = generar_meses_contrato(
        contrato.fecha_inicio,
        contrato.fecha_fin
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == 'POST':

        action = request.form.get(
            'action'
        )

        # ====================================================
        # DESCARGAR PLANTILLA
        # ====================================================

        if action == 'descargar_plantilla':

            try:

                mes = int(
                    request.form.get(
                        'mes',
                        0
                    )
                )

                anio = int(
                    request.form.get(
                        'anio',
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                flash(
                    'Seleccione mes y año.',
                    'danger'
                )

                return redirect(
                    url_for(
                        'cargas.carga_masiva_mes'
                    )
                )

            if not mes or not anio:

                flash(
                    'Seleccione mes y año.',
                    'danger'
                )

                return redirect(
                    url_for(
                        'cargas.carga_masiva_mes'
                    )
                )

            return generar_plantilla_masiva(
                contrato,
                obligaciones,
                mes,
                anio
            )

        # ====================================================
        # CARGAR MASIVO
        # ====================================================

        elif action == 'cargar_masivo':

            try:

                mes = int(
                    request.form.get(
                        'mes',
                        0
                    )
                )

                anio = int(
                    request.form.get(
                        'anio',
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                return jsonify(
                    {
                        'error':
                        'Seleccione mes y año.'
                    }
                ), 400

            if not mes or not anio:

                return jsonify(
                    {
                        'error':
                        'Seleccione mes y año.'
                    }
                ), 400

            # ------------------------------------------------
            # Validar mes
            # ------------------------------------------------

            if mes < 1 or mes > 12:

                return jsonify(
                    {
                        'error':
                        'El mes seleccionado no es válido.'
                    }
                ), 400

            # ------------------------------------------------
            # Excel
            # ------------------------------------------------

            if (
                'archivo_excel'
                not in request.files
            ):

                return jsonify(
                    {
                        'error':
                        'No se seleccionó '
                        'el archivo Excel.'
                    }
                ), 400

            archivo_excel = request.files[
                'archivo_excel'
            ]

            if archivo_excel.filename == '':

                return jsonify(
                    {
                        'error':
                        'No se seleccionó '
                        'archivo Excel.'
                    }
                ), 400

            # ------------------------------------------------
            # Extensión Excel
            # ------------------------------------------------

            if not archivo_excel.filename.lower().endswith(
                (
                    '.xlsx',
                    '.xls'
                )
            ):

                return jsonify(
                    {
                        'error':
                        'El archivo debe ser Excel '
                        '(.xlsx o .xls).'
                    }
                ), 400

            # =================================================
            # CREAR JOB
            # =================================================

            job_id = str(
                uuid.uuid4()
            )

            tmp_ts = (
                datetime.now()
                .strftime(
                    '%Y%m%d_%H%M%S'
                )
            )

            excel_tmp_name = secure_filename(
                (
                    f'tmp_excel_'
                    f'{job_id}_'
                    f'{tmp_ts}.xlsx'
                )
            )

            excel_tmp_path = os.path.join(
                current_app.config[
                    'UPLOAD_FOLDER'
                ],
                excel_tmp_name
            )

            archivo_excel.save(
                excel_tmp_path
            )

            # =================================================
            # IMÁGENES TEMPORALES
            # =================================================

            imagenes_subidas = {}

            imagenes_files = request.files.getlist(
                'imagenes'
            )

            for img_file in imagenes_files:

                if (
                    img_file
                    and
                    img_file.filename
                    and
                    allowed_file(
                        img_file.filename
                    )
                ):

                    tmp_name = secure_filename(
                        (
                            f'tmp_'
                            f'{job_id}_'
                            f'{img_file.filename}'
                        )
                    )

                    tmp_path = os.path.join(
                        current_app.config[
                            'UPLOAD_FOLDER'
                        ],
                        tmp_name
                    )

                    img_file.save(
                        tmp_path
                    )

                    imagenes_subidas[
                        img_file.filename
                    ] = tmp_path

                    imagenes_subidas[
                        secure_filename(
                            img_file.filename
                        )
                    ] = tmp_path

            # =================================================
            # API KEY
            # =================================================

            api_key = _obtener_api_key()

            # =================================================
            # INICIALIZAR JOB
            # =================================================

            _actualizar_job(
                job_id,
                'iniciado',
                0,
                'Iniciando procesamiento...'
            )

            # =================================================
            # THREAD
            # =================================================

            thread = threading.Thread(
                target=(
                    _procesar_carga_masiva_job
                ),

                args=(
                    job_id,
                    contrato,
                    obligaciones,
                    mes,
                    anio,
                    excel_tmp_path,
                    imagenes_subidas,
                    api_key
                )
            )

            thread.daemon = True

            thread.start()

            return jsonify(
                {
                    'job_id': job_id,
                    'status': 'started'
                }
            )

    # ========================================================
    # GET
    # ========================================================

    api_key_configurada = bool(
        _obtener_api_key()
    )

    return render_template(
        'carga_masiva_mes.html',

        contrato=contrato,

        obligaciones=obligaciones,

        meses=meses,

        api_key_configurada=(
            api_key_configurada
        )
    )


# ============================================================
# PROGRESO SSE
# ============================================================

@cargas_bp.route(
    '/carga-masiva-mes/progreso/<job_id>'
)
@login_required
def carga_masiva_progreso(job_id):
    """
    Server-Sent Events.

    Envía al navegador el progreso de la carga masiva
    en tiempo real.
    """

    def event_stream():

        ultimo_estado = None

        while True:

            # ------------------------------------------------
            # Leer estado
            # ------------------------------------------------

            with jobs_lock:

                job = jobs_progreso.get(
                    job_id,
                    {}
                )

            estado = job.get(
                'estado',
                'desconocido'
            )

            porcentaje = job.get(
                'porcentaje',
                0
            )

            mensaje = job.get(
                'mensaje',
                'Procesando...'
            )

            errores = job.get(
                'errores',
                []
            )

            resultado = job.get(
                'resultado'
            )

            # ------------------------------------------------
            # Datos SSE
            # ------------------------------------------------

            data = {
                'estado': estado,

                'porcentaje': porcentaje,

                'mensaje': mensaje,

                'errores': errores[:5]
            }

            if resultado:

                data[
                    'resultado'
                ] = resultado

            # ------------------------------------------------
            # Enviar
            # ------------------------------------------------

            yield (
                'data: '
                +
                json.dumps(
                    data
                )
                +
                '\n\n'
            )

            ultimo_estado = (
                estado
            )

            # ------------------------------------------------
            # Finalizado
            # ------------------------------------------------

            if estado in (
                'completado',
                'error'
            ):

                time.sleep(
                    2
                )

                with jobs_lock:

                    jobs_progreso.pop(
                        job_id,
                        None
                    )

                break

            # ------------------------------------------------
            # Esperar
            # ------------------------------------------------

            time.sleep(
                0.5
            )

    return Response(
        event_stream(),
        mimetype='text/event-stream'
    )


# ============================================================
# PLANTILLA EXCEL PARA UN REPORTE
# ============================================================

@cargas_bp.route(
    '/reporte/<int:id>/plantilla-excel'
)
@login_required
def descargar_plantilla_excel(id):
    """
    Descarga una plantilla Excel simple para registrar
    actividades de un reporte específico.
    """

    from openpyxl import Workbook

    from openpyxl.styles import (
        Font,
        PatternFill,
        Alignment
    )

    # --------------------------------------------------------
    # Validar reporte
    # --------------------------------------------------------

    reporte = (
        ReporteMensual.query
        .get_or_404(id)
    )

    obligacion = (
        reporte.obligacion
    )

    contrato = (
        Contrato.query
        .get(
            obligacion.contrato_id
        )
    )

    # --------------------------------------------------------
    # Seguridad
    # --------------------------------------------------------

    if (
        not contrato
        or
        contrato.user_id != current_user.id
    ):

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'inicio.inicio'
            )
        )

    # ========================================================
    # CREAR WORKBOOK
    # ========================================================

    wb = Workbook()

    ws = wb.active

    ws.title = (
        'Carga Masiva'
    )

    # --------------------------------------------------------
    # Encabezados
    # --------------------------------------------------------

    headers = [
        'Anuncio / Contexto',
        'Fecha de la actividad'
    ]

    ws.append(
        headers
    )

    # --------------------------------------------------------
    # Estilos
    # --------------------------------------------------------

    for cell in ws[1]:

        cell.font = Font(
            bold=True,
            color='FFFFFF'
        )

        cell.fill = PatternFill(
            start_color='2c3e50',
            end_color='2c3e50',
            fill_type='solid'
        )

        cell.alignment = Alignment(
            horizontal='center'
        )

    # --------------------------------------------------------
    # Ejemplos
    # --------------------------------------------------------

    ws.append(
        [
            'Presentacion del estado de avance '
            'de proyectos',

            '2026-07-15'
        ]
    )

    ws.append(
        [
            'Revision de solicitudes de ajuste '
            'tecnicos',

            '2026-07-20'
        ]
    )

    ws.append(
        [
            'Elaboracion del plan de trabajo '
            'mensual',

            '2026-07-25'
        ]
    )

    # --------------------------------------------------------
    # Anchos
    # --------------------------------------------------------

    ws.column_dimensions[
        'A'
    ].width = 60

    ws.column_dimensions[
        'B'
    ].width = 25

    # --------------------------------------------------------
    # Memoria
    # --------------------------------------------------------

    output = io.BytesIO()

    wb.save(
        output
    )

    output.seek(0)

    # --------------------------------------------------------
    # Nombre
    # --------------------------------------------------------

    filename = (
        f'Plantilla_Carga_Masiva_{id}.xlsx'
    )

    return send_file(
        output,

        mimetype=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),

        as_attachment=True,

        download_name=filename
    )