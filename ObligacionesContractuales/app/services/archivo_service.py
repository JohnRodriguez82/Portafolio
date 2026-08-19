"""
Servicio para gestión de archivos físicos.

Responsabilidades:
- Guardar archivos subidos.
- Generar nombres seguros.
- Buscar archivos por nombre.
- Mover archivos.
- Eliminar archivos temporales.
- Limpiar archivos no utilizados.

Este módulo NO contiene lógica de negocio.
"""

import os
import shutil

from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename


# ============================================================
# CONFIGURACIÓN
# ============================================================

EXTENSIONES_IMAGEN = {
    '.jpg',
    '.jpeg',
    '.png',
    '.gif',
    '.webp',
    '.bmp'
}


# ============================================================
# CARPETA DE UPLOADS
# ============================================================

def obtener_upload_folder():
    """
    Retorna la carpeta configurada para archivos.
    """

    folder = current_app.config.get(
        'UPLOAD_FOLDER'
    )

    if not folder:
        raise RuntimeError(
            'UPLOAD_FOLDER no está configurado.'
        )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# NOMBRE SEGURO
# ============================================================

def nombre_seguro(nombre):
    """
    Genera un nombre seguro para el sistema de archivos.
    """

    return secure_filename(
        nombre or ''
    )


# ============================================================
# GUARDAR ARCHIVO
# ============================================================

def guardar_archivo(
    archivo,
    nombre=None,
    carpeta=None
):
    """
    Guarda un archivo recibido desde Flask.

    Retorna:
        str: ruta absoluta del archivo guardado.
    """

    if not archivo:
        raise ValueError(
            'No se recibió ningún archivo.'
        )

    if carpeta is None:
        carpeta = obtener_upload_folder()

    os.makedirs(
        carpeta,
        exist_ok=True
    )

    if nombre:
        filename = nombre_seguro(
            nombre
        )
    else:
        filename = nombre_seguro(
            archivo.filename
        )

    if not filename:
        raise ValueError(
            'El archivo no tiene un nombre válido.'
        )

    ruta = os.path.join(
        carpeta,
        filename
    )

    archivo.save(
        ruta
    )

    return ruta


# ============================================================
# BUSCAR ARCHIVO
# ============================================================

def buscar_archivo(
    nombre,
    archivos
):
    """
    Busca un archivo por nombre exacto.

    También intenta encontrarlo mediante
    nombre seguro.

    Args:
        nombre: nombre buscado.
        archivos: diccionario nombre -> ruta.

    Retorna:
        ruta o None.
    """

    if not nombre:
        return None

    if nombre in archivos:
        return archivos.pop(
            nombre
        )

    nombre_seguro_archivo = nombre_seguro(
        nombre
    )

    if (
        nombre_seguro_archivo
        in archivos
    ):
        return archivos.pop(
            nombre_seguro_archivo
        )

    return None


# ============================================================
# MOVER ARCHIVO
# ============================================================

def mover_archivo(
    origen,
    destino
):
    """
    Mueve un archivo a una nueva ubicación.
    """

    if not origen:
        raise ValueError(
            'Ruta de origen vacía.'
        )

    if not os.path.exists(
        origen
    ):
        raise FileNotFoundError(
            origen
        )

    carpeta_destino = os.path.dirname(
        destino
    )

    if carpeta_destino:
        os.makedirs(
            carpeta_destino,
            exist_ok=True
        )

    shutil.move(
        origen,
        destino
    )

    return destino


# ============================================================
# GENERAR NOMBRE DE EVIDENCIA
# ============================================================

def generar_nombre_evidencia(
    reporte_id,
    nombre_original
):
    """
    Genera un nombre seguro para una evidencia.
    """

    nombre = nombre_seguro(
        nombre_original
    )

    if not nombre:
        raise ValueError(
            'Nombre de imagen inválido.'
        )

    return (
        f'evidencia_'
        f'{reporte_id}_'
        f'{nombre}'
    )


# ============================================================
# RUTA DE EVIDENCIA
# ============================================================

def obtener_ruta_evidencia(
    reporte_id,
    nombre_original
):
    """
    Construye la ruta definitiva de una evidencia.
    """

    folder = obtener_upload_folder()

    filename = generar_nombre_evidencia(
        reporte_id,
        nombre_original
    )

    return os.path.join(
        folder,
        filename
    )


# ============================================================
# ELIMINAR ARCHIVO
# ============================================================

def eliminar_archivo(
    ruta
):
    """
    Elimina un archivo si existe.
    """

    if not ruta:
        return

    try:

        if os.path.exists(
            ruta
        ):
            os.remove(
                ruta
            )

    except OSError as exc:

        current_app.logger.warning(
            'No se pudo eliminar archivo %s: %s',
            ruta,
            exc
        )


# ============================================================
# LIMPIAR ARCHIVOS
# ============================================================

def limpiar_archivos(
    archivos
):
    """
    Elimina una colección de archivos.
    """

    for archivo in archivos or []:

        eliminar_archivo(
            archivo
        )


# ============================================================
# VALIDAR IMAGEN
# ============================================================

def es_imagen(
    nombre
):
    """
    Determina si un archivo tiene extensión de imagen.
    """

    if not nombre:
        return False

    extension = Path(
        nombre
    ).suffix.lower()

    return extension in EXTENSIONES_IMAGEN
