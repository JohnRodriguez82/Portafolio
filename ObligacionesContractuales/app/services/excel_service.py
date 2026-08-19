"""
Servicio para procesamiento de archivos Excel.

Responsabilidades:

- Leer archivos Excel.
- Validar encabezados.
- Convertir filas Excel a diccionarios.
- Limpiar valores.
- Validar estructura.
- Generar plantillas mediante PlantillaService.

Este servicio NO depende de Flask.
"""

from datetime import (
    datetime,
    date
)

from pathlib import Path

from openpyxl import (
    load_workbook
)

from app.services.plantilla_service import (
    PlantillaService,
    ENCABEZADOS_CARGA_MASIVA
)


# ============================================================
# CONSTANTES
# ============================================================

EXTENSIONES_EXCEL = {
    '.xlsx',
    '.xlsm'
}


ENCABEZADOS_ESPERADOS = (
    ENCABEZADOS_CARGA_MASIVA
)


# ============================================================
# SERVICIO
# ============================================================

class ExcelService:
    """
    Servicio encargado del procesamiento de archivos Excel.
    """

    # ========================================================
    # LEER EXCEL
    # ========================================================

    @staticmethod
    def leer_excel(
        archivo
    ):
        """
        Lee un archivo Excel y retorna una lista de
        diccionarios preparada para CargaMasivaService.

        La estructura retornada es:

            [
                {
                    'obligacion': ...,
                    'descripcion_obligacion': ...,
                    'anuncio': ...,
                    'fecha': ...,
                    'nombre_imagen': ...
                }
            ]

        Args:
            archivo:
                Puede ser:

                - ruta como str
                - pathlib.Path
                - objeto FileStorage
                - objeto archivo compatible con openpyxl

        Returns:
            list[dict]
        """

        workbook = None

        try:

            workbook = (
                ExcelService._abrir_workbook(
                    archivo
                )
            )

            worksheet = (
                workbook.active
            )

            # ------------------------------------------------
            # Validar encabezados
            # ------------------------------------------------

            ExcelService.validar_encabezados(
                worksheet
            )

            registros = []

            # ------------------------------------------------
            # Leer filas
            # ------------------------------------------------

            for numero_fila, row in enumerate(
                worksheet.iter_rows(
                    min_row=2,
                    values_only=True
                ),
                start=2
            ):

                if ExcelService._fila_vacia(
                    row
                ):
                    continue

                registro = (
                    ExcelService._convertir_fila(
                        row,
                        numero_fila
                    )
                )

                # --------------------------------------------
                # Las filas sin obligación se ignoran.
                # --------------------------------------------

                if not registro[
                    'obligacion'
                ]:

                    continue

                registros.append(
                    registro
                )

            return registros

        finally:

            if workbook is not None:

                try:
                    workbook.close()

                except Exception:
                    pass

    # ========================================================
    # ABRIR WORKBOOK
    # ========================================================

    @staticmethod
    def _abrir_workbook(
        archivo
    ):
        """
        Abre un archivo Excel desde diferentes tipos
        de entrada.
        """

        if archivo is None:

            raise ValueError(
                'No se recibió un archivo Excel.'
            )

        # ----------------------------------------------------
        # Ruta
        # ----------------------------------------------------

        if isinstance(
            archivo,
            (
                str,
                Path
            )
        ):

            ruta = Path(
                archivo
            )

            if not ruta.exists():

                raise FileNotFoundError(
                    f'No existe el archivo Excel: {ruta}'
                )

            ExcelService.validar_extension(
                ruta.name
            )

            return load_workbook(
                filename=str(ruta),
                data_only=False
            )

        # ----------------------------------------------------
        # FileStorage / archivo subido
        # ----------------------------------------------------

        nombre = getattr(
            archivo,
            'filename',
            None
        )

        if nombre:

            ExcelService.validar_extension(
                nombre
            )

        # ----------------------------------------------------
        # Reiniciar posición
        # ----------------------------------------------------

        try:

            archivo.seek(
                0
            )

        except (
            AttributeError,
            OSError
        ):

            pass

        try:

            return load_workbook(
                filename=archivo,
                data_only=False
            )

        except Exception as exc:

            raise ValueError(
                'No fue posible abrir el archivo Excel. '
                'Verifique que sea un archivo .xlsx válido.'
            ) from exc

    # ========================================================
    # VALIDAR EXTENSIÓN
    # ========================================================

    @staticmethod
    def validar_extension(
        nombre_archivo
    ):
        """
        Valida la extensión del archivo Excel.
        """

        if not nombre_archivo:

            raise ValueError(
                'El archivo Excel no tiene nombre.'
            )

        extension = (
            Path(
                str(nombre_archivo)
            ).suffix.lower()
        )

        if extension not in EXTENSIONES_EXCEL:

            raise ValueError(
                'Formato de Excel no permitido. '
                'Utilice un archivo .xlsx.'
            )

        return True

    # ========================================================
    # VALIDAR ENCABEZADOS
    # ========================================================

    @staticmethod
    def validar_encabezados(
        worksheet
    ):
        """
        Valida que la primera fila del Excel contenga
        los encabezados oficiales.

        Returns:
            True

        Raises:
            ValueError
        """

        encabezados = [
            ExcelService._limpiar_texto(
                cell.value
            )
            for cell in worksheet[1]
        ]

        esperados = [
            ExcelService._limpiar_texto(
                encabezado
            )
            for encabezado in ENCABEZADOS_ESPERADOS
        ]

        encabezados_principales = (
            encabezados[:len(esperados)]
        )

        if encabezados_principales != esperados:

            raise ValueError(
                'Encabezados incorrectos. '
                'La plantilla debe conservar exactamente '
                'los encabezados: '
                f'{ENCABEZADOS_ESPERADOS}'
            )

        return True

    # ========================================================
    # CONVERTIR FILA
    # ========================================================

    @staticmethod
    def _convertir_fila(
        row,
        numero_fila
    ):
        """
        Convierte una fila Excel en un diccionario
        compatible con CargaMasivaService.
        """

        valores = list(
            row
        )

        # ----------------------------------------------------
        # Asegurar cinco columnas
        # ----------------------------------------------------

        while len(valores) < 5:

            valores.append(
                None
            )

        obligacion = (
            ExcelService._normalizar_obligacion(
                valores[0]
            )
        )

        descripcion = (
            ExcelService._limpiar_texto(
                valores[1]
            )
        )

        anuncio = (
            ExcelService._limpiar_texto(
                valores[2]
            )
        )

        fecha = (
            ExcelService._normalizar_fecha(
                valores[3]
            )
        )

        nombre_imagen = (
            ExcelService._limpiar_texto(
                valores[4]
            )
        )

        return {
            'fila': numero_fila,

            'obligacion': obligacion,

            'descripcion_obligacion': (
                descripcion
            ),

            'anuncio': (
                anuncio
            ),

            'fecha': (
                fecha
            ),

            'nombre_imagen': (
                nombre_imagen
            )
        }

    # ========================================================
    # NORMALIZAR OBLIGACIÓN
    # ========================================================

    @staticmethod
    def _normalizar_obligacion(
        valor
    ):
        """
        Normaliza el número de obligación.

        Ejemplos:

            3       -> 3
            3.0     -> 3
            "3"     -> 3
            " 3 "   -> 3
        """

        if valor is None:

            return None

        if isinstance(
            valor,
            bool
        ):

            return None

        if isinstance(
            valor,
            int
        ):

            return valor

        if isinstance(
            valor,
            float
        ):

            if valor.is_integer():

                return int(
                    valor
                )

            return valor

        texto = str(
            valor
        ).strip()

        if not texto:

            return None

        try:

            numero = float(
                texto
            )

            if numero.is_integer():

                return int(
                    numero
                )

        except ValueError:

            pass

        return texto

    # ========================================================
    # NORMALIZAR FECHA
    # ========================================================

    @staticmethod
    def _normalizar_fecha(
        valor
    ):
        """
        Normaliza fechas provenientes de Excel.

        Se conserva como string ISO cuando es posible.

        Formatos soportados:

        - datetime
        - date
        - YYYY-MM-DD
        - DD/MM/YYYY
        - DD-MM-YYYY
        """

        if valor is None:

            return ''

        # ----------------------------------------------------
        # datetime
        # ----------------------------------------------------

        if isinstance(
            valor,
            datetime
        ):

            return valor.strftime(
                '%Y-%m-%d'
            )

        # ----------------------------------------------------
        # date
        # ----------------------------------------------------

        if isinstance(
            valor,
            date
        ):

            return valor.strftime(
                '%Y-%m-%d'
            )

        texto = str(
            valor
        ).strip()

        if not texto:

            return ''

        formatos = (
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d'
        )

        for formato in formatos:

            try:

                fecha = datetime.strptime(
                    texto,
                    formato
                )

                return fecha.strftime(
                    '%Y-%m-%d'
                )

            except ValueError:

                continue

        # ----------------------------------------------------
        # Si no se puede convertir, devolver texto.
        #
        # CargaMasivaService será quien determine
        # posteriormente si es válido.
        # ----------------------------------------------------

        return texto

    # ========================================================
    # LIMPIAR TEXTO
    # ========================================================

    @staticmethod
    def _limpiar_texto(
        valor
    ):
        """
        Convierte un valor Excel a texto limpio.
        """

        if valor is None:

            return ''

        return str(
            valor
        ).strip()

    # ========================================================
    # FILA VACÍA
    # ========================================================

    @staticmethod
    def _fila_vacia(
        row
    ):
        """
        Determina si una fila está completamente vacía.
        """

        if not row:

            return True

        for valor in row:

            if valor is None:

                continue

            if isinstance(
                valor,
                str
            ):

                if valor.strip():

                    return False

            else:

                return False

        return True

    # ========================================================
    # GENERAR PLANTILLA MASIVA
    # ========================================================

    @staticmethod
    def generar_plantilla_masiva(
        obligaciones,
        mes,
        anio
    ):
        """
        Genera una plantilla Excel para carga masiva.

        La construcción real corresponde a PlantillaService.
        """

        return (
            PlantillaService.crear_plantilla(
                obligaciones=obligaciones,
                mes=mes,
                anio=anio
            )
        )

    # ========================================================
    # GENERAR PLANTILLA DE REPORTE
    # ========================================================

    @staticmethod
    def generar_plantilla_reporte():
        """
        Genera una plantilla para un reporte específico.
        """

        return (
            PlantillaService.crear_plantilla_reporte()
        )

    # ========================================================
    # NOMBRE ARCHIVO PLANTILLA
    # ========================================================

    @staticmethod
    def nombre_archivo_plantilla(
        mes,
        anio
    ):
        """
        Retorna el nombre estándar de la plantilla.
        """

        return (
            PlantillaService.nombre_archivo_masiva(
                mes,
                anio
            )
        )


# ============================================================
# INSTANCIA COMPARTIDA
# ============================================================

excel_service = (
    ExcelService()
)


# ============================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================

def leer_excel(
    archivo
):
    """
    Función de compatibilidad.
    """

    return (
        ExcelService.leer_excel(
            archivo
        )
    )


def generar_plantilla_masiva(
    obligaciones,
    mes,
    anio
):
    """
    Función de compatibilidad.
    """

    return (
        ExcelService.generar_plantilla_masiva(
            obligaciones,
            mes,
            anio
        )
    )


def generar_plantilla_reporte():
    """
    Función de compatibilidad.
    """

    return (
        ExcelService.generar_plantilla_reporte()
    )
