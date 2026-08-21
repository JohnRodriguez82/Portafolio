"""
Blueprint de las paginas principales del sistema.

Responsabilidades:
- Pagina de inicio / bienvenida.
- Panel principal del sistema.
- Consulta del contrato activo.
- Consulta paginada de obligaciones.
- Filtros de obligaciones.
- Consulta de reportes existentes.
- Preparacion de informacion para index.html.
"""

from flask import (
    Blueprint,
    render_template,
    request
)

from flask_login import (
    login_required,
    current_user
)

from models import (
    db,
    Contrato,
    Obligacion,
    ReporteMensual,
    Evidencia
)

from app.blueprints.configuracion import (
    _obtener_api_key
)


# ============================================================
# BLUEPRINT
# ============================================================

inicio_bp = Blueprint(
    'inicio',
    __name__
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def generar_meses_contrato(
    fecha_inicio,
    fecha_fin
):
    """
    Genera la lista de meses comprendidos entre
    la fecha de inicio y la fecha de finalizacion
    del contrato.

    Retorna:

        [
            (numero_mes, anio, nombre_mes),
            ...
        ]

    Ejemplo:

        [
            (1, 2026, 'Enero'),
            (2, 2026, 'Febrero'),
            ...
        ]
    """

    from datetime import date

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
# /INICIO
# ============================================================

@inicio_bp.route(
    '/inicio'
)
@login_required
def inicio():
    """
    Pagina de bienvenida del sistema.

    Esta ruta no realiza consultas innecesarias a la base
    de datos porque solamente presenta la pagina de inicio.
    """

    return render_template(
        'inicio.html'
    )


# ============================================================
# /
# ============================================================

@inicio_bp.route(
    '/'
)
@login_required
def index():
    """
    Panel principal del sistema.

    Muestra:

    - Contrato activo.
    - Obligaciones del contrato.
    - Paginacion.
    - Busqueda de obligaciones.
    - Meses del contrato.
    - Numero total de reportes.
    - Estado de API Key de Gemini.
    - Relacion obligacion/mes/reporte.
    """

    # ========================================================
    # VARIABLES INICIALES
    # ========================================================

    contrato = None

    obligaciones = []

    obligaciones_pag = None

    meses = []

    reportes_count = 0

    api_key_configurada = False

    reportes_por_obligacion_mes = {}

    meses_con_reporte = set()
    meses_reportados = 0
    meses_faltantes = 0

    # ========================================================
    # PAGINACION
    # ========================================================

    page = request.args.get(
        'page',
        1,
        type=int
    )

    per_page = request.args.get(
        'per_page',
        10,
        type=int
    )

    # --------------------------------------------------------
    # Proteccion contra valores invalidos
    # --------------------------------------------------------

    if page < 1:
        page = 1

    if per_page not in (
        5,
        10,
        20,
        50,
        100
    ):
        per_page = 10

    # ========================================================
    # BUSQUEDA
    # ========================================================

    search = request.args.get(
        'search',
        '',
        type=str
    ).strip()

    # ========================================================
    # API KEY
    # ========================================================

    api_key_configurada = bool(
        _obtener_api_key()
    )

    # ========================================================
    # CONTRATO ACTIVO
    # ========================================================

    contrato = (
        Contrato.query
        .filter_by(
            activo=True,
            user_id=current_user.id
        )
        .first()
    )

    # ========================================================
    # SI EXISTE CONTRATO
    # ========================================================

    if contrato:

        # ====================================================
        # OBLIGACIONES
        # ====================================================

        query = (
            Obligacion.query
            .filter_by(
                contrato_id=contrato.id
            )
        )

        # ----------------------------------------------------
        # Filtro de busqueda
        # ----------------------------------------------------

        if search:

            query = query.filter(
                db.or_(
                    Obligacion.numero
                    .cast(db.String)
                    .ilike(
                        f'%{search}%'
                    ),

                    Obligacion.descripcion
                    .ilike(
                        f'%{search}%'
                    )
                )
            )

        # ----------------------------------------------------
        # Orden y paginacion
        # ----------------------------------------------------

        obligaciones_pag = (
            query
            .order_by(
                Obligacion.numero
            )
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

        obligaciones = (
            obligaciones_pag.items
        )

        # ====================================================
        # MESES DEL CONTRATO
        # ====================================================

        meses = generar_meses_contrato(
            contrato.fecha_inicio,
            contrato.fecha_fin
        )

        # ====================================================
        # MESES REPORTADOS VS FALTANTES
        # ====================================================

        total_meses_contrato = len(meses)

        obligaciones_ids_todas = [
            obl.id for obl in
            Obligacion.query.filter_by(
                contrato_id=contrato.id
            ).all()
        ]

        meses_completos = 0

        # ----------------------------------------------------
        # Si no hay obligaciones, NO puede haber meses completos
        # ----------------------------------------------------

        if obligaciones_ids_todas:

            for (
                mes_num,
                anio,
                nombre
            ) in meses:

                mes_completo = True

                for obl_id in obligaciones_ids_todas:

                    rep = (
                        ReporteMensual.query
                        .filter_by(
                            mes=mes_num,
                            anio=anio,
                            obligacion_id=obl_id
                        )
                        .first()
                    )

                    if not rep or not rep.evidencias:

                        mes_completo = False

                        break

                if mes_completo:

                    meses_completos += 1

        # Si no hay obligaciones, meses_completos queda en 0

        meses_reportados = meses_completos

        meses_faltantes = (
            total_meses_contrato - meses_reportados
        )

        # ====================================================
        # TOTAL DE REPORTES
        # ====================================================

        reportes_count = (
            ReporteMensual.query
            .join(
                Obligacion
            )
            .filter(
                Obligacion.contrato_id
                == contrato.id
            )
            .count()
        )

        # ====================================================
        # REPORTES DE LAS OBLIGACIONES
        # ====================================================
        #
        # IMPORTANTE:
        #
        # El codigo original hacia:
        #
        #     for obl in obligaciones:
        #         ReporteMensual.query.filter_by(...)
        #
        # Eso genera una consulta adicional por cada
        # obligacion.
        #
        # Aqui hacemos una sola consulta para todas las
        # obligaciones mostradas en la pagina actual.
        # ====================================================

        if obligaciones:

            obligaciones_ids = [
                obl.id
                for obl in obligaciones
            ]

            reportes = (
                ReporteMensual.query
                .filter(
                    ReporteMensual.obligacion_id
                    .in_(
                        obligaciones_ids
                    )
                )
                .all()
            )

            # ------------------------------------------------
            # Construir mapa
            # ------------------------------------------------

            for reporte in reportes:

                obligacion_id = (
                    reporte.obligacion_id
                )

                if (
                    obligacion_id
                    not in reportes_por_obligacion_mes
                ):

                    reportes_por_obligacion_mes[
                        obligacion_id
                    ] = {}

                reportes_por_obligacion_mes[
                    obligacion_id
                ][
                    (
                        reporte.mes,
                        reporte.anio
                    )
                ] = reporte.id

                # --------------------------------------------
                # Meses que tienen al menos un reporte
                # --------------------------------------------

                meses_con_reporte.add(
                    (
                        reporte.mes,
                        reporte.anio
                    )
                )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        'index.html',

        contrato=contrato,

        obligaciones=obligaciones,

        obligaciones_pag=obligaciones_pag,

        meses=meses,

        reportes_count=reportes_count,

        api_key_configurada=(
            api_key_configurada
        ),

        reportes_por_obligacion_mes=(
            reportes_por_obligacion_mes
        ),

        meses_con_reporte=(
            meses_con_reporte
        ),

        meses_reportados=meses_reportados,

        meses_faltantes=meses_faltantes,

        search=search,

        per_page=per_page
    )
