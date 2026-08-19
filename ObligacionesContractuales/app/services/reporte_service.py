"""
Servicio de gestión de reportes mensuales.

Responsabilidades:

- Buscar reportes mensuales.
- Crear reportes mensuales.
- Obtener o crear reportes.
- Resolver obligaciones por número o por objeto.
- Calcular fechas de un mes.
- Validar periodos.
- Obtener la última actividad.
- Obtener el siguiente número de actividad.
- Obtener reportes de una obligación.
- Obtener reportes por ID.
- Obtener evidencias de un reporte.
- Contar evidencias.

Este servicio NO contiene rutas Flask.

El commit debe ser responsabilidad del proceso
que utiliza el servicio.
"""

import calendar

from datetime import date

from models import (
    db,
    Obligacion,
    ReporteMensual,
    Evidencia
)


class ReporteService:
    """
    Servicio de dominio para ReporteMensual.
    """

    # ============================================================
    # OBTENER REPORTE POR OBLIGACIÓN
    # ============================================================

    @staticmethod
    def obtener_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Busca un reporte mensual asociado a una obligación.

        Args:
            obligacion_id: ID de la obligación.
            mes: Número del mes.
            anio: Año del reporte.

        Returns:
            ReporteMensual | None
        """

        return (
            ReporteMensual.query
            .filter_by(
                obligacion_id=obligacion_id,
                mes=int(mes),
                anio=int(anio)
            )
            .first()
        )

    # ============================================================
    # OBTENER REPORTE POR OBJETO
    # ============================================================

    @staticmethod
    def obtener_reporte_por_obligacion(
        obligacion,
        mes,
        anio
    ):
        """
        Busca un reporte utilizando directamente
        un objeto Obligacion.
        """

        if not obligacion:
            return None

        return ReporteService.obtener_reporte(
            obligacion_id=obligacion.id,
            mes=mes,
            anio=anio
        )

    # ============================================================
    # RESOLVER OBLIGACIÓN
    # ============================================================

    @staticmethod
    def resolver_obligacion(
        obligacion,
        contrato=None
    ):
        """
        Resuelve una obligación recibida como:

        - objeto Obligacion
        - ID de obligación
        - número de obligación

        Cuando se recibe un número, se utiliza el contrato
        para garantizar que la obligación pertenece al
        contrato correspondiente.

        Returns:
            Obligacion | None
        """

        if obligacion is None:
            return None

        # --------------------------------------------------------
        # Ya es un objeto Obligacion
        # --------------------------------------------------------

        if isinstance(
            obligacion,
            Obligacion
        ):
            return obligacion

        # --------------------------------------------------------
        # Obtener valor numérico
        # --------------------------------------------------------

        try:
            valor = int(
                obligacion
            )

        except (
            TypeError,
            ValueError
        ):
            return None

        # --------------------------------------------------------
        # Si tenemos contrato, buscar por número
        # dentro del contrato.
        # --------------------------------------------------------

        if contrato is not None:

            resultado = (
                Obligacion.query
                .filter_by(
                    contrato_id=contrato.id,
                    numero=valor
                )
                .first()
            )

            if resultado:
                return resultado

        # --------------------------------------------------------
        # Como alternativa, intentar por ID.
        # --------------------------------------------------------

        return (
            Obligacion.query
            .filter_by(
                id=valor
            )
            .first()
        )

    # ============================================================
    # CREAR REPORTE
    # ============================================================

    @staticmethod
    def crear_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Crea un nuevo reporte mensual.

        No realiza commit.
        """

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                "El mes o año del reporte no es válido."
            )

        fecha_inicio, fecha_fin = (
            ReporteService.obtener_fechas_mes(
                mes,
                anio
            )
        )

        reporte = ReporteMensual(
            mes=int(mes),
            anio=int(anio),
            fecha_inicio_reporte=fecha_inicio,
            fecha_fin_reporte=fecha_fin,
            obligacion_id=obligacion_id
        )

        db.session.add(
            reporte
        )

        db.session.flush()

        return reporte

    # ============================================================
    # OBTENER O CREAR REPORTE POR ID
    # ============================================================

    @staticmethod
    def obtener_o_crear_por_id(
        obligacion_id,
        mes,
        anio
    ):
        """
        Obtiene o crea un reporte utilizando el ID
        de la obligación.

        Returns:
            ReporteMensual
        """

        reporte = (
            ReporteService.obtener_reporte(
                obligacion_id=obligacion_id,
                mes=mes,
                anio=anio
            )
        )

        if reporte:
            return reporte

        return ReporteService.crear_reporte(
            obligacion_id=obligacion_id,
            mes=mes,
            anio=anio
        )

    # ============================================================
    # OBTENER O CREAR REPORTE
    # ============================================================

    @staticmethod
    def obtener_o_crear_reporte(
        contrato=None,
        obligacion=None,
        mes=None,
        anio=None,
        obligacion_id=None
    ):
        """
        Obtiene un reporte existente o crea uno nuevo.

        Esta es la interfaz principal utilizada por
        CargaMasivaService.

        Ejemplo:

            reporte = ReporteService.obtener_o_crear_reporte(
                contrato=contrato,
                obligacion=numero_obligacion,
                mes=mes,
                anio=anio
            )

        También permite utilizar directamente
        obligacion_id para compatibilidad.

        Returns:
            ReporteMensual
        """

        # --------------------------------------------------------
        # Validar periodo
        # --------------------------------------------------------

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                "El mes o año del reporte no es válido."
            )

        # --------------------------------------------------------
        # Resolver obligación
        # --------------------------------------------------------

        obligacion_actual = None

        if obligacion is not None:

            obligacion_actual = (
                ReporteService.resolver_obligacion(
                    obligacion=obligacion,
                    contrato=contrato
                )
            )

        elif obligacion_id is not None:

            obligacion_actual = (
                ReporteService.resolver_obligacion(
                    obligacion=obligacion_id,
                    contrato=contrato
                )
            )

        # --------------------------------------------------------
        # Validar obligación
        # --------------------------------------------------------

        if obligacion_actual is None:

            raise ValueError(
                "No fue posible identificar la obligación "
                "para crear el reporte."
            )

        # --------------------------------------------------------
        # Validar contrato
        # --------------------------------------------------------

        if contrato is not None:

            if (
                obligacion_actual.contrato_id
                != contrato.id
            ):
                raise ValueError(
                    "La obligación no pertenece al "
                    "contrato seleccionado."
                )

        # --------------------------------------------------------
        # Buscar reporte existente
        # --------------------------------------------------------

        reporte = (
            ReporteService.obtener_reporte_por_obligacion(
                obligacion=obligacion_actual,
                mes=mes,
                anio=anio
            )
        )

        if reporte:

            return reporte

        # --------------------------------------------------------
        # Crear reporte
        # --------------------------------------------------------

        return ReporteService.crear_reporte(
            obligacion_id=obligacion_actual.id,
            mes=mes,
            anio=anio
        )

    # ============================================================
    # FECHAS DEL MES
    # ============================================================

    @staticmethod
    def obtener_fechas_mes(
        mes,
        anio
    ):
        """
        Obtiene el primer y último día de un mes.

        Ejemplo:

            obtener_fechas_mes(8, 2026)

        retorna:

            (
                date(2026, 8, 1),
                date(2026, 8, 31)
            )
        """

        mes = int(mes)
        anio = int(anio)

        _, ultimo_dia = calendar.monthrange(
            anio,
            mes
        )

        fecha_inicio = date(
            anio,
            mes,
            1
        )

        fecha_fin = date(
            anio,
            mes,
            ultimo_dia
        )

        return (
            fecha_inicio,
            fecha_fin
        )

    # ============================================================
    # VALIDAR MES
    # ============================================================

    @staticmethod
    def mes_valido(
        mes
    ):
        """
        Verifica si el número de mes es válido.
        """

        try:

            mes = int(
                mes
            )

        except (
            TypeError,
            ValueError
        ):

            return False

        return 1 <= mes <= 12

    # ============================================================
    # VALIDAR AÑO
    # ============================================================

    @staticmethod
    def anio_valido(
        anio
    ):
        """
        Verifica si el año es válido.
        """

        try:

            anio = int(
                anio
            )

        except (
            TypeError,
            ValueError
        ):

            return False

        return (
            1900
            <= anio
            <= 2100
        )

    # ============================================================
    # VALIDAR PERIODO
    # ============================================================

    @staticmethod
    def periodo_valido(
        mes,
        anio
    ):
        """
        Verifica que mes y año formen
        un periodo válido.
        """

        return (
            ReporteService.mes_valido(
                mes
            )
            and
            ReporteService.anio_valido(
                anio
            )
        )

    # ============================================================
    # OBTENER ÚLTIMA ACTIVIDAD
    # ============================================================

    @staticmethod
    def obtener_ultima_actividad(
        reporte_id
    ):
        """
        Obtiene el número de la última actividad
        registrada en un reporte.

        Returns:
            int
        """

        ultima = (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia.numero_actividad.desc()
            )
            .first()
        )

        if not ultima:
            return 0

        return (
            ultima.numero_actividad
        )

    # ============================================================
    # SIGUIENTE ACTIVIDAD
    # ============================================================

    @staticmethod
    def obtener_siguiente_actividad(
        reporte_id
    ):
        """
        Obtiene el siguiente número de actividad
        disponible para un reporte.
        """

        ultima = (
            ReporteService.obtener_ultima_actividad(
                reporte_id
            )
        )

        return ultima + 1

    # ============================================================
    # OBTENER REPORTES DE OBLIGACIÓN
    # ============================================================

    @staticmethod
    def obtener_reportes_obligacion(
        obligacion_id
    ):
        """
        Obtiene todos los reportes asociados
        a una obligación.

        Orden:

        - Año descendente.
        - Mes descendente.
        """

        return (
            ReporteMensual.query
            .filter_by(
                obligacion_id=obligacion_id
            )
            .order_by(
                ReporteMensual.anio.desc(),
                ReporteMensual.mes.desc()
            )
            .all()
        )

    # ============================================================
    # OBTENER REPORTES POR OBJETO
    # ============================================================

    @staticmethod
    def obtener_reportes_de_obligacion(
        obligacion
    ):
        """
        Obtiene todos los reportes de una obligación.
        """

        if not obligacion:
            return []

        return (
            ReporteService.obtener_reportes_obligacion(
                obligacion.id
            )
        )

    # ============================================================
    # OBTENER REPORTE POR ID
    # ============================================================

    @staticmethod
    def obtener_por_id(
        reporte_id
    ):
        """
        Obtiene un reporte por su ID.
        """

        return (
            ReporteMensual.query
            .filter_by(
                id=reporte_id
            )
            .first()
        )

    # ============================================================
    # OBTENER EVIDENCIAS
    # ============================================================

    @staticmethod
    def obtener_evidencias(
        reporte_id
    ):
        """
        Obtiene las evidencias de un reporte
        ordenadas por número de actividad.
        """

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .order_by(
                Evidencia.numero_actividad.asc()
            )
            .all()
        )

    # ============================================================
    # CONTAR EVIDENCIAS
    # ============================================================

    @staticmethod
    def contar_evidencias(
        reporte_id
    ):
        """
        Cuenta las evidencias asociadas a un reporte.
        """

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .count()
        )

    # ============================================================
    # EXISTE REPORTE
    # ============================================================

    @staticmethod
    def existe_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Indica si existe un reporte para una obligación
        en un periodo determinado.
        """

        return (
            ReporteService.obtener_reporte(
                obligacion_id=obligacion_id,
                mes=mes,
                anio=anio
            )
            is not None
        )

    # ============================================================
    # OBTENER REPORTES DE UN CONTRATO
    # ============================================================

    @staticmethod
    def obtener_reportes_contrato(
        contrato
    ):
        """
        Obtiene todos los reportes asociados
        a las obligaciones de un contrato.
        """

        if not contrato:
            return []

        obligaciones = (
            contrato.obligaciones
        )

        if not obligaciones:
            return []

        resultado = []

        for obligacion in obligaciones:

            reportes = (
                ReporteService.obtener_reportes_de_obligacion(
                    obligacion
                )
            )

            resultado.extend(
                reportes
            )

        return resultado

    # ============================================================
    # OBTENER REPORTE DEL CONTRATO POR PERIODO
    # ============================================================

    @staticmethod
    def obtener_reportes_contrato_periodo(
        contrato,
        mes,
        anio
    ):
        """
        Obtiene los reportes de todas las obligaciones
        de un contrato para un periodo determinado.
        """

        if not contrato:
            return []

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            return []

        return (
            ReporteMensual.query
            .join(
                Obligacion,
                ReporteMensual.obligacion_id
                == Obligacion.id
            )
            .filter(
                Obligacion.contrato_id
                == contrato.id,
                ReporteMensual.mes
                == int(mes),
                ReporteMensual.anio
                == int(anio)
            )
            .order_by(
                Obligacion.numero.asc()
            )
            .all()
        )


# ============================================================
# INSTANCIA COMPARTIDA
# ============================================================

reporte_service = ReporteService()
