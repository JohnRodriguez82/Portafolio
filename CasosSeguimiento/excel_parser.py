"""
CasosSeguimiento v2.3
Procesamiento de Excel/CSV con actualización incremental.

Características:
- Detección segura de columnas.
- Normalización de nombres.
- Fechas DD/MM/YYYY prioritarias.
- Validación de campos obligatorios.
- Inserción y actualización por numero_caso.
- Campos adicionales almacenados como JSON.
- Logs de procesamiento.
- Cálculo de fecha límite por caso.
- Conservación de fecha límite histórica.
- Cálculo de días de retraso.
- Identificación de casos resueltos a tiempo.
- Identificación de casos resueltos fuera de tiempo.
- Compatibilidad con registros existentes de v2.2.
"""

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config_manager import (
    get_campos_excel,
    get_tipo_archivo,
    load_config,
)

from database import (
    Caso,
    LogProcesamiento,
    get_db,
)

from cumplimiento import (
    calcular_fecha_limite,
    calcular_dias_retraso,
    calcular_cumplimiento,
)


# ============================================================
# CONSTANTES
# ============================================================

CAMPOS_BASE = {
    "sede",
    "seccion",
    "estudios",
    "organo",
    "profesional",
    "estado",
}

CAMPOS_FECHA = {
    "fecha_ingreso",
    "fecha_validacion",
}


# ============================================================
# UTILIDADES
# ============================================================

def _normalizar_texto(valor) -> str:
    """
    Normaliza texto para comparar nombres de columnas.

    Ejemplo:
        "Fecha de Ingreso" -> "fecha de ingreso"
        "Ubicación" -> "ubicacion"
    """

    if valor is None:
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    texto = texto.replace("_", " ")
    texto = texto.replace("-", " ")

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _valor_vacio(valor) -> bool:
    """
    Determina si un valor está vacío o es NaN.
    """

    if valor is None:
        return True

    try:
        if pd.isna(valor):
            return True
    except (TypeError, ValueError):
        pass

    if isinstance(valor, str):
        return not valor.strip()

    return False


# ============================================================
# FECHAS
# ============================================================

def _parse_fecha(valor):
    """
    Convierte valores Excel/CSV a datetime.date.

    Prioridad:
    1. datetime/date de Python
    2. Timestamp de pandas
    3. DD/MM/YYYY
    4. DD-MM-YYYY
    5. DD/MM/YY
    6. DD-MM-YY
    7. YYYY-MM-DD
    8. YYYY/MM/DD
    9. pandas como último intento

    Para strings ambiguos se prioriza formato colombiano.
    """

    if _valor_vacio(valor):
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    if isinstance(valor, pd.Timestamp):
        return valor.date()

    texto = str(valor).strip()

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(
                texto,
                fmt,
            ).date()
        except ValueError:
            continue

    try:
        parsed = pd.to_datetime(
            texto,
            errors="coerce",
            dayfirst=True,
        )

        if pd.notna(parsed):
            return parsed.date()

    except Exception:
        pass

    return None


# ============================================================
# CONFIGURACIÓN DE PLAZOS
# ============================================================

def _obtener_dias_resolucion() -> int:
    """
    Obtiene el número de días configurado para resolver
    un caso.

    Si no existe la configuración, utiliza 10 días como
    valor de compatibilidad.
    """

    try:
        cfg = load_config()

        valor = cfg.get(
            "tiempo_resolucion_dias",
            10,
        )

        dias = int(valor)

        if dias < 0:
            return 10

        return dias

    except Exception:
        return 10


def _calcular_datos_cumplimiento(
    fecha_ingreso,
    fecha_validacion,
):
    """
    Calcula los datos de cumplimiento para un caso nuevo.

    Retorna:

        fecha_limite
        dias_retraso
        cumplimiento
    """

    if not fecha_ingreso:
        return (
            None,
            0,
            None,
        )

    dias_resolucion = (
        _obtener_dias_resolucion()
    )

    fecha_limite = (
        calcular_fecha_limite(
            fecha_ingreso,
            dias_resolucion,
        )
    )

    dias_retraso = (
        calcular_dias_retraso(
            fecha_limite,
            fecha_validacion,
        )
    )

    cumplimiento = (
        calcular_cumplimiento(
            fecha_limite,
            fecha_validacion,
        )
    )

    return (
        fecha_limite,
        dias_retraso,
        cumplimiento,
    )


