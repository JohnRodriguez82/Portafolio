"""
Servicio para gestión de trabajos de carga masiva.

Responsabilidades:
- Crear jobs.
- Actualizar progreso.
- Consultar estado.
- Marcar jobs como completados.
- Marcar jobs como error.

El servicio es independiente de Flask routes.
"""

import threading
import uuid

from datetime import datetime


# ============================================================
# ALMACENAMIENTO EN MEMORIA
# ============================================================

_jobs = {}

_jobs_lock = threading.Lock()


# ============================================================
# CREAR JOB
# ============================================================

def crear_job():
    """
    Crea un nuevo trabajo.

    Retorna:
        job_id
    """

    job_id = str(
        uuid.uuid4()
    )

    job = {
        'id': job_id,
        'estado': 'iniciando',
        'porcentaje': 0,
        'mensaje': 'Iniciando...',
        'errores': [],
        'resultado': None,
        'creado': datetime.now(),
        'actualizado': datetime.now()
    }

    with _jobs_lock:

        _jobs[
            job_id
        ] = job

    return job_id


# ============================================================
# OBTENER JOB
# ============================================================

def obtener_job(
    job_id
):
    """
    Retorna el estado actual del job.
    """

    with _jobs_lock:

        job = _jobs.get(
            job_id
        )

        if not job:
            return None

        return job.copy()


# ============================================================
# ACTUALIZAR PROGRESO
# ============================================================

def actualizar_progreso(
    job_id,
    estado,
    porcentaje,
    mensaje,
    errores=None,
    resultado=None
):
    """
    Actualiza el estado de un job.
    """

    with _jobs_lock:

        job = _jobs.get(
            job_id
        )

        if not job:
            return False

        job['estado'] = estado

        job['porcentaje'] = max(
            0,
            min(
                100,
                int(
                    porcentaje or 0
                )
            )
        )

        job['mensaje'] = (
            mensaje or ''
        )

        job['actualizado'] = (
            datetime.now()
        )

        if errores is not None:

            job['errores'] = list(
                errores
            )

        if resultado is not None:

            job['resultado'] = resultado

        return True


# ============================================================
# AGREGAR ERROR
# ============================================================

def agregar_error(
    job_id,
    error
):
    """
    Agrega una advertencia o error al job.
    """

    with _jobs_lock:

        job = _jobs.get(
            job_id
        )

        if not job:
            return False

        job[
            'errores'
        ].append(
            str(error)
        )

        job['actualizado'] = (
            datetime.now()
        )

        return True


# ============================================================
# COMPLETAR JOB
# ============================================================

def completar_job(
    job_id,
    resultado=None,
    errores=None
):
    """
    Marca un job como completado.
    """

    return actualizar_progreso(
        job_id=job_id,
        estado='completado',
        porcentaje=100,
        mensaje='Proceso finalizado.',
        errores=errores,
        resultado=resultado
    )


# ============================================================
# ERROR JOB
# ============================================================

def marcar_error(
    job_id,
    mensaje,
    errores=None
):
    """
    Marca un job como fallido.
    """

    return actualizar_progreso(
        job_id=job_id,
        estado='error',
        porcentaje=0,
        mensaje=mensaje,
        errores=errores
    )


# ============================================================
# ELIMINAR JOB
# ============================================================

def eliminar_job(
    job_id
):
    """
    Elimina un job de memoria.
    """

    with _jobs_lock:

        return _jobs.pop(
            job_id,
            None
        )


# ============================================================
# LIMPIAR JOBS ANTIGUOS
# ============================================================

def limpiar_jobs(
    max_jobs=100
):
    """
    Limita el número de jobs almacenados en memoria.

    Útil para evitar que el diccionario crezca
    indefinidamente.
    """

    with _jobs_lock:

        if len(_jobs) <= max_jobs:
            return

        ordenados = sorted(
            _jobs.items(),
            key=lambda item:
                item[1].get(
                    'actualizado'
                )
        )

        cantidad_eliminar = (
            len(_jobs)
            - max_jobs
        )

        for job_id, _ in ordenados[
            :cantidad_eliminar
        ]:

            _jobs.pop(
                job_id,
                None
            )
