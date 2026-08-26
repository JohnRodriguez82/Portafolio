"""
Analizador de imagenes con Google Gemini Vision API.

Genera descripciones automaticas orientadas a la
actividad contractual realizada y consolida las
actividades de un periodo en un texto ejecutivo.

Utiliza la SDK oficial google-genai.
"""

import os
import re
import io
import mimetypes

from PIL import Image

from google import genai
from google.genai import types
import google.genai as genai_module

# ============================================================
# MODELOS GEMINI
# ============================================================

MODELOS_GEMINI = [
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-pro-vision',
]


# ============================================================
# UTILIDADES
# ============================================================

def _limpiar_key(api_key):
    """
    Limpia espacios y saltos de linea de la API key.
    """

    if not api_key:
        return None

    return (
        api_key
        .strip()
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
    )


def _encontrar_modelo_funcional(key):
    """
    Encuentra el primer modelo de Gemini que funcione
    para generacion de contenido.

    Utiliza la SDK google-genai.
    """

    try:

        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=15000)
        )

        # ----------------------------------------------------
        # Modelos preferidos
        # ----------------------------------------------------

        for modelo_nombre in MODELOS_GEMINI:

            try:

                client.models.generate_content(
                    model=modelo_nombre,
                    contents="Hola"
                )

                return modelo_nombre

            except Exception:

                continue

        # ----------------------------------------------------
        # Cualquier modelo compatible
        # ----------------------------------------------------

        for m in client.models.list():

            nombre = (
                getattr(
                    m,
                    'name',
                    str(m)
                )
                .replace(
                    "models/",
                    ""
                )
            )

            if (
                'gemini'
                in nombre.lower()
            ):

                try:

                    client.models.generate_content(
                        model=nombre,
                        contents="Hola"
                    )

                    return nombre

                except Exception:

                    continue

        return None

    except Exception:

        return None


def _limpiar_texto(texto):
    """
    Limpia referencias innecesarias a imagenes,
    fotografias y evidencias visuales.

    Tambien normaliza espacios y puntuacion.
    """

    if not texto:
        return ''

    resultado = str(
        texto
    ).strip()

    frases_a_eliminar = [

        r'[Ee]n la imagen[^.]*\.',
        r'[Ss]e observa[^.]*\.',
        r'[Ss]e visualiza[^.]*\.',
        r'[Ll]a imagen muestra[^.]*\.',
        r'[Cc]omo se ve en[^.]*\.',
        r'[Pp]antallazo de[^.]*\.',
        r'[Ff]otografia de[^.]*\.',
        r'[Cc]aptura de[^.]*\.',
        r'[Ss]creenshot de[^.]*\.',
        r'[Dd]ocumento que muestra[^.]*\.',
        r'[Aa]rchivo que contiene[^.]*\.',
        r'[Ee]videncia fotografica[^.]*\.',
        r'[Ss]oporte grafico[^.]*\.',
        r'[Ll]a evidencia adjunta[^.]*\.',
        r'[Ss]e adjunta[^.]*\.',
        r'[Ll]a imagen anexa[^.]*\.',
        r'[Ee]l soporte fotografico[^.]*\.',
        r'[Ss]e presenta la correspondiente evidencia[^.]*\.',
        r'[Ee]sta accion se documenta con la evidencia[^.]*\.',
        r'[Ll]a presente evidencia certifica[^.]*\.',
        r'[Ss]e adjunta evidencia documental[^.]*\.',
        r'[Ee]videnciado en la imagen[^,]*,\s*',
        r'[Dd]onde se observa[^.]*\.',
        r'[Pp]antallazo de[^,]*,\s*',
        r'[Ff]otografia de[^,]*,\s*',
        r'[Ss]e evidencia[^.]*\.',
        r'[Cc]omo se evidencia[^.]*\.',
        r'[Ll]a presente imagen[^.]*\.',
        r'[Ee]n la presente imagen[^.]*\.',
        r'[Ss]e aprecia[^.]*\.',
        r'[Ll]a imagen evidencia[^.]*\.',
        r'[Ee]n la fotografia[^.]*\.',
        r'[Ss]e puede observar[^.]*\.',
        r'[Cc]omo se aprecia[^.]*\.',
    ]

    for patron in frases_a_eliminar:

        resultado = re.sub(
            patron,
            ' ',
            resultado
        )

    # --------------------------------------------------------
    # Eliminar markdown accidental
    # --------------------------------------------------------

    resultado = re.sub(
        r'^\s*[-*•]\s*',
        '',
        resultado
    )

    resultado = re.sub(
        r'\*\*',
        '',
        resultado
    )

    resultado = re.sub(
        r'__',
        '',
        resultado
    )

    # --------------------------------------------------------
    # Convertir saltos de linea en espacios (parrafo unico)
    # --------------------------------------------------------

    resultado = re.sub(
        r'\n+',
        ' ',
        resultado
    )

    # --------------------------------------------------------
    # Normalizar espacios
    # --------------------------------------------------------

    resultado = re.sub(
        r'\s+',
        ' ',
        resultado
    )

    resultado = re.sub(
        r'\.\.',
        '.',
        resultado
    )

    resultado = re.sub(
        r'\.\s*\.',
        '.',
        resultado
    )

    resultado = re.sub(
        r',\s*\.',
        '.',
        resultado
    )

    resultado = resultado.strip()

    if (
        resultado
        and
        not resultado.endswith(('.', '!', '?'))
    ):

        resultado += '.'

    # --------------------------------------------------------
    # Capitalizar primera letra
    # --------------------------------------------------------

    # Capitalizar primera letra de CADA oracion

    def _cap(match):
        return match.group(1) + match.group(2).upper()
    resultado = re.sub(r'(^|[.!?]\s+)([a-záéíóúñ])', _cap, resultado)

    return resultado

