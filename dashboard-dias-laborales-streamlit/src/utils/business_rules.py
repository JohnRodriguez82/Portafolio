import numpy as np
import pandas as pd


def aplicar_reglas_negocio(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    condiciones = [
        (df["SECCION"] == "ESPECIMEN QUIRURGICO") & (df["Dias_Laborales_num"] <= 10),
        (df["SECCION"] == "CITOLOGIA DE LIQUIDOS") & (df["Dias_Laborales_num"] <= 6),
        (df["SECCION"] == "HEMATOPATOLOGIA") & (df["Dias_Laborales_num"] <= 6),
        (df["SECCION"] == "AUTOPSIA") & (df["Dias_Laborales_num"] <= 30),
    ]

    df["Dias_Oportunidad"] = np.select(condiciones, [1, 1, 1, 1], default=0)

    return df
