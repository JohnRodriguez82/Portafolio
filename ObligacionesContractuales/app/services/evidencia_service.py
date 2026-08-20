"""
Servicio para la gestión de evidencias.

Responsabilidades:

- Crear evidencias asociadas a reportes.
- Obtener el siguiente número de actividad.
- Guardar imágenes.
- Recuperar imágenes temporales.
- Generar descripciones automáticas.
- Consultar evidencias.
"""

import os

from datetime import datetime

from flask import current_app

from werkzeug.utils import secure_filename

from app import db

from models import Evidencia

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
        - un Flask FileStorage;
        - None.

        IMPORTANTE:
        Este método se encarga de guardar la imagen cuando
        se proporciona una.

        Por lo tanto, quien utilice este método NO debe llamar
        posteriormente a guardar_imagen_evidencia() para la
        misma imagen.

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

        Ejemplo:

            Evidencias existentes:
                1
                2
                3

            Retorna:
                4
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

        Si imagen es None:
            retorna ''.
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

        # ----------------------------------------------------
        # EXTENSIÓN
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # EVITAR COLISIÓN
        # ----------------------------------------------------

        if os.path.abspath(
            ruta_origen
        ) == os.path.abspath(
            ruta_final
        ):

            return ruta_final

        # ----------------------------------------------------
        # MOVER ARCHIVO
        # ----------------------------------------------------

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

        Acepta coincidencia:

        1. Exacta.
        2. Nombre seguro.
        3. Normalizada.
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

        Utiliza el método existente del modelo Evidencia
        para conservar la lógica actual de la aplicación.

        Si la generación falla, utiliza el anuncio como
        descripción alternativa.
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
        nombre_imagen=None
    ):
        """
        Método de compatibilidad con código antiguo.

        IMPORTANTE:

        La implementación nueva debe utilizar:

            crear_evidencia()

        directamente.

        Este método permanece únicamente para código
        anterior que todavía necesite guardar una imagen
        independientemente de la creación de la evidencia.

        Returns:
            str:
                Ruta final de la imagen.
        """

        if not imagen_temporal:

            return ''

        # ----------------------------------------------------
        # OBTENER SIGUIENTE ACTIVIDAD
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

        if not evidencia_id:

            return None

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
        Obtiene todas las evidencias de un reporte,
        ordenadas por número de actividad.
        """

        if not reporte_id:

            return []

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

        if not reporte_id:

            return 0

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .count()
        )
