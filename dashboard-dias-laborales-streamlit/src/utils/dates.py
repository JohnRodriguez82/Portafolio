import pandas as pd
import numpy as np
import holidays


def obtener_festivos(pais: str = "CO"):
    """
    Retorna un array numpy con los días festivos del país indicado.
    """
    festivos = holidays.CountryHoliday(pais)
    return np.array(list(festivos.keys()), dtype="datetime64[D]")


def limpiar_fechas(col: pd.Series) -> pd.Series:
    """
    Limpia y normaliza una columna de fechas que puede venir en:
    - Texto (dd/mm/yyyy, yyyy-mm-dd, etc.)
    - Serial Excel
    - Valores vacíos o inválidos
    """

    col = col.copy().astype("string").str.strip()

    # Normalizar valores inválidos comunes
    col = col.replace(
        {
            "": pd.NA,
            " ": pd.NA,
            "NA": pd.NA,
            "N/A": pd.NA,
            "None": pd.NA,
            "nan": pd.NA,
            "--": pd.NA,
            ".": pd.NA,
            "0": pd.NA,
            "00/00/0000": pd.NA,
        }
    )

    # Detectar seriales de Excel
    es_num = col.str.match(r"^\d+(\.0)?$", na=False)

    fechas_excel = pd.to_datetime(
        pd.to_numeric(col.where(es_num), errors="coerce"),
        unit="D",
        origin="1899-12-30",
        errors="coerce",
    )

    # Intentar parseo estándar de fechas
    fechas_texto = pd.to_datetime(
        col.str.replace(r"[^\d/:\- ]", "", regex=True),
        dayfirst=True,
        errors="coerce",
    )

    # Combinar resultados
    fechas_finales = fechas_texto.copy()
    fechas_finales.loc[es_num] = fechas_excel.loc[es_num]

    return fechas_finales
