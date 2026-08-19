"""
Servicio de orquestación para la carga masiva mensual.

Este servicio concentra la lógica de negocio que anteriormente
se encontraba en app/blueprints/cargas.py.

Responsabilidades:

- Validar el contrato y el período.
- Leer el archivo Excel.
- Obtener las obligaciones del contrato.
- Obtener o crear los reportes mensuales.
- Localizar imágenes temporales.
- Analizar imágenes mediante Gemini.
- Guardar imágenes como evidencias.
- Crear evidencias.
- Reportar progreso.
- Limpiar archivos temporales.

El Blueprint debe encargarse únicamente de HTTP/request/response.
"""

from datetime import datetime, date

from models import db

from app.services.excel_service import ExcelService
from app.services.contrato_service import ContratoService
from app.services.reporte_service import ReporteService
from app.services.evidencia_service import EvidenciaService
from app.services.gemini_service import GeminiService
from app.services.archivo_service import limpiar_archivos


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

        Si no se proporcionan, se utilizan las implementaciones
        reales de la aplicación.
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

    # ========================================================
    # PROCESAR CARGA MASIVA
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
        # VALIDACIÓN INICIAL
        # ----------------------------------------------------

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
        # PROGRESO
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
            self.excel_service.leer_excel(
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

        # ----------------------------------------------------
        # PROCESAMIENTO
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # COMMIT
            # ------------------------------------------------

            db.session.commit()

        except Exception:

            db.session.rollback()

            raise

        finally:

            self._limpiar_temporales(
                imagenes
            )

        # ----------------------------------------------------
        # FINALIZAR
        # ----------------------------------------------------

        self._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='completado',
            porcentaje=100,
            mensaje=(
                f'Proceso finalizado. '
                f'{exitosos} registros procesados.'
            )
        )

        return {
            'exitosos': exitosos,
            'errores': errores,
            'mes': mes,
            'anio': anio
        }

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
        Procesa una fila del Excel.
        """

        errores = []

        # ----------------------------------------------------
        # DATOS DE LA FILA
        # ----------------------------------------------------

        numero_obligacion = (
            fila.get('obligacion')
        )

        if numero_obligacion is None:

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

        # ----------------------------------------------------
        # OBLIGACIÓN
        # ----------------------------------------------------

        clave = str(
            numero_obligacion
        ).strip()

        obligacion = (
            obligaciones_por_numero.get(
                clave
            )
        )

        if obligacion is None:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'La obligación '
                        f'{numero_obligacion} '
                        f'no existe en el contrato.'
                    )
                ]
            }

        # ----------------------------------------------------
        # FECHA
        # ----------------------------------------------------

        fecha = (
            self._convertir_fecha(
                fecha
            )
        )

        if fecha is not None:

            if not self._fecha_en_mes(
                fecha,
                mes,
                anio
            ):

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'La fecha '
                            f'{fecha.strftime("%Y-%m-%d")} '
                            f'no pertenece al período '
                            f'{mes:02d}/{anio}.'
                        )
                    ]
                }

            if not self.contrato_service.fecha_dentro_del_contrato(
                contrato,
                fecha
            ):

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'La fecha '
                            f'{fecha.strftime("%Y-%m-%d")} '
                            f'no está dentro del período '
                            f'del contrato.'
                        )
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

        reporte = (
            reportes_cache.get(
                cache_key
            )
        )

        if reporte is None:

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

        # ----------------------------------------------------
        # IMAGEN TEMPORAL
        # ----------------------------------------------------

        imagen_temporal = (
            self.evidencia_service
            .obtener_imagen_temporal(
                nombre_imagen,
                imagenes
            )
        )

        if not imagen_temporal:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'No se encontró la imagen '
                        f'"{nombre_imagen}".'
                    )
                ]
            }

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        descripcion = ''

        if gemini is not None:

            contexto = self._crear_contexto_gemini(
                contrato=contrato,
                obligacion=obligacion,
                anuncio=anuncio,
                fecha=fecha
            )

            descripcion = (
                self._analizar_imagen(
                    gemini=gemini,
                    ruta_imagen=imagen_temporal,
                    contexto=contexto
                )
            )

        # ----------------------------------------------------
        # GUARDAR IMAGEN
        # ----------------------------------------------------

        imagen_guardada = (
            self.evidencia_service
            .guardar_imagen_evidencia(
                imagen_temporal=imagen_temporal,
                reporte_id=reporte.id,
                nombre_imagen=nombre_imagen
            )
        )

        if not imagen_guardada:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'No fue posible guardar '
                        f'la imagen "{nombre_imagen}".'
                    )
                ]
            }

        # ----------------------------------------------------
        # CREAR EVIDENCIA
        # ----------------------------------------------------

        evidencia = (
            self.evidencia_service
            .crear_evidencia(
                reporte=reporte,
                imagen=imagen_guardada,
                anuncio=anuncio,
                fecha=fecha,
                descripcion=descripcion
            )
        )

        if evidencia is None:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'No fue posible crear la evidencia '
                        f'para la imagen "{nombre_imagen}".'
                    )
                ]
            }

        return {
            'exitoso': True,
            'errores': [],
            'evidencia': evidencia
        }

    # ========================================================
    # CONTEXTO GEMINI
    # ========================================================

    @staticmethod
    def _crear_contexto_gemini(
        contrato,
        obligacion,
        anuncio,
        fecha
    ):
        """
        Construye el contexto enviado a Gemini.
        """

        partes = []

        numero = getattr(
            obligacion,
            'numero',
            ''
        )

        descripcion_obligacion = getattr(
            obligacion,
            'descripcion',
            ''
        )

        if numero:
            partes.append(
                f'Obligación: {numero}'
            )

        if descripcion_obligacion:
            partes.append(
                f'Descripción de la obligación: '
                f'{descripcion_obligacion}'
            )

        if anuncio:
            partes.append(
                f'Actividad/anuncio: {anuncio}'
            )

        if fecha:
            partes.append(
                f'Fecha: {fecha.strftime("%Y-%m-%d")}'
            )

        return '\n'.join(
            partes
        )

    # ========================================================
    # ANALIZAR IMAGEN
    # ========================================================

    @staticmethod
    def _analizar_imagen(
        gemini,
        ruta_imagen,
        contexto=None
    ):
        """
        Envía una imagen a Gemini.

        Gemini recibe la ruta del archivo, que coincide
        con la interfaz real del servicio.
        """

        if gemini is None:
            return ''

        try:

            activo = getattr(
                gemini,
                'activo',
                True
            )

            if callable(activo):
                activo = activo()

            if activo is False:
                return ''

            resultado = (
                gemini
                .analizar_imagen_con_reintentos(
                    ruta_imagen,
                    contexto=contexto
                )
            )

            if resultado is None:
                return ''

            return str(
                resultado
            ).strip()

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'Error analizando imagen con Gemini: '
                f'{exc}'
            )

            return ''

    # ========================================================
    # CREAR GEMINI
    # ========================================================

    @staticmethod
    def _crear_gemini(
        api_key=None
    ):
        """
        Crea GeminiService usando la interfaz real.
        """

        try:

            return GeminiService(
                api_key=api_key
            )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'No se pudo inicializar Gemini: '
                f'{exc}'
            )

            return None

    # ========================================================
    # ÍNDICE DE OBLIGACIONES
    # ========================================================

    @staticmethod
    def _crear_indice_obligaciones(
        obligaciones
    ):
        """
        Crea un índice por número de obligación.
        """

        resultado = {}

        for obligacion in obligaciones:

            numero = getattr(
                obligacion,
                'numero',
                None
            )

            if numero is None:
                continue

            resultado[
                str(numero).strip()
            ] = obligacion

        return resultado

    # ========================================================
    # VALIDACIÓN DE PARÁMETROS
    # ========================================================

    def _validar_parametros(
        self,
        contrato,
        mes,
        anio,
        excel_path
    ):
        """
        Valida los parámetros principales.
        """

        if contrato is None:

            raise ValueError(
                'No se recibió un contrato.'
            )

        if not self.contrato_service.mes_valido(
            mes
        ):

            raise ValueError(
                'El mes no es válido.'
            )

        if not self.contrato_service.anio_valido(
            anio
        ):

            raise ValueError(
                'El año no es válido.'
            )

        if not excel_path:

            raise ValueError(
                'No se recibió el archivo Excel.'
            )

    # ========================================================
    # CONVERSIÓN DE FECHA
    # ========================================================

    @staticmethod
    def _convertir_fecha(
        valor
    ):
        """
        Convierte distintos formatos a date.
        """

        if valor is None:
            return None

        if isinstance(
            valor,
            datetime
        ):
            return valor.date()

        if isinstance(
            valor,
            date
        ):
            return valor

        texto = str(
            valor
        ).strip()

        if not texto:
            return None

        formatos = (
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d'
        )

        for formato in formatos:

            try:

                return datetime.strptime(
                    texto,
                    formato
                ).date()

            except ValueError:
                continue

        raise ValueError(
            f'Formato de fecha no válido: {valor}'
        )

    # ========================================================
    # FECHA EN PERÍODO
    # ========================================================

    @staticmethod
    def _fecha_en_mes(
        fecha,
        mes,
        anio
    ):
        """
        Comprueba que la fecha pertenezca al mes/año.
        """

        if fecha is None:
            return True

        return (
            fecha.month == int(mes)
            and
            fecha.year == int(anio)
        )

    # ========================================================
    # LIMPIEZA
    # ========================================================

    @staticmethod
    def _limpiar_temporales(
        imagenes
    ):
        """
        Elimina archivos temporales.
        """

        if not imagenes:
            return

        try:

            archivos = list(
                imagenes.values()
            )

            if archivos:
                limpiar_archivos(
                    archivos
                )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'Error limpiando archivos temporales: '
                f'{exc}'
            )

    # ========================================================
    # PROGRESO
    # ========================================================

    @staticmethod
    def _actualizar_progreso(
        callback,
        job_id,
        estado,
        porcentaje,
        mensaje
    ):
        """
        Ejecuta el callback de progreso.
        """

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
                f'Error actualizando progreso: '
                f'{exc}'
            )


# ============================================================
# FUNCIÓN DE COMPATIBILIDAD
# ============================================================

def procesar_carga_masiva(
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
    Mantiene una función de entrada compatible con el
    Blueprint mientras se termina la migración de cargas.py.
    """

    servicio = CargaMasivaService()

    return servicio.procesar(
        contrato=contrato,
        mes=mes,
        anio=anio,
        excel_path=excel_path,
        imagenes=imagenes,
        api_key=api_key,
        actualizar_progreso=actualizar_progreso,
        job_id=job_id
    )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

carga_masiva_service = CargaMasivaService()
