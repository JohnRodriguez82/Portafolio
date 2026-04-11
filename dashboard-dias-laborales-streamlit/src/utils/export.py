from io import BytesIO
import pandas as pd


def dataframe_to_excel_bytes(
    df: pd.DataFrame,
    sheet_name: str = "Resultados",
) -> bytes:
    """
    Convierte un DataFrame en un archivo Excel (bytes)
    listo para descargar o guardar.
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    return output.getvalue()
