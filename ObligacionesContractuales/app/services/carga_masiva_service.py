"""
Servicio de orquestación para la carga masiva mensual.

Responsabilidades:
- Leer el archivo Excel.
- Validar las obligaciones.
- Obtener o crear los reportes mensuales.
- Localizar las imágenes asociadas a cada fila.
- Analizar las imágenes mediante Gemini.
- Guardar las imágenes como evidencias.
- Crear las evidencias en base de datos.
- Actualizar el progreso del proceso.
- Limpiar archivos temporales.

Este servicio NO contiene rutas Flask.
"""

from datetime import datetime, date

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


# ============================================================
# SERVICIO PRINCIPAL
# ============================================================

class CargaMasivaService:
    """
    Orquestador del proceso de carga masiva mensual.
    """

    # ========================================================
    # PROCESAR CARGA MASIVA
    # ========================================================

    @staticmethod
    def procesar(
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
        Procesa una carga masiva mensual.

        Args:
            contrato:
                Objeto Contrato.

            mes:
                Mes del reporte.

            anio:
                Año del reporte.

            excel_path:
                Ruta del archivo Excel.

            imagenes:
                Diccionario de imágenes temporales.

            api_key:
                API Key de Gemini.

            actualizar_progreso:
                Callback para informar progreso.

            job_id:
                Identificador del trabajo.

        Returns:
            dict:
                Resultado del procesamiento.
        """

        errores = []

        exitosos = 0

        imagenes = imagenes or {}

        # ----------------------------------------------------
        # VALIDAR PARÁMETROS
        # ----------------------------------------------------

        CargaMasivaService._validar_parametros(
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
            ContratoService.validar_contrato_para_carga(
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

        CargaMasivaService._actualizar_progreso(
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
            ExcelService.leer_excel(
                excel_path
            )
        )

        if not filas:

            raise ValueError(
                'El archivo Excel no contiene registros válidos.'
            )

        total = len(
            filas
        )

        # ----------------------------------------------------
        # OBTENER OBLIGACIONES
        # ----------------------------------------------------

        obligaciones = (
            ContratoService.obtener_obligaciones(
                contrato.id
            )
        )

        obligaciones_por_numero = (
            CargaMasivaService._crear_indice_obligaciones(
                obligaciones
            )
        )

        # ----------------------------------------------------
        # CREAR SERVICIO GEMINI
        # ----------------------------------------------------

        gemini = (
            CargaMasivaService._crear_gemini(
                api_key
            )
        )

        # ----------------------------------------------------
        # CACHE DE REPORTES
        # ----------------------------------------------------

        reportes_cache = {}

        # ----------------------------------------------------
        # PROCESAR FILAS
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
                    )
                    * 100
                )

                CargaMasivaService._actualizar_progreso(
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
                        CargaMasivaService._procesar_fila(
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

                    errores.append(
                        (
                            f'Fila '
                            f'{fila.get("fila", indice)}: '
                            f'{str(exc)}'
                        )
                    )

            # ------------------------------------------------
            # COMMIT FINAL
            # ------------------------------------------------

            db.session.commit()

        except Exception:

            db.session.rollback()

            raise

        finally:

            # ------------------------------------------------
            # LIMPIAR ARCHIVOS
            # ------------------------------------------------

            CargaMasivaService._limpiar_temporales(
                imagenes
            )

        # ----------------------------------------------------
        # RESULTADO FINAL
        # ----------------------------------------------------

        CargaMasivaService._actualizar_progreso(
            callback=actualizar_progreso,
            job_id=job_id,
            estado='completado',
            porcentaje=100,
            mensaje=(
                f'Proceso finalizado. '
                f'{exitosos} evidencias procesadas.'
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

    @staticmethod
    def _procesar_fila(
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
        # DATOS
        # ----------------------------------------------------

        numero_obligacion = (
            fila.get(
                'obligacion'
            )
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
            CargaMasivaService._convertir_fecha(
                fecha
            )
        )

        if fecha is not None:

            if not CargaMasivaService._fecha_en_mes(
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
                            f'no pertenece al periodo '
                            f'{mes:02d}/{anio}.'
                        )
                    ]
                }

            if not ContratoService.fecha_dentro_del_contrato(
                contrato,
                fecha
            ):

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'La fecha '
                            f'{fecha.strftime("%Y-%m-%d")} '
                            f'no está dentro del periodo '
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
                ReporteService.obtener_o_crear_reporte(
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
        # BUSCAR IMAGEN
        # ----------------------------------------------------

        imagen_temporal = (
            EvidenciaService.obtener_imagen_temporal(
                nombre_imagen,
                imagenes
            )
        )

        if imagen_temporal is None:

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
        # DESCRIPCIÓN
        # ----------------------------------------------------

        descripcion = ''

        if gemini is not None:

            descripcion = (
                CargaMasivaService._analizar_imagen(
                    gemini=gemini,
                    imagen=imagen_temporal
                )
            )

        # ----------------------------------------------------
        # GUARDAR IMAGEN
        # ----------------------------------------------------

        imagen_guardada = (
            EvidenciaService.guardar_imagen_evidencia(
                imagen_temporal=imagen_temporal,
                reporte_id=reporte.id,
                nombre_imagen=nombre_imagen
            )
        )

        # ----------------------------------------------------
        # CREAR EVIDENCIA
        # ----------------------------------------------------

        evidencia = (
            EvidenciaService.crear_evidencia(
                reporte=reporte,
                imagen=imagen_guardada,
                anuncio=anuncio,
                fecha=fecha,
                descripcion=descripcion
            )
        )

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        return {
            'exitoso': evidencia is not None,
            'errores': errores,
            'evidencia': evidencia
        }

    # ========================================================
    # CREAR ÍNDICE DE OBLIGACIONES
    # ========================================================

    @staticmethod
    def _crear_indice_obligaciones(
        obligaciones
    ):
        """
        Crea un índice rápido por número de obligación.
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
    # GEMINI
    # ========================================================

    @staticmethod
    def _crear_gemini(
        api_key=None
    ):
        """
        Crea la instancia de GeminiService.

        Se intenta utilizar la API key proporcionada.
        Si el servicio ya obtiene la configuración desde
        variables de entorno, se permite utilizar su
        configuración normal.
        """

        try:

            if api_key:

                return GeminiService(
                    api_key=api_key
                )

            return GeminiService()

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                f'Gemini no pudo inicializarse: {exc}'
            )

            return None

    # ========================================================
    # ANALIZAR IMAGEN
    # ========================================================

    @staticmethod
    def _analizar_imagen(
        gemini,
        imagen
    ):
        """
        Analiza una imagen utilizando Gemini.

        Se utiliza el método con reintentos cuando está
        disponible.
        """

        if gemini is None:

            return ''

        try:

            if hasattr(
                gemini,
                'activo'
            ):

                activo = gemini.activo

                if callable(activo):

                    activo = activo()

                if activo is False:

                    return ''

            if hasattr(
                gemini,
                'analizar_imagen_con_reintentos'
            ):

                resultado = (
                    gemini.analizar_imagen_con_reintentos(
                        imagen
                    )
                )

            else:

                resultado = (
                    gemini.analizar_imagen(
                        imagen
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
    # VALIDAR PARÁMETROS
    # ========================================================

    @staticmethod
    def _validar_parametros(
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

        if not ContratoService.mes_valido(
            mes
        ):

            raise ValueError(
                'El mes no es válido.'
            )

        if not ContratoService.anio_valido(
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
    # CONVERTIR FECHA
    # ========================================================

    @staticmethod
    def _convertir_fecha(
        valor
    ):
        """
        Convierte una fecha a datetime.date.
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
            (
                f'Formato de fecha no válido: '
                f'{valor}'
            )
        )

    # ========================================================
    # VALIDAR MES
    # ========================================================

    @staticmethod
    def _fecha_en_mes(
        fecha,
        mes,
        anio
    ):
        """
        Verifica que la fecha pertenezca al periodo.
        """

        if fecha is None:

            return True

        return (
            fecha.month == int(mes)
            and
            fecha.year == int(anio)
        )

    # ========================================================
    # LIMPIAR ARCHIVOS
    # ========================================================

    @staticmethod
    def _limpiar_temporales(
        imagenes
    ):
        """
        Limpia los archivos temporales restantes.
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
                'No se pudieron limpiar los archivos '
                f'temporales: {exc}'
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
        Actualiza el progreso mediante el callback.
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
                f'No se pudo actualizar el progreso: '
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
    Función de compatibilidad para el Blueprint cargas.py.

    Permite mantener temporalmente la interfaz utilizada
    por el código antiguo mientras se termina la
    refactorización.
    """

    return (
        CargaMasivaService.procesar(
            contrato=contrato,
            mes=mes,
            anio=anio,
            excel_path=excel_path,
            imagenes=imagenes,
            api_key=api_key,
            actualizar_progreso=actualizar_progreso,
            job_id=job_id
        )
    )


# ============================================================
# INSTANCIA DEL SERVICIO
# ============================================================

carga_masiva_service = (
    CargaMasivaService()
)