def _calcular_datos_cumplimiento_existente(
    existe,
    fecha_ingreso,
    fecha_validacion,
):
    """
    Calcula cumplimiento para un caso existente.

    Regla fundamental de v2.3:

    - Si el caso ya tiene fecha_limite, se conserva.
    - Si es un caso antiguo de v2.2 y no tiene fecha_limite,
      se crea una sola vez utilizando la configuración actual.
    - Una vez creada, la fecha límite queda histórica y no
      cambia aunque posteriormente cambie la configuración.

    Esto evita alterar resultados históricos.
    """

    fecha_limite_existente = getattr(
        existe,
        "fecha_limite",
        None,
    )

    if fecha_limite_existente:
        fecha_limite = (
            fecha_limite_existente
        )

    else:
        (
            fecha_limite,
            _,
            _,
        ) = _calcular_datos_cumplimiento(
            fecha_ingreso,
            fecha_validacion,
        )

    dias_retraso = (
        calcular_dias_retraso(
            fecha_limite,
            fecha_validacion,
        )
    )

    cumplimiento = (
        calcular_cumplimiento(
            fecha_limite,
            fecha_validacion,
        )
    )

    return (
        fecha_limite,
        dias_retraso,
        cumplimiento,
    )


# ============================================================
# COLUMNAS
# ============================================================

def _detectar_columnas(
    df_columns,
    campos_config,
):
    """
    Detecta columnas usando este orden:

    1. Coincidencia exacta normalizada.
    2. Coincidencia exacta con ID.
    3. Coincidencia parcial inequívoca.
    4. Si hay ambigüedad, se informa como error.
    """

    columnas = list(df_columns)

    normalizadas = {
        columna: _normalizar_texto(columna)
        for columna in columnas
    }

    mapeo = {}
    no_detectados = []
    ambiguos = []

    for campo in campos_config:

        if not campo.get(
            "activo",
            True,
        ):
            continue

        campo_id = str(
            campo.get(
                "id",
                "",
            )
        ).strip()

        sinonimos = [
            s.strip()
            for s in str(
                campo.get(
                    "sinonimos",
                    "",
                )
            ).split(",")
            if s.strip()
        ]

        candidatos_exactos = []
        candidatos_parciales = []

        nombres_busqueda = [
            campo_id,
            campo.get(
                "nombre",
                "",
            ),
            *sinonimos,
        ]

        nombres_normalizados = [
            _normalizar_texto(x)
            for x in nombres_busqueda
            if _normalizar_texto(x)
        ]

        # ----------------------------------------------------
        # Coincidencias exactas
        # ----------------------------------------------------

        for columna in columnas:

            col_norm = normalizadas[
                columna
            ]

            if col_norm in nombres_normalizados:
                candidatos_exactos.append(
                    columna
                )

        if len(candidatos_exactos) == 1:

            mapeo[campo_id] = (
                candidatos_exactos[0]
            )

            continue

        if len(candidatos_exactos) > 1:

            ambiguos.append(
                f"{campo.get('nombre', campo_id)}: "
                f"{candidatos_exactos}"
            )

            continue

        # ----------------------------------------------------
        # Coincidencias parciales
        # ----------------------------------------------------

        for columna in columnas:

            col_norm = normalizadas[
                columna
            ]

            for nombre in nombres_normalizados:

                if len(nombre) >= 4 and (
                    nombre in col_norm
                    or col_norm in nombre
                ):
                    candidatos_parciales.append(
                        columna
                    )
                    break

        candidatos_parciales = list(
            dict.fromkeys(
                candidatos_parciales
            )
        )

        if len(candidatos_parciales) == 1:

            mapeo[campo_id] = (
                candidatos_parciales[0]
            )

        elif len(candidatos_parciales) > 1:

            ambiguos.append(
                f"{campo.get('nombre', campo_id)}: "
                f"{candidatos_parciales}"
            )

        elif campo.get(
            "obligatorio",
            False,
        ):

            no_detectados.append(
                campo.get(
                    "nombre",
                    campo_id,
                )
            )

    return (
        mapeo,
        no_detectados,
        ambiguos,
    )


# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================

