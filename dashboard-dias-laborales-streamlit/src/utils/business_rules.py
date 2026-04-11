import numpy as np
import pandas as pd


def evaluar_oportunidad(
    seccion: str,
    dias_laborales: float | None,
    dias_autopsia: float | None = None,
) -> int:
    """
    Evalúa si un registro cumple la oportunidad según la sección.
    Retorna:
    - 1 si cumple
    - 0 si no cumple
    """

    if dias_laborales is None or pd.isna(dias_laborales):
        return 0

    if seccion == "ESPECIMEN QUIRURGICO":
        return int(dias_laborales <= 10)

    if seccion == "CITOLOGIA DE LIQUIDOS":
        return int(dias_laborales <= 6)

    if seccion == "HEMATOPATOLOGIA":
        return int(dias_laborales <= 6)

    if seccion == "AUTOPSIA":
        if dias_autopsia is None or pd.isna(dias_autopsia):
            return 0
        return int(dias_autopsia <= 30)

    return 0


def aplicar_reglas_negocio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica las reglas de negocio a todo el DataFrame.
    """

    df = df.copy()

    df["Dias_Oportunidad"] = df.apply(
        lambda row: evaluar_oportunidad(
            row.get("SECCION"),
            row.get("Dias_Laborales_num"),
            row.get("Dias_Laborales_Autopsia_num"),
        ),
        axis=1,
    )

    return df
