"""
Servicio para procesar cargas masivas mensuales de evidencias.

Este servicio centraliza la lógica de procesamiento de cada fila
del Excel y evita duplicar responsabilidades que pertenecen a:

    - ExcelService
    - ReporteService
    - EvidenciaService
    - GeminiService
"""

class CargaMasivaService:
    """
    Servicio encargado de procesar la carga masiva mensual
    de evidencias.

    Responsabilidades:

    - Validar filas del Excel.
    - Buscar obligaciones.
    - Crear/reutilizar reportes.
    - Buscar imágenes temporales.
    - Analizar imágenes con Gemini.
    - Crear evidencias.
    - Mantener el número consecutivo de actividad.

    IMPORTANTE:

    El servicio NO guarda directamente las imágenes.

    La responsabilidad de guardar/mover la imagen pertenece a:

        EvidenciaService.crear_evidencia()

    Por esta razón NO debe utilizarse:

        guardar_imagen_evidencia()

    después de crear una evidencia.
    """

    def __init__(
        self,
        reporte_service,
        evidencia_service
    ):
        self.reporte_service = (
            reporte_service
        )

        self.evidencia_service = (
            evidencia_service
        )

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

        La estructura esperada de `fila` es:

        {
            'obligacion': ...,
            'descripcion': ...,
            'anuncio': ...,
            'fecha': ...,
            'nombre_imagen': ...,
            '_fila_excel': ...
        }

        Returns:

            {
                'exitoso': bool,
                'errores': list,
                'evidencia': Evidencia | None
            }
        """

        errores = []

        # ----------------------------------------------------
        # VALIDAR FILA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # NÚMERO DE FILA EXCEL
        # ----------------------------------------------------

        numero_fila = (
            self._obtener_numero_fila(
                fila,
                0
            )
        )

        # ----------------------------------------------------
        # DATOS DEL EXCEL
        # ----------------------------------------------------

        numero_obligacion = (
            fila.get(
                'obligacion'
            )
        )

        anuncio = str(
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

        nombre_imagen = str(
            fila.get(
                'nombre_imagen'
            )
            or ''
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
                        f'Fila {numero_fila}: '
                        f'Obligación '
                        f'{numero_obligacion} '
                        f'no encontrada.'
                    )
                ],
                'evidencia': None
            }

        # ----------------------------------------------------
        # VALIDAR ANUNCIO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REPORTE
        # ----------------------------------------------------

        cache_key = (
            obligacion.id,
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

            reportes_cache[
                cache_key
            ] = reporte

        reporte = (
            reportes_cache[
                cache_key
            ]
        )

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

        # ----------------------------------------------------
        # IMAGEN TEMPORAL
        # ----------------------------------------------------

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

                errores.append(
                    (
                        f'Fila {numero_fila}: '
                        f'Error buscando imagen '
                        f'"{nombre_imagen}": '
                        f'{str(exc)}'
                    )
                )

            if not imagen_temporal:

                errores.append(
                    (
                        f'Fila {numero_fila}: '
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
                        f'Fila {numero_fila}: '
                        f'Error analizando imagen '
                        f'{nombre_imagen}: '
                        f'{str(exc)}'
                    )
                )

                # --------------------------------------------
                # IMPORTANTE
                #
                # Un error de Gemini NO impide crear
                # la evidencia.
                # --------------------------------------------

                descripcion = None

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
                        f'Fila {numero_fila}: '
                        f'Error creando evidencia '
                        f'para obligación '
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

        # ----------------------------------------------------
        # IMPORTANTE
        #
        # NO llamar aquí a:
        #
        # guardar_imagen_evidencia()
        #
        # porque crear_evidencia() ya guarda/mueve
        # la imagen mediante _guardar_imagen().
        #
        # Si se llama nuevamente se intenta mover
        # una imagen que ya fue movida.
        # ----------------------------------------------------

        return {
            'exitoso': True,
            'errores': errores,
            'evidencia': evidencia
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
        Busca una obligación utilizando el número
        normalizado.

        Soporta valores como:

            1
            1.0
            "1"
            "1.0"
            " 1 "
            "01"

        Returns:

            Obligacion | None
        """

        if (
            numero_obligacion is None
        ):

            return None

        if not obligaciones_por_numero:

            return None

        # ----------------------------------------------------
        # COINCIDENCIA DIRECTA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CONVERTIR A ENTERO
        # ----------------------------------------------------

        try:

            texto_numero = str(
                numero_obligacion
            ).strip()

            numero = int(
                float(
                    texto_numero.replace(
                        ',',
                        '.'
                    )
                )
            )

            if numero in obligaciones_por_numero:

                return (
                    obligaciones_por_numero[
                        numero
                    ]
                )

        except (
            ValueError,
            TypeError,
            OverflowError
        ):

            pass

        # ----------------------------------------------------
        # COMPARACIÓN TEXTUAL
        # ----------------------------------------------------

        texto = str(
            numero_obligacion
        ).strip()

        if not texto:

            return None

        for clave, obligacion in (
            obligaciones_por_numero.items()
        ):

            if (
                str(
                    clave
                ).strip()
                ==
                texto
            ):

                return obligacion

        # ----------------------------------------------------
        # COMPARACIÓN NUMÉRICA FINAL
        # ----------------------------------------------------

        try:

            numero_buscado = int(
                float(
                    texto.replace(
                        ',',
                        '.'
                    )
                )
            )

        except (
            ValueError,
            TypeError,
            OverflowError
        ):

            return None

        for clave, obligacion in (
            obligaciones_por_numero.items()
        ):

            try:

                numero_clave = int(
                    float(
                        str(
                            clave
                        ).strip().replace(
                            ',',
                            '.'
                        )
                    )
                )

            except (
                ValueError,
                TypeError,
                OverflowError
            ):

                continue

            if (
                numero_clave
                ==
                numero_buscado
            ):

                return obligacion

        return None

    # ========================================================
    # NÚMERO DE FILA
    # ========================================================

    @staticmethod
    def _obtener_numero_fila(
        fila,
        indice
    ):
        """
        Obtiene el número real de fila del Excel.

        ExcelService agrega:

            '_fila_excel': numero_fila

        Si por alguna razón no existe esa propiedad,
        se utiliza el índice recibido.
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
