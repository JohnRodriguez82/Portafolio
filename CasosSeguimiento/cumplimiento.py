"""
CasosSeguimiento v2.3
Lógica centralizada de cumplimiento de plazos.

Reglas:
- PENDIENTE: caso abierto dentro del plazo.
- ALERTA PREVENTIVA: próximo al vencimiento.
- CRÍTICO: llegó al día límite.
- VENCIDO: no resuelto y superó el plazo.
- RESUELTO A TIEMPO: fecha de resolución <= fecha límite.
- RESUELTO FUERA DE TIEMPO: fecha de resolución > fecha límite.
"""

from datetime import date, timedelta


ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_RESUELTO = "RESUELTO"

CUMPLIMIENTO_A_TIEMPO = "A TIEMPO"
CUMPLIMIENTO_FUERA_TIEMPO = "FUERA DE TIEMPO"


def calcular_fecha_limite(
    fecha_ingreso,
    dias_resolucion,
):
    """
    Calcula la fecha límite del caso.

    La fecha límite debe guardarse en el caso y no
    recalcularse posteriormente con una configuración
    diferente.
    """
    if not fecha_ingreso:
        return None

    try:
        dias = int(dias_resolucion)
    except (TypeError, ValueError):
        dias = 10

    return fecha_ingreso + timedelta(days=dias)


def calcular_dias_retraso(
    fecha_limite,
    fecha_resolucion,
):
    """
    Calcula los días de retraso.

    Si se resolvió antes o en la fecha límite:
        0

    Si se resolvió después:
        número de días de retraso.
    """
    if not fecha_limite or not fecha_resolucion:
        return 0

    diferencia = (
        fecha_resolucion - fecha_limite
    ).days

    return max(0, diferencia)


def calcular_cumplimiento(
    fecha_limite,
    fecha_resolucion,
):
    """
    Determina si un caso resuelto cumplió el plazo.
    """
    if not fecha_resolucion:
        return None

    dias_retraso = calcular_dias_retraso(
        fecha_limite,
        fecha_resolucion,
    )

    if dias_retraso > 0:
        return CUMPLIMIENTO_FUERA_TIEMPO

    return CUMPLIMIENTO_A_TIEMPO


def calcular_estado_pendiente(
    fecha_limite,
    fecha_actual=None,
    dias_alerta=2,
):
    """
    Determina el estado de un caso todavía no resuelto.
    """
    if not fecha_limite:
        return (
            "🔵 PENDIENTE",
            "blue",
            None,
        )

    if fecha_actual is None:
        fecha_actual = date.today()

    dias_restantes = (
        fecha_limite - fecha_actual
    ).days

    if dias_restantes < 0:
        return (
            "🚨 VENCIDO",
            "red",
            dias_restantes,
        )

    if dias_restantes == 0:
        return (
            "🔴 CRÍTICO",
            "red",
            dias_restantes,
        )

    if dias_restantes <= int(dias_alerta):
        return (
            "⚠️ ALERTA PREVENTIVA",
            "orange",
            dias_restantes,
        )

    return (
        "🔵 PENDIENTE",
        "blue",
        dias_restantes,
    )


def obtener_estado_visual(
    fecha_limite,
    fecha_resolucion=None,
    estado_db=None,
    dias_alerta=2,
):
    """
    Determina el estado visual del caso.

    Reglas:

    1. RESUELTO + fecha de resolución:
       se determina si cumplió o no el plazo.

    2. RESUELTO sin fecha de resolución:
       se muestra como RESUELTO - SIN FECHA.
       No se asume que fue resuelto a tiempo.

    3. PENDIENTE:
       se calcula según la fecha límite.
    """

    # ========================================================
    # CASO RESUELTO CON FECHA
    # ========================================================

    if (
        estado_db == ESTADO_RESUELTO
        and fecha_resolucion is not None
    ):

        if not fecha_limite:

            return (
                "🟢 RESUELTO",
                "green",
                0,
            )

        dias_retraso = (
            calcular_dias_retraso(
                fecha_limite,
                fecha_resolucion,
            )
        )

        if dias_retraso > 0:

            return (
                (
                    "🟠 RESUELTO FUERA DE TIEMPO "
                    f"({dias_retraso} "
                    f"{'día' if dias_retraso == 1 else 'días'})"
                ),
                "orange",
                dias_retraso,
            )

        return (
            "🟢 RESUELTO A TIEMPO",
            "green",
            0,
        )

    # ========================================================
    # CASO RESUELTO SIN FECHA
    # ========================================================

    if (
        estado_db == ESTADO_RESUELTO
        and fecha_resolucion is None
    ):

        return (
            "🟣 RESUELTO - SIN FECHA",
            "purple",
            0,
        )

    # ========================================================
    # CASO PENDIENTE
    # ========================================================

    return calcular_estado_pendiente(
        fecha_limite,
        dias_alerta=dias_alerta,
    )



def detalle_cumplimiento(
    fecha_limite,
    fecha_resolucion,
):
    """
    Texto descriptivo para mostrar en la interfaz.
    """
    if not fecha_resolucion:
        return ""

    dias = calcular_dias_retraso(
        fecha_limite,
        fecha_resolucion,
    )

    if dias > 0:
        return (
            "Resuelto fuera de tiempo — "
            f"{dias} "
            f"{'día' if dias == 1 else 'días'} de retraso"
        )

    return "Resuelto dentro del plazo"
