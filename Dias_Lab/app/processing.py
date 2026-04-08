import pandas as pd
import numpy as np
from utils import limpiar_fechas, calcular_busdays_seguro, obtener_festivos

def procesar_datos(df, col_inicio, col_fin, config):
    
    df = df.copy()

    # Limpieza
    df["fecha_inicio"] = limpiar_fechas(df[col_inicio])
    df["fecha_fin"] = limpiar_fechas(df[col_fin])

    # Festivos
    festivos = obtener_festivos() if config["festivos"] else []

    # Cálculo días
    df["dias"] = calcular_busdays_seguro(
        df["fecha_inicio"].values.astype("datetime64[D]"),
        df["fecha_fin"].values.astype("datetime64[D]"),
        festivos,
        config["weekmask"]
    )

    df["dias_num"] = pd.to_numeric(df["dias"], errors="coerce")

    # Reglas negocio
    df["oportunidad"] = np.select(
        [
            (df["SECCION"]=="ESPECIMEN QUIRURGICO") & (df["dias_num"] <= 10),
            (df["SECCION"]=="CITOLOGIA DE LIQUIDOS") & (df["dias_num"] <= 6),
            (df["SECCION"]=="HEMATOPATOLOGIA") & (df["dias_num"] <= 6)
        ],
        [1,1,1],
        default=0
    )

    return df
