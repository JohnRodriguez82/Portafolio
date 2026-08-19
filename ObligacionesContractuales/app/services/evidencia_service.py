"""
Servicio para gestionar evidencias.

Responsabilidades:

- Resolver archivos de evidencia.
- Guardar imágenes.
- Generar el número de actividad.
- Crear registros Evidencia.
- Generar la descripción de actividad.
- Mantener separada la lógica de persistencia.

El análisis de Gemini pertenece a GeminiService.

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


class EvidenciaService:
    """
    Servicio para gestionar evidencias contractuales.
    """

    # ========================================================
    # CREAR EVIDENCIA
    # ========================================================

    def crear_evidencia(
        self,
        reporte,
        imagen=None,
        anuncio=None,
        fecha=None,
        descripcion=None
    ):
        """
        Crea una evidencia asociada a un reporte.

        Args:
            reporte:
                Objeto ReporteMensual.

            imagen:
                Archivo FileStorage o ruta de archivo.

            anuncio:
                Texto ingresado por el usuario.

            fecha:
                Fecha de la actividad.

            descripcion:
                Descripción generada por Gemini.

        Returns:
            Evidencia
        """

        if reporte is None:
            raise ValueError(
                "No se recibió el reporte."
            )

        anuncio = (
            str(anuncio or '').strip()
        )

        if not anuncio:
            anuncio = (
                'Actividad contractual realizada '
                'durante el periodo reportado.'
            )

        # ----------------------------------------------------
        # Número de actividad
        # ----------------------------------------------------

        numero_actividad = (
            self._obtener_siguiente_actividad(
                reporte.id
            )
        )

        # ----------------------------------------------------
        # Guardar imagen
        # ----------------------------------------------------

        imagen_path = (
            self._guardar_imagen(
                imagen=imagen,
                reporte_id=reporte.id,
                numero_actividad=numero_actividad
            )
        )

        # ----------------------------------------------------
        # Descripción
        # ----------------------------------------------------

        descripcion_actividad = (
            descripcion
            or
            self._generar_descripcion(
                anuncio=anuncio,
                numero_actividad=numero_actividad
            )
        )

        # ----------------------------------------------------
        # Crear registro
        # ----------------------------------------------------

        evidencia = Evidencia(
            numero_actividad=numero_actividad,
            imagen_path=imagen_path,
            anuncio_usuario=anuncio,
            descripcion_visual_ia=descripcion,
            descripcion_actividad=descripcion_actividad,
            fecha_actividad=fecha,
            reporte_id=reporte.id
        )

        db.session.add(
            evidencia
        )

        db.session.flush()

        return evidencia

    # ========================================================
    # OBTENER SIGUIENTE ACTIVIDAD
    # ========================================================

    def _obtener_siguiente_actividad(
        self,
        reporte_id
    ):
        """
        Obtiene el siguiente número de actividad.
        """

        ultima = (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia.numero_actividad.desc()
            )
            .first()
        )

        if ultima is None:
            return 1

        return (
            ultima.numero_actividad + 1
        )

    # ========================================================
    # GUARDAR IMAGEN
    # ========================================================

    def _guardar_imagen(
        self,
        imagen,
        reporte_id,
        numero_actividad
    ):
        """
        Guarda una imagen en UPLOAD_FOLDER.

        Acepta:

        - Flask FileStorage.
        - Ruta de archivo.
        - None.

        Returns:
            str
        """

        if imagen is None:
            return ''

        upload_folder = (
            current_app.config.get(
                'UPLOAD_FOLDER'
            )
        )

        if not upload_folder:
            raise RuntimeError(
                'UPLOAD_FOLDER no está configurado.'
            )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        # ----------------------------------------------------
        # Nombre original
        # ----------------------------------------------------

        nombre_original = getattr(
            imagen,
            'filename',
            None
        )

        if nombre_original:
            nombre_original = secure_filename(
                nombre_original
            )
        else:
            nombre_original = secure_filename(
                os.path.basename(
                    str(imagen)
                )
            )

        if not nombre_original:
            raise ValueError(
                'No fue posible determinar el nombre '
                'de la imagen.'
            )

        extension = (
            os.path.splitext(
                nombre_original
            )[1]
            or
            '.jpg'
        )

        nombre_final = secure_filename(
            (
                f'evidencia_'
                f'{reporte_id}_'
                f'{numero_actividad}_'
                f'{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}'
                f'{extension}'
            )
        )

        ruta_final = os.path.join(
            upload_folder,
            nombre_final
        )

        # ----------------------------------------------------
        # FileStorage
        # ----------------------------------------------------

        if hasattr(
            imagen,
            'save'
        ):
            imagen.save(
                ruta_final
            )

            return ruta_final

        # ----------------------------------------------------
        # Ruta física
        # ----------------------------------------------------

        ruta_origen = os.path.abspath(
            str(imagen)
        )

        if not os.path.isfile(
            ruta_origen
        ):
            raise FileNotFoundError(
                f'No existe la imagen: {imagen}'
            )

        os.replace(
            ruta_origen,
            ruta_final
        )

        return ruta_final

    # ========================================================
    # GENERAR DESCRIPCIÓN
    # ========================================================

    @staticmethod
    def _generar_descripcion(
        anuncio,
        numero_actividad
    ):
        """
        Genera una descripción básica cuando Gemini
        no está disponible.

        La generación inteligente de contenido visual
        pertenece a GeminiService.
        """

        return (
            f'{anuncio}. '
            'Esta actividad corresponde al cumplimiento '
            'de las obligaciones contractuales durante '
            'el periodo reportado.'
        )

    # ========================================================
    # OBTENER IMAGEN TEMPORAL
    # ========================================================

    @staticmethod
    def obtener_imagen_temporal(
        nombre_imagen,
        imagenes_disponibles
    ):
        """
        Busca y consume una imagen del diccionario.

        Se mantiene como método de compatibilidad para
        otros procesos de la aplicación.
        """

        if not nombre_imagen:
            return None

        if not imagenes_disponibles:
            return None

        if nombre_imagen in imagenes_disponibles:
            return imagenes_disponibles.pop(
                nombre_imagen
            )

        safe_name = secure_filename(
            str(nombre_imagen)
        )

        if safe_name in imagenes_disponibles:
            return imagenes_disponibles.pop(
                safe_name
            )

        # Comparación normalizada
        nombre_normalizado = (
            safe_name.lower()
        )

        for clave in list(
            imagenes_disponibles.keys()
        ):
            clave_normalizada = secure_filename(
                str(clave)
            ).lower()

            if clave_normalizada == nombre_normalizado:
                return imagenes_disponibles.pop(
                    clave
                )

        return None

    # ========================================================
    # GUARDAR IMAGEN DE EVIDENCIA
    # ========================================================

    def guardar_imagen_evidencia(
        self,
        imagen_temporal,
        reporte_id,
        nombre_imagen
    ):
        """
        Guarda una imagen temporal como evidencia.

        Se mantiene como método público para compatibilidad.
        """

        if not imagen_temporal:
            return ''

        return self._guardar_imagen(
            imagen=imagen_temporal,
            reporte_id=reporte_id,
            numero_actividad=0
        )

    # ========================================================
    # OBTENER EVIDENCIA
    # ========================================================

    @staticmethod
    def obtener_por_id(
        evidencia_id
    ):
        """
        Obtiene una evidencia por ID.
        """

        return (
            Evidencia.query
            .filter_by(
                id=evidencia_id
            )
            .first()
        )

    # ========================================================
    # OBTENER EVIDENCIAS DE REPORTE
    # ========================================================

    @staticmethod
    def obtener_por_reporte(
        reporte_id
    ):
        """
        Obtiene las evidencias de un reporte.
        """

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia.numero_actividad.asc()
            )
            .all()
        )

    # ========================================================
    # CONTAR EVIDENCIAS
    # ========================================================

    @staticmethod
    def contar(
        reporte_id
    ):
        """
        Cuenta las evidencias de un reporte.
        """

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .count()
        )


# ============================================================
# INSTANCIA DEL SERVICIO
# ============================================================

evidencia_service = EvidenciaService()
