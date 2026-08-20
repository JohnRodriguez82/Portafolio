"""
Analizador de imagenes con Google Gemini Vision API.
Genera descripciones automaticas del contenido visual de las evidencias.
"""
import os
import re
import google.generativeai as genai
from PIL import Image

# Modelos probados y funcionales (ordenados por preferencia)
MODELOS_GEMINI = [
    'gemini-flash-latest',
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-pro-latest',
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash',
    'gemini-1.5-pro-latest',
    'gemini-1.5-pro',
    'gemini-pro-vision',
]


def _limpiar_key(api_key):
    """Limpia espacios y saltos de linea de la API key."""
    if not api_key:
        return None
    return api_key.strip().replace("\n", "").replace("\r", "").replace(" ", "")


def _encontrar_modelo_funcional(key):
    """Encuentra el primer modelo de Gemini que funcione con imagenes."""
    try:
        genai.configure(api_key=key)
        models = list(genai.list_models())
        disponibles = [m.name for m in models if 'gemini' in m.name.lower()]

        for modelo_nombre in MODELOS_GEMINI:
            nombre_completo = f"models/{modelo_nombre}"
            if nombre_completo not in disponibles:
                continue
            try:
                model = genai.GenerativeModel(modelo_nombre)
                model.generate_content("Hola")
                return modelo_nombre
            except Exception:
                continue

        for m in models:
            if 'gemini' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                nombre_corto = m.name.replace("models/", "")
                try:
                    model = genai.GenerativeModel(nombre_corto)
                    model.generate_content("Hola")
                    return nombre_corto
                except Exception:
                    continue

        return None
    except Exception:
        return None


def verificar_api_key(api_key):
    """
    Verifica si una API key de Gemini es valida.
    Retorna (bool, str) donde str es el mensaje de error o el modelo disponible.
    """
    key = _limpiar_key(api_key)
    if not key:
        return False, "La API key esta vacia."

    if len(key) < 10:
        return False, "La API key parece muy corta."

    modelo = _encontrar_modelo_funcional(key)
    if modelo:
        return True, modelo

    return False, (
        "No se encontro ningun modelo funcional. Verifique que la API "
        "'Generative Language API' este habilitada en su proyecto de Google Cloud."
    )


def analizar_imagen(image_path, api_key=None):
    """
    Analiza una imagen usando Google Gemini Vision.
    Detecta automaticamente el primer modelo disponible.
    """
    key = _limpiar_key(api_key) or os.environ.get('GEMINI_API_KEY')
    if not key:
        return None

    modelo = _encontrar_modelo_funcional(key)
    if not modelo:
        print("[VisionAnalyzer] No hay modelos funcionales disponibles.")
        return None

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(modelo)
        img = Image.open(image_path)

        prompt = (
            "Eres un asistente de redaccion de informes contractuales. "
            "Analiza esta imagen y describe UNICAMENTE la actividad funcional o accion que representa, "
            "como si fuera parte de un informe ejecutivo. "
            "REGLAS ESTRICTAS: "
            "1. NO digas 'en la imagen', 'se observa', 'se ve', 'la imagen muestra', 'pantallazo de'. "
            "2. NO describas elementos visuales, colores, disposicion de elementos o interfaz grafica. "
            "3. Describe la ACCION o RESULTADO funcional: que se hizo, que se reviso, que se aprobo, que se entrego. "
            "4. Maximo 2 oraciones. Se conciso y profesional. "
            "5. Ejemplo bueno: 'Revision y ajuste de casos de prueba para el modulo de gestion de usuarios.' "
            "6. Ejemplo malo: 'En la imagen se ve un pantallazo de una hoja de Excel con casos de prueba.' "
            "7. No inventes datos que no se vean en la imagen."
        )

        response = model.generate_content([prompt, img])
        descripcion = response.text.strip() if response.text else None
        print(f"[VisionAnalyzer] Usando modelo: {modelo}")
        return descripcion

    except Exception as e:
        print(f"[VisionAnalyzer] Error con modelo {modelo}: {e}")
        return None


