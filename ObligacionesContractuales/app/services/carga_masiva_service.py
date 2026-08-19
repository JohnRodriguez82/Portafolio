"""
Servicio principal de carga masiva mensual.

CargaMasivaService actúa como orquestador de la carga masiva.

Responsabilidades delegadas:

    ExcelService
        - Lectura y normalización del archivo Excel.

    ContratoService
        - Validación del contrato.
        - Consulta de obligaciones.

    ReporteService
        - Obtención o creación de reportes.

    EvidenciaService
        - Creación de evidencias.
        - Gestión de imágenes.

    GeminiService
        - Análisis de imágenes mediante Gemini.

    ArchivoService
        - Limpieza de archivos temporales.

    JobService
        - Control y seguimiento del progreso del proceso.

Este servicio no debe contener:

    - rutas Flask
    - lógica SSE
    - generación de plantillas
    - lógica propia de Excel
    - lógica propia de Gemini
    - lógica propia de evidencias
    - lógica propia de reportes
    - lógica propia de contratos
"""

from models import db


from app.services.excel_service import (
    ExcelService
)

from app.services.contrato_service import (
    ContratoService
)

from app.services.reporte_service import (
    ReporteService
)

from app.services.evidencia_service import (
    EvidenciaService
)

from app.services.gemini_service import (
    GeminiService
)

from app.services.archivo_service import (
    limpiar_archivos
)

from app.services.job_service import (
    JobService
)


