import pandas as pd
from src.data.processing import process_dataframe

def test_procesamiento_basico():
    df = pd.DataFrame({
        "inicio": ["01/01/2024", "02/01/2024"],
        "fin": ["03/01/2024", "05/01/2024"]
    })

    config = {
        "col_inicio": "inicio",
        "col_fin": "fin",
        "excluir_festivos": False,
        "weekmask": "Mon Tue Wed Thu Fri"
    }

    df_out, duracion = process_dataframe(df, config)

    assert "fecha_inicio" in df_out.columns
    assert "fecha_fin" in df_out.columns
    assert "Dias_Laborales" in df_out.columns
    assert duracion >= 0
