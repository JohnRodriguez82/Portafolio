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
- Obtener evidencias asociadas.

Este servicio NO contiene rutas Flask.
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
    Servicio de dominio para reportes mensuales.
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
        Obtiene un reporte mensual existente.

        Args:
            obligacion_id: ID de la obligación.
            mes: número del mes.
            anio: año.

        Returns:
            ReporteMensual | None
        """

        if not obligacion_id:
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

    # ========================================================
    # OBTENER O CREAR REPORTE
    # ========================================================

    @staticmethod
    def obtener_o_crear_reporte(
        contrato,
        obligacion,
        mes,
        anio
    ):
        """
        Obtiene o crea el reporte mensual correspondiente
        a una obligación.

        IMPORTANTE:

        Este método retorna directamente el objeto
        ReporteMensual porque CargaMasivaService trabaja
        directamente con dicho objeto.

        No realiza commit.
        El commit queda bajo responsabilidad del proceso
        que utiliza el servicio.
        """

        if contrato is None:
            raise ValueError(
                "No se recibió el contrato."
            )

        if obligacion is None:
            raise ValueError(
                "No se recibió la obligación."
            )

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                "El mes o año del reporte no son válidos."
            )

        mes = int(mes)
        anio = int(anio)

        reporte = (
            ReporteService.obtener_reporte(
                obligacion_id=obligacion.id,
                mes=mes,
                anio=anio
            )
        )

        if reporte:
            return reporte

        return ReporteService.crear_reporte(
            obligacion_id=obligacion.id,
            mes=mes,
            anio=anio
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

        No realiza commit.
        """

        if not ReporteService.periodo_valido(
            mes,
            anio
        ):
            raise ValueError(
                "El mes o año no son válidos."
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

        # Flush para obtener el ID sin hacer commit.
        db.session.flush()

        return reporte

    # ========================================================
    # OBTENER FECHAS DEL MES
    # ========================================================

    @staticmethod
    def obtener_fechas_mes(
        mes,
        anio
    ):
        """
        Obtiene el primer y último día del mes.

        Returns:
            tuple[date, date]
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

    # ========================================================
    # VALIDAR MES
    # ========================================================

    @staticmethod
    def mes_valido(
        mes
    ):
        """
        Verifica si el mes es válido.
        """

        try:
            mes = int(mes)
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
            anio = int(anio)
        except (
            TypeError,
            ValueError
        ):
            return False

        return (
            1900 <= anio <= 2100
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
        Verifica que mes y año sean válidos.
        """

        return (
            ReporteService.mes_valido(mes)
            and
            ReporteService.anio_valido(anio)
        )

    # ========================================================
    # OBTENER ÚLTIMA ACTIVIDAD
    # ========================================================

    @staticmethod
    def obtener_ultima_actividad(
        reporte_id
    ):
        """
        Obtiene el último número de actividad utilizado
        dentro de un reporte.
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

        if ultima is None:
            return 0

        return (
            ultima.numero_actividad or 0
        )

    # ========================================================
    # OBTENER SIGUIENTE ACTIVIDAD
    # ========================================================

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

    # ========================================================
    # OBTENER REPORTES DE UNA OBLIGACIÓN
    # ========================================================

    @staticmethod
    def obtener_reportes_obligacion(
        obligacion_id
    ):
        """
        Obtiene todos los reportes de una obligación.
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
    # OBTENER REPORTES DE UN CONTRATO
    # ========================================================

    @staticmethod
    def obtener_reportes_contrato(
        contrato_id
    ):
        """
        Obtiene los reportes asociados a todas las
        obligaciones de un contrato.
        """

        from models import Obligacion

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

    # ========================================================
    # OBTENER POR ID
    # ========================================================

    @staticmethod
    def obtener_por_id(
        reporte_id
    ):
        """
        Obtiene un reporte por ID.
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
        Obtiene las evidencias de un reporte.
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
        Cuenta las evidencias de un reporte.
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
# INSTANCIA DEL SERVICIO
# ============================================================

reporte_service = ReporteService()
