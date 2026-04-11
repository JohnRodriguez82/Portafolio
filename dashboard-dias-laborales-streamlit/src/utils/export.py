from io import BytesIO
import pandas as pd


def _sanitize_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evita que Excel interprete texto como fórmulas.
    Escapa celdas que empiezan con = + - @
    """
    df = df.copy()

    for col in df.select_dtypes(include=["string", "object"]).columns:
        df[col] = df[col].apply(
            lambda x: f"'{x}" if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x
        )

    return df

def dataframe_to_excel_bytes(
    df: pd.DataFrame,
    sheet_name: str = "Resultados",
) -> bytes:
    """
    Convierte un DataFrame en Excel (bytes) de forma segura.
    """
    output = BytesIO()

    df_safe = _sanitize_for_excel(df)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_safe.to_excel(writer, index=False, sheet_name=sheet_name)

    return output.getvalue()