# ============================================================
# OPTIMIZAR IMAGEN PARA IA
# ============================================================

def optimizar_imagen_para_ia(
    file_obj,
    max_width=1024,
    quality=85
):
    """
    Redimensiona y comprime una imagen antes de enviarla
    a la API de Gemini.

    Args:
        file_obj:
            Objeto de archivo con metodo .read() o ruta str.

        max_width:
            Ancho maximo en pixeles. Por defecto 1024.

        quality:
            Calidad JPEG de 1 a 100. Por defecto 85.

    Returns:
        io.BytesIO:
            Stream de bytes con la imagen optimizada.
    """

    # --------------------------------------------------------
    # Leer bytes originales
    # --------------------------------------------------------

    if hasattr(file_obj, 'read'):

        if hasattr(file_obj, 'stream') and file_obj.stream:
            file_obj.stream.seek(0)
            raw_bytes = file_obj.stream.read()
        else:
            file_obj.seek(0)
            raw_bytes = file_obj.read()

    elif isinstance(file_obj, (str, os.PathLike)):

        ruta = str(file_obj)

        if os.path.isfile(ruta):

            with open(ruta, 'rb') as f:
                raw_bytes = f.read()

        else:

            raise ValueError(
                f'No se encontro la imagen: {ruta}'
            )

    else:

        raise ValueError(
            'No se pudo leer la imagen para optimizar.'
        )

    # --------------------------------------------------------
    # Abrir con PIL
    # --------------------------------------------------------

    try:

        img = Image.open(io.BytesIO(raw_bytes))

    except Exception as exc:

        print(
            f'[VisionAnalyzer] '
            f'No se pudo abrir la imagen con PIL: {exc}. '
            f'Usando imagen original.'
        )

        buffer = io.BytesIO(raw_bytes)
        buffer.seek(0)
        return buffer

    # --------------------------------------------------------
    # Convertir a RGB si es necesario (PNG con transparencia,
    # modo P, etc.)
    # --------------------------------------------------------

    if img.mode in ('RGBA', 'P', 'LA'):

        img = img.convert('RGB')

    elif img.mode != 'RGB':

        img = img.convert('RGB')

    # --------------------------------------------------------
    # Redimensionar si excede el ancho maximo
    # --------------------------------------------------------

    if img.width > max_width:

        ratio = max_width / img.width
        new_height = int(img.height * ratio)

        img = img.resize(
            (max_width, new_height),
            Image.LANCZOS
        )

    # --------------------------------------------------------
    # Guardar en buffer como JPEG optimizado
    # --------------------------------------------------------

    buffer = io.BytesIO()

    img.save(
        buffer,
        format='JPEG',
        quality=quality,
        optimize=True
    )

    buffer.seek(0)

    # --------------------------------------------------------
    # Restaurar puntero del archivo original
    # --------------------------------------------------------

    try:

        if hasattr(file_obj, 'stream') and file_obj.stream:
            file_obj.stream.seek(0)
        elif hasattr(file_obj, 'seek'):
            file_obj.seek(0)

    except Exception:

        pass

    return buffer


# ============================================================
# VERIFICAR API KEY
# ============================================================

def verificar_api_key(api_key):
    """
    Verifica si una API key de Gemini es valida.

    Retorna:

        (bool, str)

    donde str corresponde al modelo disponible
    o al mensaje de error.
    """

    key = _limpiar_key(
        api_key
    )

    if not key:

        return (
            False,
            "La API key esta vacia."
        )

    if len(key) < 10:

        return (
            False,
            "La API key parece muy corta."
        )

    modelo = _encontrar_modelo_funcional(
        key
    )

    if modelo:

        return (
            True,
            modelo
        )

    return (
        False,
        (
            "No se encontro ningun modelo funcional. "
            "Verifique que la API "
            "'Generative Language API' "
            "este habilitada en su proyecto de Google Cloud."
        )
    )


