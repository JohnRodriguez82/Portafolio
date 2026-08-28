"""
CasosSeguimiento v2.1
Proceso independiente del scheduler.

Ejecutar:

    python scheduler_runner.py

Este proceso mantiene activas:
- revisión IMAP cada 5 minutos;
- verificación de alertas cada hora.
"""

import logging
import signal
import sys
import time

from config_manager import config_exists
from scheduler_service import (
    iniciar_scheduler,
    detener_scheduler,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "casos_seguimiento.scheduler"
)


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown_handler(
    signum,
    frame,
):
    logger.info(
        "Señal de apagado recibida."
    )

    detener_scheduler()

    sys.exit(0)


signal.signal(
    signal.SIGINT,
    shutdown_handler,
)

signal.signal(
    signal.SIGTERM,
    shutdown_handler,
)


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "CasosSeguimiento v2.1 - Scheduler"
    )

    if not config_exists():

        logger.error(
            "No existe configuración."
        )

        logger.error(
            "Ejecuta primero app.py y "
            "completa la configuración inicial."
        )

        sys.exit(1)

    iniciar_scheduler()

    logger.info(
        "Scheduler ejecutándose."
    )

    logger.info(
        "Correo: cada 5 minutos."
    )

    logger.info(
        "Alertas: cada hora."
    )

    try:

        while True:
            time.sleep(60)

    except KeyboardInterrupt:

        shutdown_handler(
            None,
            None,
        )


if __name__ == "__main__":
    main()
