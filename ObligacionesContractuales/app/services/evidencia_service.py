"""
Servicio para gestionar evidencias contractuales.

Responsabilidades:

- Buscar imágenes temporales.
- Guardar/mover imágenes.
- Obtener el siguiente número de actividad.
- Crear registros Evidencia.
- Generar la descripción de la actividad.
- Consultar evidencias.

El análisis mediante Gemini pertenece a GeminiService.

Este servicio no contiene rutas Flask.
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
    Servicio encargado de la gestión de evidencias.
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

        La imagen puede ser:

        - una ruta temporal;
        - un FileStorage;
        - None.

        Args:
            reporte:
                Objeto ReporteMensual.

            imagen:
                Archivo o ruta de imagen.

            anuncio:
                Texto ingresado por el usuario.

            fecha:
                Fecha de la actividad.

            descripcion:
                Descripción visual generada por Gemini.

        Returns:
            Evidencia
        """

        if reporte is None:

            raise ValueError(
                'No se recibió el reporte.'
            )

        anuncio = str(
            anuncio or ''
        ).strip()

        if not anuncio:

            anuncio = (
                'Actividad contractual realizada '
                'durante el periodo reportado.'
            )

        # ----------------------------------------------------
        # SIGUIENTE ACTIVIDAD
        # ----------------------------------------------------

        numero_actividad = (
            self._obtener_siguiente_actividad(
                reporte.id
            )
        )

        # ----------------------------------------------------
        # GUARDAR IMAGEN
        # ----------------------------------------------------

        imagen_path = (
            self._guardar_imagen(
                imagen=imagen,
                reporte_id=reporte.id,
                numero_actividad=numero_actividad
            )
        )

        # ----------------------------------------------------
        # DESCRIPCIÓN DE ACTIVIDAD
        # ----------------------------------------------------

        descripcion_actividad = (
            self._generar_descripcion_actividad(
                reporte=reporte,
                anuncio=anuncio
            )
        )

        # ----------------------------------------------------
        # CREAR EVIDENCIA
        # ----------------------------------------------------

        evidencia = Evidencia(
            numero_actividad=numero_actividad,

            imagen_path=imagen_path,

            anuncio_usuario=anuncio,

            descripcion_visual_ia=(
                descripcion or ''
            ),

            descripcion_actividad=(
                descripcion_actividad
            ),

            fecha_actividad=fecha,

            reporte_id=reporte.id
        )

        db.session.add(
            evidencia
        )

        return evidencia

    # ========================================================
    # SIGUIENTE ACTIVIDAD
    # ========================================================

    @staticmethod
    def _obtener_siguiente_actividad(
        reporte_id
    ):
        """
        Obtiene el siguiente número consecutivo
        de actividad dentro del reporte.
        """

        ultima = (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia
                .numero_actividad
                .desc()
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

    @staticmethod
    def _guardar_imagen(
        imagen,
        reporte_id,
        numero_actividad
    ):
        """
        Guarda una imagen en UPLOAD_FOLDER.

        Acepta:

        - Flask FileStorage.
        - Ruta física.
        - None.

        Returns:
            str:
                Ruta final de la imagen.
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
        # NOMBRE ORIGINAL
        # ----------------------------------------------------

        nombre_original = getattr(
            imagen,
            'filename',
            None
        )

        if nombre_original:

            nombre_original = (
                secure_filename(
                    nombre_original
                )
            )

        else:

            nombre_original = (
                secure_filename(
                    os.path.basename(
                        str(imagen)
                    )
                )
            )

        if not nombre_original:

            raise ValueError(
                'No fue posible determinar '
                'el nombre de la imagen.'
            )

        extension = (
            os.path.splitext(
                nombre_original
            )[1]
            or
            '.jpg'
        )

        # ----------------------------------------------------
        # NOMBRE FINAL
        # ----------------------------------------------------

        timestamp = (
            datetime.now()
            .strftime(
                '%Y%m%d_%H%M%S_%f'
            )
        )

        nombre_final = secure_filename(
            (
                f'evidencia_'
                f'{reporte_id}_'
                f'{numero_actividad}_'
                f'{timestamp}'
                f'{extension}'
            )
        )

        ruta_final = os.path.join(
            upload_folder,
            nombre_final
        )

        # ----------------------------------------------------
        # FILE STORAGE
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
        # RUTA FÍSICA
        # ----------------------------------------------------

        ruta_origen = os.path.abspath(
            str(imagen)
        )

        if not os.path.isfile(
            ruta_origen
        ):

            raise FileNotFoundError(
                f'No existe la imagen: '
                f'{imagen}'
            )

        os.replace(
            ruta_origen,
            ruta_final
        )

        return ruta_final

    # ========================================================
    # OBTENER IMAGEN TEMPORAL
    # ========================================================

    @staticmethod
    def obtener_imagen_temporal(
        nombre_imagen,
        imagenes_disponibles
    ):
        """
        Busca una imagen en los archivos temporales.

        La imagen encontrada se elimina del diccionario
        para impedir que sea utilizada nuevamente.
        """

        if not nombre_imagen:

            return None

        if not imagenes_disponibles:

            return None

        # ----------------------------------------------------
        # COINCIDENCIA EXACTA
        # ----------------------------------------------------

        if (
            nombre_imagen
            in imagenes_disponibles
        ):

            return (
                imagenes_disponibles.pop(
                    nombre_imagen
                )
            )

        # ----------------------------------------------------
        # NOMBRE SEGURO
        # ----------------------------------------------------

        nombre_seguro = secure_filename(
            str(nombre_imagen)
        )

        if (
            nombre_seguro
            in imagenes_disponibles
        ):

            return (
                imagenes_disponibles.pop(
                    nombre_seguro
                )
            )

        # ----------------------------------------------------
        # COMPARACIÓN NORMALIZADA
        # ----------------------------------------------------

        nombre_normalizado = (
            nombre_seguro.lower()
        )

        for clave in list(
            imagenes_disponibles.keys()
        ):

            clave_normalizada = (
                secure_filename(
                    str(clave)
                ).lower()
            )

            if (
                clave_normalizada
                == nombre_normalizado
            ):

                return (
                    imagenes_disponibles.pop(
                        clave
                    )
                )

        return None

    # ========================================================
    # GENERAR DESCRIPCIÓN
    # ========================================================

    @staticmethod
    def _generar_descripcion_actividad(
        reporte,
        anuncio
    ):
        """
        Genera la descripción automática de la actividad.

        Se utiliza el método existente del modelo Evidencia
        para conservar la lógica actual de la aplicación.
        """

        try:

            obligacion = (
                reporte.obligacion
            )

            evidencia_temporal = Evidencia(
                anuncio_usuario=anuncio
            )

            return (
                evidencia_temporal
                .generar_descripcion_automatica(
                    obligacion
                )
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                'No fue posible generar la '
                'descripción automática: '
                f'{exc}'
            )

            return (
                anuncio
                or
                'Actividad realizada durante '
                'el periodo reportado.'
            )

    # ========================================================
    # COMPATIBILIDAD
    # ========================================================

    def guardar_imagen_evidencia(
        self,
        imagen_temporal,
        reporte_id,
        nombre_imagen
    ):
        """
        Método de compatibilidad.

        IMPORTANTE:
        Este método se mantiene para código antiguo.

        La carga masiva nueva debe utilizar
        crear_evidencia() directamente para que
        el número de actividad sea correcto.
        """

        if not imagen_temporal:

            return ''

        # ----------------------------------------------------
        # Obtener siguiente actividad
        # ----------------------------------------------------

        numero_actividad = (
            self._obtener_siguiente_actividad(
                reporte_id
            )
        )

        return self._guardar_imagen(
            imagen=imagen_temporal,
            reporte_id=reporte_id,
            numero_actividad=numero_actividad
        )

    # ========================================================
    # OBTENER POR ID
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
    # OBTENER POR REPORTE
    # ========================================================

    @staticmethod
    def obtener_por_reporte(
        reporte_id
    ):
        """
        Obtiene todas las evidencias de un reporte.
        """

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia
                .numero_actividad
                .asc()
            )
            .all()
        )

    # ========================================================
    # CONTAR
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
# INSTANCIA
# ============================================================

evidencia_service = (
    EvidenciaService()
)
