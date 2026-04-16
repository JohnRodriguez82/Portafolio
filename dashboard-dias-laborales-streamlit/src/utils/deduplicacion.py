import pandas as pd


def eliminar_duplicados(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Elimina registros duplicados conservando:
    - el más reciente según una columna auxiliar de fecha
    - sin modificar las columnas originales de fecha
    """

    if not config.get("aplicar_deduplicacion"):
        return df

    col_id = config.get("columna_duplicados")
    col_fecha = config.get("columna_fecha_dedup")

    if not col_id or not col_fecha:
        return df

    df = df.copy()

    # ✅ Crear columna auxiliar SOLO para deduplicación
    col_aux = "__fecha_dedup_aux__"

    df[col_aux] = pd.to_datetime(
        df[col_fecha],
        errors="coerce",
        dayfirst=True  # 🔑 MUY IMPORTANTE para tu formato
    )

    # Separar con y sin fecha válida (auxiliar)
    df_con_fecha = df[df[col_aux].notna()]
    df_sin_fecha = df[df[col_aux].isna()]

    # ✅ Con fecha válida → conservar el más reciente
    df_con_fecha = (
        df_con_fecha
        .sort_values(by=col_aux, ascending=False)
        .drop_duplicates(subset=col_id, keep="first")
    )

    # ✅ Sin fecha válida → dejar uno cualquiera
    df_sin_fecha = df_sin_fecha.drop_duplicates(subset=col_id, keep="first")

    # Unir resultados
    df_final = pd.concat([df_con_fecha, df_sin_fecha], ignore_index=True)

    # ✅ Eliminar columna auxiliar (NO contaminar cálculo)
    df_final = df_final.drop(columns=[col_aux])

    return df_final
