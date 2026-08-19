"""
Servicio para generación de plantillas Excel.

Responsabilidades:
- Construir plantilla mensual.
- Agregar obligaciones.
- Definir encabezados.
- Aplicar formato.
- Retornar el workbook listo para descarga.
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
# ENCABEZADOS
# ============================================================

ENCABEZADOS = [
    'Obligacion No.',
    'Descripcion Obligacion',
    'Anuncio / Contexto',
    'Fecha de la actividad',
    'Nombre Imagen'
]


# ============================================================
# CREAR WORKBOOK
# ============================================================

def crear_plantilla(
    obligaciones,
    mes,
    anio
):
    """
    Genera el workbook Excel para un mes.

    Args:
        obligaciones: lista de obligaciones.
        mes: número del mes.
        anio: año.

    Retorna:
        BytesIO
    """

    wb = Workbook()

    ws = wb.active

    ws.title = (
        f'Reporte {mes}-{anio}'
    )

    # --------------------------------------------------------
    # ENCABEZADOS
    # --------------------------------------------------------

    for columna, encabezado in enumerate(
        ENCABEZADOS,
        start=1
    ):

        cell = ws.cell(
            row=1,
            column=columna,
            value=encabezado
        )

        _estilizar_encabezado(
            cell
        )

    # --------------------------------------------------------
    # OBLIGACIONES
    # --------------------------------------------------------

    for fila, obligacion in enumerate(
        obligaciones,
        start=2
    ):

        ws.cell(
            fila,
            1,
            getattr(
                obligacion,
                'numero',
                ''
            )
        )

        ws.cell(
            fila,
            2,
            getattr(
                obligacion,
                'descripcion',
                ''
            )
        )

        ws.cell(
            fila,
            3,
            ''
        )

        ws.cell(
            fila,
            4,
            ''
        )

        ws.cell(
            fila,
            5,
            ''
        )

    # --------------------------------------------------------
    # FORMATO
    # --------------------------------------------------------

    _ajustar_columnas(
        ws
    )

    ws.freeze_panes = 'A2'

    ws.auto_filter.ref = (
        ws.dimensions
    )

    # --------------------------------------------------------
    # GUARDAR EN MEMORIA
    # --------------------------------------------------------

    output = BytesIO()

    wb.save(
        output
    )

    output.seek(
        0
    )

    return output


# ============================================================
# ESTILO ENCABEZADO
# ============================================================

def _estilizar_encabezado(
    cell
):
    """
    Aplica formato al encabezado.
    """

    cell.font = Font(
        bold=True,
        color='FFFFFF'
    )

    cell.fill = PatternFill(
        fill_type='solid',
        fgColor='1F4E78'
    )

    cell.alignment = Alignment(
        horizontal='center',
        vertical='center',
        wrap_text=True
    )

    cell.border = Border(
        bottom=Side(
            style='thin',
            color='FFFFFF'
        )
    )


# ============================================================
# AJUSTAR COLUMNAS
# ============================================================

def _ajustar_columnas(
    ws
):
    """
    Ajusta anchos de columnas.
    """

    anchos = {
        'A': 18,
        'B': 60,
        'C': 50,
        'D': 22,
        'E': 35
    }

    for columna, ancho in anchos.items():

        ws.column_dimensions[
            columna
        ].width = ancho


# ============================================================
# NOMBRE DE ARCHIVO
# ============================================================

def nombre_archivo_plantilla(
    mes,
    anio
):
    """
    Genera el nombre de descarga.
    """

    return (
        f'plantilla_carga_masiva_'
        f'{mes}_{anio}.xlsx'
    )
