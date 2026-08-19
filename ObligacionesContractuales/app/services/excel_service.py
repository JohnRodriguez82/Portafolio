"""
Servicio para generación y lectura de archivos Excel.

Responsabilidades:

- Leer archivos Excel de carga masiva.
- Validar encabezados.
- Normalizar registros.
- Generar plantilla Excel para carga masiva.
- Generar plantilla Excel para reportes.

Este módulo NO depende de Flask.
"""

import io

from datetime import date, datetime

from openpyxl import (
    Workbook,
    load_workbook
)

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

ENCABEZADOS_CARGA = [
    'Obligacion No.',
    'Descripcion',
    'Anuncio',
    'Fecha',
    'Nombre Imagen'
]


class ExcelService:
    """
    Servicio para trabajar con archivos Excel.
    """

    # ========================================================
    # LEER EXCEL
    # ========================================================

    def leer_excel(
        self,
        archivo_excel
    ):
        """
        Lee un Excel de carga masiva.

        Retorna una lista de diccionarios:

        [
            {
                "obligacion": ...,
                "descripcion": ...,
                "anuncio": ...,
                "fecha": ...,
                "nombre_imagen": ...
            }
        ]
        """

        if archivo_excel is None:
            raise ValueError(
                'No se recibió el archivo Excel.'
            )

        workbook = self._abrir_workbook(
            archivo_excel
        )

        try:
            worksheet = workbook.active

            filas = list(
                worksheet.iter_rows(
                    values_only=True
                )
            )

            if not filas:
                return []

            encabezados = [
                self._normalizar_encabezado(
                    valor
                )
                for valor in filas[0]
            ]

            self._validar_encabezados(
                encabezados
            )

            resultado = []

            for numero_fila, fila in enumerate(
                filas[1:],
                start=2
            ):
                registro = (
                    self._convertir_fila(
                        fila=fila,
                        numero_fila=numero_fila,
                        encabezados=encabezados
                    )
                )

                if registro is not None:
                    resultado.append(
                        registro
                    )

            return resultado

        finally:
            workbook.close()

    # ========================================================
    # ABRIR WORKBOOK
    # ========================================================

    @staticmethod
    def _abrir_workbook(
        archivo_excel
    ):
        """
        Abre un archivo Excel recibido como:

        - FileStorage
        - BytesIO
        - bytes
        - ruta
        """

        if hasattr(
            archivo_excel,
            'stream'
        ):
            archivo_excel.stream.seek(0)

            return load_workbook(
                filename=archivo_excel.stream,
                data_only=True
            )

        if hasattr(
            archivo_excel,
            'seek'
        ):
            archivo_excel.seek(0)

        return load_workbook(
            filename=archivo_excel,
            data_only=True
        )

    # ========================================================
    # VALIDAR ENCABEZADOS
    # ========================================================

    @classmethod
    def _validar_encabezados(
        cls,
        encabezados
    ):
        """
        Valida que el Excel tenga las columnas necesarias.
        """

        requeridos = {
            cls._normalizar_encabezado(
                encabezado
            )
            for encabezado in ENCABEZADOS_CARGA
        }

        disponibles = set(
            encabezados
        )

        faltantes = (
            requeridos - disponibles
        )

        if faltantes:
            raise ValueError(
                'El archivo Excel no contiene '
                'los encabezados requeridos. '
                f'Faltan: {", ".join(faltantes)}'
            )

    # ========================================================
    # CONVERTIR FILA
    # ========================================================

    @classmethod
    def _convertir_fila(
        cls,
        fila,
        numero_fila,
        encabezados
    ):
        """
        Convierte una fila del Excel en un diccionario.
        """

        datos = {}

        for indice, encabezado in enumerate(
            encabezados
        ):
            if indice >= len(fila):
                valor = None
            else:
                valor = fila[indice]

            datos[encabezado] = valor

        obligacion = (
            datos.get(
                cls._normalizar_encabezado(
                    'Obligacion No.'
                )
            )
        )

        descripcion = (
            datos.get(
                cls._normalizar_encabezado(
                    'Descripcion'
                )
            )
        )

        anuncio = (
            datos.get(
                cls._normalizar_encabezado(
                    'Anuncio'
                )
            )
        )

        fecha = (
            datos.get(
                cls._normalizar_encabezado(
                    'Fecha'
                )
            )

        nombre_imagen = (
            datos.get(
                cls._normalizar_encabezado(
                    'Nombre Imagen'
                )
            )
        )

        # ----------------------------------------------------
        # Ignorar filas completamente vacías
        # ----------------------------------------------------

        valores = [
            obligacion,
            descripcion,
            anuncio,
            fecha,
            nombre_imagen
        ]

        if all(
            cls._esta_vacio(valor)
            for valor in valores
        ):
            return None

        return {
            'obligacion': (
                cls._normalizar_obligacion(
                    obligacion
                )
            ),
            'descripcion': (
                cls._texto(
                    descripcion
                )
            ),
            'anuncio': (
                cls._texto(
                    anuncio
                )
            ),
            'fecha': (
                cls._normalizar_fecha(
                    fecha
                )
            ),
            'nombre_imagen': (
                cls._texto(
                    nombre_imagen
                )
            ),
            '_fila_excel': numero_fila
        }

    # ========================================================
    # NORMALIZAR OBLIGACIÓN
    # ========================================================

    @staticmethod
    def _normalizar_obligacion(
        valor
    ):
        """
        Convierte el número de obligación a un formato
        manejable por ContratoService.
        """

        if valor is None:
            return None

        if isinstance(
            valor,
            float
        ) and valor.is_integer():
            return int(valor)

        if isinstance(
            valor,
            int
        ):
            return valor

        texto = str(
            valor
        ).strip()

        if not texto:
            return None

        try:
            numero = float(
                texto.replace(
                    ',',
                    '.'
                )
            )

            if numero.is_integer():
                return int(numero)

        except (
            ValueError,
            TypeError
        ):
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
        Convierte fechas de Excel a datetime/date.

        Acepta:

        - date
        - datetime
        - YYYY-MM-DD
        - DD/MM/YYYY
        """

        if valor is None:
            return None

        if isinstance(
            valor,
            datetime
        ):
            return valor.date()

        if isinstance(
            valor,
            date
        ):
            return valor

        texto = str(
            valor
        ).strip()

        if not texto:
            return None

        formatos = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d'
        ]

        for formato in formatos:
            try:
                return datetime.strptime(
                    texto,
                    formato
                ).date()
            except ValueError:
                continue

        raise ValueError(
            f'Fecha no válida: {valor}'
        )

    # ========================================================
    # NORMALIZAR TEXTO
    # ========================================================

    @staticmethod
    def _texto(
        valor
    ):
        """
        Convierte un valor a texto limpio.
        """

        if valor is None:
            return ''

        return str(
            valor
        ).strip()

    # ========================================================
    # VALIDAR VACÍO
    # ========================================================

    @staticmethod
    def _esta_vacio(
        valor
    ):
        """
        Determina si un valor está vacío.
        """

        if valor is None:
            return True

        if isinstance(
            valor,
            str
        ):
            return not valor.strip()

        return False

    # ========================================================
    # NORMALIZAR ENCABEZADO
    # ========================================================

    @staticmethod
    def _normalizar_encabezado(
        valor
    ):
        """
        Normaliza nombres de columnas.

        Permite tolerar diferencias menores de espacios
        y mayúsculas.
        """

        if valor is None:
            return ''

        texto = str(
            valor
        ).strip().lower()

        reemplazos = {
            'á': 'a',
            'é': 'e',
            'í': 'i',
            'ó': 'o',
            'ú': 'u',
            'ü': 'u'
        }

        for origen, destino in (
            reemplazos.items()
        ):
            texto = texto.replace(
                origen,
                destino
            )

        texto = (
            texto
            .replace(
                '_',
                ' '
            )
            .replace(
                '-',
                ' '
            )
        )

        return ' '.join(
            texto.split()
        )

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
        Genera plantilla para carga masiva mensual.
        """

        wb = Workbook()

        ws = wb.active

        ws.title = (
            f'Carga_{int(mes):02d}_{anio}'
        )

        # ----------------------------------------------------
        # Estilos
        # ----------------------------------------------------

        encabezado_fill = PatternFill(
            'solid',
            fgColor='0D6EFD'
        )

        encabezado_font = Font(
            bold=True,
            color='FFFFFF'
        )

        borde = Border(
            bottom=Side(
                style='thin',
                color='CCCCCC'
            )
        )

        # ----------------------------------------------------
        # Encabezados
        # ----------------------------------------------------

        for columna, encabezado in enumerate(
            ENCABEZADOS_CARGA,
            start=1
        ):
            celda = ws.cell(
                row=1,
                column=columna,
                value=encabezado
            )

            celda.fill = encabezado_fill
            celda.font = encabezado_font
            celda.alignment = Alignment(
                horizontal='center',
                vertical='center'
            )
            celda.border = borde

        # ----------------------------------------------------
        # Obligaciones
        # ----------------------------------------------------

        fila = 2

        for obligacion in (
            obligaciones or []
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

            fila += 1

        # ----------------------------------------------------
        # Anchos
        # ----------------------------------------------------

        ws.column_dimensions[
            'A'
        ].width = 18

        ws.column_dimensions[
            'B'
        ].width = 70

        ws.column_dimensions[
            'C'
        ].width = 55

        ws.column_dimensions[
            'D'
        ].width = 18

        ws.column_dimensions[
            'E'
        ].width = 35

        ws.freeze_panes = 'A2'

        # ----------------------------------------------------
        # Hoja de instrucciones
        # ----------------------------------------------------

        ws_instr = wb.create_sheet(
            'Instrucciones'
        )

        instrucciones = [
            [
                'INSTRUCCIONES DE CARGA MASIVA POR MES'
            ],
            [''],
            [
                '1. NO modifique los encabezados.'
            ],
            [
                '2. NO modifique las columnas A y B.'
            ],
            [
                '3. Columna C: Anuncio o contexto.'
            ],
            [
                '4. Columna D: Fecha.'
            ],
            [
                '5. Columna E: Nombre exacto de imagen.'
            ],
            [
                '6. Puede duplicar filas para una obligación.'
            ],
            [
                '7. La fecha debe pertenecer al periodo.'
            ],
            [
                '8. Las imágenes deben coincidir '
                'exactamente con el nombre del Excel.'
            ]
        ]

        for fila_instruccion in instrucciones:
            ws_instr.append(
                fila_instruccion
            )

        ws_instr.column_dimensions[
            'A'
        ].width = 100

        # ----------------------------------------------------
        # Archivo en memoria
        # ----------------------------------------------------

        output = io.BytesIO()

        wb.save(
            output
        )

        output.seek(0)

        return output

    # ========================================================
    # GENERAR PLANTILLA REPORTE
    # ========================================================

    @staticmethod
    def generar_plantilla_reporte():
        """
        Genera una plantilla Excel básica para reporte.
        """

        wb = Workbook()

        ws = wb.active

        ws.title = 'Carga Masiva'

        encabezados = [
            'Anuncio',
            'Fecha',
            'Nombre Imagen'
        ]

        for columna, encabezado in enumerate(
            encabezados,
            start=1
        ):
            celda = ws.cell(
                row=1,
                column=columna,
                value=encabezado
            )

            celda.font = Font(
                bold=True
            )

        ws.column_dimensions[
            'A'
        ].width = 60

        ws.column_dimensions[
            'B'
        ].width = 20

        ws.column_dimensions[
            'C'
        ].width = 35

        output = io.BytesIO()

        wb.save(
            output
        )

        output.seek(0)

        return output


# ============================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================

def leer_excel(
    archivo_excel
):
    """
    Función de compatibilidad.

    Permite utilizar:

        leer_excel(archivo)

    además de:

        ExcelService().leer_excel(archivo)
    """

    return ExcelService().leer_excel(
        archivo_excel
    )


def generar_plantilla_masiva(
    obligaciones,
    mes,
    anio
):
    """
    Función de compatibilidad.
    """

    return ExcelService.generar_plantilla_masiva(
        obligaciones,
        mes,
        anio
    )


def generar_plantilla_reporte():
    """
    Función de compatibilidad.
    """

    return ExcelService.generar_plantilla_reporte()
