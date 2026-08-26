"""
Servicio para procesar cargas masivas mensuales de evidencias.

Responsabilidades:

- Procesar las filas normalizadas por ExcelService.
- Validar obligaciones.
- Validar anuncio/contexto.
- Validar fechas del periodo.
- Obtener o crear reportes mensuales.
- Resolver imágenes temporales.
- Analizar imágenes mediante GeminiService.
- Crear evidencias mediante EvidenciaService.
- Mantener una única responsabilidad por servicio.

Este servicio NO contiene rutas Flask.

Dependencias esperadas:

    ExcelService
        Se encarga de leer y normalizar el Excel.

    ReporteService
        Se encarga de obtener o crear ReporteMensual.

    EvidenciaService
        Se encarga de guardar/mover la imagen y crear Evidencia.

    GeminiService
        Se encarga del análisis visual mediante IA.

IMPORTANTE:

CargaMasivaService NO debe mover directamente las imágenes.

La imagen temporal debe entregarse a:

    EvidenciaService.crear_evidencia()

Ese servicio es el responsable de persistirla.
"""

from datetime import date, datetime
from vision_analyzer import analizar_imagen_con_reintentos


class CargaMasivaService:
    """
    Servicio encargado de procesar cargas masivas
    mensuales de evidencias.
    """

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(
        self,
        reporte_service,
        evidencia_service
    ):
        """
        Inicializa el servicio.

        Args:
            reporte_service:
                Instancia de ReporteService.

            evidencia_service:
                Instancia de EvidenciaService.
        """

        self.reporte_service = (
            reporte_service
        )

        self.evidencia_service = (
            evidencia_service
        )
        self._ia_cache = {}

    # ============================================================
    # PROCESAR FILA
    # ============================================================

    # ============================================================
    # CACHE DE IA
    # ============================================================

    def _cache_key_ia(self, image_bytes, contexto, anuncio):
        import hashlib
        hasher = hashlib.md5()
        hasher.update(image_bytes)
        hasher.update(str(contexto).encode('utf-8'))
        hasher.update(str(anuncio).encode('utf-8'))
        return hasher.hexdigest()

    def _get_cached_ia(self, image_bytes, contexto, anuncio):
        from datetime import datetime
        key = self._cache_key_ia(image_bytes, contexto, anuncio)
        entry = self._ia_cache.get(key)
        if entry:
            ts, desc = entry
            if (datetime.utcnow() - ts).total_seconds() < 86400:
                return desc
            else:
                del self._ia_cache[key]
        return None

    def _set_cached_ia(self, image_bytes, contexto, anuncio, descripcion):
        from datetime import datetime
        key = self._cache_key_ia(image_bytes, contexto, anuncio)
        self._ia_cache[key] = (datetime.utcnow(), descripcion)

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
        api_key,
        reportes_cache
    ):
        """
        Procesa una fila individual del Excel.

        La fila debe venir normalizada por ExcelService:

        {
            'obligacion': ...,
            'descripcion': ...,
            'anuncio': ...,
            'fecha': ...,
            'nombre_imagen': ...,
            '_fila_excel': ...
        }

        Args:
            contrato:
                Contrato activo.

            mes:
                Mes del proceso.

            anio:
                Año del proceso.

            fila:
                Diccionario normalizado.

            imagenes:
                Diccionario de imágenes temporales.

            obligaciones_por_numero:
                Diccionario:
                    numero -> Obligacion

            api_key:
                API key de Gemini o None.

            reportes_cache:
                Diccionario utilizado para reutilizar
                reportes durante la misma carga.

        Returns:

            {
                'exitoso': bool,
                'errores': list,
                'evidencia': Evidencia | None
            }
        """

        errores = []

        # --------------------------------------------------------
        # VALIDAR FILA
        # --------------------------------------------------------

        if not isinstance(
            fila,
            dict
        ):

            return {
                'exitoso': False,
                'errores': [
                    'La fila recibida no tiene '
                    'un formato válido.'
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # NÚMERO DE FILA
        # --------------------------------------------------------

        numero_fila = (
            self._obtener_numero_fila(
                fila,
                0
            )
        )

        # --------------------------------------------------------
        # DATOS
        # --------------------------------------------------------

        numero_obligacion = (
            fila.get(
                'obligacion'
            )
        )

        anuncio = (
            str(
                fila.get(
                    'anuncio'
                )
                or ''
            )
            .strip()
        )

        fecha = (
            fila.get(
                'fecha'
            )
        )

        nombre_imagen = (
            str(
                fila.get(
                    'nombre_imagen'
                )
                or ''
            )
            .strip()
        )

        # --------------------------------------------------------
        # VALIDAR PERIODO
        # --------------------------------------------------------

        periodo_error = (
            self._validar_periodo(
                mes,
                anio
            )
        )

        if periodo_error:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'{periodo_error}'
                    )
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # NORMALIZAR MES / AÑO
        # --------------------------------------------------------

        mes = int(
            mes
        )

        anio = int(
            anio
        )

        # --------------------------------------------------------
        # VALIDAR OBLIGACIÓN
        # --------------------------------------------------------

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
                        f'Fila {numero_fila}: '
                        f'Obligación '
                        f'{numero_obligacion} '
                        f'no encontrada.'
                    )
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # VALIDAR QUE LA OBLIGACIÓN PERTENEZCA AL CONTRATO
        # --------------------------------------------------------

        if contrato is not None:

            contrato_id = getattr(
                contrato,
                'id',
                None
            )

            obligacion_contrato_id = getattr(
                obligacion,
                'contrato_id',
                None
            )

            if (
                contrato_id is not None
                and
                obligacion_contrato_id is not None
                and
                contrato_id
                !=
                obligacion_contrato_id
            ):

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'Fila {numero_fila}: '
                            f'La obligación '
                            f'{numero_obligacion} '
                            f'no pertenece al contrato '
                            f'seleccionado.'
                        )
                    ],
                    'evidencia': None
                }

        # --------------------------------------------------------
        # VALIDAR ANUNCIO
        # --------------------------------------------------------

        if not anuncio:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'El anuncio/contexto '
                        f'es obligatorio.'
                    )
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # NORMALIZAR FECHA
        # --------------------------------------------------------

        try:

            fecha_actividad = (
                self._normalizar_fecha(
                    fecha
                )
            )

        except ValueError as exc:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'{str(exc)}'
                    )
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # FECHA POR DEFECTO
        # --------------------------------------------------------

        if fecha_actividad is None:

            fecha_actividad = date(
                anio,
                mes,
                15
            )

        # --------------------------------------------------------
        # VALIDAR FECHA DEL MES
        # --------------------------------------------------------

        fecha_error = (
            self._validar_fecha_periodo(
                fecha_actividad,
                mes,
                anio
            )
        )

        if fecha_error:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'{fecha_error}'
                    )
                ],
                'evidencia': None
            }

        # ========================================================
        # REPORTE
        # ========================================================

        cache_key = (
            getattr(
                obligacion,
                'id',
                None
            ),
            mes,
            anio
        )

        if cache_key not in reportes_cache:

            try:

                reporte = (
                    self.reporte_service
                    .obtener_o_crear_reporte(
                        contrato=contrato,
                        obligacion=obligacion,
                        mes=mes,
                        anio=anio
                    )
                )

            except Exception as exc:

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'Fila {numero_fila}: '
                            f'Error obteniendo o creando '
                            f'el reporte para la obligación '
                            f'{numero_obligacion}: '
                            f'{str(exc)}'
                        )
                    ],
                    'evidencia': None
                }

            if reporte is None:

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'Fila {numero_fila}: '
                            f'No fue posible obtener o crear '
                            f'el reporte para la obligación '
                            f'{numero_obligacion}.'
                        )
                    ],
                    'evidencia': None
                }

            reportes_cache[
                cache_key
            ] = reporte

        reporte = (
            reportes_cache[
                cache_key
            ]
        )

        # ========================================================
        # IMAGEN
        # ========================================================

        imagen_temporal = None

        if nombre_imagen:

            try:

                imagen_temporal = (
                    self.evidencia_service
                    .obtener_imagen_temporal(
                        nombre_imagen,
                        imagenes
                    )
                )

            except Exception as exc:

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'Fila {numero_fila}: '
                            f'Error buscando imagen '
                            f'"{nombre_imagen}": '
                            f'{str(exc)}'
                        )
                    ],
                    'evidencia': None
                }

            # ----------------------------------------------------
            # IMPORTANTE
            #
            # Si el Excel indica una imagen y esa imagen no existe,
            # NO se debe crear una evidencia sin imagen.
            # ----------------------------------------------------

            if not imagen_temporal:

                return {
                    'exitoso': False,
                    'errores': [
                        (
                            f'Fila {numero_fila}: '
                            f'Imagen "{nombre_imagen}" '
                            f'no encontrada entre los '
                            f'archivos cargados.'
                        )
                    ],
                    'evidencia': None
                }

        # ========================================================
        # ANALISIS MEDIANTE IA
        # ========================================================

        descripcion = None

        if imagen_temporal and api_key:

            try:

                print(
                    f'[CargaMasiva] Analizando imagen '
                    f'"{nombre_imagen}" '
                    f'para obligación '
                    f'{numero_obligacion}...'
                )

                descripcion = analizar_imagen_con_reintentos(
                    image_path=imagen_temporal,
                    api_key=api_key,
                    contexto_obligacion=(
                        getattr(
                            obligacion,
                            'descripcion',
                            ''
                        )
                        or ''
                    ),
                    anuncio_usuario=anuncio,
                    max_reintentos=3,
                    espera_segundos=5
                )

                if descripcion:

                    descripcion = str(
                        descripcion
                    ).strip()

                    print(
                        '[CargaMasiva] '
                        'Descripción IA generada: '
                        f'{descripcion[:400]}'
                    )

                else:

                    print(
                        '[CargaMasiva] '
                        f'Gemini no generó descripción '
                        f'para "{nombre_imagen}".'
                    )

                    errores.append(
                        (
                            f'Fila {numero_fila}: '
                            f'Gemini no generó descripción '
                            f'para "{nombre_imagen}".'
                        )
                    )

            except Exception as exc:

                print(
                    '[CargaMasiva] Error con Gemini: '
                    f'{exc}'
                )

                errores.append(
                    (
                        f'Fila {numero_fila}: '
                        f'Error analizando imagen '
                        f'"{nombre_imagen}" con IA: '
                        f'{str(exc)}'
                    )
                )

                descripcion = None

        # ========================================================
        # CREAR EVIDENCIA
        # ========================================================

        try:

            evidencia = (
                self.evidencia_service
                .crear_evidencia(
                    reporte=reporte,
                    imagen=imagen_temporal,
                    anuncio=anuncio,
                    fecha=fecha_actividad,
                    descripcion=descripcion
                )
            )

        except Exception as exc:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'Error creando evidencia '
                        f'para la obligación '
                        f'{numero_obligacion}: '
                        f'{str(exc)}'
                    )
                ],
                'evidencia': None
            }

        if evidencia is None:

            return {
                'exitoso': False,
                'errores': [
                    (
                        f'Fila {numero_fila}: '
                        f'No fue posible crear la evidencia '
                        f'para la obligación '
                        f'{numero_obligacion}.'
                    )
                ],
                'evidencia': None
            }

        # --------------------------------------------------------
        # NO MOVER LA IMAGEN NUEVAMENTE
        #
        # EvidenciaService.crear_evidencia() ya llama a:
        #
        #     _guardar_imagen()
        #
        # Por tanto NO se debe llamar aquí:
        #
        #     guardar_imagen_evidencia()
        #
        # porque la ruta temporal ya fue consumida.
        # --------------------------------------------------------

        return {
            'exitoso': True,
            'errores': errores,
            'evidencia': evidencia
        }
    

    # ============================================================
    # BUSCAR OBLIGACIÓN
    # ============================================================

    @staticmethod
    def _buscar_obligacion(
        numero_obligacion,
        obligaciones_por_numero
    ):
        """
        Busca una obligación utilizando diferentes
        representaciones del número.

        Soporta:

            1
            1.0
            "1"
            "1.0"
            " 1 "
            "01"
            "1,0"

        Returns:

            Obligacion | None
        """

        if (
            numero_obligacion is None
        ):

            return None

        if not obligaciones_por_numero:

            return None

        # --------------------------------------------------------
        # COINCIDENCIA DIRECTA
        # --------------------------------------------------------

        try:

            if (
                numero_obligacion
                in obligaciones_por_numero
            ):

                return (
                    obligaciones_por_numero[
                        numero_obligacion
                    ]
                )

        except (
            TypeError,
            AttributeError
        ):

            pass

        # --------------------------------------------------------
        # NORMALIZAR NÚMERO
        # --------------------------------------------------------

        numero_normalizado = (
            CargaMasivaService
            ._normalizar_numero_obligacion(
                numero_obligacion
            )
        )

        # --------------------------------------------------------
        # BÚSQUEDA DIRECTA NORMALIZADA
        # --------------------------------------------------------

        if numero_normalizado is not None:

            try:

                if (
                    numero_normalizado
                    in obligaciones_por_numero
                ):

                    return (
                        obligaciones_por_numero[
                            numero_normalizado
                        ]
                    )

            except (
                TypeError,
                AttributeError
            ):

                pass

        # --------------------------------------------------------
        # COMPARAR TODAS LAS CLAVES NORMALIZADAS
        # --------------------------------------------------------

        for clave, obligacion in (
            obligaciones_por_numero.items()
        ):

            clave_normalizada = (
                CargaMasivaService
                ._normalizar_numero_obligacion(
                    clave
                )
            )

            if (
                numero_normalizado
                is not None
                and
                clave_normalizada
                ==
                numero_normalizado
            ):

                return obligacion

            # ----------------------------------------------------
            # Comparación textual de respaldo.
            # ----------------------------------------------------

            texto_clave = str(
                clave
            ).strip()

            texto_buscado = str(
                numero_obligacion
            ).strip()

            if (
                texto_clave
                ==
                texto_buscado
            ):

                return obligacion

        return None

    # ============================================================
    # NORMALIZAR NÚMERO DE OBLIGACIÓN
    # ============================================================

    @staticmethod
    def _normalizar_numero_obligacion(
        valor
    ):
        """
        Convierte diferentes representaciones de un número
        de obligación a entero cuando es posible.

        Ejemplos:

            1       -> 1
            1.0     -> 1
            "1"     -> 1
            "1.0"   -> 1
            "01"    -> 1
            "1,0"   -> 1

        Si no representa un entero válido, retorna
        el texto limpio.
        """

        if valor is None:

            return None

        if isinstance(
            valor,
            bool
        ):

            return int(
                valor
            )

        if isinstance(
            valor,
            int
        ):

            return valor

        if isinstance(
            valor,
            float
        ):

            if valor.is_integer():

                return int(
                    valor
                )

            return valor

        texto = str(
            valor
        ).strip()

        if not texto:

            return None

        texto_numerico = (
            texto.replace(
                ',',
                '.'
            )
        )

        try:

            numero = float(
                texto_numerico
            )

            if numero.is_integer():

                return int(
                    numero
                )

        except (
            ValueError,
            TypeError,
            OverflowError
        ):

            pass

        return texto

    # ============================================================
    # NORMALIZAR FECHA
    # ============================================================

    @staticmethod
    def _normalizar_fecha(
        valor
    ):
        """
        Normaliza una fecha recibida desde Excel.

        Soporta:

            None
            date
            datetime
            YYYY-MM-DD
            DD/MM/YYYY
            DD-MM-YYYY
            YYYY/MM/DD

        Returns:

            date | None

        Raises:

            ValueError
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

        formatos = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d'
        ]

        for formato in formatos:

            try:

                return datetime.strptime(
                    texto,
                    formato
                ).date()

            except ValueError:

                continue

        raise ValueError(
            f'Fecha no válida: {valor}. '
            f'Use YYYY-MM-DD o DD/MM/YYYY.'
        )

    # ============================================================
    # VALIDAR PERIODO
    # ============================================================

    @staticmethod
    def _validar_periodo(
        mes,
        anio
    ):
        """
        Valida mes y año del proceso.

        Returns:

            None si es válido.

            str con mensaje si es inválido.
        """

        try:

            mes_int = int(
                mes
            )

        except (
            TypeError,
            ValueError
        ):

            return (
                f'El mes "{mes}" no es válido.'
            )

        try:

            anio_int = int(
                anio
            )

        except (
            TypeError,
            ValueError
        ):

            return (
                f'El año "{anio}" no es válido.'
            )

        if not (
            1
            <=
            mes_int
            <=
            12
        ):

            return (
                f'El mes "{mes}" debe estar '
                f'entre 1 y 12.'
            )

        if not (
            1900
            <=
            anio_int
            <=
            2100
        ):

            return (
                f'El año "{anio}" debe estar '
                f'entre 1900 y 2100.'
            )

        return None

    # ============================================================
    # VALIDAR FECHA DEL PERIODO
    # ============================================================

    @staticmethod
    def _validar_fecha_periodo(
        fecha,
        mes,
        anio
    ):
        """
        Verifica que una fecha pertenezca al mes/año
        seleccionado.

        Returns:

            None si es válida.

            str con mensaje si está fuera del periodo.
        """

        if not isinstance(
            fecha,
            date
        ):

            return (
                'La fecha de actividad no es válida.'
            )

        try:

            mes_int = int(
                mes
            )

            anio_int = int(
                anio
            )

        except (
            TypeError,
            ValueError
        ):

            return (
                'El mes o año del proceso no es válido.'
            )

        if (
            fecha.year
            !=
            anio_int
            or
            fecha.month
            !=
            mes_int
        ):

            return (
                f'La fecha {fecha.strftime("%Y-%m-%d")} '
                f'no pertenece al periodo '
                f'{mes_int:02d}/{anio_int}.'
            )

        return None

    # ============================================================
    # NÚMERO DE FILA
    # ============================================================

    @staticmethod
    def _obtener_numero_fila(
        fila,
        indice
    ):
        """
        Obtiene el número real de fila del Excel.

        ExcelService agrega:

            '_fila_excel': numero_fila

        Si no existe, utiliza el índice recibido.
        """

        if isinstance(
            fila,
            dict
        ):

            numero_fila = fila.get(
                '_fila_excel'
            )

            if numero_fila is not None:

                return numero_fila

        return indice


# ================================================================
# INSTANCIA POR DEFECTO
# ================================================================

# No se crea una instancia global aquí porque los servicios
# ReporteService, EvidenciaService y GeminiService pueden ser
# inicializados/configurados por la aplicación.
#
# Ejemplo de utilización:
#
#     carga_service = CargaMasivaService(
#         reporte_service=reporte_service,
#         evidencia_service=evidencia_service
#     )
#
# La instancia debe construirse donde se conozcan las dependencias.
