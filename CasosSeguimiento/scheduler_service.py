"""
CasosSeguimiento v2.2
Servicio de tareas programadas.

Funciones:
- Revisar correo periódicamente.
- Procesar archivos nuevos.
- Verificar alertas automáticamente.

Regla v2.2:
Las alertas automáticas solamente se generan para
profesionales configurados para seguimiento.
"""

import os

from datetime import (
    datetime,
    date,
)

from apscheduler.schedulers.background import (
    BackgroundScheduler,
)

from apscheduler.triggers.interval import (
    IntervalTrigger,
)

from database import (
    get_db,
    Caso,
    LogAlerta,
)

from email_processor import (
    check_emails_and_download_excel,
)

from excel_parser import (
    procesar_archivo,
)

from email_sender import (
    enviar_alerta_individual,
    enviar_resumen_casos,
)

from config_manager import (
    get_encargado,
    get_profesionales_seguimiento_normalizados,
    normalizar_nombre_profesional,
    load_config,
)


scheduler = None


# ============================================================
# PROFESIONALES
# ============================================================

def caso_en_seguimiento(
    caso,
    profesionales_normalizados,
):
    """
    Determina si un caso pertenece a un profesional
    configurado para seguimiento.
    """

    nombre = (
        normalizar_nombre_profesional(
            caso.profesional
        )
    )

    if not nombre:

        return False

    return (
        nombre
        in profesionales_normalizados
    )


# ============================================================
# REVISIÓN DE CORREO
# ============================================================

def tarea_revisar_correo():

    print(
        f"[{datetime.now()}] "
        "Revisando correos..."
    )

    try:

        files = (
            check_emails_and_download_excel()
        )

        for f in files:

            print(
                "  → Procesando: "
                f"{os.path.basename(f)}"
            )

            res = procesar_archivo(
                f
            )

            if res["ok"]:

                print(
                    "     Insertados: "
                    f"{res['insertados']}, "
                    "Actualizados: "
                    f"{res['actualizados']}, "
                    "Cambios: "
                    f"{len(res.get('cambios', []))}"
                )

            else:

                print(
                    "     ERROR: "
                    f"{res.get('error')}"
                )

    except Exception as exc:

        print(
            "  → ERROR revisando correo: "
            f"{exc}"
        )


# ============================================================
# ALERTAS AUTOMÁTICAS
# ============================================================