class CargaMasivaService:
    """
    Orquestador principal de la carga masiva mensual.
    """

    def __init__(
        self,
        excel_service=None,
        contrato_service=None,
        reporte_service=None,
        evidencia_service=None,
        gemini_service=None,
        job_service=None
    ):
        """
        Permite inyectar servicios para facilitar pruebas.

        Si no se proporcionan servicios, se utilizan las
        implementaciones reales de la aplicación.
        """

        self.excel_service = (
            excel_service
            or ExcelService
        )

        self.contrato_service = (
            contrato_service
            or ContratoService
        )

        self.reporte_service = (
            reporte_service
            or ReporteService
        )

        self.evidencia_service = (
            evidencia_service
            or EvidenciaService()
        )

        self.gemini_service = (
            gemini_service
        )

        self.job_service = (
            job_service
            or JobService()
        )

    # ============================================================
    # PROCESAMIENTO PRINCIPAL
    # ============================================================

    def procesar(
        self,
        contrato,
        mes,
        anio,
        excel_path,
        imagenes=None,
        api_key=None,
        actualizar_progreso=None,
        job_id=None
    ):
        """
        Procesa una carga masiva mensual completa.

        Args:
            contrato:
                Objeto Contrato.

            mes:
                Mes de la carga.

            anio:
                Año de la carga.

            excel_path:
                Ruta del archivo Excel.

            imagenes:
                Diccionario con imágenes temporales.

            api_key:
                API Key de Gemini.

            actualizar_progreso:
                Callback de compatibilidad con cargas.py.

            job_id:
                Identificador del trabajo.

        Returns:
            dict:
                {
                    'exitosos': int,
                    'errores': list,
                    'mes': int,
                    'anio': int
                }
        """

        errores = []

        exitosos = 0

        imagenes = imagenes or {}

        # --------------------------------------------------------
        # VALIDACIÓN INICIAL
        # --------------------------------------------------------

        self._validar_parametros(
            contrato=contrato,
            mes=mes,
            anio=anio,
            excel_path=excel_path
        )

        mes = int(mes)

        anio = int(anio)

        # --------------------------------------------------------
        # VALIDAR CONTRATO
        # --------------------------------------------------------

        valido, mensaje = (
            self.contrato_service
            .validar_contrato_para_carga(
                contrato=contrato,
                mes=mes,
                anio=anio
            )
        )

        if not valido:
            raise ValueError(
                mensaje
            )

        # --------------------------------------------------------
        # PROGRESO INICIAL
        # --------------------------------------------------------

        self._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='procesando',
            porcentaje=0,
            mensaje='Leyendo archivo Excel...'
        )

        # --------------------------------------------------------
        # LEER EXCEL
        # --------------------------------------------------------

        filas = (
            self.excel_service
            .leer_excel(
                excel_path
            )
        )

        if not filas:
            raise ValueError(
                'El archivo Excel no contiene registros válidos.'
            )

        total = len(filas)

        # --------------------------------------------------------
        # OBLIGACIONES
        # --------------------------------------------------------

        obligaciones = (
            self.contrato_service
            .obtener_obligaciones(
                contrato.id
            )
        )

        obligaciones_por_numero = (
            self._crear_indice_obligaciones(
                obligaciones
            )
        )

        # --------------------------------------------------------
        # GEMINI
        # --------------------------------------------------------

        gemini = self._crear_gemini(
            api_key
        )

        # --------------------------------------------------------
        # CACHE DE REPORTES
        # --------------------------------------------------------

        reportes_cache = {}

        # --------------------------------------------------------
        # PROCESAMIENTO
        # --------------------------------------------------------

        try:

            for indice, fila in enumerate(
                filas,
                start=1
            ):

                porcentaje = int(
                    (
                        (indice - 1)
                        / total
                    ) * 100
                )

                self._actualizar_progreso(
                    callback=actualizar_progreso,
                    job_id=job_id,
                    estado='procesando',
                    porcentaje=porcentaje,
                    mensaje=(
                        f'Procesando fila '
                        f'{indice} de {total}...'
                    )
                )

                try:

                    resultado = (
                        self._procesar_fila(
                            contrato=contrato,
                            mes=mes,
                            anio=anio,
                            fila=fila,
                            imagenes=imagenes,
                            obligaciones_por_numero=(
                                obligaciones_por_numero
                            ),
                            gemini=gemini,
                            reportes_cache=(
                                reportes_cache
                            )
                        )
                    )

                    if resultado.get(
                        'exitoso',
                        False
                    ):
                        exitosos += 1

                    errores.extend(
                        resultado.get(
                            'errores',
                            []
                        )
                    )

                except Exception as exc:

                    db.session.rollback()

                    numero_fila = fila.get(
                        'fila',
                        indice
                    )

                    errores.append(
                        (
                            f'Fila {numero_fila}: '
                            f'{str(exc)}'
                        )
                    )

            # ----------------------------------------------------
            # COMMIT FINAL
            # ----------------------------------------------------

            db.session.commit()

        except Exception:

            db.session.rollback()

            raise

        finally:

            self._limpiar_temporales(
                imagenes
            )

        # --------------------------------------------------------
        # FINALIZAR JOB
        # --------------------------------------------------------

        mensaje_final = (
            f'Proceso finalizado. '
            f'{exitosos} registros procesados.'
        )

        self._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='completado',
            porcentaje=100,
            mensaje=mensaje_final
        )

        return {
            'exitosos': exitosos,
            'errores': errores,
            'mes': mes,
            'anio': anio
        }

    # ============================================================
    # PROCESAR FILA
    # ============================================================

    def _procesar_fila(
        self,
        contrato,
        mes,
        anio,
        fila,
        imagenes,
        obligaciones_por_numero,
        gemini,
        reportes_cache
    ):
        """
        Procesa una fila individual del Excel.
        """

        errores = []

        # --------------------------------------------------------
        # DATOS DEL EXCEL
        # --------------------------------------------------------

        numero_obligacion = (
            fila.get(
                'obligacion_numero'
            )
        )

        anuncio = (
            fila.get(
                'anuncio'
            )
            or ''
        ).strip()

        fecha = (
            fila.get(
                'fecha'
            )
        )

        nombre_imagen = (
            fila.get(
                'nombre_imagen'
            )
            or ''
        ).strip()

        # --------------------------------------------------------
        # OBLIGACIÓN
        # --------------------------------------------------------

        obligacion = (
            obligaciones_por_numero
            .get(
                str(
                    numero_obligacion
                ).strip()
            )
        )

        if not obligacion:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Obligación '
                        f'{numero_obligacion} '
                        'no encontrada.'
                    )
                ]
            }

        # --------------------------------------------------------
        # REPORTE
        # --------------------------------------------------------

        cache_key = (
            obligacion.id,
            mes,
            anio
        )

        if cache_key not in reportes_cache:

            reportes_cache[
                cache_key
            ] = (
                self.reporte_service
                .obtener_o_crear_reporte(
                    contrato=contrato,
                    obligacion=obligacion,
                    mes=mes,
                    anio=anio
                )
            )

        reporte = (
            reportes_cache[
                cache_key
            ]
        )

        # --------------------------------------------------------
        # IMAGEN
        # --------------------------------------------------------

        imagen_temporal = None

        if nombre_imagen:

            imagen_temporal = (
                self.evidencia_service
                .obtener_imagen_temporal(
                    nombre_imagen,
                    imagenes
                )
            )

        # --------------------------------------------------------
        # GEMINI
        # --------------------------------------------------------

        descripcion = None

        if imagen_temporal and gemini:

            try:

                descripcion = (
                    gemini
                    .analizar_imagen_con_reintentos(
                        imagen_temporal,
                        contexto={
                            'contrato': contrato,
                            'obligacion': obligacion,
                            'mes': mes,
                            'anio': anio,
                            'anuncio': anuncio
                        }
                    )
                )

            except Exception as exc:

                errores.append(
                    (
                        f'Error analizando imagen '
                        f'{nombre_imagen}: '
                        f'{str(exc)}'
                    )
                )

        # --------------------------------------------------------
        # CREAR EVIDENCIA
        # --------------------------------------------------------

        try:

            evidencia = (
                self.evidencia_service
                .crear_evidencia(
                    reporte=reporte,
                    imagen=imagen_temporal,
                    anuncio=anuncio,
                    fecha=fecha,
                    descripcion=descripcion
                )
            )

        except Exception as exc:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Error creando evidencia '
                        f'para obligación '
                        f'{numero_obligacion}: '
                        f'{str(exc)}'
                    )
                ]
            }

        # --------------------------------------------------------
        # GUARDAR IMAGEN
        # --------------------------------------------------------

        if (
            imagen_temporal
            and reporte
            and nombre_imagen
        ):

            try:

                self.evidencia_service.guardar_imagen_evidencia(
                    imagen_temporal=imagen_temporal,
                    reporte_id=reporte.id,
                    nombre_imagen=nombre_imagen
                )

            except Exception as exc:

                errores.append(
                    (
                        f'Error guardando imagen '
                        f'{nombre_imagen}: '
                        f'{str(exc)}'
                    )
                )

        # --------------------------------------------------------
        # RESULTADO
        # --------------------------------------------------------

        return {
            'exitoso': evidencia is not None,
            'errores': errores
        }

    # ============================================================
    # VALIDACIONES
    # ============================================================

    @staticmethod
    def _validar_parametros(
        contrato,
        mes,
        anio,
        excel_path
    ):
        """
        Valida los parámetros mínimos de una carga.
        """

        if contrato is None:

            raise ValueError(
                'El contrato es obligatorio.'
            )

        if mes is None:

            raise ValueError(
                'El mes es obligatorio.'
            )

        if anio is None:

            raise ValueError(
                'El año es obligatorio.'
            )

        if not excel_path:

            raise ValueError(
                'El archivo Excel es obligatorio.'
            )

    # ============================================================
    # ÍNDICE DE OBLIGACIONES
    # ============================================================

    @staticmethod
    def _crear_indice_obligaciones(
        obligaciones
    ):
        """
        Crea un índice de obligaciones por número.
        """

        indice = {}

        for obligacion in (
            obligaciones or []
        ):

            numero = getattr(
                obligacion,
                'numero',
                None
            )

            if numero is None:
                continue

            indice[
                str(
                    numero
                ).strip()
            ] = obligacion

        return indice

    # ============================================================
    # CREAR GEMINI
    # ============================================================

    def _crear_gemini(
        self,
        api_key=None
    ):
        """
        Obtiene la instancia de Gemini.

        Si se inyectó un GeminiService, se reutiliza.

        Si se proporciona api_key, se crea una nueva instancia.
        """

        if self.gemini_service is not None:

            return self.gemini_service

        try:

            return GeminiService(
                api_key=api_key
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'No fue posible inicializar Gemini: '
                f'{exc}'
            )

            return None

    # ============================================================
    # PROGRESO
    # ============================================================

    def _actualizar_progreso(
        self,
        callback,
        job_id,
        estado,
        porcentaje,
        mensaje
    ):
        """
        Actualiza el progreso del proceso.

        Primero actualiza JobService.

        Después ejecuta el callback existente de cargas.py.

        Esto permite mantener compatibilidad con el Blueprint
        mientras se termina la refactorización.
        """

        # --------------------------------------------------------
        # JOB SERVICE
        # --------------------------------------------------------

        if job_id:

            try:

                self.job_service.actualizar(
                    job_id,
                    estado=estado,
                    porcentaje=porcentaje,
                    mensaje=mensaje
                )

            except Exception as exc:

                print(
                    '[ADVERTENCIA] '
                    f'Error actualizando JobService: '
                    f'{exc}'
                )

        # --------------------------------------------------------
        # CALLBACK LEGACY
        # --------------------------------------------------------

        if callback is None:
            return

        try:

            callback(
                job_id,
                estado,
                porcentaje,
                mensaje
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'Error ejecutando callback '
                f'de progreso: '
                f'{exc}'
            )

    # ============================================================
    # LIMPIEZA
    # ============================================================

    @staticmethod
    def _limpiar_temporales(
        imagenes
    ):
        """
        Limpia los archivos temporales asociados a la carga.
        """

        if not imagenes:
            return

        try:

            limpiar_archivos(
                imagenes
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'Error limpiando archivos temporales: '
                f'{exc}'
            )
