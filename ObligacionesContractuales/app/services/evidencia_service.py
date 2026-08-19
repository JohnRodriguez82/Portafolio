"""
Servicio para procesamiento de evidencias.

Responsabilidades:
- Buscar imágenes cargadas.
- Mover imágenes al almacenamiento definitivo.
- Crear registros de evidencias.
- Analizar imágenes con IA cuando sea necesario.
- Generar la descripción de la actividad.
- Mantener la lógica de evidencias fuera de los Blueprints.
"""

import os

from datetime import datetime

from pathlib import Path

from flask import current_app

from werkzeug.utils import secure_filename

from models import (
    db,
    Evidencia
)

from app.services.archivo_service import (
    ArchivoService
)


# ============================================================
# SERVICIO DE EVIDENCIAS
# ============================================================

class EvidenciaService:
    """
    Servicio encargado de gestionar las evidencias
    asociadas a los reportes mensuales.
    """

    def __init__(
        self,
        archivo_service=None
    ):
        """
        Inicializa el servicio.

        Args:
            archivo_service:
                Servicio utilizado para gestionar los
                archivos físicos.
        """

        self.archivo_service = (
            archivo_service
            or ArchivoService()
        )

    # ========================================================
    # OBTENER IMAGEN TEMPORAL
    # ========================================================

    def obtener_imagen_temporal(
        self,
        nombre_imagen,
        imagenes_disponibles
    ):
        """
        Busca una imagen por nombre y la consume
        del diccionario de imágenes disponibles.

        Esto evita que una misma imagen sea utilizada
        más de una vez durante la carga masiva.

        Args:
            nombre_imagen:
                Nombre indicado en el Excel.

            imagenes_disponibles:
                Diccionario de imágenes disponibles.

        Returns:
            Archivo/ruta de la imagen o None.
        """

        if not nombre_imagen:

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

        # Comparación adicional sin diferencias
        # de mayúsculas/minúsculas.

        nombre_normalizado = (
            self._normalizar_nombre_archivo(
                nombre_imagen
            )
        )

        for nombre, imagen in list(
            imagenes_disponibles.items()
        ):

            if (
                self._normalizar_nombre_archivo(
                    nombre
                )
                ==
                nombre_normalizado
            ):

                return imagenes_disponibles.pop(
                    nombre
                )

        return None

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
        Crea una evidencia asociada a un reporte mensual.

        Esta es la interfaz principal utilizada por
        CargaMasivaService.

        Args:
            reporte:
                Instancia de ReporteMensual.

            imagen:
                Archivo de imagen recibido mediante Flask
                o ruta de archivo.

            anuncio:
                Texto/contexto indicado por el usuario.

            fecha:
                Fecha de la actividad.

            descripcion:
                Descripción generada por Gemini.

        Returns:
            Evidencia creada.

        Raises:
            ValueError:
                Si no se proporciona un reporte.
        """

        if reporte is None:

            raise ValueError(
                "No se proporcionó el reporte "
                "para crear la evidencia."
            )

        # ----------------------------------------------------
        # Número consecutivo de actividad
        # ----------------------------------------------------

        numero_actividad = (
            self._obtener_siguiente_numero_actividad(
                reporte
            )
        )

        # ----------------------------------------------------
        # Imagen
        # ----------------------------------------------------

        imagen_path = ""

        if imagen:

            imagen_path = (
                self._guardar_imagen(
                    imagen=imagen,
                    reporte=reporte
                )
            )

        # ----------------------------------------------------
        # Texto del anuncio
        # ----------------------------------------------------

        anuncio_usuario = (
            str(anuncio).strip()
            if anuncio
            else ""
        )

        # ----------------------------------------------------
        # Descripción visual de IA
        # ----------------------------------------------------

        descripcion_visual_ia = (
            str(descripcion).strip()
            if descripcion
            else None
        )

        # ----------------------------------------------------
        # Crear objeto Evidencia
        # ----------------------------------------------------

        evidencia = Evidencia(

            numero_actividad=(
                numero_actividad
            ),

            imagen_path=(
                imagen_path
            ),

            anuncio_usuario=(
                anuncio_usuario
            ),

            descripcion_visual_ia=(
                descripcion_visual_ia
            ),

            descripcion_actividad=(
                anuncio_usuario
            ),

            fecha_actividad=(
                self._normalizar_fecha(
                    fecha
                )
            ),

            reporte_id=(
                reporte.id
            )
        )

        # ----------------------------------------------------
        # Generar descripción automática
        # ----------------------------------------------------

        try:

            descripcion_generada = (
                evidencia.generar_descripcion_automatica(
                    reporte.obligacion
                )
            )

            if descripcion_generada:

                evidencia.descripcion_actividad = (
                    descripcion_generada
                )

        except Exception as exc:

            # La generación automática de texto
            # no debe impedir la creación de la evidencia.

            print(
                "[ADVERTENCIA] "
                "No fue posible generar la "
                f"descripción automática: {exc}"
            )

        # ----------------------------------------------------
        # Guardar en base de datos
        # ----------------------------------------------------

        db.session.add(
            evidencia
        )

        db.session.commit()

        return evidencia

    # ========================================================
    # GUARDAR IMAGEN
    # ========================================================

    def _guardar_imagen(
        self,
        imagen,
        reporte
    ):
        """
        Guarda una imagen en el almacenamiento definitivo.

        Si el objeto recibido ya corresponde a una ruta,
        se conserva dicha ruta.

        Returns:
            str: ruta del archivo almacenado.
        """

        if not imagen:

            return ""

        # ----------------------------------------------------
        # Si ya es una ruta
        # ----------------------------------------------------

        if isinstance(
            imagen,
            (str, Path)
        ):

            ruta = Path(
                imagen
            )

            if ruta.exists():

                return self._guardar_imagen_desde_ruta(
                    ruta=ruta,
                    reporte=reporte
                )

            return str(
                ruta
            )

        # ----------------------------------------------------
        # Archivo recibido mediante Flask
        # ----------------------------------------------------

        filename = getattr(
            imagen,
            "filename",
            None
        )

        if not filename:

            raise ValueError(
                "La imagen no tiene un nombre de archivo válido."
            )

        # ----------------------------------------------------
        # Obtener carpeta de uploads
        # ----------------------------------------------------

        upload_folder = (
            current_app.config[
                "UPLOAD_FOLDER"
            ]
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        # ----------------------------------------------------
        # Nombre seguro
        # ----------------------------------------------------

        nombre_seguro = secure_filename(
            filename
        )

        if not nombre_seguro:

            raise ValueError(
                "No fue posible generar un nombre "
                "válido para la imagen."
            )

        # ----------------------------------------------------
        # Nombre definitivo
        # ----------------------------------------------------

        timestamp = (
            datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )

        nombre_final = (
            f"evidencia_"
            f"{reporte.id}_"
            f"{timestamp}_"
            f"{nombre_seguro}"
        )

        ruta_final = os.path.join(
            upload_folder,
            nombre_final
        )

        # ----------------------------------------------------
        # Guardar archivo
        # ----------------------------------------------------

        imagen.save(
            ruta_final
        )

        return ruta_final

    # ========================================================
    # GUARDAR IMAGEN DESDE RUTA
    # ========================================================

    def _guardar_imagen_desde_ruta(
        self,
        ruta,
        reporte
    ):
        """
        Copia/mueve una imagen existente al almacenamiento
        definitivo.
        """

        filename = secure_filename(
            ruta.name
        )

        timestamp = (
            datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )

        nombre_final = (
            f"evidencia_"
            f"{reporte.id}_"
            f"{timestamp}_"
            f"{filename}"
        )

        upload_folder = (
            current_app.config[
                "UPLOAD_FOLDER"
            ]
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        ruta_final = (
            Path(upload_folder)
            / nombre_final
        )

        # ----------------------------------------------------
        # Mover archivo
        # ----------------------------------------------------

        try:

            os.replace(
                str(ruta),
                str(ruta_final)
            )

        except OSError:

            # Si no se puede mover, intentamos copiar
            # y posteriormente eliminar el original.

            import shutil

            shutil.copy2(
                str(ruta),
                str(ruta_final)
            )

            try:

                ruta.unlink()

            except OSError:

                pass

        return str(
            ruta_final
        )

    # ========================================================
    # SIGUIENTE NÚMERO DE ACTIVIDAD
    # ========================================================

    @staticmethod
    def _obtener_siguiente_numero_actividad(
        reporte
    ):
        """
        Obtiene el siguiente número consecutivo de actividad
        dentro del reporte.

        Ejemplo:

            Actividad 1
            Actividad 2
            Actividad 3

        """

        evidencias = (
            reporte.evidencias
            or []
        )

        if not evidencias:

            return 1

        numeros = [

            evidencia.numero_actividad

            for evidencia in evidencias

            if evidencia.numero_actividad
            is not None

        ]

        if not numeros:

            return 1

        return max(
            numeros
        ) + 1

    # ========================================================
    # NORMALIZAR FECHA
    # ========================================================

    @staticmethod
    def _normalizar_fecha(
        fecha
    ):
        """
        Convierte diferentes formatos de fecha
        a datetime.date.

        Soporta:

            datetime.date
            datetime.datetime
            YYYY-MM-DD
            DD/MM/YYYY
        """

        if not fecha:

            return None

        # ----------------------------------------------------
        # datetime
        # ----------------------------------------------------

        if isinstance(
            fecha,
            datetime
        ):

            return fecha.date()

        # ----------------------------------------------------
        # date
        # ----------------------------------------------------

        from datetime import date

        if isinstance(
            fecha,
            date
        ):

            return fecha

        # ----------------------------------------------------
        # Texto
        # ----------------------------------------------------

        if isinstance(
            fecha,
            str
        ):

            fecha_limpia = (
                fecha.strip()
            )

            formatos = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y"
            ]

            for formato in formatos:

                try:

                    return datetime.strptime(
                        fecha_limpia,
                        formato
                    ).date()

                except ValueError:

                    continue

        raise ValueError(
            "Formato de fecha no válido: "
            f"{fecha}"
        )

    # ========================================================
    # NORMALIZAR NOMBRE DE ARCHIVO
    # ========================================================

    @staticmethod
    def _normalizar_nombre_archivo(
        nombre
    ):
        """
        Normaliza el nombre de un archivo para
        realizar comparaciones seguras.
        """

        if nombre is None:

            return ""

        return (
            Path(
                str(nombre).strip()
            )
            .name
            .lower()
        )

    # ========================================================
    # OBTENER RUTA DE IMAGEN
    # ========================================================

    @staticmethod
    def obtener_ruta_imagen(
        imagen
    ):
        """
        Obtiene la ruta física de una imagen.

        Soporta:
            - str
            - pathlib.Path
            - objetos con atributo ruta
            - objetos con atributo path
            - FileStorage con filename
        """

        if isinstance(
            imagen,
            (str, Path)
        ):

            return Path(
                imagen
            )

        ruta = getattr(
            imagen,
            "ruta",
            None
        )

        if ruta:

            return Path(
                ruta
            )

        ruta = getattr(
            imagen,
            "path",
            None
        )

        if ruta:

            return Path(
                ruta
            )

        nombre = getattr(
            imagen,
            "filename",
            None
        )

        if nombre:

            return Path(
                nombre
            )

        raise ValueError(
            "No fue posible determinar la ruta "
            "de la imagen."
        )

    # ========================================================
    # GUARDAR IMAGEN EVIDENCIA
    # ========================================================

    def guardar_imagen_evidencia(
        self,
        imagen_temporal,
        reporte_id,
        nombre_imagen
    ):
        """
        Mueve una imagen temporal al almacenamiento
        definitivo de evidencias.

        Este método mantiene compatibilidad con la
        lógica anterior de la aplicación.
        """

        if not imagen_temporal:

            return ""

        final_name = secure_filename(
            (
                f"evidencia_"
                f"{reporte_id}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_"
                f"{nombre_imagen}"
            )
        )

        upload_folder = (
            current_app.config[
                "UPLOAD_FOLDER"
            ]
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        final_path = os.path.join(
            upload_folder,
            final_name
        )

        os.replace(
            str(imagen_temporal),
            final_path
        )

        return final_path

    # ========================================================
    # ANALIZAR EVIDENCIA CON IA
    # ========================================================

    def analizar_evidencia_con_ia(
        self,
        imagen_path,
        api_key
    ):
        """
        Mantiene compatibilidad con la implementación
        anterior basada directamente en vision_analyzer.

        Nota:
        La nueva arquitectura utiliza GeminiService.
        Este método se conserva temporalmente para
        compatibilidad con código existente.
        """

        if not imagen_path or not api_key:

            return None

        try:

            from vision_analyzer import (
                analizar_imagen
            )

            return analizar_imagen(
                imagen_path,
                api_key
            )

        except Exception as exc:

            print(
                "[ADVERTENCIA] "
                "No fue posible analizar la evidencia "
                f"con IA: {exc}"
            )

            return None


# ============================================================
# INSTANCIA DEL SERVICIO
# ============================================================

evidencia_service = (
    EvidenciaService()
)
