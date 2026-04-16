import pandas as pd


def eliminar_duplicados(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Elimina registros duplicados sin modificar las columnas originales.
    - Usa una columna auxiliar de fecha SOLO para ordenar.
    - Conserva:
        • el más reciente si existe fecha válida
        • uno cualquiera si no hay fecha válida
    """

    if not config.get("aplicar_deduplicacion"):
        return df

    col_id = config.get("columna_duplicados")
    col_fecha = config.get("columna_fecha_dedup")

    if not col_id or not col_fecha:
        return df

    df = df.copy()

    # ✅ Columna auxiliar solo para deduplicación
    aux_col = "__fecha_dedup_aux__"

    df[aux_col] = pd.to_datetime(
        df[col_fecha],
        errors="coerce",
        dayfirst=True
    )

    # Separar con y sin fecha válida
    df_con_fecha = df[df[aux_col].notna()]
    df_sin_fecha = df[df[aux_col].isna()]

    # ✅ Con fecha → conservar el más reciente
    df_con_fecha = (
        df_con_fecha
        .sort_values(by=aux_col, ascending=False)
        .drop_duplicates(subset=col_id, keep="first")
    )

    # ✅ Sin fecha → dejar uno cualquiera
    df_sin_fecha = (
        df_sin_fecha
        .drop_duplicates(subset=col_id, keep="first")
    )

    # Unir resultados
    df_final = pd.concat([df_con_fecha, df_sin_fecha], ignore_index=True)

    # ✅ Eliminar columna auxiliar
    df_final.drop(columns=[aux_col], inplace=True)

    return df_final
