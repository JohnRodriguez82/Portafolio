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

ef guardar_imagen_evidencia(
    imagen_temporal,
    reporte_id,
    nombre_imagen
):
    """
    Mueve una imagen temporal al almacenamiento
    definitivo de evidencias.

    Retorna:
        str: ruta definitiva.
    """

    if not imagen_temporal:
        return ''

    final_name = secure_filename(
        (
            f'evidencia_'
            f'{reporte_id}_'
            f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_'
            f'{nombre_imagen}'
        )
    )

    final_path = os.path.join(
        current_app.config[
            'UPLOAD_FOLDER'
        ],
        final_name
    )

    os.rename(
        imagen_temporal,
        final_path
    )

    return final_path
