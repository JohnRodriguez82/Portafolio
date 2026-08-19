"""
Servicio de procesamiento de carga masiva de evidencias.

Responsabilidades:
- Coordinar el procesamiento de un archivo Excel.
- Procesar las evidencias asociadas.
- Utilizar Gemini cuando esté disponible.
- Coordinar la creación/actualización de reportes.
- Centralizar errores y resultados del procesamiento.

Este servicio NO contiene rutas Flask.
"""

from pathlib import Path


from app.services.excel_service import (
    ExcelService
)

from app.services.evidencia_service import (
    EvidenciaService
)

from app.services.contrato_service import (
    ContratoService
)

from app.services.reporte_service import (
    ReporteService
)

from app.services.gemini_service import (
    GeminiService,
    gemini_service
)


# ============================================================
# SERVICIO DE CARGA MASIVA
# ============================================================

class CargaMasivaService:
    """
    Servicio principal para coordinar una carga masiva.
    """

    def __init__(
        self,
        excel_service=None,
        evidencia_service=None,
        contrato_service=None,
        reporte_service=None,
        gemini=None
    ):
        """
        Inicializa los servicios utilizados por la carga masiva.

        Se permite inyectar los servicios para facilitar
        pruebas y mantener bajo acoplamiento.
        """

        self.excel_service = (
            excel_service
            or ExcelService()
        )

        self.evidencia_service = (
            evidencia_service
            or EvidenciaService()
        )

        self.contrato_service = (
            contrato_service
            or ContratoService()
        )

        self.reporte_service = (
            reporte_service
            or ReporteService()
        )

        self.gemini = (
            gemini
            or gemini_service
        )

    # ========================================================
    # PROCESAR CARGA
    # ========================================================

    def procesar(
        self,
        archivo_excel,
        imagenes,
        mes,
        anio,
        usuario=None,
        contrato=None
    ):
        """
        Procesa una carga masiva completa.

        Args:
            archivo_excel:
                Archivo Excel recibido.

            imagenes:
                Lista de imágenes recibidas.

            mes:
                Mes del reporte.

            anio:
                Año del reporte.

            usuario:
                Usuario que realiza la carga.

            contrato:
                Contrato asociado, si ya fue identificado.

        Returns:
            dict:
                Resultado del procesamiento.
        """

        resultado = {
            "exitosos": 0,
            "errores": [],
            "advertencias": [],
            "mes": mes,
            "anio": anio
        }

        # ----------------------------------------------------
        # Validaciones iniciales
        # ----------------------------------------------------

        if not archivo_excel:

            raise ValueError(
                "No se recibió el archivo Excel."
            )

        if not mes:

            raise ValueError(
                "Debe indicar el mes."
            )

        if not anio:

            raise ValueError(
                "Debe indicar el año."
            )

        # ----------------------------------------------------
        # Guardar/leer Excel
        # ----------------------------------------------------

        try:

            datos = (
                self.excel_service.leer_excel(
                    archivo_excel
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "No fue posible procesar el archivo Excel: "
                f"{exc}"
            ) from exc

        if not datos:

            resultado["advertencias"].append(
                "El archivo Excel no contiene registros "
                "para procesar."
            )

            return resultado

        # ----------------------------------------------------
        # Preparar imágenes
        # ----------------------------------------------------

        imagenes_por_nombre = (
            self._indexar_imagenes(
                imagenes
            )
        )

        # ----------------------------------------------------
        # Procesar registros
        # ----------------------------------------------------

        for indice, registro in enumerate(
            datos,
            start=1
        ):

            try:

                resultado_registro = (
                    self._procesar_registro(
                        registro=registro,
                        imagenes_por_nombre=(
                            imagenes_por_nombre
                        ),
                        mes=mes,
                        anio=anio,
                        usuario=usuario,
                        contrato=contrato
                    )
                )

                if resultado_registro:

                    resultado["exitosos"] += 1

            except Exception as exc:

                resultado["errores"].append(
                    {
                        "fila": indice,
                        "error": str(exc)
                    }
                )

        return resultado

    # ========================================================
    # PROCESAR REGISTRO
    # ========================================================

    def _procesar_registro(
        self,
        registro,
        imagenes_por_nombre,
        mes,
        anio,
        usuario=None,
        contrato=None
    ):
        """
        Procesa una fila del Excel.
        """

        obligacion = (
            registro.get(
                "obligacion"
            )
        )

        anuncio = (
            registro.get(
                "anuncio"
            )
        )

        fecha = (
            registro.get(
                "fecha"
            )
        )

        nombre_imagen = (
            registro.get(
                "nombre_imagen"
            )
        )

        # ----------------------------------------------------
        # Validar obligación
        # ----------------------------------------------------

        if not obligacion:

            raise ValueError(
                "La fila no contiene obligación."
            )

        # ----------------------------------------------------
        # Buscar contrato
        # ----------------------------------------------------

        contrato_actual = contrato

        if contrato_actual is None:

            contrato_actual = (
                self.contrato_service.obtener_contrato(
                    usuario=usuario
                )
            )

        if contrato_actual is None:

            raise ValueError(
                "No fue posible identificar el contrato."
            )

        # ----------------------------------------------------
        # Buscar/crear reporte
        # ----------------------------------------------------

        reporte = (
            self.reporte_service.obtener_o_crear_reporte(
                contrato=contrato_actual,
                obligacion=obligacion,
                mes=mes,
                anio=anio
            )
        )

        # ----------------------------------------------------
        # Preparar evidencia
        # ----------------------------------------------------

        imagen = None

        if nombre_imagen:

            imagen = (
                imagenes_por_nombre.get(
                    self._normalizar_nombre_archivo(
                        nombre_imagen
                    )
                )
            )

            if imagen is None:

                raise FileNotFoundError(
                    "No se encontró la imagen "
                    f"'{nombre_imagen}'."
                )

        # ----------------------------------------------------
        # Analizar imagen con Gemini
        # ----------------------------------------------------

        descripcion_ia = None

        if imagen and self.gemini.activo:

            ruta_imagen = (
                self._obtener_ruta_imagen(
                    imagen
                )
            )

            contexto = (
                anuncio
                or
                obligacion
            )

            descripcion_ia = (
                self.gemini.analizar_imagen_con_reintentos(
                    ruta_imagen=ruta_imagen,
                    contexto=contexto
                )
            )

        # ----------------------------------------------------
        # Crear evidencia
        # ----------------------------------------------------

        evidencia = (
            self.evidencia_service.crear_evidencia(
                reporte=reporte,
                imagen=imagen,
                anuncio=anuncio,
                fecha=fecha,
                descripcion=descripcion_ia
            )
        )

        return evidencia

    # ========================================================
    # INDEXAR IMÁGENES
    # ========================================================

    def _indexar_imagenes(
        self,
        imagenes
    ):
        """
        Crea un diccionario:

            nombre_archivo -> archivo

        para localizar rápidamente las imágenes
        indicadas en el Excel.
        """

        resultado = {}

        if not imagenes:
            return resultado

        for imagen in imagenes:

            nombre = getattr(
                imagen,
                "filename",
                None
            )

            if not nombre:
                continue

            nombre_normalizado = (
                self._normalizar_nombre_archivo(
                    nombre
                )
            )

            resultado[
                nombre_normalizado
            ] = imagen

        return resultado

    # ========================================================
    # NORMALIZAR NOMBRE
    # ========================================================

    @staticmethod
    def _normalizar_nombre_archivo(
        nombre
    ):
        """
        Normaliza el nombre de una imagen para realizar
        comparaciones seguras.
        """

        if nombre is None:
            return ""

        return Path(
            str(nombre).strip()
        ).name.lower()

    # ========================================================
    # OBTENER RUTA DE IMAGEN
    # ========================================================

    @staticmethod
    def _obtener_ruta_imagen(
        imagen
    ):
        """
        Obtiene la ruta física de una imagen.

        Dependiendo de cómo se haya guardado el archivo,
        puede tratarse de un objeto Werkzeug FileStorage
        o directamente de una ruta.
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
            return Path(ruta)

        ruta = getattr(
            imagen,
            "path",
            None
        )

        if ruta:
            return Path(ruta)

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


# ============================================================
# INSTANCIA DEL SERVICIO
# ============================================================

carga_masiva_service = (
    CargaMasivaService()
)
