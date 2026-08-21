"""
Blueprint de gestión de contratos y obligaciones.

Responsabilidades:
- Listado de contratos
- Creación de contratos
- Edición de contratos
- Eliminación de contratos
- Activación / desactivación de contratos
- Finalización de contratos
- Validación de obligaciones y evidencias

IMPORTANTE:
Este Blueprint conserva la lógica existente de app.py.
La migración busca cambiar la estructura, no el comportamiento.
"""

from datetime import datetime, date

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
    login_required,
    current_user
)

from models import (
    db,
    Contrato,
    Obligacion,
    ReporteMensual
)


# ============================================================
# BLUEPRINT
# ============================================================

contratos_bp = Blueprint(
    'contratos',
    __name__
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def generar_meses_contrato(fecha_inicio, fecha_fin):
    """
    Genera la lista de meses comprendidos entre la fecha
    de inicio y la fecha de finalización del contrato.

    Retorna:
        [
            (numero_mes, anio, nombre_mes),
            ...
        ]

    Ejemplo:

        [
            (1, 2026, 'Enero'),
            (2, 2026, 'Febrero'),
            (3, 2026, 'Marzo')
        ]
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
                nombres_meses[current.month]
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
# LISTADO Y GESTIÓN DE CONTRATOS
# ============================================================

@contratos_bp.route('/contratos')
@login_required
def contratos():
    """
    Vista de gestión de contratos.

    Muestra:
    - Todos los contratos del usuario.
    - Contrato activo.
    - Obligaciones del contrato activo.
    - Paginación.
    - Búsqueda.
    """

    # --------------------------------------------------------
    # Contratos pertenecientes al usuario actual
    # --------------------------------------------------------

    contratos_list = (
        Contrato.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Contrato.fecha_creacion.desc()
        )
        .all()
    )

    # --------------------------------------------------------
    # Datos preparados para JSON / edición en frontend
    # --------------------------------------------------------

    contratos_datos = []

    for contrato_item in contratos_list:

        contratos_datos.append(
            {
                'id': contrato_item.id,

                'contratista': (
                    contrato_item.contratista
                    or ''
                ),

                'numero_contrato': (
                    contrato_item.numero_contrato
                    or ''
                ),

                'fecha_inicio': (
                    contrato_item.fecha_inicio
                    .strftime('%Y-%m-%d')
                ),

                'fecha_fin': (
                    contrato_item.fecha_fin
                    .strftime('%Y-%m-%d')
                ),

                'activo': contrato_item.activo,

                'etapa': contrato_item.etapa
            }
        )

    # --------------------------------------------------------
    # Obtener contrato activo del usuario
    # --------------------------------------------------------

    contrato = (
        Contrato.query
        .filter_by(
            activo=True,
            user_id=current_user.id
        )
        .first()
    )

    # --------------------------------------------------------
    # Paginación y búsqueda de obligaciones
    # --------------------------------------------------------

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

    search = request.args.get(
        'search',
        '',
        type=str
    ).strip()

    obligaciones = []

    obligaciones_pag = None

    # --------------------------------------------------------
    # Obtener obligaciones del contrato activo
    # --------------------------------------------------------

    if contrato:

        query = (
            Obligacion.query
            .filter_by(
                contrato_id=contrato.id
            )
        )

        # ----------------------------------------------------
        # Filtro de búsqueda
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
        # Paginación
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

    # --------------------------------------------------------
    # Renderizar vista
    # --------------------------------------------------------

    return render_template(
        'contratos.html',

        contratos=contratos_list,

        contratos_datos=contratos_datos,

        generar_meses=generar_meses_contrato,

        contrato=contrato,

        obligaciones=obligaciones,

        obligaciones_pag=obligaciones_pag,

        search=search,

        per_page=per_page,

        # Mensajes temporales utilizados cuando
        # se intenta crear una obligación duplicada.
        obl_numero_error=session.pop(
            'obl_numero_error',
            ''
        ),

        obl_descripcion_error=session.pop(
            'obl_descripcion_error',
            ''
        )
    )


# ============================================================
# CREAR CONTRATO
# ============================================================

@contratos_bp.route(
    '/contrato/nuevo',
    methods=['POST']
)
@login_required
def contrato_nuevo():
    """
    Crea un nuevo contrato.

    Los contratos nuevos quedan INACTIVOS por defecto.
    """

    contratista = request.form.get(
        'contratista',
        ''
    ).strip()

    numero_contrato = request.form.get(
        'numero_contrato',
        ''
    ).strip()

    # --------------------------------------------------------
    # Validar campos obligatorios
    # --------------------------------------------------------

    if not contratista or not numero_contrato:

        flash(
            'Contratista y Numero de contrato son obligatorios.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    fecha_inicio = datetime.strptime(
        request.form['fecha_inicio'],
        '%Y-%m-%d'
    ).date()

    fecha_fin = datetime.strptime(
        request.form['fecha_fin'],
        '%Y-%m-%d'
    ).date()

    # --------------------------------------------------------
    # Crear contrato
    # --------------------------------------------------------

    nuevo = Contrato(
        fecha_inicio=fecha_inicio,

        fecha_fin=fecha_fin,

        contratista=contratista,

        numero_contrato=numero_contrato,

        # Los contratos nuevos comienzan inactivos.
        activo=False,

        etapa='Reporte en Proceso',

        user_id=current_user.id
    )

    db.session.add(nuevo)

    db.session.commit()

    # --------------------------------------------------------
    # Confirmación
    # --------------------------------------------------------

    flash(
        f'Contrato "{contratista}" creado exitosamente. '
        'Recuerde activarlo para usarlo.',
        'success'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# EDITAR CONTRATO
# ============================================================

@contratos_bp.route(
    '/contrato/<int:id>/editar',
    methods=['POST']
)
@login_required
def contrato_editar(id):
    """
    Edita un contrato existente.
    """

    contrato = Contrato.query.get_or_404(id)

    # --------------------------------------------------------
    # Seguridad:
    # verificar que el contrato pertenezca al usuario.
    # --------------------------------------------------------

    if contrato.user_id != current_user.id:

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    contratista = request.form.get(
        'contratista',
        ''
    ).strip()

    numero_contrato = request.form.get(
        'numero_contrato',
        ''
    ).strip()

    # --------------------------------------------------------
    # Validar campos
    # --------------------------------------------------------

    if not contratista or not numero_contrato:

        flash(
            'Contratista y Numero de contrato son obligatorios.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Actualizar datos
    # --------------------------------------------------------

    contrato.contratista = contratista

    contrato.numero_contrato = numero_contrato

    contrato.fecha_inicio = datetime.strptime(
        request.form['fecha_inicio'],
        '%Y-%m-%d'
    ).date()

    contrato.fecha_fin = datetime.strptime(
        request.form['fecha_fin'],
        '%Y-%m-%d'
    ).date()

    db.session.commit()

    flash(
        'Contrato actualizado correctamente.',
        'success'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# ELIMINAR CONTRATO
# ============================================================

@contratos_bp.route(
    '/contrato/<int:id>/eliminar',
    methods=['POST']
)
@login_required
def contrato_eliminar(id):
    """
    Elimina un contrato únicamente cuando ninguna de sus
    obligaciones tiene evidencias registradas.
    """

    contrato = Contrato.query.get_or_404(id)

    # --------------------------------------------------------
    # Seguridad:
    # verificar propietario.
    # --------------------------------------------------------

    if contrato.user_id != current_user.id:

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Verificar evidencias existentes
    # --------------------------------------------------------

    tiene_evidencias = False

    obligaciones_con_evidencias = []

    for obligacion in contrato.obligaciones:

        for reporte in obligacion.reportes:

            if reporte.evidencias:

                tiene_evidencias = True

                obligaciones_con_evidencias.append(
                    f'Obligacion No. {obligacion.numero}'
                )

                break

    # --------------------------------------------------------
    # No permitir eliminación si existen evidencias
    # --------------------------------------------------------

    if tiene_evidencias:

        flash(
            'No se puede eliminar el contrato porque '
            'tiene evidencias registradas. '
            'Elimine primero las evidencias de: '
            + ', '.join(
                obligaciones_con_evidencias
            )
            + '.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Eliminar contrato
    #
    # Las relaciones de SQLAlchemy tienen cascade
    # all, delete-orphan, por lo que las obligaciones
    # y reportes asociados se eliminan en cascada.
    # --------------------------------------------------------

    db.session.delete(contrato)

    db.session.commit()

    flash(
        'Contrato eliminado correctamente.',
        'success'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# CAMBIAR ESTADO
# ============================================================

@contratos_bp.route(
    '/contrato/<int:id>/cambiar-estado',
    methods=['POST']
)
@login_required
def contrato_cambiar_estado(id):
    """
    Activa o desactiva un contrato.

    Regla:
    Solo puede existir UN contrato activo por usuario.
    """

    contrato = Contrato.query.get_or_404(id)

    # --------------------------------------------------------
    # Seguridad
    # --------------------------------------------------------

    if contrato.user_id != current_user.id:

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # ========================================================
    # DESACTIVAR
    # ========================================================

    if contrato.activo:

        # ----------------------------------------------------
        # Verificar cantidad total de contratos
        # ----------------------------------------------------

        total_contratos = (
            Contrato.query
            .filter_by(
                user_id=current_user.id
            )
            .count()
        )

        # ----------------------------------------------------
        # No permitir dejar al usuario sin contrato activo
        # cuando solamente tiene uno.
        # ----------------------------------------------------

        if total_contratos <= 1:

            flash(
                'No puede inactivar el unico contrato '
                'existente. Cree otro contrato primero.',
                'danger'
            )

            return redirect(
                url_for(
                    'contratos.contratos'
                )
            )

        contrato.activo = False

        db.session.commit()

        flash(
            f'Contrato "{contrato.contratista}" desactivado.',
            'info'
        )

    # ========================================================
    # ACTIVAR
    # ========================================================

    else:

        # ----------------------------------------------------
        # Primero desactivar todos los contratos activos
        # del usuario.
        # ----------------------------------------------------

        (
            Contrato.query
            .filter_by(
                user_id=current_user.id,
                activo=True
            )
            .update(
                {
                    'activo': False
                }
            )
        )

        # ----------------------------------------------------
        # Activar el contrato seleccionado
        # ----------------------------------------------------

        contrato.activo = True

        db.session.commit()

        flash(
            f'Contrato "{contrato.contratista}" activado. '
            'Ahora puede gestionar sus obligaciones y reportes.',
            'success'
        )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# FINALIZAR CONTRATO
# ============================================================

@contratos_bp.route(
    '/contrato/<int:id>/finalizar',
    methods=['POST']
)
@login_required
def contrato_finalizar(id):
    """
    Finaliza un contrato.

    Requisitos:

    1. El contrato debe tener obligaciones.
    2. Cada obligación debe tener un reporte para
       CADA MES del contrato.
    3. Cada reporte debe tener al menos una evidencia.

    Si todo está completo:

        etapa = 'Reporte Cerrado'
    """

    contrato = Contrato.query.get_or_404(id)

    # --------------------------------------------------------
    # Seguridad
    # --------------------------------------------------------

    if contrato.user_id != current_user.id:

        flash(
            'No tiene permiso.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Obtener obligaciones
    # --------------------------------------------------------

    obligaciones = (
        Obligacion.query
        .filter_by(
            contrato_id=contrato.id
        )
        .all()
    )

    # --------------------------------------------------------
    # Debe existir al menos una obligación
    # --------------------------------------------------------

    if not obligaciones:

        flash(
            'No se puede finalizar el contrato porque '
            'no tiene obligaciones registradas.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Obtener todos los meses del contrato
    # --------------------------------------------------------

    meses_contrato = generar_meses_contrato(
        contrato.fecha_inicio,
        contrato.fecha_fin
    )

    # Formato:
    #
    # [
    #     (mes_numero, anio, nombre_mes),
    #     ...
    # ]

    errores = []

    # ========================================================
    # VALIDAR CADA OBLIGACIÓN
    # ========================================================

    for obligacion in obligaciones:

        # ----------------------------------------------------
        # Obtener reportes de la obligación
        # ----------------------------------------------------

        reportes = (
            ReporteMensual.query
            .filter_by(
                obligacion_id=obligacion.id
            )
            .all()
        )

        # ----------------------------------------------------
        # Crear mapa:
        #
        # (mes, anio) -> reporte
        # ----------------------------------------------------

        reportes_map = {
            (
                reporte.mes,
                reporte.anio
            ): reporte
            for reporte in reportes
        }

        meses_faltantes = []

        meses_sin_evidencia = []

        # ----------------------------------------------------
        # Revisar todos los meses del contrato
        # ----------------------------------------------------

        for (
            mes_num,
            anio,
            nombre
        ) in meses_contrato:

            clave = (
                mes_num,
                anio
            )

            # ------------------------------------------------
            # No existe reporte
            # ------------------------------------------------

            if clave not in reportes_map:

                meses_faltantes.append(
                    f'{nombre} {anio}'
                )

            # ------------------------------------------------
            # Existe reporte pero no evidencia
            # ------------------------------------------------

            else:

                reporte = reportes_map[
                    clave
                ]

                if not reporte.evidencias:

                    meses_sin_evidencia.append(
                        f'{nombre} {anio}'
                    )

        # ----------------------------------------------------
        # Registrar meses faltantes
        # ----------------------------------------------------

        if meses_faltantes:

            errores.append(
                f'Obligacion No. '
                f'{obligacion.numero}: '
                f'falta(n) reporte(s) para '
                f'{", ".join(meses_faltantes)}.'
            )

        # ----------------------------------------------------
        # Registrar meses sin evidencia
        # ----------------------------------------------------

        if meses_sin_evidencia:

            errores.append(
                f'Obligacion No. '
                f'{obligacion.numero}: '
                f'reporte(s) sin evidencia en '
                f'{", ".join(meses_sin_evidencia)}.'
            )

    # ========================================================
    # SI EXISTEN ERRORES, NO FINALIZAR
    # ========================================================

    if errores:

        lista_html = (
            '<ul class="mb-0">'
            +
            ''.join(
                [
                    f'<li>{error}</li>'
                    for error in errores
                ]
            )
            +
            '</ul>'
        )

        flash(
            '<strong>'
            'No se puede finalizar el contrato.'
            '</strong><br>'
            'Cada obligacion debe tener un reporte '
            'con al menos una evidencia para '
            '<strong>TODOS los meses</strong> '
            'del contrato.<br><br>'
            f'<strong>'
            f'Detalles encontrados ({len(errores)}):'
            f'</strong>'
            f'{lista_html}',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # ========================================================
    # FINALIZAR CONTRATO
    # ========================================================

    contrato.etapa = 'Reporte Cerrado'

    db.session.commit()

    flash(
        f'Contrato "{contrato.contratista}" '
        'finalizado exitosamente. '
        'Etapa: Reporte Cerrado. '
        'No se podran agregar mas evidencias.',
        'success'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )

# ============================================================
# AGREGAR OBLIGACIÓN
# ============================================================

@contratos_bp.route(
    '/obligacion/agregar',
    methods=['POST']
)
@login_required
def agregar_obligacion():
    """
    Crea una nueva obligación para el contrato activo.
    """

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
            'Primero debe tener un contrato activo.',
            'danger'
        )
        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    try:
        numero = int(
            request.form.get(
                'numero',
                0
            )
        )
    except (
        ValueError,
        TypeError
    ):
        flash(
            'El número de obligación no es válido.',
            'danger'
        )
        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    descripcion = request.form.get(
        'descripcion',
        ''
    ).strip()

    if not descripcion:
        flash(
            'La descripción de la obligación es obligatoria.',
            'danger'
        )
        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Validar duplicado de número en el mismo contrato
    # --------------------------------------------------------

    existente = (
        Obligacion.query
        .filter_by(
            numero=numero,
            contrato_id=contrato.id
        )
        .first()
    )

    if existente:
        session[
            'obl_numero_error'
        ] = numero

        session[
            'obl_descripcion_error'
        ] = descripcion

        flash(
            f'Ya existe una obligación con el número {numero} '
            f'en este contrato. Use otro número.',
            'danger'
        )

        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    # --------------------------------------------------------
    # Crear obligación
    # --------------------------------------------------------

    obligacion = Obligacion(
        numero=numero,
        descripcion=descripcion,
        contrato_id=contrato.id
    )

    db.session.add(
        obligacion
    )

    db.session.commit()

    flash(
        f'Obligación No. {numero} agregada.',
        'success'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# EDITAR OBLIGACIÓN
# ============================================================

@contratos_bp.route(
    '/obligacion/<int:id>/editar',
    methods=['POST']
)
@login_required
def editar_obligacion(id):
    """
    Actualiza la descripción de una obligación.
    """

    obligacion = (
        Obligacion.query
        .get_or_404(id)
    )

    contrato = (
        Contrato.query
        .get(
            obligacion.contrato_id
        )
    )

    if (
        not contrato
        or contrato.user_id != current_user.id
    ):
        flash(
            'No tiene permiso.',
            'danger'
        )
        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    nueva_descripcion = request.form.get(
        'descripcion',
        ''
    ).strip()

    if nueva_descripcion:
        obligacion.descripcion = (
            nueva_descripcion
        )
        db.session.commit()

        flash(
            f'Obligación No. {obligacion.numero} actualizada.',
            'success'
        )
    else:
        flash(
            'La descripción no puede estar vacía.',
            'danger'
        )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )


# ============================================================
# ELIMINAR OBLIGACIÓN
# ============================================================

@contratos_bp.route(
    '/obligacion/<int:id>/eliminar',
    methods=['POST']
)
@login_required
def eliminar_obligacion(id):
    """
    Elimina una obligación y sus reportes en cascada.
    """

    obligacion = (
        Obligacion.query
        .get_or_404(id)
    )

    contrato = (
        Contrato.query
        .get(
            obligacion.contrato_id
        )
    )

    if (
        not contrato
        or contrato.user_id != current_user.id
    ):
        flash(
            'No tiene permiso.',
            'danger'
        )
        return redirect(
            url_for(
                'contratos.contratos'
            )
        )

    db.session.delete(
        obligacion
    )

    db.session.commit()

    flash(
        'Obligación eliminada.',
        'info'
    )

    return redirect(
        url_for(
            'contratos.contratos'
        )
    )
