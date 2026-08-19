"""
Servicio de integración con Google Gemini.

Responsabilidades:
- Obtener y validar la API Key de Gemini.
- Analizar imágenes de evidencias.
- Generar descripciones de las evidencias.
- Manejar errores de comunicación con Gemini.
- Mantener aislada la dependencia de Gemini del resto de la aplicación.

Este servicio NO maneja:
- Flask
- SQLAlchemy
- archivos Excel
- reportes
- contratos
- progreso SSE
- procesamiento de la carga masiva
"""

import os
import time
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

DEFAULT_MODEL = "gemini-2.0-flash"

MAX_IMAGENES_POR_MINUTO = 15

ESPERA_ENTRE_IMAGENES = (
    60 / MAX_IMAGENES_POR_MINUTO
)


# ============================================================
# SERVICIO GEMINI
# ============================================================

class GeminiService:
    """
    Encapsula toda la comunicación con Google Gemini.
    """

    def __init__(
        self,
        api_key=None,
        modelo=None
    ):
        """
        Inicializa el servicio.

        Args:
            api_key:
                API Key de Gemini. Si no se proporciona,
                se intenta obtener desde GEMINI_API_KEY.

            modelo:
                Nombre del modelo Gemini.
        """

        self.api_key = (
            api_key
            or os.environ.get(
                "GEMINI_API_KEY",
                ""
            ).strip()
        )

        self.modelo = (
            modelo
            or os.environ.get(
                "GEMINI_MODEL",
                DEFAULT_MODEL
            ).strip()
        )

        self.client = None

        self._inicializar_cliente()

    # ========================================================
    # INICIALIZACIÓN
    # ========================================================

    def _inicializar_cliente(self):
        """
        Inicializa el cliente de Gemini.

        Si no existe API Key, el servicio queda desactivado.
        """

        if not self.api_key:
            return

        try:

            from google import genai

            self.client = genai.Client(
                api_key=self.api_key
            )

        except ImportError as exc:

            raise RuntimeError(
                "No está instalada la librería "
                "google-genai. Ejecute: "
                "pip install google-genai"
            ) from exc

    # ========================================================
    # ESTADO
    # ========================================================

    @property
    def activo(self):
        """
        Indica si Gemini está disponible.
        """

        return (
            bool(self.api_key)
            and self.client is not None
        )

    # ========================================================
    # ANALIZAR IMAGEN
    # ========================================================

    def analizar_imagen(
        self,
        ruta_imagen,
        contexto=None
    ):
        """
        Analiza una imagen de evidencia utilizando Gemini.

        Args:
            ruta_imagen:
                Ruta física de la imagen.

            contexto:
                Información adicional que puede utilizar Gemini
                para comprender la evidencia.

        Returns:
            str:
                Descripción generada por Gemini.

            None:
                Si Gemini no está configurado.

        Raises:
            FileNotFoundError:
                Si la imagen no existe.

            RuntimeError:
                Si ocurre un error al comunicarse con Gemini.
        """

        if not self.activo:
            return None

        ruta = Path(
            ruta_imagen
        )

        if not ruta.exists():

            raise FileNotFoundError(
                f"No existe la imagen: {ruta}"
            )

        if not ruta.is_file():

            raise FileNotFoundError(
                f"La ruta no corresponde a un archivo: {ruta}"
            )

        try:

            from google.genai import types

            archivo = self.client.files.upload(
                file=str(ruta)
            )

            prompt = self._crear_prompt(
                contexto
            )

            response = (
                self.client.models.generate_content(
                    model=self.modelo,
                    contents=[
                        archivo,
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.2
                    )
                )
            )

            texto = self._extraer_texto(
                response
            )

            return texto

        except Exception as exc:

            raise RuntimeError(
                "Error al analizar la imagen con Gemini: "
                f"{exc}"
            ) from exc

    # ========================================================
    # PROMPT
    # ========================================================

    def _crear_prompt(
        self,
        contexto=None
    ):
        """
        Construye el prompt utilizado para analizar
        una evidencia contractual.
        """

        prompt = """
Analiza la imagen proporcionada como evidencia de una
actividad relacionada con una obligación contractual.

Genera una descripción objetiva, clara y profesional
de lo que se observa en la imagen.

La descripción debe:

- Explicar qué se observa.
- Identificar, cuando sea posible, la actividad realizada.
- Evitar inventar información que no sea visible.
- No afirmar fechas, nombres o datos que no puedan
  comprobarse visualmente.
- Utilizar lenguaje formal apropiado para un informe
  contractual.
- Ser breve pero suficientemente descriptiva.

Entrega únicamente el párrafo descriptivo.
"""

        if contexto:

            prompt += f"""

Contexto proporcionado para esta evidencia:

{contexto}

Utiliza este contexto únicamente como apoyo.
No inventes información que contradiga la imagen.
"""

        return prompt.strip()

    # ========================================================
    # EXTRAER TEXTO
    # ========================================================

    def _extraer_texto(
        self,
        response
    ):
        """
        Extrae de forma segura el texto generado
        por Gemini.
        """

        if response is None:
            return ""

        texto = getattr(
            response,
            "text",
            None
        )

        if texto:

            return texto.strip()

        return ""

    # ========================================================
    # ANALIZAR CON REINTENTOS
    # ========================================================

    def analizar_imagen_con_reintentos(
        self,
        ruta_imagen,
        contexto=None,
        max_reintentos=3,
        espera=2
    ):
        """
        Analiza una imagen realizando reintentos en caso
        de error temporal.

        Args:
            ruta_imagen:
                Ruta de la imagen.

            contexto:
                Contexto de la evidencia.

            max_reintentos:
                Número máximo de intentos adicionales.

            espera:
                Segundos iniciales entre reintentos.

        Returns:
            str | None
        """

        ultimo_error = None

        for intento in range(
            max_reintentos + 1
        ):

            try:

                return self.analizar_imagen(
                    ruta_imagen=ruta_imagen,
                    contexto=contexto
                )

            except Exception as exc:

                ultimo_error = exc

                if intento >= max_reintentos:
                    break

                tiempo_espera = (
                    espera * (intento + 1)
                )

                time.sleep(
                    tiempo_espera
                )

        raise RuntimeError(
            "No fue posible analizar la imagen "
            f"después de {max_reintentos + 1} intentos. "
            f"Último error: {ultimo_error}"
        )

    # ========================================================
    # ESPERA POR RATE LIMIT
    # ========================================================

    def esperar_rate_limit(
        self,
        segundos=None
    ):
        """
        Aplica una pausa para respetar el límite de
        solicitudes configurado.

        Por defecto:

            15 imágenes / minuto

        equivale aproximadamente a:

            4 segundos por imagen
        """

        if segundos is None:

            segundos = (
                ESPERA_ENTRE_IMAGENES
            )

        if segundos > 0:

            time.sleep(
                segundos
            )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

gemini_service = GeminiService()
