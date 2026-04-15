import pandas as pd


def eliminar_duplicados(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Elimina registros duplicados conservando el más reciente
    según la columna de fecha seleccionada por el usuario.
    """

    # Si el usuario no activó la deduplicación, no hacemos nada
    if not config.get("aplicar_deduplicacion"):
        return df

    col_id = config.get("columna_duplicados")
    col_fecha = config.get("columna_fecha_dedup")

    # Validación defensiva
    if not col_id or not col_fecha:
        return df

    df = df.copy()

    # Convertir la columna de fecha seleccionada
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")

    # Ordenar: más reciente primero
    df = df.sort_values(by=col_fecha, ascending=False)

    # Eliminar duplicados conservando el más reciente
    df = df.drop_duplicates(subset=col_id, keep="first")

    return df
