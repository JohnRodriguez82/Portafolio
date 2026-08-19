"""
Servicio principal de carga masiva mensual.

Este módulo funciona como ORQUESTADOR.

Responsabilidades:
- Leer el Excel mediante ExcelService.
- Obtener las obligaciones mediante ContratoService.
- Obtener o crear reportes mediante ReporteService.
- Procesar evidencias mediante EvidenciaService.
- Utilizar GeminiService para análisis de imágenes.
- Limpiar archivos temporales mediante ArchivoService.
- Informar progreso mediante un callback.

Este módulo NO contiene:
- rutas Flask,
- lógica SSE,
- generación de plantillas,
- lógica de lectura directa de Excel,
- lógica directa de Gemini,
- lógica de almacenamiento de evidencias.
"""

from datetime import (
    datetime,
    date
)

from models import db

from app.services.excel_service import (
    ExcelService
)

from app.services.evidencia_service import (
    procesar_evidencia
)

from app.services.reporte_service import (
    ReporteService
)

from app.services.contrato_service import (
    ContratoService
)

from app.services.gemini_service import (
    GeminiService
)

from app.services.archivo_service import (
    limpiar_archivos
)


# ============================================================
# SERVICIO
# ============================================================

class CargaMasivaService:
    """
    Orquestador del proceso de carga masiva mensual.
    """

    # ========================================================
    # PROCESAMIENTO PRINCIPAL
    # ========================================================

    @staticmethod
    def procesar(
        contrato,
        mes,
        anio,
        excel_path,
        imagenes,
        api_key=None,
        actualizar_progreso=None,
        job_id=None
    ):
        """
        Ejecuta el procesamiento completo de una carga masiva.

        Args:
            contrato:
                Objeto Contrato.

            mes:
                Mes del reporte.

            anio:
                Año del reporte.

            excel_path:
                Ruta física del archivo Excel.

            imagenes:
                Diccionario:

                    {
                        "foto1.jpg": "/ruta/temporal/foto1.jpg",
                        "foto2.jpg": "/ruta/temporal/foto2.jpg"
                    }

            api_key:
                API Key de Gemini.

            actualizar_progreso:
                Callback utilizado para informar progreso.

            job_id:
                Identificador del trabajo.

        Returns:
            dict
        """

        errores = []

        exitosos = 0

        # ----------------------------------------------------
        # VALIDAR DATOS BÁSICOS
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
        # PROGRESO INICIAL
        # ----------------------------------------------------

        CargaMasivaService._actualizar(
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
                'El Excel no contiene filas válidas.'
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

        obligaciones_por_numero = {
            str(obligacion.numero).strip(): obligacion
            for obligacion in obligaciones
        }

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        gemini = GeminiService(
            api_key=api_key
        )

        # ----------------------------------------------------
        # CACHE DE REPORTES
        #
        # Evita consultar/crear el mismo reporte varias veces
        # cuando existen varias evidencias para una obligación.
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

                CargaMasivaService._actualizar(
                    callback=actualizar_progreso,
                    job_id=job_id,
                    estado='procesando',
                    porcentaje=porcentaje,
                    mensaje=(
                        f'Procesando fila '
                        f'{indice}/{total}...'
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
                            ),
                            actualizar_progreso=(
                                actualizar_progreso
                            ),
                            job_id=job_id
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

                    errores.append(
                        (
                            f'Fila {indice}: '
                            f'{str(exc)}'
                        )
                    )

                    # ----------------------------------------
                    # IMPORTANTE
                    # ----------------------------------------
                    #
                    # Si ocurre un error inesperado,
                    # dejamos la sesión preparada para
                    # continuar con las siguientes filas.
                    #
                    # ----------------------------------------

                    try:

                        db.session.rollback()

                    except Exception:

                        pass

            # ------------------------------------------------
            # COMMIT FINAL
            # ------------------------------------------------

            db.session.commit()

        except Exception:

            db.session.rollback()

            raise

        finally:

            # ------------------------------------------------
            # LIMPIAR ARCHIVOS TEMPORALES
            # ------------------------------------------------

            CargaMasivaService._limpiar_temporales(
                imagenes
            )

        # ----------------------------------------------------
        # PROGRESO FINAL
        # ----------------------------------------------------

        CargaMasivaService._actualizar(
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
        reportes_cache,
        actualizar_progreso=None,
        job_id=None
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
                'obligacion'
            )
        )

        # ----------------------------------------------------
        # COMPATIBILIDAD
        #
        # Permite también trabajar con una versión anterior
        # del ExcelService que utilizara:
        #
        #     obligacion_numero
        #
        # ----------------------------------------------------

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
        # VALIDAR OBLIGACIÓN
        # ----------------------------------------------------

        clave_obligacion = (
            str(
                numero_obligacion
            ).strip()
        )

        obligacion = (
            obligaciones_por_numero.get(
                clave_obligacion
            )
        )

        if not obligacion:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {fila.get("fila", "?")}: '
                        f'la obligación '
                        f'{numero_obligacion} '
                        f'no existe en el contrato.'
                    )
                ]
            }

        # ----------------------------------------------------
        # VALIDAR FECHA
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
                            f'Fila {fila.get("fila", "?")}: '
                            f'la fecha {fecha.strftime("%Y-%m-%d")} '
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
                            f'Fila {fila.get("fila", "?")}: '
                            f'la fecha '
                            f'{fecha.strftime("%Y-%m-%d")} '
                            f'no está dentro del periodo '
                            f'del contrato.'
                        )
                    ]
                }

        # ----------------------------------------------------
        # OBTENER / CREAR REPORTE
        # ----------------------------------------------------

        cache_key = (
            obligacion.id,
            mes,
            anio
        )

        if cache_key not in reportes_cache:

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

        else:

            reporte = (
                reportes_cache[
                    cache_key
                ]
            )

        # ----------------------------------------------------
        # PROCESAR EVIDENCIA
        # ----------------------------------------------------

        try:

            resultado = (
                procesar_evidencia(
                    reporte=reporte,
                    obligacion=obligacion,
                    anuncio=anuncio,
                    fecha=fecha,
                    nombre_imagen=nombre_imagen,
                    imagenes=imagenes,
                    gemini=gemini,
                    actualizar_progreso=(
                        actualizar_progreso
                    ),
                    job_id=job_id
                )
            )

        except Exception as exc:

            # -----------------------------------------------
            # Si el servicio de evidencia hizo rollback,
            # el objeto almacenado en cache puede haber
            # quedado inválido.
            # -----------------------------------------------

            reportes_cache.pop(
                cache_key,
                None
            )

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Error procesando la obligación '
                        f'{numero_obligacion}: '
                        f'{str(exc)}'
                    )
                ]
            }

        # ----------------------------------------------------
        # ERRORES DE EVIDENCIA
        # ----------------------------------------------------

        errores.extend(
            resultado.get(
                'errores',
                []
            )
        )

        # ----------------------------------------------------
        # SI NO SE CREÓ
        # ----------------------------------------------------

        if not resultado.get(
            'creada',
            False
        ):

            return {
                'exitoso': False,
                'errores': errores
            }

        # ----------------------------------------------------
        # ÉXITO
        # ----------------------------------------------------

        return {
            'exitoso': True,
            'errores': errores,
            'evidencia': (
                resultado.get(
                    'evidencia'
                )
            )
        }

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
        Valida los parámetros mínimos del proceso.
        """

        if contrato is None:

            raise ValueError(
                'No se recibió un contrato.'
            )

        if not ContratoService.mes_valido(
            mes
        ):

            raise ValueError(
                'El mes del reporte no es válido.'
            )

        if not ContratoService.anio_valido(
            anio
        ):

            raise ValueError(
                'El año del reporte no es válido.'
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
        Convierte una fecha recibida desde ExcelService
        a datetime.date.

        ExcelService normalmente devuelve:
            YYYY-MM-DD

        También soportamos:
            DD/MM/YYYY
            DD-MM-YYYY
            YYYY/MM/DD
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
                f'{valor}. '
                f'Use YYYY-MM-DD o DD/MM/YYYY.'
            )
        )

    # ========================================================
    # VALIDAR FECHA DEL MES
    # ========================================================

    @staticmethod
    def _fecha_en_mes(
        fecha,
        mes,
        anio
    ):
        """
        Verifica que una fecha pertenezca al
        mes y año seleccionado.
        """

        if not fecha:

            return True

        return (
            fecha.month == int(mes)
            and
            fecha.year == int(anio)
        )

    # ========================================================
    # LIMPIAR TEMPORALES
    # ========================================================

    @staticmethod
    def _limpiar_temporales(
        imagenes
    ):
        """
        Elimina las imágenes temporales que no fueron
        consumidas por EvidenciaService.

        Las imágenes procesadas correctamente ya fueron
        movidas al almacenamiento definitivo, por lo que
        solamente permanecen en el diccionario las que
        no fueron utilizadas.
        """

        if not imagenes:

            return

        try:

            archivos_pendientes = list(
                imagenes.values()
            )

            if archivos_pendientes:

                limpiar_archivos(
                    archivos_pendientes
                )

        except Exception as exc:

            print(
                '[ADVERTENCIA] '
                'No fue posible limpiar archivos '
                f'temporales: {exc}'
            )

    # ========================================================
    # PROGRESO
    # ========================================================

    @staticmethod
    def _actualizar(
        callback,
        job_id,
        estado,
        porcentaje,
        mensaje
    ):
        """
        Ejecuta el callback de progreso si existe.
        """

        if not callback:

            return

        try:

            callback(
                job_id,
                estado,
                porcentaje,
                mensaje
            )

        except Exception as exc:

            # El progreso nunca debe detener
            # el procesamiento principal.

            print(
                '[ADVERTENCIA] '
                f'Error actualizando progreso: {exc}'
            )


# ============================================================
# FUNCIÓN DE COMPATIBILIDAD
# ============================================================

def procesar_carga_masiva(
    contrato,
    mes,
    anio,
    excel_path,
    imagenes,
    api_key=None,
    actualizar_progreso=None,
    job_id=None
):
    """
    Función de compatibilidad para el Blueprint cargas.py.

    Permite que inicialmente NO sea necesario modificar
    cargas.py.

    Posteriormente esta función puede eliminarse cuando
    el Blueprint utilice directamente CargaMasivaService.
    """

    return (
        CargaMasivaService.procesar(
            contrato=contrato,
            mes=mes,
            anio=anio,
            excel_path=excel_path,
            imagenes=imagenes,
            api_key=api_key,
            actualizar_progreso=(
                actualizar_progreso
            ),
            job_id=job_id
        )
    )


# ============================================================
# INSTANCIA COMPARTIDA
# ============================================================

carga_masiva_service = (
    CargaMasivaService()
)
