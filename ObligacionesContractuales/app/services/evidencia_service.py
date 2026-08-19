"""
Servicio para procesamiento de evidencias.

Responsabilidades:
- Buscar imágenes cargadas temporalmente.
- Mover imágenes al almacenamiento definitivo.
- Analizar imágenes mediante Gemini.
- Crear registros Evidencia.
- Generar descripción de la actividad.
- Mantener la lógica de evidencias fuera del Blueprint.
"""

import os

from datetime import datetime

from flask import current_app

from werkzeug.utils import secure_filename

from models import (
    db,
    Evidencia
)


# ============================================================
# SERVICIO DE EVIDENCIAS
# ============================================================

class EvidenciaService:

    # ========================================================
    # OBTENER IMAGEN TEMPORAL
    # ========================================================

    @staticmethod
    def obtener_imagen_temporal(
        nombre_imagen,
        imagenes_disponibles
    ):
        """
        Obtiene una imagen del conjunto de archivos
        cargados y la elimina del diccionario para
        evitar reutilizarla.
        """

        if not nombre_imagen:

            return None

        # ----------------------------------------------------
        # BÚSQUEDA EXACTA
        # ----------------------------------------------------

        if nombre_imagen in imagenes_disponibles:

            return imagenes_disponibles.pop(
                nombre_imagen
            )

        # ----------------------------------------------------
        # BÚSQUEDA CON NOMBRE SEGURO
        # ----------------------------------------------------

        nombre_seguro = secure_filename(
            nombre_imagen
        )

        if nombre_seguro in imagenes_disponibles:

            return imagenes_disponibles.pop(
                nombre_seguro
            )

        return None

    # ========================================================
    # GUARDAR IMAGEN
    # ========================================================

    @staticmethod
    def guardar_imagen_evidencia(
        imagen_temporal,
        reporte_id,
        nombre_imagen
    ):
        """
        Mueve una imagen temporal al almacenamiento
        definitivo.
        """

        if not imagen_temporal:

            return None

        if not os.path.exists(
            imagen_temporal
        ):

            raise FileNotFoundError(
                (
                    'No se encontró la imagen temporal: '
                    f'{imagen_temporal}'
                )
            )

        upload_folder = current_app.config.get(
            'UPLOAD_FOLDER'
        )

        if not upload_folder:

            raise ValueError(
                'UPLOAD_FOLDER no está configurado.'
            )

        # ----------------------------------------------------
        # CARPETA DEL REPORTE
        # ----------------------------------------------------

        carpeta_reporte = os.path.join(
            upload_folder,
            'evidencias',
            str(reporte_id)
        )

        os.makedirs(
            carpeta_reporte,
            exist_ok=True
        )

        # ----------------------------------------------------
        # NOMBRE
        # ----------------------------------------------------

        nombre_original = secure_filename(
            nombre_imagen or 'imagen'
        )

        timestamp = datetime.now().strftime(
            '%Y%m%d_%H%M%S_%f'
        )

        nombre_final = (
            f'{timestamp}_{nombre_original}'
        )

        ruta_final = os.path.join(
            carpeta_reporte,
            nombre_final
        )

        # ----------------------------------------------------
        # MOVER
        # ----------------------------------------------------

        os.replace(
            imagen_temporal,
            ruta_final
        )

        return ruta_final

    # ========================================================
    # ANALIZAR CON IA
    # ========================================================

    @staticmethod
    def analizar_con_ia(
        imagen_path,
        gemini
    ):
        """
        Analiza una imagen utilizando GeminiService.
        """

        if not imagen_path:

            return None

        if not gemini:

            return None

        try:

            return gemini.analizar_imagen(
                imagen_path
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                'No fue posible analizar la imagen '
                f'con Gemini: {exc}'
            )

            return None

    # ========================================================
    # SIGUIENTE NÚMERO DE ACTIVIDAD
    # ========================================================

    @staticmethod
    def obtener_siguiente_numero(
        reporte
    ):
        """
        Obtiene el siguiente número consecutivo
        de actividad dentro del reporte.
        """

        actividades = reporte.evidencias

        if not actividades:

            return 1

        numeros = [
            evidencia.numero_actividad
            for evidencia in actividades
            if evidencia.numero_actividad is not None
        ]

        if not numeros:

            return 1

        return max(numeros) + 1

    # ========================================================
    # CREAR EVIDENCIA
    # ========================================================

    @staticmethod
    def crear_evidencia(
        reporte,
        anuncio,
        fecha,
        ruta_imagen,
        descripcion_visual_ia=''
    ):
        """
        Crea una evidencia utilizando exactamente
        las columnas definidas en el modelo Evidencia.
        """

        numero_actividad = (
            EvidenciaService.obtener_siguiente_numero(
                reporte
            )
        )

        # ----------------------------------------------------
        # CREAR OBJETO
        # ----------------------------------------------------

        evidencia = Evidencia(
            numero_actividad=numero_actividad,

            imagen_path=ruta_imagen,

            anuncio_usuario=(
                anuncio or ''
            ),

            descripcion_visual_ia=(
                descripcion_visual_ia or ''
            ),

            descripcion_actividad='',

            fecha_actividad=fecha,

            reporte_id=reporte.id
        )

        # ----------------------------------------------------
        # GENERAR DESCRIPCIÓN
        # ----------------------------------------------------

        try:

            obligacion = reporte.obligacion

            evidencia.descripcion_actividad = (
                evidencia.generar_descripcion_automatica(
                    obligacion
                )
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                'No fue posible generar la descripción '
                f'automática: {exc}'
            )

            evidencia.descripcion_actividad = (
                anuncio or
                'Actividad realizada durante '
                'el periodo reportado.'
            )

        db.session.add(
            evidencia
        )

        return evidencia


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def procesar_evidencia(
    reporte,
    obligacion,
    anuncio,
    fecha,
    nombre_imagen,
    imagenes,
    gemini,
    actualizar_progreso=None,
    job_id=None
):
    """
    Procesa una evidencia individual.

    Es la función principal consumida por
    CargaMasivaService.
    """

    errores = []

    # ========================================================
    # VALIDACIONES
    # ========================================================

    if reporte is None:

        return {
            'creada': False,
            'errores': [
                'No se recibió un reporte válido.'
            ],
            'evidencia': None
        }

    # ========================================================
    # SIN IMAGEN
    # ========================================================

    if not nombre_imagen:

        try:

            evidencia = (
                EvidenciaService.crear_evidencia(
                    reporte=reporte,
                    anuncio=anuncio,
                    fecha=fecha,
                    ruta_imagen='',
                    descripcion_visual_ia=''
                )
            )

            return {
                'creada': True,
                'errores': [],
                'evidencia': evidencia
            }

        except Exception as exc:

            db.session.rollback()

            return {
                'creada': False,
                'errores': [
                    (
                        'No fue posible crear la actividad: '
                        f'{str(exc)}'
                    )
                ],
                'evidencia': None
            }

    # ========================================================
    # BUSCAR IMAGEN
    # ========================================================

    imagen_temporal = (
        EvidenciaService.obtener_imagen_temporal(
            nombre_imagen,
            imagenes
        )
    )

    if not imagen_temporal:

        errores.append(
            (
                f'No se encontró la imagen '
                f'"{nombre_imagen}".'
            )
        )

        return {
            'creada': False,
            'errores': errores,
            'evidencia': None
        }

    # ========================================================
    # GUARDAR IMAGEN
    # ========================================================

    try:

        ruta_imagen = (
            EvidenciaService.guardar_imagen_evidencia(
                imagen_temporal=imagen_temporal,
                reporte_id=reporte.id,
                nombre_imagen=nombre_imagen
            )
        )

    except Exception as exc:

        errores.append(
            (
                f'No fue posible guardar la imagen '
                f'"{nombre_imagen}": {str(exc)}'
            )
        )

        return {
            'creada': False,
            'errores': errores,
            'evidencia': None
        }

    # ========================================================
    # ANALIZAR CON GEMINI
    # ========================================================

    descripcion_visual_ia = ''

    if gemini:

        try:

            descripcion_visual_ia = (
                EvidenciaService.analizar_con_ia(
                    imagen_path=ruta_imagen,
                    gemini=gemini
                )
                or ''
            )

        except Exception as exc:

            errores.append(
                (
                    'La imagen fue guardada, pero '
                    f'no pudo analizarse con IA: {str(exc)}'
                )
            )

    # ========================================================
    # CREAR EVIDENCIA
    # ========================================================

    try:

        evidencia = (
            EvidenciaService.crear_evidencia(
                reporte=reporte,
                anuncio=anuncio,
                fecha=fecha,
                ruta_imagen=ruta_imagen,
                descripcion_visual_ia=(
                    descripcion_visual_ia
                )
            )
        )

        return {
            'creada': True,
            'errores': errores,
            'evidencia': evidencia
        }

    except Exception as exc:

        db.session.rollback()

        errores.append(
            (
                'No fue posible crear el registro '
                f'de evidencia: {str(exc)}'
            )
        )

        return {
            'creada': False,
            'errores': errores,
            'evidencia': None
        }


# ============================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================

def obtener_imagen_temporal(
    nombre_imagen,
    imagenes_disponibles
):
    """
    Compatibilidad con código anterior.
    """

    return EvidenciaService.obtener_imagen_temporal(
        nombre_imagen,
        imagenes_disponibles
    )


def guardar_imagen_evidencia(
    imagen_temporal,
    reporte_id,
    nombre_imagen
):
    """
    Compatibilidad con código anterior.
    """

    return EvidenciaService.guardar_imagen_evidencia(
        imagen_temporal,
        reporte_id,
        nombre_imagen
    )


def analizar_evidencia_con_ia(
    imagen_path,
    gemini
):
    """
    Compatibilidad con código anterior.
    """

    return EvidenciaService.analizar_con_ia(
        imagen_path,
        gemini
    )
