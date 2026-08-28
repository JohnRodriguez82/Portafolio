"""
Servicio de tareas programadas.
Revisa correo periódicamente y envía alertas automáticas.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date
from database import get_db, Caso, LogAlerta
from email_processor import check_emails_and_download_excel
from excel_parser import procesar_archivo
from email_sender import enviar_alerta_individual, enviar_resumen_casos
from config_manager import get_email_settings, get_encargado
import os

scheduler = None


def tarea_revisar_correo():
    print(f"[{datetime.now()}] Revisando correos...")
    files = check_emails_and_download_excel()
    for f in files:
        print(f"  → Procesando: {os.path.basename(f)}")
        res = procesar_archivo(f)
        if res["ok"]:
            print(f"     Insertados: {res['insertados']}, Actualizados: {res['actualizados']}, Cambios: {len(res.get('cambios', []))}")
        else:
            print(f"     ERROR: {res.get('error')}")


def tarea_verificar_alertas():
    print(f"[{datetime.now()}] Verificando alertas...")
    db = get_db()
    try:
        hoy = date.today()
        limite_dias = 10
        dias_alerta = 2

        encargado = get_encargado()
        destino = encargado.get("email", "")
        if not destino:
            print("  → No hay correo de encargado configurado.")
            return

        casos = db.query(Caso).all()
        vencidos = []
        preventivos = []
        pendientes = []

        for caso in casos:
            if caso.estado == "RESUELTO" or not caso.fecha_ingreso:
                continue

            dias_transcurridos = (hoy - caso.fecha_ingreso).days
            pendientes.append(caso)

            # Alerta preventiva: día 8
            if dias_transcurridos == (limite_dias - dias_alerta) and not caso.alerta_preventiva_enviada:
                ok, err = enviar_alerta_individual(destino, caso, "PREVENTIVA", dias_transcurridos)
                if ok:
                    caso.alerta_preventiva_enviada = True
                    db.add(LogAlerta(caso_id=caso.id, tipo_alerta="PREVENTIVA", destinatario=destino, contenido=f"Faltan 2 días. Día {dias_transcurridos}"))
                    preventivos.append(caso)
                    print(f"  → ALERTA PREVENTIVA enviada: {caso.numero_caso}")
                else:
                    print(f"  → ERROR enviando preventiva {caso.numero_caso}: {err}")

            # Alerta vencida: más de 10 días
            elif dias_transcurridos > limite_dias and not caso.alerta_vencido_enviada:
                caso.estado = "VENCIDO"
                ok, err = enviar_alerta_individual(destino, caso, "VENCIDA", dias_transcurridos)
                if ok:
                    caso.alerta_vencido_enviada = True
                    db.add(LogAlerta(caso_id=caso.id, tipo_alerta="VENCIDA", destinatario=destino, contenido=f"Caso vencido. Día {dias_transcurridos}"))
                    vencidos.append(caso)
                    print(f"  → ALERTA VENCIDA enviada: {caso.numero_caso}")
                else:
                    print(f"  → ERROR enviando vencida {caso.numero_caso}: {err}")

            if dias_transcurridos > limite_dias:
                vencidos.append(caso)
            elif dias_transcurridos == (limite_dias - dias_alerta):
                preventivos.append(caso)

        db.commit()

        if vencidos or preventivos:
            ok, err = enviar_resumen_casos(destino, pendientes, vencidos, preventivos)
            if ok:
                print(f"  → Resumen enviado a {destino}")
            else:
                print(f"  → ERROR enviando resumen: {err}")

    except Exception as e:
        print(f"  → ERROR general en alertas: {e}")
    finally:
        db.close()


def iniciar_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        return scheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(tarea_revisar_correo, IntervalTrigger(minutes=5), id="revisar_correo", replace_existing=True)
    scheduler.add_job(tarea_verificar_alertas, IntervalTrigger(hours=1), id="verificar_alertas", replace_existing=True)
    scheduler.start()
    return scheduler


def detener_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
