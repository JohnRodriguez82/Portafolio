"""
Servicio para gestionar los reportes mensuales.

Responsabilidades:
- Obtener reportes mensuales.
- Crear reportes mensuales.
- Obtener o crear un reporte.
- Calcular las fechas de un mes.
- Obtener el número de la última actividad.
- Obtener reportes de una obligación.
- Obtener reportes de un contrato.

Este módulo contiene lógica de negocio y no define rutas Flask.
"""

import calendar

from datetime import date

from models import (
    db,
    ReporteMensual,
    Evidencia
)


class ReporteService:
    """
    Servicio de dominio para ReporteMensual.
    """

    # ========================================================
    # OBTENER REPORTE
    # ========================================================

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
                mes=mes,
                anio=anio,
                obligacion_id=obligacion_id
            )
            .first()
        )

    # ========================================================
    # CREAR REPORTE
    # ========================================================

    @staticmethod
    def crear_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Crea un nuevo reporte mensual.

        Args:
            obligacion_id: ID de la obligación.
            mes: Número del mes.
            anio: Año del reporte.

        Returns:
            ReporteMensual
        """

        fecha_inicio, fecha_fin = (
            ReporteService.obtener_fechas_mes(
                mes,
                anio
            )
        )

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

    # ========================================================
    # OBTENER O CREAR
    # ========================================================

    @staticmethod
    def obtener_o_crear_reporte(
        obligacion_id,
        mes,
        anio
    ):
        """
        Obtiene un reporte existente.

        Si no existe, crea uno nuevo.

        No realiza commit. El commit debe ser
        responsabilidad del proceso que utiliza
        el servicio.

        Returns:
            tuple:

                (
                    reporte,
                    creado
                )

        donde creado es True si se creó un
        nuevo reporte.
        """

        reporte = (
            ReporteService.obtener_reporte(
                obligacion_id,
                mes,
                anio
            )
        )

        if reporte:

            return (
                reporte,
                False
            )

        reporte = (
            ReporteService.crear_reporte(
                obligacion_id,
                mes,
                anio
            )
        )

        return (
            reporte,
            True
        )

    # ========================================================
    # FECHAS DEL MES
    # ========================================================

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

        Returns:
            tuple[date, date]
        """

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

    # ========================================================
    # VALIDAR MES
    # ========================================================

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

    # ========================================================
    # VALIDAR AÑO
    # ========================================================

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

    # ========================================================
    # VALIDAR PERIODO
    # ========================================================

    @staticmethod
    def periodo_valido(
        mes,
        anio
    ):
        """
        Verifica que mes y año formen un periodo válido.
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

    # ========================================================
    # OBTENER ÚLTIMA ACTIVIDAD
    # ========================================================

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

    # ========================================================
    # SIGUIENTE ACTIVIDAD
    # ========================================================

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

    # ========================================================
    # OBTENER REPORTES DE OBLIGACIÓN
    # ========================================================

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

    # ========================================================
    # OBTENER REPORTE POR ID
    # ========================================================

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

    # ========================================================
    # OBTENER EVIDENCIAS
    # ========================================================

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

    # ========================================================
    # CONTAR EVIDENCIAS
    # ========================================================

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

    # ========================================================
    # NOMBRE DEL MES
    # ========================================================

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

            mes = int(
                mes
            )

        except (
            TypeError,
            ValueError
        ):

            return ''

        if not 1 <= mes <= 12:

            return ''

        return meses[
            mes
        ]

    # ========================================================
    # NOMBRE DEL PERIODO
    # ========================================================

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

            return str(
                anio
            )

        return (
            f'{nombre} {anio}'
        )