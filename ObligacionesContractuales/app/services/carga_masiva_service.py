"""
Servicio de carga masiva mensual.

Responsabilidades:
- Validar los parámetros de una carga.
- Leer y validar el Excel mediante ExcelService.
- Obtener las obligaciones del contrato.
- Crear o reutilizar reportes mensuales.
- Procesar cada fila del Excel.
- Asociar imágenes.
- Analizar imágenes mediante Gemini cuando esté disponible.
- Crear evidencias.
- Actualizar el progreso mediante JobService y/o callback legacy.
- Limpiar archivos temporales.

Este servicio está diseñado para ser utilizado desde:
    app.blueprints.cargas
"""

import os
import traceback


# ============================================================
# IMPORTACIONES DE LA APLICACIÓN
# ============================================================

try:
    from models import db
except ImportError:
    db = None


# Servicios principales
try:
    from app.services.excel_service import ExcelService
except ImportError:
    ExcelService = None


try:
    from app.services.contrato_service import ContratoService
except ImportError:
    ContratoService = None


try:
    from app.services.reporte_service import ReporteService
except ImportError:
    ReporteService = None


try:
    from app.services.evidencia_service import EvidenciaService
except ImportError:
    EvidenciaService = None


try:
    from app.services.gemini_service import GeminiService
except ImportError:
    GeminiService = None


try:
    from app.services.job_service import JobService
except ImportError:
    JobService = None


# ============================================================
# LIMPIEZA DE TEMPORALES
# ============================================================

try:
    from app.services.archivo_service import limpiar_archivos
except ImportError:

    def limpiar_archivos(imagenes):
        """
        Fallback para limpiar archivos temporales.

        Se utiliza solamente si la aplicación no dispone
        de la función centralizada limpiar_archivos().
        """

        if not imagenes:
            return

        archivos = set()

        if isinstance(imagenes, dict):

            for ruta in imagenes.values():

                if ruta:
                    archivos.add(ruta)

        elif isinstance(imagenes, (list, tuple, set)):

            for ruta in imagenes:

                if ruta:
                    archivos.add(ruta)

        for ruta in archivos:

            try:

                if os.path.isfile(ruta):
                    os.remove(ruta)

            except Exception as exc:

                print(
                    '[CargaMasivaService] '
                    f'No fue posible eliminar temporal: '
                    f'{ruta} - {exc}'
                )


# ============================================================
# SERVICIO
# ============================================================

