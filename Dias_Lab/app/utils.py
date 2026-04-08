import pandas as pd
import numpy as np
import holidays

def obtener_festivos(pais="CO"):
    co = holidays.CountryHoliday(pais)
    return np.array(list(co.keys()), dtype="datetime64[D]")

def limpiar_fechas(col):
    col = col.astype("string").str.strip()

    col = col.replace({
        "": np.nan, "NA": np.nan, "N/A": np.nan,
        "None": np.nan, "nan": np.nan, "--": np.nan
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

def calcular_busdays_seguro(inicio, fin, festivos, weekmask):
    ini = inicio.copy()
    fin = fin.copy()

    mask_ini = pd.isna(ini)
    mask_fin = pd.isna(fin)

    ini[mask_ini] = np.datetime64("1970-01-01")
    fin[mask_fin] = np.datetime64("1970-01-01")

    dias = np.busday_count(
        ini,
        fin + np.timedelta64(1, "D"),
        holidays=festivos,
        weekmask=weekmask
    ).astype(object)

    dias[mask_ini] = None
    dias[mask_fin] = "Sin dato"

    return dias
