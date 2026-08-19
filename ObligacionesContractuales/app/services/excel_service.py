"""
Servicios para generación de archivos Excel.

Este módulo NO depende de Flask.

Responsabilidades:
- Generar plantilla Excel para carga masiva mensual.
- Generar plantilla Excel para un reporte específico.
"""

import io

from openpyxl import Workbook

from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)


# ============================================================
# CONSTANTES
# ============================================================

EXCEL_MIMETYPE = (
    'application/vnd.openxmlformats-officedocument.'
    'spreadsheetml.sheet'
)


# ============================================================
# PLANTILLA CARGA MASIVA POR MES
# ============================================================

def generar_plantilla_masiva(
    obligaciones,
    mes,
    anio
):
    """
    Genera el archivo Excel de plantilla para carga masiva
    de evidencias de todas las obligaciones de un mes.

    Retorna:
        BytesIO: archivo Excel en memoria.
    """

    wb = Workbook()

    ws = wb.active

    ws.title = (
        f'Carga_{mes:02d}_{anio}'
    )

    # ========================================================
    # ENCABEZADOS
    # ========================================================

    headers = [
        'Obligacion No.',
        'Descripcion Obligacion',
        'Anuncio / Contexto',
        'Fecha de la actividad',
        'Nombre Imagen'
    ]

    ws.append(headers)

    # ========================================================
    # ESTILOS
    # ========================================================

    header_font = Font(
        bold=True,
        color='FFFFFF',
        size=11
    )

    header_fill = PatternFill(
        start_color='2c3e50',
        end_color='2c3e50',
        fill_type='solid'
    )

    header_align = Alignment(
        horizontal='center',
        vertical='center',
        wrap_text=True
    )

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for cell in ws[1]:

        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # ========================================================
    # OBLIGACIONES
    # ========================================================

    for obligacion in obligaciones:

        ws.append(
            [
                obligacion.numero,
                obligacion.descripcion,
                '',
                f'{anio}-{mes:02d}-15',
                ''
            ]
        )

    # ========================================================
    # ANCHOS
    # ========================================================

    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 55
    ws.column_dimensions['C'].width = 55
    ws.column_dimensions['D'].width = 22
    ws.column_dimensions['E'].width = 28

    ws.freeze_panes = 'A2'

    # ========================================================
    # HOJA DE INSTRUCCIONES
    # ========================================================

    ws_instr = wb.create_sheet(
        'Instrucciones'
    )

    instrucciones = [

        [
            'INSTRUCCIONES DE CARGA MASIVA POR MES'
        ],

        [''],

        [
            '1. NO modifique los encabezados '
            'de columna (fila 1).'
        ],

        [
            '2. NO modifique las columnas A y B '
            '(Obligacion No. y Descripcion).'
        ],

        [
            '3. En la columna C escriba el anuncio '
            'o contexto de la actividad '
            '(solo para el sistema).'
        ],

        [
            '4. En la columna D indique la fecha '
            'en formato YYYY-MM-DD o DD/MM/YYYY.'
        ],

        [
            '5. En la columna E escriba el nombre '
            'EXACTO del archivo de imagen, '
            'incluyendo extension '
            '(ej: evidencia1.jpg).'
        ],

        [
            '6. Puede INSERTAR mas filas para la '
            'misma obligacion si tiene multiples evidencias.'
        ],

        [
            '7. Puede ELIMINAR las filas de obligaciones '
            'que no tengan evidencias este mes.'
        ],

        [
            '8. Las imagenes deben cargarse JUNTO '
            'con el Excel en el formulario web '
            '(campo de archivos multiples).'
        ],

        [''],

        [
            'REGLAS IMPORTANTES:'
        ],

        [
            '- La fecha debe pertenecer al mes '
            'y año seleccionados.'
        ],

        [
            '- El nombre de imagen en el Excel '
            'debe coincidir EXACTAMENTE con el archivo subido.'
        ],

        [
            '- Si no adjunta imagen, deje la columna E vacia; '
            'se creara la actividad sin evidencia visual.'
        ],

        [
            '- El sistema creara automaticamente '
            'los reportes mensuales por obligacion '
            'si no existen.'
        ],

        [
            '- Si tiene API key de Gemini configurada, '
            'analizara automaticamente cada imagen.'
        ],

        [
            '- NOTA: El tier gratuito de Gemini '
            'permite 15 imagenes/minuto. '
            'Si sube mas, el sistema las procesara '
            'automaticamente con pausas.'
        ]
    ]

    for row in instrucciones:

        ws_instr.append(row)

    ws_instr.column_dimensions[
        'A'
    ].width = 100

    # ========================================================
    # ARCHIVO EN MEMORIA
    # ========================================================

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return output


# ============================================================
# PLANTILLA EXCEL PARA UN REPORTE
# ============================================================

def generar_plantilla_reporte():
    """
    Genera una plantilla Excel para un reporte específico.

    Retorna:
        BytesIO: archivo Excel en memoria.
    """

    wb = Workbook()

    ws = wb.active

    ws.title = 'Carga Masiva'

    # ========================================================
    # ENCABEZADOS
    # ========================================================

    headers = [
        'Anuncio / Contexto',
        'Fecha de la actividad'
    ]

    ws.append(headers)

    # ========================================================
    # ESTILOS
    # ========================================================

    for cell in ws[1]:

        cell.font = Font(
            bold=True,
            color='FFFFFF'
        )

        cell.fill = PatternFill(
            start_color='2c3e50',
            end_color='2c3e50',
            fill_type='solid'
        )

        cell.alignment = Alignment(
            horizontal='center'
        )

    # ========================================================
    # EJEMPLOS
    # ========================================================

    ws.append(
        [
            'Presentacion del estado de avance '
            'de proyectos',
            '2026-07-15'
        ]
    )

    ws.append(
        [
            'Revision de solicitudes de ajuste '
            'tecnicos',
            '2026-07-20'
        ]
    )

    ws.append(
        [
            'Elaboracion del plan de trabajo '
            'mensual',
            '2026-07-25'
        ]
    )

    # ========================================================
    # ANCHOS
    # ========================================================

    ws.column_dimensions['A'].width = 60
    ws.column_dimensions['B'].width = 25

    # ========================================================
    # ARCHIVO EN MEMORIA
    # ========================================================

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return output
