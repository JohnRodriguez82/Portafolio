"""
CasosSeguimiento v2.1
Servicio de tareas programadas.

Tareas:
- Revisar correo cada 5 minutos.
- Verificar alertas cada hora.

IMPORTANTE:
Este módulo NO debe depender del ciclo de vida de Streamlit.
Para ejecución continua se recomienda scheduler_runner.py.
"""

import logging
from datetime import date
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config_manager import get_encargado
from database import Caso, LogAlerta, get_db
from email_processor import (
    check_emails_and_download_excel,
)
from email_sender import (
    enviar_alerta_individual,
    enviar_resumen_casos,
)
from excel_parser import procesar_archivo


logger = logging.getLogger(__name__)


scheduler = None


# ============================================================
# REVISAR CORREO
# ============================================================

def tarea_revisar_correo():

    logger.info(
        "Iniciando revisión automática de correo."
    )

    try:

        files = (
            check_emails_and_download_excel()
        )

        if not files:
            logger.info(
                "No se encontraron archivos nuevos."
            )
            return

        for filepath in files:

            logger.info(
                "Procesando archivo: %s",
                Path(filepath).name,
            )

            resultado = procesar_archivo(
                filepath
            )

            if resultado["ok"]:

                logger.info(
                    "Archivo procesado. "
                    "Insertados=%s Actualizados=%s "
                    "Errores=%s",
                    resultado["insertados"],
                    resultado["actualizados"],
                    len(
                        resultado.get(
                            "errores",
                            [],
                        )
                    ),
                )

            else:

                logger.error(
                    "Error procesando %s: %s",
                    filepath,
                    resultado.get(
                        "error"
                    ),
                )

    except Exception:

        logger.exception(
            "Error en tarea_revisar_correo."
        )


# ============================================================
# ALERTAS
# ============================================================

def tarea_verificar_alertas():

    logger.info(
        "Iniciando verificación automática de alertas."
    )

    db = get_db()

    try:

        encargado = get_encargado()

        destino = str(
            encargado.get(
                "email",
                "",
            )
        ).strip()

        if not destino:

            logger.warning(
                "No existe correo de encargado."
            )

            return

        hoy = date.today()

        limite_dias = 10
        dias_alerta = 2

        dia_alerta_preventiva = (
            limite_dias - dias_alerta
        )

        casos = (
            db.query(Caso)
            .all()
        )

        vencidos = []
        preventivos = []
        pendientes = []

        for caso in casos:

            if (
                caso.estado == "RESUELTO"
                or caso.fecha_validacion
                or not caso.fecha_ingreso
            ):
                continue

            dias_transcurridos = (
                hoy - caso.fecha_ingreso
            ).days

            pendientes.append(caso)

            # ------------------------------------------------
            # PREVENTIVA
            # ------------------------------------------------

            if (
                dias_transcurridos
                >= dia_alerta_preventiva
                and not caso.alerta_preventiva_enviada
                and dias_transcurridos
                <= limite_dias
            ):

                ok, error = (
                    enviar_alerta_individual(
                        destino,
                        caso,
                        "PREVENTIVA",
                        dias_transcurridos,
                    )
                )

                if ok:

                    caso.alerta_preventiva_enviada = (
                        True
                    )

                    db.add(
                        LogAlerta(
                            caso_id=caso.id,
                            tipo_alerta="PREVENTIVA",
                            destinatario=destino,
                            contenido=(
                                "Alerta preventiva. "
                                f"Día {dias_transcurridos}."
                            ),
                        )
                    )

                    logger.info(
                        "Alerta preventiva enviada: %s",
                        caso.numero_caso,
                    )

                else:

                    logger.error(
                        "No se pudo enviar alerta preventiva "
                        "%s: %s",
                        caso.numero_caso,
                        error,
                    )

            # ------------------------------------------------
            # VENCIDA
            # ------------------------------------------------

            if (
                dias_transcurridos
                > limite_dias
            ):

                if caso not in vencidos:
                    vencidos.append(caso)

                caso.estado = "VENCIDO"

                if not caso.alerta_vencido_enviada:

                    ok, error = (
                        enviar_alerta_individual(
                            destino,
                            caso,
                            "VENCIDA",
                            dias_transcurridos,
                        )
                    )

                    if ok:

                        caso.alerta_vencido_enviada = (
                            True
                        )

                        db.add(
                            LogAlerta(
                                caso_id=caso.id,
                                tipo_alerta="VENCIDA",
                                destinatario=destino,
                                contenido=(
                                    "Caso vencido. "
                                    f"Día {dias_transcurridos}."
                                ),
                            )
                        )

                        logger.info(
                            "Alerta vencida enviada: %s",
                            caso.numero_caso,
                        )

                    else:

                        logger.error(
                            "No se pudo enviar alerta vencida "
                            "%s: %s",
                            caso.numero_caso,
                            error,
                        )

            # ------------------------------------------------
            # PREVENTIVOS PARA RESUMEN
            # ------------------------------------------------

            if (
                dias_transcurridos
                == dia_alerta_preventiva
            ):
                if caso not in preventivos:
                    preventivos.append(
                        caso
                    )

        db.commit()

        # ----------------------------------------------------
        # RESUMEN
        # ----------------------------------------------------

        if vencidos or preventivos:

            ok, error = (
                enviar_resumen_casos(
                    destino,
                    pendientes,
                    vencidos,
                    preventivos,
                )
            )

            if ok:

                logger.info(
                    "Resumen automático enviado a %s",
                    destino,
                )

            else:

                logger.error(
                    "No se pudo enviar resumen: %s",
                    error,
                )

    except Exception:

        db.rollback()

        logger.exception(
            "Error general verificando alertas."
        )

    finally:

        db.close()


# ============================================================
# SCHEDULER
# ============================================================

def iniciar_scheduler():

    global scheduler

    if scheduler and scheduler.running:
        return scheduler

    scheduler = BackgroundScheduler(
        daemon=True,
    )

    scheduler.add_job(
        tarea_revisar_correo,
        trigger=IntervalTrigger(
            minutes=5
        ),
        id="revisar_correo",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        tarea_verificar_alertas,
        trigger=IntervalTrigger(
            hours=1
        ),
        id="verificar_alertas",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.info(
        "Scheduler iniciado."
    )

    return scheduler


def detener_scheduler():

    global scheduler

    if scheduler:

        try:
            scheduler.shutdown(
                wait=False
            )
        except Exception:
            logger.exception(
                "Error cerrando scheduler."
            )

        scheduler = None

        logger.info(
            "Scheduler detenido."
        )
