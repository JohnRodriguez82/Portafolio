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