def _leer_archivo(filepath: str):
    """
    Lee Excel o CSV según configuración.
    """

    path = Path(filepath)

    if not path.exists():

        raise FileNotFoundError(
            f"No existe el archivo: {path}"
        )

    tipo_cfg = get_tipo_archivo()

    extension = (
        path.suffix.lower()
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    if (
        extension == ".csv"
        or tipo_cfg == "csv"
    ):

        errores_csv = []

        for sep in [
            ",",
            ";",
            "\t",
        ]:

            try:

                df = pd.read_csv(
                    path,
                    sep=sep,
                    engine="python",
                    dtype=object,
                )

                if len(df.columns) > 1:
                    return df

            except Exception as exc:

                errores_csv.append(
                    f"{sep}: {exc}"
                )

        raise ValueError(
            "No se pudo leer el CSV. "
            "Verifica el separador. "
            f"Detalles: {errores_csv}"
        )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    if extension not in {
        ".xlsx",
        ".xls",
    }:

        raise ValueError(
            f"Extensión no soportada: {extension}"
        )

    return pd.read_excel(
        path,
        dtype=object,
    )


# ============================================================
# CONVERSIÓN DE VALORES
# ============================================================

def _convertir_valor(
    valor,
    tipo,
):
    """
    Convierte un valor de acuerdo con el tipo configurado.
    """

    if _valor_vacio(valor):

        return (
            None
            if tipo == "fecha"
            else ""
        )

    if tipo == "fecha":

        return _parse_fecha(
            valor
        )

    if tipo == "numero":

        try:

            numero = pd.to_numeric(
                valor,
                errors="coerce",
            )

            if pd.isna(numero):
                return ""

            return float(numero)

        except Exception:

            return ""

    return str(
        valor
    ).strip()


# ============================================================
# CAMPOS EXTRA
# ============================================================

def _obtener_campos_extra(
    valores,
):
    """
    Separa los campos parametrizables de los campos base.
    """

    campos_extra = {}

    for campo_id, valor in valores.items():

        if (
            campo_id not in CAMPOS_BASE
            and campo_id not in CAMPOS_FECHA
            and campo_id != "numero_caso"
        ):

            campos_extra[
                campo_id
            ] = valor

    return campos_extra


# ============================================================
# ESTADO
# ============================================================

def _obtener_estado(
    valores,
):
    """
    Determina el estado lógico del caso.

    Si existe fecha de validación, se considera RESUELTO
    aunque el Excel indique PENDIENTE.
    """

    fecha_validacion = valores.get(
        "fecha_validacion"
    )

    estado_raw = str(
        valores.get(
            "estado"
        )
        or ""
    ).strip().upper()

    estado = (
        estado_raw
        if estado_raw
        else (
            "RESUELTO"
            if fecha_validacion
            else "PENDIENTE"
        )
    )

    if (
        fecha_validacion
        and estado in {
            "",
            "PENDIENTE",
        }
    ):

        estado = "RESUELTO"

    return estado


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_archivo(
    filepath: str,
) -> dict:
    """
    Procesa un archivo Excel/CSV y actualiza la base.

    La identificación del registro se realiza por
    numero_caso.

    Los casos existentes conservan su fecha límite histórica.
    """

    db = get_db()

    resultado = {
        "ok": False,
        "insertados": 0,
        "actualizados": 0,
        "errores": [],
        "cambios": [],
        "columnas_detectadas": {},
    }

    try:

        # ====================================================
        # LEER ARCHIVO
        # ====================================================

        df = _leer_archivo(
            filepath
        )

        if df.empty:

            resultado["error"] = (
                "El archivo está vacío."
            )

            return resultado

        # ====================================================
        # CONFIGURACIÓN
        # ====================================================

        campos_config = (
            get_campos_excel()
        )

        (
            mapeo,
            faltantes,
            ambiguos,
        ) = _detectar_columnas(
            df.columns.tolist(),
            campos_config,
        )

        resultado[
            "columnas_detectadas"
        ] = {
            campo: str(columna)
            for campo, columna in mapeo.items()
        }

        if faltantes:

            resultado["error"] = (
                "Columnas obligatorias no "
                "detectadas: "
                f"{faltantes}. "
                "Columnas encontradas: "
                f"{list(df.columns)}"
            )

            return resultado

        if ambiguos:

            resultado["error"] = (
                "Se encontraron columnas "
                "ambiguas: "
                f"{ambiguos}. "
                "Corrige los nombres o "
                "sinónimos."
            )

            return resultado

        # ====================================================
        # CONFIGURACIÓN POR ID
        # ====================================================

        config_por_id = {
            campo["id"]: campo
            for campo in campos_config
            if campo.get(
                "activo",
                True,
            )
        }

        # ====================================================
        # PROCESAR FILAS
        # ====================================================

        for idx, row in df.iterrows():

            numero_fila = idx + 2

            try:

                # ------------------------------------------------
                # Número de caso
                # ------------------------------------------------

                if (
                    "numero_caso"
                    not in mapeo
                ):

                    resultado[
                        "errores"
                    ].append(
                        f"Fila {numero_fila}: "
                        "No se detectó "
                        "número de caso."
                    )

                    continue

                numero_raw = row[
                    mapeo[
                        "numero_caso"
                    ]
                ]

                if _valor_vacio(
                    numero_raw
                ):

                    resultado[
                        "errores"
                    ].append(
                        f"Fila {numero_fila}: "
                        "Número de caso "
                        "vacío."
                    )

                    continue

                numero_caso = str(
                    numero_raw
                ).strip()

                # Evitar números tipo 123.0
                # provenientes de Excel.

                if re.fullmatch(
                    r"\d+\.0",
                    numero_caso,
                ):

                    numero_caso = (
                        numero_caso[:-2]
                    )

                # ------------------------------------------------
                # Extraer valores
                # ------------------------------------------------

                valores = {}

                for (
                    campo_id,
                    columna,
                ) in mapeo.items():

                    cfg = (
                        config_por_id.get(
                            campo_id,
                            {},
                        )
                    )

                    tipo = cfg.get(
                        "tipo",
                        "texto",
                    )

                    valores[
                        campo_id
                    ] = _convertir_valor(
                        row[columna],
                        tipo,
                    )

                # ------------------------------------------------
                # Campos obligatorios
                # ------------------------------------------------

                fecha_ingreso = (
                    valores.get(
                        "fecha_ingreso"
                    )
                )

                profesional = (
                    valores.get(
                        "profesional"
                    )
                )

                if not fecha_ingreso:

                    resultado[
                        "errores"
                    ].append(
                        f"Fila {numero_fila}: "
                        f"Caso {numero_caso}: "
                        "fecha_ingreso "
                        "inválida o vacía."
                    )

                    continue

                if not profesional:

                    resultado[
                        "errores"
                    ].append(
                        f"Fila {numero_fila}: "
                        f"Caso {numero_caso}: "
                        "profesional vacío."
                    )

                    continue

                # ------------------------------------------------
                # Fecha de resolución
                # ------------------------------------------------

                fecha_validacion = (
                    valores.get(
                        "fecha_validacion"
                    )
                )

                # ------------------------------------------------
                # Estado
                # ------------------------------------------------

                estado = _obtener_estado(
                    valores
                )

                # ------------------------------------------------
                # Campos extra
                # ------------------------------------------------

                campos_extra = (
                    _obtener_campos_extra(
                        valores
                    )
                )

                # ------------------------------------------------
                # Buscar caso existente
                # ------------------------------------------------

                existe = (
                    db.query(Caso)
                    .filter(
                        Caso.numero_caso
                        == numero_caso
                    )
                    .first()
                )

                # =================================================
                # ACTUALIZAR CASO EXISTENTE
                # =================================================

                if existe:

                    cambios = []

                    # ------------------------------------------------
                    # Calcular cumplimiento conservando fecha límite
                    # histórica.
                    # ------------------------------------------------

                    (
                        fecha_limite,
                        dias_retraso,
                        cumplimiento,
                    ) = (
                        _calcular_datos_cumplimiento_existente(
                            existe,
                            fecha_ingreso,
                            fecha_validacion,
                        )
                    )

                    campos_a_comparar = {
                        "fecha_ingreso":
                            fecha_ingreso,

                        "fecha_validacion":
                            fecha_validacion,

                        "fecha_limite":
                            fecha_limite,

                        "dias_retraso":
                            dias_retraso,

                        "cumplimiento_plazo":
                            cumplimiento,

                        "estado":
                            estado,

                        "profesional":
                            profesional,

                        "sede":
                            valores.get(
                                "sede",
                                "",
                            ),

                        "seccion":
                            valores.get(
                                "seccion",
                                "",
                            ),

                        "estudios":
                            valores.get(
                                "estudios",
                                "",
                            ),

                        "organo":
                            valores.get(
                                "organo",
                                "",
                            ),
                    }

                    # ------------------------------------------------
                    # Comparar y actualizar campos
                    # ------------------------------------------------

                    for (
                        atributo,
                        nuevo_valor,
                    ) in (
                        campos_a_comparar.items()
                    ):

                        anterior = getattr(
                            existe,
                            atributo,
                            None,
                        )

                        if (
                            anterior
                            != nuevo_valor
                        ):

                            cambios.append(
                                f"{atributo}: "
                                f"{anterior} → "
                                f"{nuevo_valor}"
                            )

                            setattr(
                                existe,
                                atributo,
                                nuevo_valor,
                            )

                    # ------------------------------------------------
                    # Campos extra
                    # ------------------------------------------------

                    if campos_extra:

                        anterior_extra = (
                            existe.campos_extra
                            or {}
                        )

                        nuevo_extra = dict(
                            anterior_extra
                        )

                        for (
                            clave,
                            valor,
                        ) in (
                            campos_extra.items()
                        ):

                            if (
                                nuevo_extra.get(
                                    clave
                                )
                                != valor
                            ):

                                cambios.append(
                                    f"{clave}: "
                                    f"{nuevo_extra.get(clave)} "
                                    f"→ {valor}"
                                )

                            nuevo_extra[
                                clave
                            ] = valor

                        existe.campos_extra = (
                            nuevo_extra
                        )

                    # ------------------------------------------------
                    # Reiniciar alertas cuando el caso se resuelve
                    # ------------------------------------------------

                    if (
                        fecha_validacion
                        or estado == "RESUELTO"
                    ):

                        existe.alerta_preventiva_enviada = (
                            False
                        )

                        existe.alerta_vencido_enviada = (
                            False
                        )

                    # ------------------------------------------------
                    # Registrar cambios
                    # ------------------------------------------------

                    if cambios:

                        resultado[
                            "cambios"
                        ].append(
                            f"Caso {numero_caso}: "
                            + "; ".join(
                                cambios
                            )
                        )

                    resultado[
                        "actualizados"
                    ] += 1

                # =================================================
                # INSERTAR CASO NUEVO
                # =================================================

                else:

                    (
                        fecha_limite,
                        dias_retraso,
                        cumplimiento,
                    ) = (
                        _calcular_datos_cumplimiento(
                            fecha_ingreso,
                            fecha_validacion,
                        )
                    )

                    nuevo = Caso(
                        numero_caso=numero_caso,

                        fecha_ingreso=(
                            fecha_ingreso
                        ),

                        fecha_validacion=(
                            fecha_validacion
                        ),

                        fecha_limite=(
                            fecha_limite
                        ),

                        dias_retraso=(
                            dias_retraso
                        ),

                        cumplimiento_plazo=(
                            cumplimiento
                        ),

                        estado=(
                            estado
                        ),

                        profesional=(
                            profesional
                        ),

                        sede=valores.get(
                            "sede",
                            "",
                        ),

                        seccion=valores.get(
                            "seccion",
                            "",
                        ),

                        estudios=valores.get(
                            "estudios",
                            "",
                        ),

                        organo=valores.get(
                            "organo",
                            "",
                        ),

                        campos_extra=(
                            campos_extra
                        ),
                    )

                    db.add(
                        nuevo
                    )

                    resultado[
                        "insertados"
                    ] += 1

            except Exception as exc:

                resultado[
                    "errores"
                ].append(
                    f"Fila {numero_fila}: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

        # ====================================================
        # COMMIT PRINCIPAL
        # ====================================================

        db.commit()

        # ====================================================
        # LOG DE PROCESAMIENTO
        # ====================================================

        log = LogProcesamiento(
            archivo=str(
                Path(
                    filepath
                ).resolve()
            ),

            insertados=(
                resultado[
                    "insertados"
                ]
            ),

            actualizados=(
                resultado[
                    "actualizados"
                ]
            ),

            errores=len(
                resultado[
                    "errores"
                ]
            ),

            detalle="\n".join(
                resultado[
                    "cambios"
                ][:50]
            ),
        )

        db.add(
            log
        )

        db.commit()

        resultado[
            "ok"
        ] = True

        return resultado

    except Exception as exc:

        db.rollback()

        resultado[
            "ok"
        ] = False

        resultado[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return resultado

    finally:

        db.close()
