"""
Servicio para gestionar contratos y sus obligaciones.

Responsabilidades:
- Obtener el contrato activo del usuario.
- Validar propiedad del contrato.
- Validar estado del contrato.
- Obtener obligaciones del contrato.
- Generar los meses comprendidos dentro del contrato.
"""

from datetime import date

from models import (
    Contrato,
    Obligacion
)


class ContratoService:
    """
    Servicio de dominio para contratos.
    """

    NOMBRE_MESES = [
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

    # ========================================================
    # CONTRATO ACTIVO
    # ========================================================

    @staticmethod
    def obtener_contrato_activo(user_id):
        """
        Obtiene el contrato activo perteneciente al usuario.

        Args:
            user_id: ID del usuario autenticado.

        Returns:
            Contrato | None
        """

        return (
            Contrato.query
            .filter_by(
                activo=True,
                user_id=user_id
            )
            .first()
        )

    # ========================================================
    # CONTRATO POR ID
    # ========================================================

    @staticmethod
    def obtener_contrato(contrato_id):
        """
        Obtiene un contrato por su ID.

        Args:
            contrato_id: ID del contrato.

        Returns:
            Contrato | None
        """

        return (
            Contrato.query
            .filter_by(
                id=contrato_id
            )
            .first()
        )

    # ========================================================
    # VALIDAR PROPIEDAD
    # ========================================================

    @staticmethod
    def pertenece_a_usuario(
        contrato,
        user_id
    ):
        """
        Verifica que el contrato pertenezca al usuario.

        Args:
            contrato: instancia de Contrato.
            user_id: ID del usuario.

        Returns:
            bool
        """

        if not contrato:
            return False

        return (
            contrato.user_id == user_id
        )

    # ========================================================
    # CONTRATO DISPONIBLE PARA EL USUARIO
    # ========================================================

    @staticmethod
    def obtener_contrato_usuario(
        contrato_id,
        user_id
    ):
        """
        Obtiene un contrato verificando que pertenezca
        al usuario autenticado.

        Args:
            contrato_id: ID del contrato.
            user_id: ID del usuario.

        Returns:
            Contrato | None
        """

        contrato = (
            ContratoService.obtener_contrato(
                contrato_id
            )
        )

        if not ContratoService.pertenece_a_usuario(
            contrato,
            user_id
        ):
            return None

        return contrato

    # ========================================================
    # CONTRATO CERRADO
    # ========================================================

    @staticmethod
    def esta_cerrado(contrato):
        """
        Verifica si el contrato está cerrado.

        Args:
            contrato: instancia de Contrato.

        Returns:
            bool
        """

        if not contrato:
            return False

        return (
            contrato.etapa == 'Reporte Cerrado'
        )

    # ========================================================
    # CONTRATO ABIERTO
    # ========================================================

    @staticmethod
    def esta_abierto(contrato):
        """
        Verifica si el contrato permite nuevas cargas.
        """

        if not contrato:
            return False

        return not ContratoService.esta_cerrado(
            contrato
        )

    # ========================================================
    # OBLIGACIONES
    # ========================================================

    @staticmethod
    def obtener_obligaciones(
        contrato_id
    ):
        """
        Obtiene las obligaciones de un contrato
        ordenadas por número.
        """

        return (
            Obligacion.query
            .filter_by(
                contrato_id=contrato_id
            )
            .order_by(
                Obligacion.numero
            )
            .all()
        )

    # ========================================================
    # OBLIGACIONES DEL CONTRATO
    # ========================================================

    @staticmethod
    def obtener_obligaciones_contrato(
        contrato
    ):
        """
        Obtiene las obligaciones asociadas a un contrato.
        """

        if not contrato:
            return []

        return ContratoService.obtener_obligaciones(
            contrato.id
        )

    # ========================================================
    # GENERAR MESES
    # ========================================================

    @staticmethod
    def generar_meses(
        fecha_inicio,
        fecha_fin
    ):
        """
        Genera todos los meses comprendidos entre
        las fechas de inicio y fin del contrato.

        Retorna:

            [
                (mes, anio, nombre_mes),
                ...
            ]

        Ejemplo:

            [
                (1, 2026, 'Enero'),
                (2, 2026, 'Febrero'),
                ...
            ]
        """

        if not fecha_inicio or not fecha_fin:
            return []

        meses = []

        current = date(
            fecha_inicio.year,
            fecha_inicio.month,
            1
        )

        end = date(
            fecha_fin.year,
            fecha_fin.month,
            1
        )

        while current <= end:

            meses.append(
                (
                    current.month,
                    current.year,
                    ContratoService.NOMBRE_MESES[
                        current.month
                    ]
                )
            )

            if current.month == 12:

                current = date(
                    current.year + 1,
                    1,
                    1
                )

            else:

                current = date(
                    current.year,
                    current.month + 1,
                    1
                )

        return meses

    # ========================================================
    # MESES DEL CONTRATO
    # ========================================================

    @staticmethod
    def obtener_meses_contrato(
        contrato
    ):
        """
        Genera los meses correspondientes al contrato.
        """

        if not contrato:
            return []

        return ContratoService.generar_meses(
            contrato.fecha_inicio,
            contrato.fecha_fin
        )

    # ========================================================
    # VALIDAR MES
    # ========================================================

    @staticmethod
    def mes_valido(mes):
        """
        Verifica si un número corresponde a un mes válido.
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
    # VALIDAR PERIODO DEL CONTRATO
    # ========================================================

    @staticmethod
    def fecha_dentro_del_contrato(
        contrato,
        fecha
    ):
        """
        Verifica si una fecha está dentro del periodo
        contractual.
        """

        if not contrato or not fecha:
            return False

        return (
            contrato.fecha_inicio
            <= fecha
            <= contrato.fecha_fin
        )
