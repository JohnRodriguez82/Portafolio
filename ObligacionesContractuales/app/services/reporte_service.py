"""
Servicio para gestionar los reportes mensuales.

Responsabilidades:
- Obtener reportes mensuales.
- Crear reportes mensuales.
- Obtener o crear reportes.
- Trabajar con contrato + obligación.
- Calcular las fechas de un mes.
- Obtener el número de la última actividad.
- Obtener reportes de una obligación.
- Obtener reportes por contrato.
- Obtener evidencias de un reporte.

Este servicio NO contiene rutas Flask.
"""

import calendar

from datetime import date

from models import (
    db,
    ReporteMensual,
    Evidencia,
    Obligacion
)


class ReporteService:
    """
    Servicio de dominio para ReporteMensual.
    """

    # ============================================================
    # OBTENER REPORTE
    # ============================================================

    @staticmethod
    def obtener_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Busca un reporte mensual asociado
        a una obligación.

        Args:
            obligacion_id:
                ID de la obligación.

            mes:
                Número del mes.

            anio:
                Año del reporte.

        Returns:
            ReporteMensual | None
        """

        if not obligacion_id:
            return None

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            return None

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
    # OBTENER REPORTE POR ID
    # ============================================================

    @staticmethod
    def obtener_por_id(
        reporte_id
    ):
        """
        Obtiene un reporte por su ID.
        """

        if not reporte_id:
            return None

        return (
            ReporteMensual.query
            .filter_by(
                id=reporte_id
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

        El commit queda bajo responsabilidad
        del proceso que utiliza el servicio.

        Returns:
            ReporteMensual
        """

        if not obligacion_id:
            raise ValueError(
                'Debe indicar la obligación.'
            )

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                'El mes o año del reporte no es válido.'
            )

        mes = int(mes)
        anio = int(anio)

        # --------------------------------------------------------
        # Evitar duplicados
        # --------------------------------------------------------

        existente = (
            ReporteService.obtener_reporte(
                obligacion_id=obligacion_id,
                mes=mes,
                anio=anio
            )
        )

        if existente:
            return existente

        # --------------------------------------------------------
        # Fechas del periodo
        # --------------------------------------------------------

        fecha_inicio, fecha_fin = (
            ReporteService.obtener_fechas_mes(
                mes,
                anio
            )
        )

        # --------------------------------------------------------
        # Crear objeto
        # --------------------------------------------------------

        reporte = ReporteMensual(
            mes=mes,
            anio=anio,
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
    # OBTENER O CREAR REPORTE
    # ============================================================

    @staticmethod
    def obtener_o_crear_reporte(
        contrato=None,
        obligacion=None,
        obligacion_id=None,
        mes=None,
        anio=None
    ):
        """
        Obtiene o crea un reporte mensual.

        Esta es la interfaz principal utilizada por
        CargaMasivaService.

        Puede recibir:

            contrato
            obligacion
            mes
            anio

        También conserva compatibilidad con código
        anterior que utilice:

            obligacion_id
            mes
            anio

        IMPORTANTE:

        Retorna directamente el objeto ReporteMensual.

        NO retorna:

            (reporte, creado)

        porque CargaMasivaService necesita trabajar
        directamente con el reporte.
        """

        # --------------------------------------------------------
        # Determinar ID de obligación
        # --------------------------------------------------------

        if obligacion is not None:

            obligacion_id = getattr(
                obligacion,
                'id',
                None
            )

        if not obligacion_id:

            raise ValueError(
                'No fue posible identificar la obligación.'
            )

        # --------------------------------------------------------
        # Validar periodo
        # --------------------------------------------------------

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):

            raise ValueError(
                'El mes o año del reporte no es válido.'
            )

        mes = int(mes)
        anio = int(anio)

        # --------------------------------------------------------
        # Validar que la obligación pertenezca
        # al contrato cuando se proporciona contrato
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
                contrato_id
                and obligacion_contrato_id
                and
                contrato_id
                != obligacion_contrato_id
            ):

                raise ValueError(
                    'La obligación no pertenece '
                    'al contrato indicado.'
                )

        # --------------------------------------------------------
        # Buscar reporte existente
        # --------------------------------------------------------

        reporte = (
            ReporteService.obtener_reporte(
                obligacion_id=obligacion_id,
                mes=mes,
                anio=anio
            )
        )

        if reporte:

            return reporte

        # --------------------------------------------------------
        # Crear reporte
        # --------------------------------------------------------

        return (
            ReporteService.crear_reporte(
                obligacion_id=obligacion_id,
                mes=mes,
                anio=anio
            )
        )

    # ============================================================
    # OBTENER FECHAS DEL MES
    # ============================================================

    @staticmethod
    def obtener_fechas_mes(
        mes,
        anio
    ):
        """
        Obtiene el primer y último día del mes.

        Ejemplo:

            obtener_fechas_mes(8, 2026)

        retorna:

            (
                date(2026, 8, 1),
                date(2026, 8, 31)
            )
        """

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                'Periodo inválido.'
            )

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

            mes = int(mes)

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

            anio = int(anio)

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

        if not reporte_id:
            return 0

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
            or 0
        )

    # ============================================================
    # OBTENER SIGUIENTE ACTIVIDAD
    # ============================================================

    @staticmethod
    def obtener_siguiente_actividad(
        reporte_id
    ):
        """
        Obtiene el siguiente número de actividad.
        """

        return (
            ReporteService.obtener_ultima_actividad(
                reporte_id
            )
            + 1
        )

    # ============================================================
    # OBTENER REPORTES DE UNA OBLIGACIÓN
    # ============================================================

    @staticmethod
    def obtener_reportes_obligacion(
        obligacion_id
    ):
        """
        Obtiene todos los reportes asociados
        a una obligación.

        Orden:
            Año descendente.
            Mes descendente.
        """

        if not obligacion_id:
            return []

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
    # OBTENER REPORTES DE CONTRATO
    # ============================================================

    @staticmethod
    def obtener_reportes_contrato(
        contrato_id
    ):
        """
        Obtiene todos los reportes asociados
        a un contrato.

        Se utiliza la relación:

            Contrato
                |
                +-- Obligacion
                        |
                        +-- ReporteMensual
        """

        if not contrato_id:
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
                == contrato_id
            )
            .order_by(
                ReporteMensual.anio.desc(),
                ReporteMensual.mes.desc()
            )
            .all()
        )

    # ============================================================
    # OBTENER EVIDENCIAS
    # ============================================================

    @staticmethod
    def obtener_evidencias(
        reporte_id
    ):
        """
        Obtiene las evidencias de un reporte.

        Ordenadas por número de actividad.
        """

        if not reporte_id:
            return []

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
        Cuenta las evidencias asociadas
        a un reporte.
        """

        if not reporte_id:
            return 0

        return (
            Evidencia.query
            .filter_by(
                reporte_id=reporte_id
            )
            .count()
        )

    # ============================================================
    # NOMBRE DEL MES
    # ============================================================

    @staticmethod
    def nombre_mes(
        mes
    ):
        """
        Devuelve el nombre del mes en español.
        """

        meses = [
            '',
            'Enero',
            'Febrero',
            'Marzo',
            'Abril',
            'Mayo',
            'Junio',
            'Julio',
            'Agosto',
            'Septiembre',
            'Octubre',
            'Noviembre',
            'Diciembre'
        ]

        try:

            mes = int(mes)

        except (
            TypeError,
            ValueError
        ):

            return ''

        if not 1 <= mes <= 12:
            return ''

        return meses[mes]

    # ============================================================
    # NOMBRE DEL PERIODO
    # ============================================================

    @staticmethod
    def nombre_periodo(
        mes,
        anio
    ):
        """
        Devuelve el periodo en formato:

            Agosto 2026
        """

        nombre = (
            ReporteService.nombre_mes(
                mes
            )
        )

        if not nombre:
            return str(anio)

        return (
            f'{nombre} {anio}'
        )


# ============================================================
# INSTANCIA DEL SERVICIO
# ============================================================

reporte_service = (
    ReporteService()
)