class CargaMasivaService:
    """
    Orquestador principal de la carga masiva mensual.

    Los servicios pueden ser inyectados para facilitar pruebas
    unitarias y mantener desacoplada la lógica del Blueprint.
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
        Inicializa el servicio.

        Si se proporciona una dependencia, se utiliza esa instancia.

        Si no se proporciona, se intenta utilizar la implementación
        real correspondiente.
        """

        self.excel_service = (
            excel_service
            if excel_service is not None
            else (
                ExcelService()
                if ExcelService is not None
                else None
            )
        )

        self.contrato_service = (
            contrato_service
            if contrato_service is not None
            else (
                ContratoService()
                if ContratoService is not None
                else None
            )
        )

        self.reporte_service = (
            reporte_service
            if reporte_service is not None
            else (
                ReporteService()
                if ReporteService is not None
                else None
            )
        )

        self.evidencia_service = (
            evidencia_service
            if evidencia_service is not None
            else (
                EvidenciaService()
                if EvidenciaService is not None
                else None
            )
        )

        self.gemini_service = gemini_service

        self.job_service = (
            job_service
            if job_service is not None
            else (
                JobService()
                if JobService is not None
                else None
            )
        )

    # ========================================================
    # PROCESAMIENTO PRINCIPAL
    # ========================================================

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
                Diccionario:
                    nombre_archivo -> ruta_temporal

            api_key:
                API Key de Gemini.

            actualizar_progreso:
                Callback legacy utilizado por cargas.py.

                Firma esperada:
                    callback(
                        job_id,
                        estado,
                        porcentaje,
                        mensaje
                    )

            job_id:
                Identificador del job.

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

        # ----------------------------------------------------
        # VALIDACIONES
        # ----------------------------------------------------

        self._validar_dependencias()

        self._validar_parametros(
            contrato=contrato,
            mes=mes,
            anio=anio,
            excel_path=excel_path
        )

        mes = int(mes)

        anio = int(anio)

        # ----------------------------------------------------
        # VALIDAR CONTRATO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # PROGRESO INICIAL
        # ----------------------------------------------------

        self._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='procesando',
            porcentaje=0,
            mensaje='Leyendo archivo Excel...'
        )

        # ----------------------------------------------------
        # LEER EXCEL
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # OBLIGACIONES
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        gemini = self._crear_gemini(
            api_key
        )

        # ----------------------------------------------------
        # CACHE DE REPORTES
        # ----------------------------------------------------

        reportes_cache = {}

        # ====================================================
        # PROCESAR FILAS
        # ====================================================

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

                    self._rollback()

                    numero_fila = self._obtener_numero_fila(
                        fila,
                        indice
                    )

                    errores.append(
                        (
                            f'Fila {numero_fila}: '
                            f'{str(exc)}'
                        )
                    )

            # ------------------------------------------------
            # COMMIT FINAL
            # ------------------------------------------------

            self._commit()

        except Exception:

            self._rollback()

            raise

        finally:

            self._limpiar_temporales(
                imagenes
            )

        # ----------------------------------------------------
        # RESULTADO FINAL
        # ----------------------------------------------------

        mensaje_final = (
            f'Proceso finalizado. '
            f'{exitosos} registros procesados.'
        )

        resultado_final = {
            'exitosos': exitosos,
            'errores': errores,
            'mes': mes,
            'anio': anio
        }

        self._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='completado',
            porcentaje=100,
            mensaje=mensaje_final,
            resultado=resultado_final
        )

        return resultado_final

    # ========================================================
    # PROCESAR FILA
    # ========================================================

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

        # ----------------------------------------------------
        # DATOS DEL EXCEL
        # ----------------------------------------------------

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
        )

        anuncio = str(
            anuncio
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
        )

        nombre_imagen = str(
            nombre_imagen
        ).strip()

        # ----------------------------------------------------
        # VALIDAR OBLIGACIÓN
        # ----------------------------------------------------

        obligacion = (
            self._buscar_obligacion(
                numero_obligacion,
                obligaciones_por_numero
            )
        )

        if not obligacion:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Obligación '
                        f'{numero_obligacion} '
                        f'no encontrada.'
                    )
                ]
            }

        # ----------------------------------------------------
        # VALIDAR ANUNCIO
        # ----------------------------------------------------

        if not anuncio:

            return {
                'exitoso': False,
                'errores': [
                    'El anuncio/contexto es obligatorio.'
                ]
            }

        # ----------------------------------------------------
        # REPORTE
        # ----------------------------------------------------

        cache_key = (
            obligacion.id,
            mes,
            anio
        )

        if cache_key not in reportes_cache:

            reporte = (
                self.reporte_service
                .obtener_o_crear_reporte(
                    contrato=contrato,
                    obligacion=obligacion,
                    mes=mes,
                    anio=anio
                )
            )

            reportes_cache[
                cache_key
            ] = reporte

        reporte = (
            reportes_cache[
                cache_key
            ]
        )

        if reporte is None:

            raise ValueError(
                (
                    f'No fue posible obtener o crear '
                    f'el reporte para la obligación '
                    f'{numero_obligacion}.'
                )
            )

        # ----------------------------------------------------
        # IMAGEN TEMPORAL
        # ----------------------------------------------------

        imagen_temporal = None

        if nombre_imagen:

            imagen_temporal = (
                self.evidencia_service
                .obtener_imagen_temporal(
                    nombre_imagen,
                    imagenes
                )
            )

            if not imagen_temporal:

                errores.append(
                    (
                        f'Imagen "{nombre_imagen}" '
                        f'no encontrada.'
                    )
                )

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CREAR EVIDENCIA
        # ----------------------------------------------------

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

        if evidencia is None:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'No fue posible crear la evidencia '
                        f'para la obligación '
                        f'{numero_obligacion}.'
                    )
                ]
            }

        # ----------------------------------------------------
        # GUARDAR IMAGEN
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        return {
            'exitoso': True,
            'errores': errores
        }

    # ========================================================
    # BUSCAR OBLIGACIÓN
    # ========================================================

    @staticmethod
    def _buscar_obligacion(
        numero_obligacion,
        obligaciones_por_numero
    ):
        """
        Busca una obligación tolerando valores Excel como:

            1
            "1"
            1.0
            "1.0"
        """

        if numero_obligacion is None:

            return None

        valor = str(
            numero_obligacion
        ).strip()

        if not valor:

            return None

        # Coincidencia directa
        obligacion = (
            obligaciones_por_numero
            .get(valor)
        )

        if obligacion:

            return obligacion

        # Excel puede devolver 1.0 para un número entero
        try:

            numero = float(
                valor
            )

            if numero.is_integer():

                valor_normalizado = str(
                    int(numero)
                )

                return (
                    obligaciones_por_numero
                    .get(
                        valor_normalizado
                    )
                )

        except (
            ValueError,
            TypeError
        ):

            pass

        return None

    # ========================================================
    # VALIDAR DEPENDENCIAS
    # ========================================================

    def _validar_dependencias(self):
        """
        Verifica que los servicios indispensables estén
        disponibles.
        """

        faltantes = []

        if self.excel_service is None:

            faltantes.append(
                'ExcelService'
            )

        if self.contrato_service is None:

            faltantes.append(
                'ContratoService'
            )

        if self.reporte_service is None:

            faltantes.append(
                'ReporteService'
            )

        if self.evidencia_service is None:

            faltantes.append(
                'EvidenciaService'
            )

        if self.job_service is None:

            # JobService no debe impedir una carga cuando
            # se está utilizando únicamente el callback legacy.
            pass

        if faltantes:

            raise RuntimeError(
                (
                    'No fue posible inicializar los servicios '
                    'requeridos: '
                    +
                    ', '.join(faltantes)
                )
            )

    # ========================================================
    # VALIDACIONES
    # ========================================================

    @staticmethod
    def _validar_parametros(
        contrato,
        mes,
        anio,
        excel_path
    ):
        """
        Valida los parámetros mínimos.
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

        try:

            mes_int = int(
                mes
            )

        except (
            TypeError,
            ValueError
        ):

            raise ValueError(
                'El mes debe ser numérico.'
            )

        if mes_int < 1 or mes_int > 12:

            raise ValueError(
                'El mes debe estar entre 1 y 12.'
            )

        try:

            anio_int = int(
                anio
            )

        except (
            TypeError,
            ValueError
        ):

            raise ValueError(
                'El año debe ser numérico.'
            )

        if anio_int < 1900 or anio_int > 3000:

            raise ValueError(
                'El año no es válido.'
            )

    # ========================================================
    # ÍNDICE DE OBLIGACIONES
    # ========================================================

    @staticmethod
    def _crear_indice_obligaciones(
        obligaciones
    ):
        """
        Crea un índice:

            numero -> objeto Obligacion
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

            clave = str(
                numero
            ).strip()

            indice[
                clave
            ] = obligacion

        return indice

    # ========================================================
    # GEMINI
    # ========================================================

    def _crear_gemini(
        self,
        api_key=None
    ):
        """
        Obtiene la instancia de Gemini.

        Si se inyectó un servicio se reutiliza.

        Si no existe servicio Gemini o no hay API key,
        se devuelve None y la carga continúa sin análisis IA.
        """

        if self.gemini_service is not None:

            return self.gemini_service

        if not api_key:

            return None

        if GeminiService is None:

            print(
                '[CargaMasivaService] '
                'GeminiService no está disponible.'
            )

            return None

        try:

            return GeminiService(
                api_key=api_key
            )

        except TypeError:

            # Compatibilidad con servicios que reciben
            # la API key mediante otro mecanismo.
            try:

                servicio = GeminiService()

                if hasattr(
                    servicio,
                    'api_key'
                ):

                    servicio.api_key = (
                        api_key
                    )

                return servicio

            except Exception as exc:

                print(
                    '[CargaMasivaService] '
                    f'No fue posible inicializar Gemini: '
                    f'{exc}'
                )

                return None

        except Exception as exc:

            print(
                '[CargaMasivaService] '
                f'No fue posible inicializar Gemini: '
                f'{exc}'
            )

            return None

    # ========================================================
    # PROGRESO
    # ========================================================

    def _actualizar_progreso(
        self,
        callback,
        job_id,
        estado,
        porcentaje,
        mensaje,
        resultado=None,
        error=None
    ):
        """
        Actualiza el progreso.

        Orden:

        1. JobService.
        2. Callback legacy.

        Esto permite convivir con la implementación actual
        de cargas.py.
        """

        # ----------------------------------------------------
        # JOB SERVICE
        # ----------------------------------------------------

        if (
            job_id
            and
            self.job_service is not None
        ):

            try:

                self.job_service.actualizar(
                    job_id,
                    estado=estado,
                    porcentaje=porcentaje,
                    mensaje=mensaje,
                    resultado=resultado,
                    error=error
                )

            except Exception as exc:

                print(
                    '[CargaMasivaService] '
                    f'Error actualizando JobService: '
                    f'{exc}'
                )

        # ----------------------------------------------------
        # CALLBACK LEGACY
        # ----------------------------------------------------

        if callback is None:

            return

        try:

            callback(
                job_id,
                estado,
                porcentaje,
                mensaje
            )

        except TypeError:

            # Compatibilidad por si el callback antiguo
            # solamente recibe estado, porcentaje y mensaje.
            try:

                callback(
                    estado,
                    porcentaje,
                    mensaje
                )

            except Exception as exc:

                print(
                    '[CargaMasivaService] '
                    f'Error ejecutando callback: '
                    f'{exc}'
                )

        except Exception as exc:

            print(
                '[CargaMasivaService] '
                f'Error ejecutando callback: '
                f'{exc}'
            )

    # ========================================================
    # LIMPIEZA
    # ========================================================

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
                '[CargaMasivaService] '
                f'Error limpiando archivos temporales: '
                f'{exc}'
            )

    # ========================================================
    # DATABASE
    # ========================================================

    @staticmethod
    def _commit():
        """
        Ejecuta commit si existe db.session.
        """

        if db is None:

            return

        db.session.commit()

    @staticmethod
    def _rollback():
        """
        Ejecuta rollback si existe db.session.
        """

        if db is None:

            return

        try:

            db.session.rollback()

        except Exception as exc:

            print(
                '[CargaMasivaService] '
                f'Error realizando rollback: '
                f'{exc}'
            )

    # ========================================================
    # FILA
    # ========================================================

    @staticmethod
    def _obtener_numero_fila(
        fila,
        indice
    ):
        """
        Obtiene el número de fila original del Excel.
        """

        if isinstance(
            fila,
            dict
        ):

            return fila.get(
                'fila',
                indice
            )

        return indice
