"""
Blueprint de reportes y evidencias.

Responsabilidades:
- Listado de reportes.
- Creacion de reportes mensuales.
- Visualizacion de reportes.
- Registro de evidencias.
- Edicion de evidencias.
- Eliminacion de evidencias.
- Generacion de PDF individual.
- Eliminacion de reportes.
- Servir archivos de evidencias.
- Descarga masiva de PDFs por mes.
- Generacion de Excel consolidado.
"""

import os
import io
import zipfile
import calendar
import threading
import logging

from datetime import datetime, date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    session,
    send_file,
    jsonify,
    current_app
)

from werkzeug.exceptions import RequestEntityTooLarge

from flask_login import login_required, current_user

from werkzeug.utils import secure_filename

from models import db, Contrato, Obligacion, ReporteMensual, Evidencia

from pdf_generator import PDFGenerator

from vision_analyzer import analizar_imagen, consolidar_textos_ejecutivo

from app.blueprints.configuracion import _obtener_api_key

from app.services.evidencia_service import EvidenciaService


# ============================================================
# BLUEPRINT
# ============================================================

reportes_bp = Blueprint('reportes', __name__)


# ============================================================
# CONFIGURACION DE ARCHIVOS
# ============================================================

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def generar_meses_contrato(fecha_inicio, fecha_fin):
    meses = []
    current = date(fecha_inicio.year, fecha_inicio.month, 1)
    end = date(fecha_fin.year, fecha_fin.month, 1)
    nombres_meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    while current <= end:
        meses.append((current.month, current.year, nombres_meses[current.month]))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return meses


def obtener_nombre_mes(mes):
    nombres_meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    if not mes or mes < 1 or mes > 12:
        return ''
    return nombres_meses[mes]


# ============================================================
# LOGGING PARA IA BACKGROUND
# ============================================================

_ia_log_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'ia_background.log'
)

_ia_handler = logging.FileHandler(_ia_log_path, encoding='utf-8')
_ia_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

ia_logger = logging.getLogger('ia_background')
ia_logger.setLevel(logging.DEBUG)
if not ia_logger.handlers:
    ia_logger.addHandler(_ia_handler)


# ============================================================
# ANALISIS IA EN BACKGROUND
# ============================================================

def _analizar_ia_background(app, evidencia_id, imagen_path, api_key, obligacion_desc, anuncio):
    import time
    time.sleep(2)

    with app.app_context():
        from models import db, Evidencia
        from vision_analyzer import analizar_imagen

        db.session.remove()

        try:
            ia_logger.info(f'=== INICIO analisis IA evidencia {evidencia_id} ===')
            descripcion = analizar_imagen(
                imagen_path,
                api_key=api_key,
                contexto_obligacion=obligacion_desc,
                anuncio_usuario=anuncio
            )
            ia_logger.info(f'Respuesta Gemini: {str(descripcion)[:200]}')

            if descripcion:
                evidencia = Evidencia.query.get(evidencia_id)
                if evidencia:
                    evidencia.descripcion_visual_ia = descripcion
                    evidencia.descripcion_actividad = descripcion
                    db.session.commit()
                    ia_logger.info(f'=== EXITO evidencia {evidencia_id} ===')
                else:
                    ia_logger.error(f'Evidencia {evidencia_id} NO ENCONTRADA')
            else:
                ia_logger.warning(f'Evidencia {evidencia_id}: Gemini NO retorno descripcion')

        except Exception as e:
            ia_logger.exception(f'=== ERROR evidencia {evidencia_id}: {e} ===')
            db.session.rollback()
        finally:
            db.session.remove()


# ============================================================
# LISTADO DE REPORTES
# ============================================================

