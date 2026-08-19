"""
Servicio para gestionar trabajos de procesamiento en segundo plano.

Este servicio encapsula el estado de los jobs que anteriormente
se manejaba directamente desde cargas.py.

No contiene lógica de negocio de cargas masivas.
"""

from threading import Lock
from uuid import uuid4


class JobService:
    """
    Gestiona jobs y su progreso en memoria.

    La información permanece en memoria mientras el proceso
    Flask esté ejecutándose.

    IMPORTANTE:
    Esta implementación conserva el comportamiento apropiado
    para la arquitectura actual de la aplicación.
    """

    def __init__(self):
        self._jobs = {}
        self._lock = Lock()

    # ========================================================
    # CREAR JOB
    # ========================================================

    def crear(
        self,
        estado='pendiente',
        porcentaje=0,
        mensaje=''
    ):
        """
        Crea un nuevo job.

        Returns:
            str:
                Identificador único del job.
        """

        job_id = str(
            uuid4()
        )

        with self._lock:

            self._jobs[job_id] = {
                'id': job_id,
                'estado': estado,
                'porcentaje': porcentaje,
                'mensaje': mensaje,
                'resultado': None,
                'error': None
            }

        return job_id

    # ========================================================
    # OBTENER JOB
    # ========================================================

    def obtener(
        self,
        job_id
    ):
        """
        Obtiene el estado actual de un job.

        Returns:
            dict | None
        """

        if not job_id:
            return None

        with self._lock:

            job = self._jobs.get(
                job_id
            )

            if job is None:
                return None

            return dict(
                job
            )

    # ========================================================
    # ACTUALIZAR
    # ========================================================

    def actualizar(
        self,
        job_id,
        estado=None,
        porcentaje=None,
        mensaje=None,
        resultado=None,
        error=None
    ):
        """
        Actualiza uno o varios campos del job.

        Returns:
            dict | None
        """

        if not job_id:
            return None

        with self._lock:

            job = self._jobs.get(
                job_id
            )

            if job is None:
                return None

            if estado is not None:

                job['estado'] = (
                    estado
                )

            if porcentaje is not None:

                job['porcentaje'] = (
                    int(porcentaje)
                )

            if mensaje is not None:

                job['mensaje'] = (
                    mensaje
                )

            if resultado is not None:

                job['resultado'] = (
                    resultado
                )

            if error is not None:

                job['error'] = (
                    error
                )

            return dict(
                job
            )

    # ========================================================
    # PROGRESO
    # ========================================================

    def actualizar_progreso(
        self,
        job_id,
        porcentaje,
        mensaje=''
    ):
        """
        Actualiza únicamente el progreso.
        """

        return self.actualizar(
            job_id=job_id,
            estado='procesando',
            porcentaje=porcentaje,
            mensaje=mensaje
        )

    # ========================================================
    # COMPLETAR
    # ========================================================

    def completar(
        self,
        job_id,
        resultado=None,
        mensaje='Proceso completado.'
    ):
        """
        Marca un job como completado.
        """

        return self.actualizar(
            job_id=job_id,
            estado='completado',
            porcentaje=100,
            mensaje=mensaje,
            resultado=resultado
        )

    # ========================================================
    # ERROR
    # ========================================================

    def error(
        self,
        job_id,
        error,
        mensaje='Error durante el procesamiento.'
    ):
        """
        Marca un job como fallido.
        """

        return self.actualizar(
            job_id=job_id,
            estado='error',
            mensaje=mensaje,
            error=str(error)
        )

    # ========================================================
    # ELIMINAR
    # ========================================================

    def eliminar(
        self,
        job_id
    ):
        """
        Elimina un job de memoria.
        """

        if not job_id:
            return False

        with self._lock:

            if job_id not in self._jobs:
                return False

            del self._jobs[job_id]

            return True

    # ========================================================
    # EXISTE
    # ========================================================

    def existe(
        self,
        job_id
    ):
        """
        Comprueba si existe un job.
        """

        if not job_id:
            return False

        with self._lock:

            return (
                job_id
                in self._jobs
            )

    # ========================================================
    # LIMPIAR
    # ========================================================

    def limpiar(
        self
    ):
        """
        Elimina todos los jobs almacenados.
        """

        with self._lock:

            self._jobs.clear()


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

job_service = JobService()
