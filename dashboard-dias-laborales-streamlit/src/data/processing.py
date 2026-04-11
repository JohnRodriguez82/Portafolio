def process_dataframe(df, config):
    import time
    import numpy as np
    import pandas as pd
    from src.utils.dates import limpiar_fechas, obtener_festivos

    start_time = time.time()
    df = df.copy()

    # Limpieza de fechas
    df["fecha_inicio"] = limpiar_fechas(df[config["col_inicio"]])
    df["fecha_fin"] = limpiar_fechas(df[config["col_fin"]])

    # Inicializar columnas
    df["Dias_Laborales"] = "Sin dato"
    df["Dias_Laborales_num"] = np.nan

    # Festivos
    festivos = obtener_festivos() if config["excluir_festivos"] else []

    # Máscara de filas válidas
    mask_validas = (
        df["fecha_inicio"].notna()
        & df["fecha_fin"].notna()
        & (df["fecha_fin"] >= df["fecha_inicio"])
    )

    if mask_validas.any():
        inicio_vals = df.loc[mask_validas, "fecha_inicio"].values.astype("datetime64[D]")
        fin_vals = df.loc[mask_validas, "fecha_fin"].values.astype("datetime64[D]")

        dias = np.busday_count(
            inicio_vals,
            fin_vals + np.timedelta64(1, "D"),
            holidays=festivos,
            weekmask=config["weekmask"]
        )

        df.loc[mask_validas, "Dias_Laborales_num"] = dias
        df.loc[mask_validas, "Dias_Laborales"] = dias.astype(int)

    duracion = time.time() - start_time
    return df, duracion