@reportes_bp.route('/reportes')
@login_required
def reportes():
    contrato = Contrato.query.filter_by(activo=True, user_id=current_user.id).first()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str).strip()
    filtro_mes = request.args.get('filtro_mes', '', type=str)
    filtro_anio = request.args.get('filtro_anio', '', type=str)
    filtro_obligacion = request.args.get('filtro_obligacion', '', type=str)

    reportes_list = []
    reportes_pag = None
    obligaciones_list = []

    if contrato:
        obligaciones_list = Obligacion.query.filter_by(contrato_id=contrato.id).order_by(Obligacion.numero).all()

        query = ReporteMensual.query.join(Obligacion).filter(Obligacion.contrato_id == contrato.id)

        if search:
            query = query.filter(
                db.or_(
                    Obligacion.descripcion.ilike(f'%{search}%'),
                    Obligacion.numero.cast(db.String).ilike(f'%{search}%')
                )
            )

        if filtro_mes:
            try:
                query = query.filter(ReporteMensual.mes == int(filtro_mes))
            except ValueError:
                pass

        if filtro_anio:
            try:
                query = query.filter(ReporteMensual.anio == int(filtro_anio))
            except ValueError:
                pass

        if filtro_obligacion:
            try:
                query = query.filter(Obligacion.id == int(filtro_obligacion))
            except ValueError:
                pass

        reportes_pag = query.order_by(
            ReporteMensual.anio.desc(),
            ReporteMensual.mes.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        reportes_list = reportes_pag.items

    return render_template(
        'reportes.html',
        reportes=reportes_list,
        reportes_pag=reportes_pag,
        contrato=contrato,
        obligaciones_list=obligaciones_list,
        search=search,
        filtro_mes=filtro_mes,
        filtro_anio=filtro_anio,
        filtro_obligacion=filtro_obligacion,
        per_page=per_page
    )


# ============================================================
# NUEVO REPORTE
# ============================================================

@reportes_bp.route('/reporte/nuevo/<int:obligacion_id>', methods=['GET', 'POST'])
@login_required
def nuevo_reporte(obligacion_id):
    obligacion = Obligacion.query.get_or_404(obligacion_id)
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    if contrato.etapa == 'Reporte Cerrado':
        flash('Este contrato esta finalizado. No se pueden crear nuevos reportes.', 'warning')
        return redirect(url_for('reportes.reportes'))

    meses = generar_meses_contrato(contrato.fecha_inicio, contrato.fecha_fin)

    form_data = {
        'mes': session.pop('nuevo_rep_mes', ''),
        'anio': session.pop('nuevo_rep_anio', ''),
        'fecha_inicio_reporte': session.pop('nuevo_rep_fecha_inicio', ''),
        'fecha_fin_reporte': session.pop('nuevo_rep_fecha_fin', '')
    }

    if request.method == 'POST':
        try:
            mes = int(request.form['mes'])
            anio = int(request.form['anio'])
            fecha_inicio_rep = datetime.strptime(request.form['fecha_inicio_reporte'], '%Y-%m-%d').date()
            fecha_fin_rep = datetime.strptime(request.form['fecha_fin_reporte'], '%Y-%m-%d').date()
        except (KeyError, ValueError, TypeError):
            flash('Los datos del reporte no son validos.', 'danger')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        if mes < 1 or mes > 12:
            flash('El mes seleccionado no es valido.', 'danger')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        nombre_mes = obtener_nombre_mes(mes)
        _, last_day = calendar.monthrange(anio, mes)
        primer_dia_mes = date(anio, mes, 1)
        ultimo_dia_mes = date(anio, mes, last_day)

        if fecha_inicio_rep < primer_dia_mes or fecha_inicio_rep > ultimo_dia_mes:
            session['nuevo_rep_mes'] = str(mes)
            session['nuevo_rep_anio'] = str(anio)
            session['nuevo_rep_fecha_inicio'] = request.form['fecha_inicio_reporte']
            session['nuevo_rep_fecha_fin'] = request.form['fecha_fin_reporte']
            flash(f'La fecha de inicio debe estar dentro de {nombre_mes} {anio}.', 'danger')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        if fecha_fin_rep < primer_dia_mes or fecha_fin_rep > ultimo_dia_mes:
            session['nuevo_rep_mes'] = str(mes)
            session['nuevo_rep_anio'] = str(anio)
            session['nuevo_rep_fecha_inicio'] = request.form['fecha_inicio_reporte']
            session['nuevo_rep_fecha_fin'] = request.form['fecha_fin_reporte']
            flash(f'La fecha de fin debe estar dentro de {nombre_mes} {anio}.', 'danger')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        if fecha_inicio_rep > fecha_fin_rep:
            session['nuevo_rep_mes'] = str(mes)
            session['nuevo_rep_anio'] = str(anio)
            session['nuevo_rep_fecha_inicio'] = request.form['fecha_inicio_reporte']
            session['nuevo_rep_fecha_fin'] = request.form['fecha_fin_reporte']
            flash('La fecha de inicio no puede ser posterior a la fecha de fin.', 'danger')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        # Validar consecutividad
        if mes == 1:
            mes_ant, anio_ant = 12, anio - 1
        else:
            mes_ant, anio_ant = mes - 1, anio

        fecha_mes_ant = date(anio_ant, mes_ant, 1)
        fecha_inicio_contrato_mes = date(contrato.fecha_inicio.year, contrato.fecha_inicio.month, 1)

        if fecha_mes_ant >= fecha_inicio_contrato_mes:
            reporte_anterior = ReporteMensual.query.filter_by(
                mes=mes_ant, anio=anio_ant, obligacion_id=obligacion_id
            ).first()

            if not reporte_anterior:
                nombres_meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                session['nuevo_rep_mes'] = str(mes)
                session['nuevo_rep_anio'] = str(anio)
                session['nuevo_rep_fecha_inicio'] = request.form['fecha_inicio_reporte']
                session['nuevo_rep_fecha_fin'] = request.form['fecha_fin_reporte']
                flash(f'No puede saltar meses. Cree primero el reporte de {nombres_meses[mes_ant]} {anio_ant}.', 'danger')
                return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        # Validar duplicado
        existente = ReporteMensual.query.filter_by(mes=mes, anio=anio, obligacion_id=obligacion_id).first()
        if existente:
            session['nuevo_rep_mes'] = str(mes)
            session['nuevo_rep_anio'] = str(anio)
            session['nuevo_rep_fecha_inicio'] = request.form['fecha_inicio_reporte']
            session['nuevo_rep_fecha_fin'] = request.form['fecha_fin_reporte']
            flash(f'Ya existe un reporte para {existente.nombre_mes} {anio}.', 'warning')
            return redirect(url_for('reportes.nuevo_reporte', obligacion_id=obligacion_id))

        reporte = ReporteMensual(
            mes=mes,
            anio=anio,
            fecha_inicio_reporte=fecha_inicio_rep,
            fecha_fin_reporte=fecha_fin_rep,
            obligacion_id=obligacion_id
        )
        db.session.add(reporte)
        db.session.commit()

        flash(f'Reporte de {reporte.nombre_mes} {anio} creado.', 'success')
        return redirect(url_for('reportes.ver_reporte', id=reporte.id))

    return render_template(
        'nuevo_reporte.html',
        obligacion=obligacion,
        meses=meses,
        contrato=contrato,
        form_data=form_data
    )


# ============================================================
# VER REPORTE
# ============================================================

@reportes_bp.route('/reporte/<int:id>')
@login_required
def ver_reporte(id):
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    evidencias = Evidencia.query.filter_by(reporte_id=id).order_by(Evidencia.numero_actividad).all()
    api_key_configurada = bool(_obtener_api_key())

    form_data = {
        'anuncio_usuario': session.pop('evidencia_anuncio', ''),
        'fecha_actividad': session.pop('evidencia_fecha', '')
    }

    return render_template(
        'ver_reporte.html',
        reporte=reporte,
        obligacion=obligacion,
        contrato=contrato,
        evidencias=evidencias,
        api_key_configurada=api_key_configurada,
        form_data=form_data
    )


# ============================================================
# SUBIR EVIDENCIA (POST TRADICIONAL)
# ============================================================

@reportes_bp.route('/reporte/<int:id>/evidencia', methods=['POST'])
@login_required
def subir_evidencia(id):
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    if reporte.cerrado:
        flash('Este reporte esta cerrado. No se pueden agregar mas evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if contrato.etapa == 'Reporte Cerrado':
        flash('Este contrato esta finalizado. No se pueden agregar mas evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    api_key = _obtener_api_key()

    session['evidencia_anuncio'] = request.form.get('anuncio_usuario', '')
    session['evidencia_fecha'] = request.form.get('fecha_actividad', '')

    if 'imagen' not in request.files:
        flash('No se selecciono ningun archivo.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    file = request.files['imagen']
    anuncio_usuario = request.form.get('anuncio_usuario', '').strip()

    if not anuncio_usuario:
        flash('Debe escribir un anuncio/contexto.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if file.filename == '':
        flash('No se selecciono ningun archivo.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if not allowed_file(file.filename):
        flash('Formato no permitido.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    fecha_actividad_str = request.form.get('fecha_actividad', '').strip()
    try:
        if fecha_actividad_str:
            fecha_actividad = datetime.strptime(fecha_actividad_str, '%Y-%m-%d').date()
        else:
            fecha_actividad = date.today()
    except ValueError:
        flash('La fecha de actividad no es valida.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if fecha_actividad < reporte.fecha_inicio_reporte or fecha_actividad > reporte.fecha_fin_reporte:
        flash(
            f'La fecha de la actividad debe estar dentro del periodo del reporte: '
            f'{reporte.fecha_inicio_reporte.strftime("%d/%m/%Y")} a '
            f'{reporte.fecha_fin_reporte.strftime("%d/%m/%Y")}.',
            'danger'
        )
        return redirect(url_for('reportes.ver_reporte', id=id))

    try:
        evidencia_service = EvidenciaService()

        # ========================================================
        # MODO SINCRONO: La IA se ejecuta ahora mismo
        # ========================================================

        descripcion_visual = None

        if api_key:
            try:
                descripcion_visual = analizar_imagen(
                    file,
                    api_key=api_key,
                    contexto_obligacion=obligacion.descripcion,
                    anuncio_usuario=anuncio_usuario
                )
            except Exception as e:
                print(f'[IA] Error analizando imagen: {e}')

        evidencia = evidencia_service.crear_evidencia(
            reporte=reporte,
            imagen=file,
            anuncio=anuncio_usuario,
            fecha=fecha_actividad,
            descripcion=descripcion_visual
        )

        db.session.commit()

        session.pop('evidencia_anuncio', None)
        session.pop('evidencia_fecha', None)

        if descripcion_visual:
            flash(f'Actividad {evidencia.numero_actividad} registrada con descripcion de IA.', 'success')
        else:
            flash(f'Actividad {evidencia.numero_actividad} registrada.', 'success')

    except RequestEntityTooLarge:
        db.session.rollback()
        flash('El archivo es demasiado grande. Maximo 16MB.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('reportes.ver_reporte', id=id))


# ============================================================
# ELIMINAR EVIDENCIA
# ============================================================

@reportes_bp.route('/reporte/<int:id>/evidencia/<int:evidencia_id>/eliminar', methods=['POST'])
@login_required
def eliminar_evidencia(id, evidencia_id):
    evidencia = Evidencia.query.get_or_404(evidencia_id)
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    if reporte.cerrado:
        flash('Este reporte esta cerrado. No se pueden eliminar evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if contrato.etapa == 'Reporte Cerrado':
        flash('Este contrato esta finalizado. No se pueden eliminar evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    try:
        db.session.delete(evidencia)
        db.session.commit()
        flash('Evidencia eliminada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar evidencia: {str(e)}', 'danger')

    return redirect(url_for('reportes.ver_reporte', id=id))


# ============================================================
# EDITAR EVIDENCIA
# ============================================================

@reportes_bp.route('/reporte/<int:id>/evidencia/<int:evidencia_id>/editar', methods=['POST'])
@login_required
def editar_evidencia(id, evidencia_id):
    evidencia = Evidencia.query.get_or_404(evidencia_id)
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    if reporte.cerrado:
        flash('Este reporte esta cerrado. No se pueden editar evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    if contrato.etapa == 'Reporte Cerrado':
        flash('Este contrato esta finalizado. No se pueden editar evidencias.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    descripcion = request.form.get('descripcion_actividad', '').strip()
    fecha_actividad_str = request.form.get('fecha_actividad', '').strip()

    if not descripcion:
        flash('La descripcion no puede estar vacia.', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))

    try:
        if fecha_actividad_str:
            evidencia.fecha_actividad = datetime.strptime(fecha_actividad_str, '%Y-%m-%d').date()
        evidencia.descripcion_actividad = descripcion
        db.session.commit()
        flash('Evidencia actualizada.', 'success')
    except ValueError:
        flash('La fecha no es valida.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar evidencia: {str(e)}', 'danger')

    return redirect(url_for('reportes.ver_reporte', id=id))


# ============================================================
# GENERAR PDF INDIVIDUAL
# ============================================================

@reportes_bp.route('/reporte/<int:id>/pdf')
@login_required
def generar_pdf(id):
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    evidencias = Evidencia.query.filter_by(reporte_id=id).order_by(Evidencia.numero_actividad).all()

    if not evidencias:
        flash(
            'No se puede generar el PDF porque este reporte no tiene evidencias registradas. '
            'Agregue al menos una evidencia antes de descargar.',
            'warning'
        )
        return redirect(url_for('reportes.ver_reporte', id=id))

    pdf_filename = f'Reporte_Obligacion_{obligacion.numero}_{reporte.nombre_mes}_{reporte.anio}.pdf'
    pdf_path = os.path.join(current_app.config['PDF_FOLDER'], pdf_filename)

    try:
        generator = PDFGenerator(pdf_path)
        generator.generar_reporte(reporte, obligacion, evidencias, contrato)

        return send_from_directory(
            current_app.config['PDF_FOLDER'],
            pdf_filename,
            as_attachment=True
        )
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'danger')
        return redirect(url_for('reportes.ver_reporte', id=id))


# ============================================================
# SERVIR ARCHIVO DE EVIDENCIA
# ============================================================

@reportes_bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ============================================================
# DESCARGA MASIVA DE PDFS POR MES
# ============================================================

@reportes_bp.route('/reportes/descargar-masivo-mes', methods=['POST'])
@login_required
def descargar_masivo_mes():
    contrato = Contrato.query.filter_by(activo=True, user_id=current_user.id).first()

    if not contrato:
        flash('No hay contrato activo.', 'warning')
        return redirect(url_for('reportes.reportes'))

    try:
        mes = int(request.form.get('mes', 0))
        anio = int(request.form.get('anio', 0))
    except (ValueError, TypeError):
        flash('Mes y año invalidos.', 'danger')
        return redirect(url_for('reportes.reportes'))

    if not mes or not anio:
        flash('Debe seleccionar mes y año.', 'warning')
        return redirect(url_for('reportes.reportes'))

    obligaciones = Obligacion.query.filter_by(contrato_id=contrato.id).all()
    obligaciones_ids = [obl.id for obl in obligaciones]

    reportes = ReporteMensual.query.filter(
        ReporteMensual.mes == mes,
        ReporteMensual.anio == anio,
        ReporteMensual.obligacion_id.in_(obligaciones_ids)
    ).all()

    if not reportes:
        flash(f'No hay reportes para {obtener_nombre_mes(mes)} {anio}.', 'warning')
        return redirect(url_for('reportes.reportes'))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rep in reportes:
            evidencias = Evidencia.query.filter_by(reporte_id=rep.id).order_by(Evidencia.numero_actividad).all()
            if not evidencias:
                continue

            pdf_filename = f'Reporte_Obligacion_{rep.obligacion.numero}_{rep.nombre_mes}_{rep.anio}.pdf'
            pdf_path = os.path.join(current_app.config['PDF_FOLDER'], pdf_filename)

            if not os.path.exists(pdf_path):
                try:
                    generator = PDFGenerator(pdf_path)
                    generator.generar_reporte(rep, rep.obligacion, evidencias, contrato)
                except Exception as e:
                    print(f'[Descarga Masiva] Error generando PDF {pdf_filename}: {e}')
                    continue

            if os.path.exists(pdf_path):
                zf.write(pdf_path, pdf_filename)

    zip_buffer.seek(0)
    zip_filename = f'Reportes_{obtener_nombre_mes(mes)}_{anio}.zip'

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename
    )


# ============================================================
# ELIMINAR REPORTE
# ============================================================

@reportes_bp.route('/reporte/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_reporte(id):
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    try:
        db.session.delete(reporte)
        db.session.commit()
        flash('Reporte eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar reporte: {str(e)}', 'danger')

    return redirect(url_for('reportes.reportes'))


# ============================================================
# CERRAR REPORTE
# ============================================================

@reportes_bp.route('/reporte/<int:id>/cerrar', methods=['POST'])
@login_required
def cerrar_reporte(id):
    reporte = ReporteMensual.query.get_or_404(id)
    obligacion = reporte.obligacion
    contrato = Contrato.query.get(obligacion.contrato_id)

    if not contrato or contrato.user_id != current_user.id:
        flash('No tiene permiso.', 'danger')
        return redirect(url_for('inicio.inicio'))

    if reporte.cerrado:
        flash('Este reporte ya esta cerrado.', 'warning')
        return redirect(url_for('reportes.ver_reporte', id=id))

    try:
        reporte.cerrado = True
        db.session.commit()
        flash('Reporte cerrado. Ahora es de solo lectura.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cerrar reporte: {str(e)}', 'danger')

    return redirect(url_for('reportes.ver_reporte', id=id))


# ============================================================
# CERRAR MES REPORTADO (TODAS LAS OBLIGACIONES)
# ============================================================

@reportes_bp.route('/reportes/cerrar-mes', methods=['POST'])
@login_required
def cerrar_mes_reportado():
    try:
        mes = int(request.form.get('mes', 0))
        anio = int(request.form.get('anio', 0))
    except (TypeError, ValueError):
        flash('Debe seleccionar mes y año validos.', 'danger')
        return redirect(url_for('reportes.reportes'))

    if not mes or not anio:
        flash('Mes y año son obligatorios.', 'danger')
        return redirect(url_for('reportes.reportes'))

    if mes < 1 or mes > 12:
        flash('El mes seleccionado no es valido.', 'danger')
        return redirect(url_for('reportes.reportes'))

    nombre_mes = obtener_nombre_mes(mes)

    hoy = date.today()

    if anio > hoy.year or (anio == hoy.year and mes >= hoy.month):
        flash(
            f'Solo se pueden cerrar meses anteriores al actual '
            f'({obtener_nombre_mes(hoy.month)} {hoy.year}).',
            'warning'
        )
        return redirect(url_for('reportes.reportes'))

    contrato = Contrato.query.filter_by(activo=True, user_id=current_user.id).first()

    if not contrato:
        flash('No hay contrato activo.', 'warning')
        return redirect(url_for('reportes.reportes'))

    obligaciones = Obligacion.query.filter_by(contrato_id=contrato.id).all()

    if not obligaciones:
        flash('No hay obligaciones registradas.', 'warning')
        return redirect(url_for('reportes.reportes'))

    obligaciones_faltantes = []

    for obl in obligaciones:
        reporte = ReporteMensual.query.filter_by(mes=mes, anio=anio, obligacion_id=obl.id).first()

        if not reporte:
            obligaciones_faltantes.append(f'Obligacion No. {obl.numero} (sin reporte)')
        elif not reporte.evidencias:
            obligaciones_faltantes.append(f'Obligacion No. {obl.numero} (sin actividades)')

    if obligaciones_faltantes:
        flash(
            'No se puede cerrar el mes porque faltan reportes o '
            'actividades en: ' + '; '.join(obligaciones_faltantes),
            'danger'
        )
        return redirect(url_for('reportes.reportes'))

    reportes_mes = (
        ReporteMensual.query
        .join(Obligacion)
        .filter(
            Obligacion.contrato_id == contrato.id,
            ReporteMensual.mes == mes,
            ReporteMensual.anio == anio
        )
        .all()
    )

    for rep in reportes_mes:
        rep.cerrado = True

    db.session.commit()

    flash(
        f'Mes {nombre_mes} {anio} cerrado exitosamente. '
        f'Todos los reportes ({len(reportes_mes)}) son ahora de solo lectura.',
        'success'
    )

    return redirect(url_for('reportes.reportes'))


# ============================================================
# SELECCIONAR OBLIGACION PARA NUEVO REPORTE
# ============================================================

@reportes_bp.route('/reporte/nuevo')
@login_required
def nuevo_reporte_selector():
    contrato = Contrato.query.filter_by(activo=True, user_id=current_user.id).first()

    if not contrato:
        flash('No hay contrato activo.', 'warning')
        return redirect(url_for('contratos.contratos'))

    obligaciones = (
        Obligacion.query
        .filter_by(contrato_id=contrato.id)
        .order_by(Obligacion.numero)
        .all()
    )

    if not obligaciones:
        flash('No hay obligaciones registradas. Cree obligaciones primero.', 'warning')
        return redirect(url_for('contratos.contratos'))

    return render_template(
        'seleccionar_obligacion.html',
        obligaciones=obligaciones,
        contrato=contrato
    )