def consolidar_textos_ejecutivo(descripciones, api_key=None):
    """
    Consolida multiples descripciones de actividades en un texto ejecutivo fluido.
    Usa Gemini si hay API key disponible; si no, usa un enfoque de union inteligente.
    """
    if not descripciones:
        return "Sin actividades reportadas."

    key = _limpiar_key(api_key) or os.environ.get('GEMINI_API_KEY')

    if key:
        modelo = _encontrar_modelo_funcional(key)
        if modelo:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(modelo)

                texto_base = "\n\n".join([f"- {d}" for d in descripciones])

                prompt = (
                    "Eres un redactor profesional de informes contractuales. "
                    "A partir de las siguientes descripciones de actividades realizadas durante un mes, "
                    "redacta UN SOLO texto ejecutivo fluido, profesional y coherente. "
                    "REGLAS ESTRICTAS: "
                    "1. NO menciones imagenes, fotografias, pantallazos, evidencias visuales ni archivos adjuntos. "
                    "2. NO uses frases como 'se observa', 'se evidencia', 'la imagen muestra', 'como se ve en'. "
                    "3. Escribe en parrafos conectados con conectores logicos (Una vez..., Posteriormente..., Finalmente...). "
                    "4. El tono debe ser formal, de informe ejecutivo contractual. "
                    "5. Agrupa actividades relacionadas en parrafos tematicos. "
                    "6. Maximo 3-4 parrafos. "
                    "\n\nDESCRIPCIONES DE ACTIVIDADES:\n"
                    + texto_base
                )

                response = model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[VisionAnalyzer] Error al consolidar con Gemini: {e}")

    return _consolidar_manual(descripciones)


def _consolidar_manual(descripciones):
    """Consolida descripciones manualmente cuando no hay Gemini."""
    if len(descripciones) == 1:
        return _limpiar_texto(descripciones[0])

    limpias = [_limpiar_texto(d) for d in descripciones]

    conectores_inicio = [
        "Durante el mes reportado, ",
        "En el marco de las actividades contractuales, ",
        "Como parte del cumplimiento de las obligaciones pactadas, ",
    ]

    conectores_medio = [
        "Posteriormente, ",
        "De manera complementaria, ",
        "En paralelo, ",
        "Asimismo, ",
        "En otro frente de trabajo, ",
    ]

    conectores_cierre = [
        "Finalmente, ",
        "Para cerrar el periodo, ",
        "Como cierre de las actividades del mes, ",
    ]

    import random

    n = len(limpias)
    if n <= 2:
        partes = [limpias]
    elif n <= 4:
        mitad = n // 2
        partes = [limpias[:mitad], limpias[mitad:]]
    else:
        tercio = n // 3
        partes = [limpias[:tercio], limpias[tercio:2*tercio], limpias[2*tercio:]]

    parrafos = []

    for i, grupo in enumerate(partes):
        if i == 0:
            conector = random.choice(conectores_inicio)
        elif i == len(partes) - 1:
            conector = random.choice(conectores_cierre)
        else:
            conector = random.choice(conectores_medio)

        texto_grupo = " ".join(grupo)
        texto_grupo = texto_grupo[0].lower() + texto_grupo[1:]
        parrafo = conector + texto_grupo
        parrafos.append(parrafo)

    return "\n\n".join(parrafos)


def _limpiar_texto(texto):
    """Elimina referencias a imagenes y evidencias del texto."""
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
        r'[Ss]e observa[^.]*\.',
        r'[Ll]a imagen muestra[^.]*\.',
        r'[Cc]omo se ve en[^.]*\.',
        r'[Pp]antallazo de[^,]*,\s*',
        r'[Ff]otografia de[^,]*,\s*',
    ]

    resultado = texto
    for patron in frases_a_eliminar:
        resultado = re.sub(patron, ' ', resultado)

    resultado = re.sub(r'\s+', ' ', resultado)
    resultado = re.sub(r'\.\.', '.', resultado)
    resultado = re.sub(r'\.\s*\.', '.', resultado)
    resultado = resultado.strip()

    if resultado and not resultado.endswith('.'):
        resultado += '.'

    return resultado
