"""
Servicio para procesamiento de evidencias.

Responsabilidades:
- Buscar imágenes cargadas.
- Mover imágenes al almacenamiento definitivo.
- Analizar imágenes con IA.
- Crear evidencias.
"""

import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from models import Evidencia
from vision_analyzer import analizar_imagen

def obtener_imagen_temporal(
    nombre_imagen,
    imagenes_disponibles
):
    """
    Busca una imagen por nombre y la consume
    del diccionario de imágenes disponibles.

    Retorna:
        str | None: ruta temporal de la imagen.
    """

    if not nombre_imagen:
        return None

    if nombre_imagen in imagenes_disponibles:

        return imagenes_disponibles.pop(
            nombre_imagen
        )

    safe_name = secure_filename(
        nombre_imagen
    )

    if safe_name in imagenes_disponibles:

        return imagenes_disponibles.pop(
            safe_name
        )

    return None
