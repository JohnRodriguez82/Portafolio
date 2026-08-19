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
    """

    def __init__(
        self,
        reporte_service,
        evidencia_service
    ):
        self.reporte_service = reporte_service
        self.evidencia_service = evidencia_service

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
        """

        errores = []

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

        numero_obligacion = fila.get(
            'obligacion'
        )

        anuncio = str(
            fila.get(
                'anuncio'
            )
            or ''
        ).strip()

        fecha = fila.get(
            'fecha'
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
                ]
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

        reporte = reportes_cache[
            cache_key
        ]

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
                ]
            }

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
                ]
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
                ]
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
        """

        if numero_obligacion is None:
            return None

        # Coincidencia directa
        if numero_obligacion in obligaciones_por_numero:

            return obligaciones_por_numero[
                numero_obligacion
            ]

        # Intentar convertir a entero
        try:

            numero = int(
                float(
                    str(
                        numero_obligacion
                    ).replace(
                        ',',
                        '.'
                    )
                )
            )

            if numero in obligaciones_por_numero:

                return obligaciones_por_numero[
                    numero
                ]

        except (
            ValueError,
            TypeError
        ):

            pass

        # Comparación textual
        texto = str(
            numero_obligacion
        ).strip()

        for clave, obligacion in (
            obligaciones_por_numero.items()
        ):

            if str(
                clave
            ).strip() == texto:

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

        if isinstance(
            fila,
            dict
        ):

            return fila.get(
                '_fila_excel',
                indice
            )

        return indice