# ============================================================
# ANALIZAR IMAGEN
# ============================================================

def analizar_imagen(
    image_path,
    api_key=None,
    contexto_obligacion=None,
    anuncio_usuario=None
):
    """
    Analiza una imagen mediante Gemini.

    Gemini NO redacta aquí el párrafo contractual final.

    Su función es analizar técnicamente la evidencia y
    entregar información adicional que posteriormente será
    utilizada por Evidencia/modelos.py para construir:

        descripcion_actividad

    La respuesta de esta función se guarda como:

        descripcion_visual_ia
    """

    key = (
        _limpiar_key(api_key)
        or
        os.environ.get(
            'GEMINI_API_KEY'
        )
    )

    if not key:

        print(
            '[VisionAnalyzer] '
            'No existe API key de Gemini.'
        )

        return None

    modelo = _encontrar_modelo_funcional(
        key
    )

    if not modelo:

        print(
            '[VisionAnalyzer] '
            'No hay modelos funcionales disponibles.'
        )

        return None

    try:

        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=120000
            )
        )

        # ----------------------------------------------------
        # OPTIMIZAR IMAGEN
        # ----------------------------------------------------

        imagen_optimizada = (
            optimizar_imagen_para_ia(
                image_path,
                max_width=1024,
                quality=85
            )
        )

        image_bytes = (
            imagen_optimizada.read()
        )

        mime = 'image/jpeg'

        # ----------------------------------------------------
        # RESTAURAR PUNTERO
        # ----------------------------------------------------

        try:

            if (
                hasattr(
                    image_path,
                    'stream'
                )
                and image_path.stream
            ):

                image_path.stream.seek(0)

            elif hasattr(
                image_path,
                'seek'
            ):

                image_path.seek(0)

        except Exception as exc:

            print(
                '[VisionAnalyzer] '
                'No fue posible restaurar el '
                f'puntero: {exc}'
            )

        # ----------------------------------------------------
        # CONTEXTO
        # ----------------------------------------------------

        contexto = (
            str(
                contexto_obligacion
                or ''
            )
            .strip()
        )

        anuncio = (
            str(
                anuncio_usuario
                or ''
            )
            .strip()
        )

        if not contexto:

            contexto = (
                'No se proporcionó la '
                'descripción de la obligación.'
            )

        if not anuncio:

            anuncio = (
                'No se proporcionó '
                'contexto adicional.'
            )

        # ----------------------------------------------------
        # PROMPT DE ANÁLISIS VISUAL
        # ----------------------------------------------------

        prompt = f"""
Eres un analista técnico especializado en evidencias
para informes de ejecución contractual de entidades
públicas.

Tu función es analizar la evidencia suministrada y
proporcionar información técnica adicional que pueda
utilizarse posteriormente para redactar el párrafo
contractual de la actividad.

OBLIGACIÓN CONTRACTUAL:

{contexto}

ANUNCIO O CONTEXTO PROPORCIONADO POR EL USUARIO:

{anuncio}

ANALIZA LOS ELEMENTOS QUE PUEDAN IDENTIFICARSE CON
SEGURIDAD Y DESCRIBE, CUANDO APLIQUE:

- funcionalidades;
- módulos;
- formularios;
- campos;
- botones;
- tablas;
- interfaces;
- configuraciones;
- componentes técnicos;
- documentos;
- información textual legible;
- avances funcionales;
- relaciones entre los elementos identificados.

REGLAS:

1. Utiliza el anuncio del usuario como contexto de
   interpretación.

2. Aporta información adicional obtenida del análisis
   visual.

3. No repitas innecesariamente el anuncio.

4. No inventes información.

5. No inventes fechas, cantidades, porcentajes,
   nombres, reuniones, aprobaciones o resultados.

6. No afirmes que una actividad está terminada si la
   evidencia solamente permite identificar un avance.

7. No utilices expresiones como:
   "en la imagen",
   "se observa",
   "la imagen muestra",
   "captura de pantalla",
   "fotografía",
   "evidencia fotográfica".

8. Utiliza lenguaje técnico y profesional.

9. Escribe entre 3 y 5 oraciones sustanciales.

10. Entrega únicamente el texto descriptivo.

11. No escribas "IA vio:".

12. Este texto será utilizado posteriormente para
    construir el párrafo profesional de la actividad.
"""

        # ----------------------------------------------------
        # LLAMADA A GEMINI
        # ----------------------------------------------------

        response = (
            client.models.generate_content(
                model=modelo,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=512
                )
            )
        )

        raw_text = (
            response.text.strip()
            if response.text
            else None
        )

        print(
            f'[VisionAnalyzer] Modelo: {modelo}'
        )

        print(
            '[VisionAnalyzer] Raw response: '
            f'{repr(raw_text)[:500]}'
        )

        if not raw_text:

            print(
                '[VisionAnalyzer] '
                'Gemini retornó texto vacío.'
            )

            return None

        descripcion = _limpiar_texto(
            raw_text
        )

        if not descripcion:

            descripcion = (
                raw_text.strip()
            )

        print(
            '[VisionAnalyzer] '
            'Descripción visual IA: '
            f'{repr(descripcion)[:500]}'
        )

        return descripcion

    except Exception as exc:

        print(
            '[VisionAnalyzer] '
            f'Error con modelo {modelo}: {exc}'
        )

        return None

    finally:

        # ----------------------------------------------------
        # RESTAURAR ARCHIVO
        # ----------------------------------------------------

        try:

            if (
                hasattr(
                    image_path,
                    'stream'
                )
                and image_path.stream
            ):

                image_path.stream.seek(0)

            elif hasattr(
                image_path,
                'seek'
            ):

                image_path.seek(0)

        except Exception as exc:

            print(
                '[VisionAnalyzer] '
                'No fue posible restaurar el '
                f'puntero: {exc}'
            )


