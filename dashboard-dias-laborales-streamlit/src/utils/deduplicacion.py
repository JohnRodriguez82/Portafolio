import pandas as pd


def eliminar_duplicados(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Elimina registros duplicados conservando:
    - el más reciente si existe fecha válida
    - cualquiera si no hay fecha válida
    """

    if not config.get("aplicar_deduplicacion"):
        return df

    col_id = config.get("columna_duplicados")
    col_fecha = config.get("columna_fecha_dedup")

    if not col_id or not col_fecha:
        return df

    df = df.copy()

    # Convertir columna de fecha (los inválidos quedan como NaT)
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")

    # Separar registros con y sin fecha válida
    df_con_fecha = df[df[col_fecha].notna()]
    df_sin_fecha = df[df[col_fecha].isna()]

    # ✅ Con fecha válida → conservar el más reciente
    df_con_fecha = (
        df_con_fecha
        .sort_values(by=col_fecha, ascending=False)
        .drop_duplicates(subset=col_id, keep="first")
    )

    # ✅ Sin fecha válida → eliminar duplicados dejando uno cualquiera
    df_sin_fecha = df_sin_fecha.drop_duplicates(subset=col_id, keep="first")

    # Unir ambos mundos
    df_final = pd.concat([df_con_fecha, df_sin_fecha], ignore_index=True)

    return df_final
