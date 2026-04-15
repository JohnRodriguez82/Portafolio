import pandas as pd


def aplicar_reglas_negocio(df, config):
    df = df.copy()

    def evaluar(row):
        seccion = row["SECCION"]
        estudio = row.get("ESTUDIO")
        dias = row["Dias_Laborales_num"]

        if pd.isna(dias):
            return 0

        # =========================
        # PASO 3: SLA específico por ESTUDIO (tiene prioridad)
        # =========================
        if (
            config.get("estudio_especial")
            and estudio == config.get("estudio_especial")
            and config.get("sla_estudio_especial") is not None
        ):
            return int(dias <= config["sla_estudio_especial"])

        # =========================
        # SLA generales por SECCION
        # =========================
        if seccion == "ESPECIMEN QUIRURGICO":
            return int(dias <= config["sla_quirurgico"])

        if seccion == "CITOLOGIA DE LIQUIDOS":
            return int(dias <= config["sla_citologia"])

        if seccion == "HEMATOPATOLOGIA":
            return int(dias <= config["sla_hematopatologia"])

        if seccion == "AUTOPSIA":
            return int(dias <= config["sla_autopsia"])

        return 0

    df["Dentro_Oportunidad"] = df.apply(evaluar, axis=1)
    return df
