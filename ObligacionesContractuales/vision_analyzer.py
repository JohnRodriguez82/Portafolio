"""
Analizador de imagenes con Google Gemini Vision API.

Genera descripciones automaticas orientadas a la
actividad contractual realizada y consolida las
actividades de un periodo en un texto ejecutivo.

Utiliza la SDK oficial google-genai.
"""

import os
import re
import mimetypes

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

    resultado = resultado.strip()

    if (
        resultado
        and
        not resultado.endswith(('.', '!', '?'))
    ):

        resultado += '.'

    return resultado


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

    1. La imagen.
    2. La obligacion contractual.
    3. El contexto escrito por el usuario.

    Esto permite que la descripcion no sea solamente
    una descripcion visual, sino una interpretacion
    orientada a la actividad contractual.
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
        # Asegurar que la lectura comienza desde el inicio
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # Leer imagen como bytes
        # --------------------------------------------------------

        if hasattr(
            image_path,
            'read'
        ):

            image_bytes = image_path.read()

            mime = (
                getattr(
                    image_path,
                    'content_type',
                    None
                )
                or
                getattr(
                    image_path,
                    'mimetype',
                    None
                )
                or
                'image/jpeg'
            )

            # ------------------------------------------------
            # Restaurar puntero para EvidenciaService
            # ------------------------------------------------

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

        else:

            with open(
                image_path,
                'rb'
            ) as f:

                image_bytes = f.read()

            mime, _ = mimetypes.guess_type(
                str(image_path)
            )

            if not mime:

                mime = 'image/jpeg'

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
Eres un profesional encargado de redactar
informes de ejecucion contractual para una
entidad publica.

Debes analizar una actividad utilizando:

1. La informacion contenida en la imagen.
2. La obligacion contractual.
3. El contexto proporcionado por el usuario.

OBLIGACION CONTRACTUAL:

{contexto}

CONTEXTO PROPORCIONADO POR EL USUARIO:

{anuncio}

OBJETIVO:

Redacta una descripcion profesional de la actividad
realizada y relacionala con la obligacion contractual
cuando exista informacion suficiente para hacerlo.

La descripcion debe responder, en la medida en que
la informacion disponible lo permita:

- Que actividad se realizo?
- Que gestion se desarrollo?
- Que se reviso, elaboro, actualizo, valido,
  gestiono, implemento o coordino?
- Que resultado, avance o producto puede
  identificarse?
- Como contribuye la actividad al cumplimiento
  de la obligacion?

REGLAS OBLIGATORIAS:

1. NO digas:
   "en la imagen",
   "se observa",
   "se ve",
   "la imagen muestra",
   "pantallazo",
   "captura de pantalla",
   "fotografia",
   "evidencia visual".

2. NO describas colores, posiciones, botones,
   ventanas o elementos graficos que no aporten
   informacion sobre la actividad.

3. Describe la actividad funcional y contractual.

4. Utiliza lenguaje formal, tecnico y administrativo.

5. No inventes datos.

6. No inventes cantidades, porcentajes, nombres,
   fechas, resultados, usuarios, reuniones,
   entregables o aprobaciones.

7. Si la informacion unicamente demuestra un
   avance o una gestion, no afirmes que existe
   cumplimiento total.

8. Utiliza verbos de accion como:
   revision, analisis, elaboracion, actualizacion,
   seguimiento, validacion, configuracion,
   implementacion, documentacion, coordinacion,
   verificacion, atencion, gestion, consolidacion,
   socializacion, ajuste y preparacion.

9. La descripcion debe tener entre 1 y 3 oraciones.

10. No utilices listas.

11. La descripcion debe poder copiarse directamente
    en un informe de actividades contractuales.

12. Entrega unicamente la descripcion final.
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
                temperature=0.2
            )
        )

        descripcion = (
            response.text.strip()
            if response.text
            else None
        )

        if descripcion:

            descripcion = _limpiar_texto(
                descripcion
            )

        print(
            f'[VisionAnalyzer] '
            f'Usando modelo: {modelo}'
        )

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
                temperature=0.2
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
