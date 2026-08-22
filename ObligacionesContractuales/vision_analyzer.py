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
            api_key=key
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

    if resultado:
        resultado = resultado[0].upper() + resultado[1:]

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

    La IA recibe tres elementos:

    1. La imagen (optimizada: redimensionada y comprimida).
    2. La obligacion contractual.
    3. El contexto escrito por el usuario.
    """

    key = (
        _limpiar_key(api_key)
        or
        os.environ.get(
            'GEMINI_API_KEY'
        )
    )

    if not key:

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
            api_key=key
        )

        # --------------------------------------------------------
        # OPTIMIZAR IMAGEN ANTES DE ENVIARLA A GEMINI
        # --------------------------------------------------------

        imagen_optimizada = optimizar_imagen_para_ia(
            image_path,
            max_width=1024,
            quality=85
        )

        image_bytes = imagen_optimizada.read()

        mime = 'image/jpeg'

        # --------------------------------------------------------
        # Restaurar puntero del archivo original para que
        # EvidenciaService pueda guardarlo despues.
        # --------------------------------------------------------

        try:

            if hasattr(
                image_path,
                'stream'
            ) and image_path.stream:

                image_path.stream.seek(0)

            elif hasattr(
                image_path,
                'seek'
            ):

                image_path.seek(0)

        except Exception as exc:

            print(
                '[VisionAnalyzer] '
                'No fue posible restaurar el puntero '
                f'del archivo original: {exc}'
            )

        # ----------------------------------------------------
        # Contexto
        # ----------------------------------------------------

        contexto = (
            contexto_obligacion
            or
            'No se proporciono la descripcion de la obligacion.'
        )

        anuncio = (
            anuncio_usuario
            or
            'No se proporciono contexto adicional.'
        )

        # ----------------------------------------------------
        # Prompt contractual
        # ----------------------------------------------------

        prompt = f"""
Eres un redactor de informes de ejecucion contractual
para entidades publicas.

Analiza la imagen adjunta y redacta UN PARRAFO
profesional que describa la actividad contractual
realizada.

OBLIGACION CONTRACTUAL:
{contexto}

CONTEXTO DEL USUARIO:
{anuncio}

INSTRUCCIONES:

1. Usa el contexto del usuario como BASE, pero
   ENRIQUECELO con lo que ves en la imagen.

2. Describe los elementos funcionales o tecnicos
   visibles: formularios, campos, modulos,
   mockups, tablas, interfaces, configuraciones,
   esquemas, documentos, etc.

3. Relaciona la actividad con la obligacion
   contractual.

4. Escribe UN SOLO PARRAFO de 4 a 6 oraciones.

5. NO digas "en la imagen", "se observa",
   "la imagen muestra", "fotografia",
   "captura de pantalla".

6. NO inventes datos, cantidades, nombres,
   fechas, porcentajes ni reuniones.

7. Usa lenguaje formal y tecnico.

