def evaluar_oportunidad(seccion, dias, dias_autopsia=None):
    if seccion == "ESPECIMEN QUIRURGICO":
        return dias <= 10
    if seccion == "CITOLOGIA DE LIQUIDOS":
        return dias <= 6
    if seccion == "HEMATOPATOLOGIA":
        return dias <= 6
    if seccion == "AUTOPSIA":
        return dias_autopsia <= 30
    return False
