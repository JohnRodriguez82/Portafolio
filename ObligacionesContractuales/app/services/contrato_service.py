"""
Servicio para gestionar contratos y sus obligaciones.

Responsabilidades:
- Obtener el contrato activo del usuario.
- Obtener contratos por ID.
- Validar propiedad del contrato.
- Validar estado del contrato.
- Obtener obligaciones del contrato.
- Generar los meses comprendidos dentro del contrato.
- Validar meses y fechas contractuales.

Este módulo contiene lógica de negocio.
No define rutas Flask.
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

    # ============================================================
    # OBTENER CONTRATO
    # ============================================================

    @staticmethod
    def obtener_contrato(
        contrato_id=None,
        usuario=None
    ):
        """
        Obtiene un contrato.

        Puede utilizarse de dos formas:

        1. Por ID:

            obtener_contrato(contrato_id=10)

        2. Por usuario:

            obtener_contrato(usuario=usuario)

        En el segundo caso se obtiene el contrato activo
        perteneciente al usuario.

        Esto permite mantener compatibilidad con diferentes
        partes de la aplicación.
        """

        # --------------------------------------------------------
        # Si se recibe usuario, buscar contrato activo
        # --------------------------------------------------------

        if usuario is not None:

            user_id = (
                getattr(
                    usuario,
                    'id',
                    None
                )
                if not isinstance(
                    usuario,
                    int
                )
                else usuario
            )

            if not user_id:
                return None

            return ContratoService.obtener_contrato_activo(
                user_id
            )

        # --------------------------------------------------------
        # Si se recibe ID, buscar por ID
        # --------------------------------------------------------

        if contrato_id is None:
            return None

        return (
            Contrato.query
            .filter_by(
                id=contrato_id
            )
            .first()
        )

    # ============================================================
    # CONTRATO ACTIVO
    # ============================================================

    @staticmethod
    def obtener_contrato_activo(
        user_id
    ):
        """
        Obtiene el contrato activo perteneciente
        al usuario indicado.

        Args:
            user_id:
                ID del usuario autenticado.

        Returns:
            Contrato | None
        """

        if not user_id:
            return None

        return (
            Contrato.query
            .filter_by(
                activo=True,
                user_id=user_id
            )
            .first()
        )

    # ============================================================
    # CONTRATO POR ID
    # ============================================================

    @staticmethod
    def obtener_contrato_por_id(
        contrato_id
    ):
        """
        Obtiene un contrato exclusivamente por ID.
        """

        if not contrato_id:
            return None

        return (
            Contrato.query
            .filter_by(
                id=contrato_id
            )
            .first()
        )

    # ============================================================
    # CONTRATO DEL USUARIO
    # ============================================================

    @staticmethod
    def obtener_contrato_usuario(
        contrato_id,
        user_id
    ):
        """
        Obtiene un contrato verificando que pertenezca
        al usuario autenticado.

        Returns:
            Contrato | None
        """

        contrato = (
            ContratoService.obtener_contrato_por_id(
                contrato_id
            )
        )

        if not ContratoService.pertenece_a_usuario(
            contrato,
            user_id
        ):
            return None

        return contrato

    # ============================================================
    # VALIDAR PROPIEDAD
    # ============================================================

    @staticmethod
    def pertenece_a_usuario(
        contrato,
        user_id
    ):
        """
        Verifica que un contrato pertenezca
        al usuario indicado.
        """

        if not contrato:
            return False

        if not user_id:
            return False

        return (
            contrato.user_id == user_id
        )

    # ============================================================
    # CONTRATO CERRADO
    # ============================================================

    @staticmethod
    def esta_cerrado(
        contrato
    ):
        """
        Verifica si el contrato está cerrado.
        """

        if not contrato:
            return False

        return (
            contrato.etapa == 'Reporte Cerrado'
        )

    # ============================================================
    # CONTRATO ABIERTO
    # ============================================================

    @staticmethod
    def esta_abierto(
        contrato
    ):
        """
        Verifica si el contrato permite nuevas cargas.
        """

        if not contrato:
            return False

        return not (
            ContratoService.esta_cerrado(
                contrato
            )
        )

    # ============================================================
    # OBLIGACIONES
    # ============================================================

    @staticmethod
    def obtener_obligaciones(
        contrato_id
    ):
        """
        Obtiene las obligaciones de un contrato
        ordenadas por número.
        """

        if not contrato_id:
            return []

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

    # ============================================================
    # OBLIGACIONES DEL CONTRATO
    # ============================================================

    @staticmethod
    def obtener_obligaciones_contrato(
        contrato
    ):
        """
        Obtiene las obligaciones asociadas
        a un objeto Contrato.
        """

        if not contrato:
            return []

        return (
            ContratoService.obtener_obligaciones(
                contrato.id
            )
        )

    # ============================================================
    # GENERAR MESES
    # ============================================================

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

            # ----------------------------------------------------
            # Pasar al siguiente mes
            # ----------------------------------------------------

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

    # ============================================================
    # MESES DEL CONTRATO
    # ============================================================

    @staticmethod
    def obtener_meses_contrato(
        contrato
    ):
        """
        Obtiene los meses correspondientes
        al periodo contractual.
        """

        if not contrato:
            return []

        return (
            ContratoService.generar_meses(
                contrato.fecha_inicio,
                contrato.fecha_fin
            )
        )

    # ============================================================
    # VALIDAR MES
    # ============================================================

    @staticmethod
    def mes_valido(
        mes
    ):
        """
        Verifica si un número corresponde
        a un mes válido.
        """

        try:

            mes = int(mes)

        except (
            TypeError,
            ValueError
        ):

            return False

        return 1 <= mes <= 12

    # ============================================================
    # VALIDAR AÑO
    # ============================================================

    @staticmethod
    def anio_valido(
        anio
    ):
        """
        Verifica si el año tiene un formato válido.
        """

        try:

            anio = int(anio)

        except (
            TypeError,
            ValueError
        ):

            return False

        return anio >= 1900

    # ============================================================
    # VALIDAR PERIODO DEL CONTRATO
    # ============================================================

    @staticmethod
    def fecha_dentro_del_contrato(
        contrato,
        fecha
    ):
        """
        Verifica si una fecha está dentro
        del periodo contractual.
        """

        if not contrato or not fecha:
            return False

        if not contrato.fecha_inicio:
            return False

        if not contrato.fecha_fin:
            return False

        return (
            contrato.fecha_inicio
            <= fecha
            <= contrato.fecha_fin
        )

    # ============================================================
    # VALIDAR MES DEL CONTRATO
    # ============================================================

    @staticmethod
    def mes_dentro_del_contrato(
        contrato,
        mes,
        anio
    ):
        """
        Verifica si el mes/año indicado se encuentra
        dentro del periodo contractual.
        """

        if not contrato:
            return False

        if not ContratoService.mes_valido(
            mes
        ):
            return False

        if not ContratoService.anio_valido(
            anio
        ):
            return False

        mes = int(mes)
        anio = int(anio)

        inicio = (
            contrato.fecha_inicio.year,
            contrato.fecha_inicio.month
        )

        fin = (
            contrato.fecha_fin.year,
            contrato.fecha_fin.month
        )

        periodo = (
            anio,
            mes
        )

        return (
            inicio
            <= periodo
            <= fin
        )

    # ============================================================
    # OBTENER NOMBRE DEL MES
    # ============================================================

    @staticmethod
    def obtener_nombre_mes(
        mes
    ):
        """
        Obtiene el nombre en español de un mes.

        Returns:
            str | None
        """

        if not ContratoService.mes_valido(
            mes
        ):
            return None

        return ContratoService.NOMBRE_MESES[
            int(mes)
        ]

    # ============================================================
    # VALIDAR CONTRATO PARA CARGA
    # ============================================================

    @staticmethod
    def validar_contrato_para_carga(
        contrato,
        mes=None,
        anio=None
    ):
        """
        Valida que un contrato pueda utilizarse
        para una carga masiva.

        Returns:
            tuple:

                (True, None)

            o:

                (False, 'mensaje de error')
        """

        if not contrato:

            return (
                False,
                'No se encontró un contrato.'
            )

        if not contrato.activo:

            return (
                False,
                'El contrato no está activo.'
            )

        if ContratoService.esta_cerrado(
            contrato
        ):

            return (
                False,
                'El contrato se encuentra cerrado.'
            )

        if (
            mes is not None
            and
            anio is not None
        ):

            if not ContratoService.mes_dentro_del_contrato(
                contrato,
                mes,
                anio
            ):

                return (
                    False,
                    (
                        'El mes seleccionado no se '
                        'encuentra dentro del periodo '
                        'del contrato.'
                    )
                )

        return (
            True,
            None
        )