8. Entrega SOLO el parrafo, sin titulos ni listas.
"""

        response = client.models.generate_content(
            model=modelo,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512
            )
        )

        raw_text = response.text.strip() if response.text else None

        print(f'[VisionAnalyzer] Modelo: {modelo}')
        print(f'[VisionAnalyzer] Raw response: {repr(raw_text)[:300]}')

        if raw_text:
            descripcion = _limpiar_texto(raw_text)
            print(f'[VisionAnalyzer] Limpio: {repr(descripcion)[:300]}')
            if not descripcion:
                print('[VisionAnalyzer] WARNING: _limpiar_texto dejo el texto vacio. Usando raw.')
                descripcion = raw_text
        else:
            descripcion = None
            print('[VisionAnalyzer] Gemini retorno texto vacio o None.')

        return descripcion

    except Exception as e:

        print(
            f'[VisionAnalyzer] '
            f'Error con modelo {modelo}: {e}'
        )

        return None

    finally:

        # --------------------------------------------------------
        # MUY IMPORTANTE:
        # devolver el archivo al inicio para que posteriormente
        # EvidenciaService pueda guardarlo correctamente.
        # --------------------------------------------------------

        try:

            if hasattr(
                image_path,
                'stream'
            ) and image_path.stream:

                image_path.stream.seek(0)

            elif hasattr(
                image_path,
                'seek'
            ):

                image_path.seek(0)

        except Exception as exc:

            print(
                '[VisionAnalyzer] '
                'No fue posible restaurar el puntero '
                f'del archivo: {exc}'
            )


# ============================================================
# CONSOLIDAR ACTIVIDADES
# ============================================================

def consolidar_textos_ejecutivo(
    descripciones,
    api_key=None,
    obligacion=None,
    periodo=None
):
    """
    Consolida las actividades de un reporte mensual
    en un unico parrafo ejecutivo.

    La obligacion contractual se utiliza como contexto
    para que el resumen explique la relacion entre las
    actividades y el cumplimiento contractual.
    """

    if not descripciones:

        return (
            'Durante el periodo reportado no se '
            'registraron actividades.'
        )

    # --------------------------------------------------------
    # Limpiar descripciones
    # --------------------------------------------------------

    descripciones_limpias = []

    for descripcion in descripciones:

        if not descripcion:

            continue

        texto = _limpiar_texto(
            descripcion
        )

        if texto:

            descripciones_limpias.append(
                texto
            )

    if not descripciones_limpias:

        return (
            'Durante el periodo reportado no se '
            'registraron actividades.'
        )

    # --------------------------------------------------------
    # Una sola actividad
    # --------------------------------------------------------

    if len(descripciones_limpias) == 1:

        return descripciones_limpias[0]

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    key = (
        _limpiar_key(api_key)
        or
        os.environ.get(
            'GEMINI_API_KEY'
        )
    )

    if not key:

        return _consolidar_manual(
            descripciones_limpias
        )

    modelo = _encontrar_modelo_funcional(
        key
    )

    if not modelo:

        return _consolidar_manual(
            descripciones_limpias
        )

    try:

        client = genai.Client(
            api_key=key
        )

        contexto_obligacion = (
            obligacion
            or
            'No especificada.'
        )

        contexto_periodo = (
            periodo
            or
            'Periodo reportado.'
        )

        actividades = "\n".join(
            [
                f'{i + 1}. {texto}'
                for i, texto
                in enumerate(
                    descripciones_limpias
                )
            ]
        )

        prompt = f"""
Eres un redactor especializado en informes
de ejecucion contractual para entidades publicas.

Debes consolidar las actividades realizadas durante
un periodo en UN SOLO PARRAFO EJECUTIVO.

OBLIGACION CONTRACTUAL:

{contexto_obligacion}

PERIODO:

{contexto_periodo}

ACTIVIDADES REGISTRADAS:

{actividades}

OBJETIVO:

Redacta un unico parrafo que explique de manera
clara, profesional y coherente las principales
actividades desarrolladas y su contribucion al
cumplimiento de la obligacion contractual.

REGLAS:

1. Escribe UN SOLO PARRAFO.

2. Utiliza lenguaje formal, tecnico y administrativo.

3. Integra las actividades en una narrativa coherente.

4. NO enumeres las actividades.

5. Evita repetir las mismas palabras.

6. Agrupa actividades relacionadas.

7. Utiliza conectores naturales:
   "Durante el periodo...",
   "Asimismo...",
   "De manera complementaria...",
   "Posteriormente...",
   "Como resultado...",
   "Finalmente...".

8. Prioriza:
   - acciones realizadas;
   - gestiones adelantadas;
   - avances;
   - productos;
   - resultados;
   - seguimiento;
   - contribucion contractual.

9. NO inventes informacion.

10. NO inventes cantidades, porcentajes,
    fechas, resultados, nombres, reuniones,
    entregables o aprobaciones.

11. NO menciones:
    imagenes,
    fotografias,
    capturas,
    pantallazos,
    evidencias,
    archivos adjuntos.

12. NO utilices:
    "se observa",
    "se evidencia",
    "la imagen muestra",
    "como se ve".

13. Evita frases vacias como:
    "se realizaron las actividades correspondientes",
    cuando no aporten informacion concreta.

14. No exageres el cumplimiento.

15. Si la informacion demuestra solamente un avance,
    revision, gestion o seguimiento, utiliza ese
    nivel de certeza.

16. El texto debe parecer redactado por un profesional
    responsable de un informe contractual.

17. Cuando exista informacion suficiente,
    procura una extension aproximada de 100 a 180 palabras.

18. Entrega unicamente el parrafo final.
"""

        response = client.models.generate_content(
            model=modelo,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512
            )
        )

        if response.text:

            resultado = _limpiar_texto(
                response.text
            )

            # ------------------------------------------------
            # Convertir saltos de linea en espacio para
            # garantizar un unico parrafo.
            # ------------------------------------------------

            resultado = re.sub(
                r'\s+',
                ' ',
                resultado
            ).strip()

            return resultado

    except Exception as e:

        print(
            '[VisionAnalyzer] '
            'Error al consolidar con Gemini: '
            f'{e}'
        )

    return _consolidar_manual(
        descripciones_limpias
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
