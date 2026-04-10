import pandas as pd
import numpy as np
import holidays

def obtener_festivos(pais="CO"):
    co = holidays.CountryHoliday(pais)
    return np.array(list(co.keys()), dtype="datetime64[D]")

def limpiar_fechas(col):
    col = col.astype("string").str.strip()
    col = col.replace({
        "": np.nan, "NA": np.nan, "nan": np.nan,
        "--": np.nan, "0": np.nan
    })

    es_num = col.str.match(r"^\d+(\.0)?$", na=False)

    fechas_excel = pd.to_datetime(
        pd.to_numeric(col.where(es_num), errors="coerce"),
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    )

    fecha = pd.to_datetime(col, dayfirst=True, errors="coerce")
    fecha.loc[es_num] = fechas_excel.loc[es_num]

    return fecha
