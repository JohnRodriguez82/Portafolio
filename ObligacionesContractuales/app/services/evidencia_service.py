"""
Servicio para procesamiento de evidencias.

Responsabilidades:
- Buscar imágenes cargadas temporalmente.
- Consumir cada imagen una sola vez.
- Mover imágenes al almacenamiento definitivo.
- Analizar imágenes mediante Gemini cuando esté disponible.
- Crear registros de Evidencia.
- Mantener la lógica de evidencias fuera del Blueprint.

Este servicio NO contiene rutas Flask.
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
    """
    Servicio encargado de gestionar las evidencias
    asociadas a un reporte.
    """

    # ========================================================
    # OBTENER IMAGEN TEMPORAL
    # ========================================================

    @staticmethod
    def obtener_imagen_temporal(
        nombre_imagen,
        imagenes_disponibles
    ):
        """
        Busca una imagen por nombre y la consume
        del diccionario de imágenes disponibles.

        La imagen se elimina del diccionario mediante pop()
        para evitar que pueda utilizarse nuevamente.

        Args:
            nombre_imagen:
                Nombre indicado en el Excel.

            imagenes_disponibles:
                Diccionario:
                    nombre_archivo -> ruta_temporal

        Returns:
            str | None:
                Ruta temporal de la imagen.
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
        Mueve una imagen temporal al almacenamiento definitivo.

        Args:
            imagen_temporal:
                Ruta temporal de la imagen.

            reporte_id:
                ID del reporte asociado.

            nombre_imagen:
                Nombre original de la imagen.

        Returns:
            str:
                Ruta definitiva de la imagen.

        Raises:
            FileNotFoundError:
                Si la imagen temporal no existe.
        """

        if not imagen_temporal:

            return ''

        if not os.path.exists(
            imagen_temporal
        ):

            raise FileNotFoundError(
                (
                    'No se encontró la imagen temporal: '
                    f'{imagen_temporal}'
                )
            )

        # ----------------------------------------------------
        # CARPETA DESTINO
        # ----------------------------------------------------

        upload_folder = current_app.config.get(
            'UPLOAD_FOLDER'
        )

        if not upload_folder:

            raise ValueError(
                'UPLOAD_FOLDER no está configurado.'
            )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        # ----------------------------------------------------
        # NOMBRE DEFINITIVO
        # ----------------------------------------------------

        nombre_original = secure_filename(
            nombre_imagen or 'imagen'
        )

        timestamp = datetime.now().strftime(
            '%Y%m%d_%H%M%S_%f'
        )

        nombre_final = secure_filename(
            (
                f'evidencia_'
                f'{reporte_id}_'
                f'{timestamp}_'
                f'{nombre_original}'
            )
        )

        ruta_final = os.path.join(
            upload_folder,
            nombre_final
        )

        # ----------------------------------------------------
        # MOVER ARCHIVO
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
        Analiza una imagen mediante Gemini.

        El servicio Gemini se recibe como dependencia para
        evitar que EvidenciaService conozca directamente
        la implementación de la IA.

        Args:
            imagen_path:
                Ruta de la imagen.

            gemini:
                Instancia de GeminiService.

        Returns:
            str | None:
                Descripción generada por IA.
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
                f'No fue posible analizar la imagen '
                f'con Gemini: {exc}'
            )

            return None

    # ========================================================
    # CREAR EVIDENCIA
    # ========================================================

    @staticmethod
    def crear_evidencia(
        reporte,
        obligacion,
        anuncio,
        fecha,
        ruta_imagen=None,
        descripcion_ia=None
    ):
        """
        Crea un registro de Evidencia.

        Esta función concentra la creación del objeto
        SQLAlchemy para evitar que CargaMasivaService
        conozca la estructura interna del modelo.

        Args:
            reporte:
                Reporte al que pertenece la evidencia.

            obligacion:
                Obligación contractual.

            anuncio:
                Contexto o anuncio de la actividad.

            fecha:
                Fecha de la actividad.

            ruta_imagen:
                Ruta definitiva de la imagen.

            descripcion_ia:
                Descripción generada por Gemini.

        Returns:
            Evidencia:
                Objeto creado.
        """

        evidencia = Evidencia(
            reporte_id=reporte.id,
            obligacion_id=obligacion.id,
            anuncio=anuncio or '',
            fecha=fecha,
            imagen=ruta_imagen or '',
            descripcion=descripcion_ia or ''
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

    Esta es la función utilizada actualmente por
    CargaMasivaService.

    Flujo:

        1. Busca la imagen.
        2. Consume la imagen del diccionario.
        3. La mueve al almacenamiento definitivo.
        4. Analiza con Gemini si está disponible.
        5. Crea el registro Evidencia.
        6. Retorna resultado estructurado.

    Args:
        reporte:
            Reporte mensual.

        obligacion:
            Obligación contractual.

        anuncio:
            Contexto/anuncio de la actividad.

        fecha:
            Fecha de la evidencia.

        nombre_imagen:
            Nombre de imagen indicado en Excel.

        imagenes:
            Diccionario nombre -> ruta temporal.

        gemini:
            Instancia de GeminiService.

        actualizar_progreso:
            Callback opcional de progreso.

        job_id:
            Identificador del trabajo.

    Returns:
        dict:
            {
                'creada': bool,
                'errores': list,
                'evidencia': Evidencia | None
            }
    """

    errores = []

    evidencia = None

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    if reporte is None:

        return {
            'creada': False,
            'errores': [
                'No se recibió un reporte válido.'
            ],
            'evidencia': None
        }

    if obligacion is None:

        return {
            'creada': False,
            'errores': [
                'No se recibió una obligación válida.'
            ],
            'evidencia': None
        }

    # ========================================================
    # SIN IMAGEN
    # ========================================================

    if not nombre_imagen:

        try:

            evidencia = EvidenciaService.crear_evidencia(
                reporte=reporte,
                obligacion=obligacion,
                anuncio=anuncio,
                fecha=fecha,
                ruta_imagen=None,
                descripcion_ia=None
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
                        'No fue posible crear la actividad '
                        f'sin imagen: {str(exc)}'
                    )
                ],
                'evidencia': None
            }

    # ========================================================
    # BUSCAR IMAGEN
    # ========================================================

    imagen_temporal = (
        EvidenciaService.obtener_imagen_temporal(
            nombre_imagen=nombre_imagen,
            imagenes_disponibles=imagenes
        )
    )

    if not imagen_temporal:

        errores.append(
            (
                f'No se encontró la imagen '
                f'"{nombre_imagen}" '
                'entre los archivos cargados.'
            )
        )

        # ----------------------------------------------------
        # CREAR ACTIVIDAD SIN IMAGEN
        # ----------------------------------------------------

        try:

            evidencia = EvidenciaService.crear_evidencia(
                reporte=reporte,
                obligacion=obligacion,
                anuncio=anuncio,
                fecha=fecha,
                ruta_imagen=None,
                descripcion_ia=None
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
                    'No fue posible crear la actividad: '
                    f'{str(exc)}'
                )
            )

            return {
                'creada': False,
                'errores': errores,
                'evidencia': None
            }

    # ========================================================
    # MOVER IMAGEN
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
    # ANALIZAR IMAGEN
    # ========================================================

    descripcion_ia = None

    if gemini:

        try:

            descripcion_ia = (
                EvidenciaService.analizar_con_ia(
                    imagen_path=ruta_imagen,
                    gemini=gemini
                )
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

        evidencia = EvidenciaService.crear_evidencia(
            reporte=reporte,
            obligacion=obligacion,
            anuncio=anuncio,
            fecha=fecha,
            ruta_imagen=ruta_imagen,
            descripcion_ia=descripcion_ia
        )

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

    # ========================================================
    # PROGRESO
    # ========================================================

    if actualizar_progreso:

        try:

            actualizar_progreso(
                job_id,
                'procesando',
                0,
                (
                    f'Evidencia procesada: '
                    f'{nombre_imagen}'
                )
            )

        except Exception:
            pass

    # ========================================================
    # RESULTADO
    # ========================================================

    return {
        'creada': True,
        'errores': errores,
        'evidencia': evidencia
    }


# ============================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================

def obtener_imagen_temporal(
    nombre_imagen,
    imagenes_disponibles
):
    """
    Wrapper de compatibilidad.

    Permite mantener llamadas antiguas mientras
    la aplicación termina la refactorización.
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
    Wrapper de compatibilidad para código existente.
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
    Wrapper de compatibilidad.

    Nota:
        La nueva implementación utiliza GeminiService.
    """

    return EvidenciaService.analizar_con_ia(
        imagen_path,
        gemini
    )
