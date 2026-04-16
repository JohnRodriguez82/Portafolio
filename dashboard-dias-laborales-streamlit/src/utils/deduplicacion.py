import pandas as pd


def eliminar_duplicados(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Elimina registros duplicados dejando EXACTAMENTE UNO por identificador.

    Prioridad:
    1. Registro con fecha válida
    2. Fecha más reciente
    3. Si ninguno tiene fecha, deja uno cualquiera

    NO modifica columnas originales del DataFrame.
    """

    if not config.get("aplicar_deduplicacion"):
        return df

    col_id = config.get("columna_duplicados")
    col_fecha = config.get("columna_fecha_dedup")

    if not col_id or not col_fecha:
        return df

    df = df.copy()

    # ✅ Columna auxiliar SOLO para deduplicación
    aux_fecha = "__fecha_dedup_aux__"

    df[aux_fecha] = pd.to_datetime(
        df[col_fecha],
        errors="coerce",
        dayfirst=True
    )

    # ✅ Bandera: tiene fecha válida
    df["__tiene_fecha__"] = df[aux_fecha].notna()

    # ✅ ORDEN CLAVE:
    # 1. Primero los que tienen fecha
    # 2. Luego la fecha más reciente
    df = df.sort_values(
        by=["__tiene_fecha__", aux_fecha],
        ascending=[False, False]
    )

    # ✅ Ahora SÍ: un solo registro por ID
    df = df.drop_duplicates(subset=col_id, keep="first")

    # ✅ Limpiar columnas auxiliares
    df = df.drop(columns=["__tiene_fecha__", aux_fecha])

    return df
