"""
Servicio para generación de plantillas Excel.

Responsabilidades:

- Construir plantilla para carga masiva mensual.
- Definir encabezados oficiales.
- Agregar obligaciones.
- Aplicar formato.
- Agregar instrucciones.
- Generar nombres de archivo.

Este servicio NO depende de Flask.
"""

from io import BytesIO

from openpyxl import Workbook

from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)

from openpyxl.utils import get_column_letter


# ============================================================
# CONSTANTES
# ============================================================

ENCABEZADOS_CARGA_MASIVA = [
    'Obligacion No.',
    'Descripcion Obligacion',
    'Anuncio / Contexto',
    'Fecha de la actividad',
    'Nombre Imagen'
]


NOMBRE_HOJA_CARGA_MASIVA = 'Carga Masiva'


# ============================================================
# SERVICIO
# ============================================================

class PlantillaService:
    """
    Servicio encargado exclusivamente de construir
    plantillas Excel.
    """

    # ========================================================
    # CREAR PLANTILLA MENSUAL
    # ========================================================

    @staticmethod
    def crear_plantilla(
        obligaciones,
        mes,
        anio
    ):
        """
        Crea una plantilla Excel para carga masiva mensual.

        Args:
            obligaciones:
                Lista de objetos Obligacion.

            mes:
                Número del mes.

            anio:
                Año.

        Returns:
            BytesIO:
                Archivo Excel en memoria.
        """

        mes = int(mes)
        anio = int(anio)

        wb = Workbook()

        ws = wb.active

        ws.title = (
            f'Carga_{mes:02d}_{anio}'
        )

        # ----------------------------------------------------
        # ENCABEZADOS
        # ----------------------------------------------------

        for columna, encabezado in enumerate(
            ENCABEZADOS_CARGA_MASIVA,
            start=1
        ):

            cell = ws.cell(
                row=1,
                column=columna,
                value=encabezado
            )

            PlantillaService._estilizar_encabezado(
                cell
            )

        # ----------------------------------------------------
        # OBLIGACIONES
        # ----------------------------------------------------

        for fila, obligacion in enumerate(
            obligaciones,
            start=2
        ):

            numero = getattr(
                obligacion,
                'numero',
                ''
            )

            descripcion = getattr(
                obligacion,
                'descripcion',
                ''
            )

            ws.cell(
                row=fila,
                column=1,
                value=numero
            )

            ws.cell(
                row=fila,
                column=2,
                value=descripcion
            )

            # Anuncio / Contexto
            ws.cell(
                row=fila,
                column=3,
                value=''
            )

            # Fecha
            ws.cell(
                row=fila,
                column=4,
                value=''
            )

            # Nombre Imagen
            ws.cell(
                row=fila,
                column=5,
                value=''
            )

            # Formato de las celdas
            for columna in range(
                1,
                6
            ):

                cell = ws.cell(
                    row=fila,
                    column=columna
                )

                cell.alignment = Alignment(
                    vertical='top',
                    wrap_text=True
                )

                cell.border = (
                    PlantillaService._borde_delgado()
                )

        # ----------------------------------------------------
        # FORMATO GENERAL
        # ----------------------------------------------------

        PlantillaService._configurar_hoja_principal(
            ws
        )

        # ----------------------------------------------------
        # HOJA DE INSTRUCCIONES
        # ----------------------------------------------------

        PlantillaService._agregar_hoja_instrucciones(
            wb,
            mes,
            anio
        )

        # ----------------------------------------------------
        # ARCHIVO EN MEMORIA
        # ----------------------------------------------------

        output = BytesIO()

        wb.save(
            output
        )

        output.seek(
            0
        )

        return output

    # ========================================================
    # CREAR PLANTILLA DE REPORTE
    # ========================================================

    @staticmethod
    def crear_plantilla_reporte():
        """
        Crea una plantilla sencilla para carga de actividades
        de un reporte específico.

        Returns:
            BytesIO
        """

        wb = Workbook()

        ws = wb.active

        ws.title = (
            'Carga Masiva'
        )

        encabezados = [
            'Anuncio / Contexto',
            'Fecha de la actividad'
        ]

        for columna, encabezado in enumerate(
            encabezados,
            start=1
        ):

            cell = ws.cell(
                row=1,
                column=columna,
                value=encabezado
            )

            PlantillaService._estilizar_encabezado(
                cell
            )

        # ----------------------------------------------------
        # EJEMPLOS
        # ----------------------------------------------------

        ejemplos = [
            (
                'Presentacion del estado de avance '
                'de proyectos',
                '2026-07-15'
            ),
            (
                'Revision de solicitudes de ajuste '
                'tecnicos',
                '2026-07-20'
            ),
            (
                'Elaboracion del plan de trabajo '
                'mensual',
                '2026-07-25'
            )
        ]

        for fila, ejemplo in enumerate(
            ejemplos,
            start=2
        ):

            ws.cell(
                row=fila,
                column=1,
                value=ejemplo[0]
            )

            ws.cell(
                row=fila,
                column=2,
                value=ejemplo[1]
            )

        ws.column_dimensions[
            'A'
        ].width = 60

        ws.column_dimensions[
            'B'
        ].width = 25

        ws.freeze_panes = 'A2'

        # ----------------------------------------------------
        # ARCHIVO
        # ----------------------------------------------------

        output = BytesIO()

        wb.save(
            output
        )

        output.seek(
            0
        )

        return output

    # ========================================================
    # ESTILO ENCABEZADO
    # ========================================================

    @staticmethod
    def _estilizar_encabezado(
        cell
    ):
        """
        Aplica el estilo estándar de los encabezados.
        """

        cell.font = Font(
            bold=True,
            color='FFFFFF',
            size=11
        )

        cell.fill = PatternFill(
            fill_type='solid',
            fgColor='2C3E50'
        )

        cell.alignment = Alignment(
            horizontal='center',
            vertical='center',
            wrap_text=True
        )

        cell.border = (
            PlantillaService._borde_delgado()
        )

    # ========================================================
    # BORDE
    # ========================================================

    @staticmethod
    def _borde_delgado():
        """
        Retorna un borde estándar para las celdas.
        """

        return Border(
            left=Side(
                style='thin',
                color='D9D9D9'
            ),
            right=Side(
                style='thin',
                color='D9D9D9'
            ),
            top=Side(
                style='thin',
                color='D9D9D9'
            ),
            bottom=Side(
                style='thin',
                color='D9D9D9'
            )
        )

    # ========================================================
    # CONFIGURAR HOJA PRINCIPAL
    # ========================================================

    @staticmethod
    def _configurar_hoja_principal(
        ws
    ):
        """
        Configura dimensiones y comportamiento
        de la hoja principal.
        """

        anchos = {
            'A': 18,
            'B': 60,
            'C': 55,
            'D': 25,
            'E': 35
        }

        for columna, ancho in anchos.items():

            ws.column_dimensions[
                columna
            ].width = ancho

        ws.row_dimensions[
            1
        ].height = 32

        ws.freeze_panes = 'A2'

        # ----------------------------------------------------
        # Filtro
        # ----------------------------------------------------

        if ws.max_row >= 1:

            ws.auto_filter.ref = (
                f'A1:E{ws.max_row}'
            )

    # ========================================================
    # HOJA DE INSTRUCCIONES
    # ========================================================

    @staticmethod
    def _agregar_hoja_instrucciones(
        wb,
        mes,
        anio
    ):
        """
        Agrega la hoja de instrucciones.
        """

        ws = wb.create_sheet(
            'Instrucciones'
        )

        titulo = (
            'INSTRUCCIONES DE CARGA MASIVA '
            f'{mes:02d}/{anio}'
        )

        ws.append(
            [titulo]
        )

        ws['A1'].font = Font(
            bold=True,
            color='FFFFFF',
            size=14
        )

        ws['A1'].fill = PatternFill(
            fill_type='solid',
            fgColor='1F4E78'
        )

        ws['A1'].alignment = Alignment(
            horizontal='center'
        )

        instrucciones = [

            '',

            '1. NO modifique los encabezados '
            'de la fila 1.',

            '2. NO modifique las columnas A y B. '
            'Estas contienen la obligación y su descripción.',

            '3. En la columna C escriba el '
            'Anuncio / Contexto de la actividad.',

            '4. En la columna D indique la fecha '
            'de la actividad.',

            '5. Puede utilizar los formatos '
            'YYYY-MM-DD, DD/MM/YYYY o DD-MM-YYYY.',

            '6. La fecha debe pertenecer al mes '
            'y año seleccionado.',

            '7. En la columna E escriba el nombre '
            'EXACTO de la imagen.',

            '8. Incluya la extensión del archivo '
            '(por ejemplo: evidencia01.jpg).',

            '9. Puede agregar varias filas para '
            'una misma obligación.',

            '10. Puede eliminar las filas de '
            'obligaciones que no tengan actividades.',

            '11. Las imágenes deben cargarse '
            'junto con el archivo Excel.',

            '12. Si deja Nombre Imagen vacío, '
            'se registrará la actividad sin imagen.',

            '13. Cada imagen cargada se utiliza '
            'una sola vez.',

            '',

            'IMPORTANTE:',

            'La información de las columnas A y B '
            'no debe modificarse.',

            'El nombre de la imagen debe coincidir '
            'con el archivo cargado.'
        ]

        for texto in instrucciones:

            ws.append(
                [texto]
            )

        ws.column_dimensions[
            'A'
        ].width = 110

        ws.freeze_panes = 'A2'

        # ----------------------------------------------------
        # Ajustar título
        # ----------------------------------------------------

        ws.merge_cells(
            'A1:E1'
        )

    # ========================================================
    # NOMBRE DE ARCHIVO
    # ========================================================

    @staticmethod
    def nombre_archivo_masiva(
        mes,
        anio
    ):
        """
        Genera el nombre estándar del archivo.
        """

        return (
            f'plantilla_carga_masiva_'
            f'{int(mes):02d}_'
            f'{int(anio)}.xlsx'
        )

    @staticmethod
    def nombre_archivo_plantilla(
        mes,
        anio
    ):
        """
        Alias compatible con la interfaz anterior.
        """

        return (
            PlantillaService.nombre_archivo_masiva(
                mes,
                anio
            )
        )


# ============================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================

def crear_plantilla(
    obligaciones,
    mes,
    anio
):
    """
    Función de compatibilidad.

    Permite utilizar el servicio sin instanciarlo.
    """

    return (
        PlantillaService.crear_plantilla(
            obligaciones,
            mes,
            anio
        )
    )


def generar_plantilla_masiva(
    obligaciones,
    mes,
    anio
):
    """
    Función de compatibilidad para código existente.
    """

    return (
        PlantillaService.crear_plantilla(
            obligaciones,
            mes,
            anio
        )
    )


def generar_plantilla_reporte():
    """
    Función de compatibilidad para código existente.
    """

    return (
        PlantillaService.crear_plantilla_reporte()
    )


def nombre_archivo_plantilla(
    mes,
    anio
):
    """
    Función de compatibilidad.
    """

    return (
        PlantillaService.nombre_archivo_masiva(
            mes,
            anio
        )
    )
