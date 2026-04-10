import pandas as pd
import numpy as np
from src.utils.dates import limpiar_fechas

def test_limpieza_fecha_texto_valida():
    col = pd.Series(["01/04/2024"])
    result = limpiar_fechas(col)
    assert result.iloc[0] == pd.Timestamp("2024-04-01")

def test_limpieza_fecha_vacia():
    col = pd.Series(["", "NA", None])
    result = limpiar_fechas(col)
    assert result.isna().all()

def test_limpieza_fecha_excel_serial():
    # 45292 = 2024-01-01 en Excel
    col = pd.Series(["45292"])
    result = limpiar_fechas(col)
    assert result.iloc[0] == pd.Timestamp("2024-01-01")

def test_limpieza_fecha_invalida():
    col = pd.Series(["fecha random"])
    result = limpiar_fechas(col)
    assert pd.isna(result.iloc[0])