# ============================================================
# CONSOLIDACION SIN IA
# ============================================================

def _consolidar_manual(
    descripciones
):
    """
    Consolida actividades sin utilizar IA.

    La salida es deterministica: no utiliza random,
    de modo que el mismo conjunto de actividades
    produce siempre el mismo resultado.
    """

    limpias = []

    for descripcion in descripciones:

        texto = _limpiar_texto(
            descripcion
        )

        if texto:

            limpias.append(
                texto
            )

    if not limpias:

        return (
            'Durante el periodo reportado no se '
            'registraron actividades.'
        )

    if len(limpias) == 1:

        return limpias[0]

    partes = []

    for indice, texto in enumerate(
        limpias
    ):

        texto = texto.strip()

        if not texto:

            continue

        # ----------------------------------------------------
        # Primera actividad
        # ----------------------------------------------------

        if indice == 0:

            prefijo = (
                'Durante el periodo reportado, '
            )

        # ----------------------------------------------------
        # Ultima actividad
        # ----------------------------------------------------

        elif indice == len(limpias) - 1:

            prefijo = (
                'Finalmente, '
            )

        # ----------------------------------------------------
        # Actividades intermedias
        # ----------------------------------------------------

        else:

            prefijo = (
                'Asimismo, '
            )

        if texto:

            texto = (
                texto[0].lower()
                + texto[1:]
            )

        partes.append(
            prefijo + texto
        )

    return _limpiar_texto(
        ' '.join(partes)
    )


# ============================================================
# ANALIZAR IMAGEN CON REINTENTOS
# ============================================================

def analizar_imagen_con_reintentos(
    image_path,
    api_key=None,
    contexto_obligacion=None,
    anuncio_usuario=None,
    max_reintentos=2,
    espera_segundos=3
):
    """
    Analiza una imagen con Gemini reintentando en caso
    de error temporal (rate limit, timeout, etc.).

    Args:
        image_path: Ruta o archivo de imagen.
        api_key: API key de Gemini.
        contexto_obligacion: Descripcion de la obligacion.
        anuncio_usuario: Contexto del usuario.
        max_reintentos: Numero de reintentos adicionales.
        espera_segundos: Tiempo de espera entre reintentos.

    Returns:
        str: Descripcion generada, o None si fallo todo.
    """
    import time

    ultimo_error = None

    for intento in range(max_reintentos + 1):

        try:

            resultado = analizar_imagen(
                image_path,
                api_key=api_key,
                contexto_obligacion=contexto_obligacion,
                anuncio_usuario=anuncio_usuario
            )

            if resultado:

                return resultado

            # Si retorno None pero no lanzo excepcion,
            # puede ser que Gemini no genero texto.
            # Reintentamos una vez mas.

            if intento < max_reintentos:

                time.sleep(espera_segundos)

        except Exception as e:

            ultimo_error = e

            print(
                f'[VisionAnalyzer] '
                f'Intento {intento + 1}/{max_reintentos + 1} '
                f'fallo: {e}'
            )

            if intento < max_reintentos:

                time.sleep(espera_segundos * (intento + 1))

    print(
        f'[VisionAnalyzer] '
        f'Todos los intentos fallaron. '
        f'Ultimo error: {ultimo_error}'
    )

    return None