def tarea_verificar_alertas():

    print(
        f"[{datetime.now()}] "
        "Verificando alertas..."
    )

    db = get_db()

    try:

        hoy = date.today()

        cfg = load_config()

        limite_dias = int(
            cfg.get(
                "tiempo_resolucion_dias",
                10,
            )
        )

        dias_alerta = int(
            cfg.get(
                "dias_alerta_previa",
                2,
            )
        )

        profesionales_normalizados = (
            get_profesionales_seguimiento_normalizados()
        )

        if not profesionales_normalizados:

            print(
                "  → No hay profesionales "
                "configurados para seguimiento."
            )

            return

        encargado = get_encargado()

        destino = encargado.get(
            "email",
            "",
        )

        if not destino:

            print(
                "  → No hay correo de "
                "encargado configurado."
            )

            return

        casos = (
            db.query(
                Caso
            ).all()
        )

        vencidos = []

        preventivos = []

        pendientes = []

        casos_ignorados = 0

        for caso in casos:

            # ------------------------------------------------
            # FILTRO CENTRAL DE v2.2
            # ------------------------------------------------

            if not caso_en_seguimiento(
                caso,
                profesionales_normalizados,
            ):

                casos_ignorados += 1

                continue

            if (
                caso.estado == "RESUELTO"
                or not caso.fecha_ingreso
            ):

                continue

            dias_transcurridos = (
                hoy
                - caso.fecha_ingreso
            ).days

            pendientes.append(
                caso
            )

            # ------------------------------------------------
            # ALERTA PREVENTIVA
            # ------------------------------------------------

            if (
                dias_transcurridos
                >= (
                    limite_dias
                    - dias_alerta
                )
                and dias_transcurridos
                <= limite_dias
                and not caso.alerta_preventiva_enviada
            ):

                ok, err = (
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
                            tipo_alerta=(
                                "PREVENTIVA"
                            ),
                            destinatario=destino,
                            contenido=(
                                "Alerta preventiva. "
                                f"Día {dias_transcurridos}."
                            ),
                        )
                    )

                    preventivos.append(
                        caso
                    )

                    print(
                        "  → ALERTA PREVENTIVA "
                        "enviada: "
                        f"{caso.numero_caso}"
                    )

                else:

                    print(
                        "  → ERROR enviando "
                        "preventiva "
                        f"{caso.numero_caso}: "
                        f"{err}"
                    )

            # ------------------------------------------------
            # ALERTA VENCIDA
            # ------------------------------------------------

            if (
                dias_transcurridos
                > limite_dias
                and not caso.alerta_vencido_enviada
            ):

                caso.estado = (
                    "VENCIDO"
                )

                ok, err = (
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
                            tipo_alerta=(
                                "VENCIDA"
                            ),
                            destinatario=destino,
                            contenido=(
                                "Caso vencido. "
                                f"Día {dias_transcurridos}."
                            ),
                        )
                    )

                    vencidos.append(
                        caso
                    )

                    print(
                        "  → ALERTA VENCIDA "
                        "enviada: "
                        f"{caso.numero_caso}"
                    )

                else:

                    print(
                        "  → ERROR enviando "
                        "vencida "
                        f"{caso.numero_caso}: "
                        f"{err}"
                    )

            # ------------------------------------------------
            # CLASIFICACIÓN PARA RESUMEN
            # ------------------------------------------------

            if (
                dias_transcurridos
                > limite_dias
            ):

                if caso not in vencidos:

                    vencidos.append(
                        caso
                    )

            elif (
                dias_transcurridos
                >= (
                    limite_dias
                    - dias_alerta
                )
            ):

                if caso not in preventivos:

                    preventivos.append(
                        caso
                    )

        db.commit()

        print(
            "  → Casos bajo seguimiento: "
            f"{len(pendientes)}"
        )

        print(
            "  → Casos fuera de seguimiento "
            f"ignorados: {casos_ignorados}"
        )

        # ----------------------------------------------------
        # RESUMEN
        # ----------------------------------------------------

        if (
            vencidos
            or preventivos
        ):

            ok, err = (
                enviar_resumen_casos(
                    destino,
                    pendientes,
                    vencidos,
                    preventivos,
                )
            )

            if ok:

                print(
                    "  → Resumen enviado a "
                    f"{destino}"
                )

            else:

                print(
                    "  → ERROR enviando resumen: "
                    f"{err}"
                )

    except Exception as exc:

        print(
            "  → ERROR general en alertas: "
            f"{exc}"
        )

        try:

            db.rollback()

        except Exception:

            pass

    finally:

        db.close()


# ============================================================
# INICIAR
# ============================================================

def iniciar_scheduler():

    global scheduler

    if (
        scheduler
        and scheduler.running
    ):

        return scheduler

    scheduler = (
        BackgroundScheduler()
    )

    scheduler.add_job(
        tarea_revisar_correo,
        IntervalTrigger(
            minutes=5
        ),
        id="revisar_correo",
        replace_existing=True,
    )

    scheduler.add_job(
        tarea_verificar_alertas,
        IntervalTrigger(
            hours=1
        ),
        id="verificar_alertas",
        replace_existing=True,
    )

    scheduler.start()

    return scheduler


# ============================================================
# DETENER
# ============================================================

def detener_scheduler():

    global scheduler

    if scheduler:

        scheduler.shutdown()

        scheduler = None
