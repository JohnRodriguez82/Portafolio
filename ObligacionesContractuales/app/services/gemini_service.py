"""
Servicio de integración con Google Gemini.

Responsabilidades:
- Obtener la API Key global desde la base de datos.
- Desencriptar la API Key utilizando APP_ENCRYPTION_KEY.
- Analizar imágenes de evidencias.
- Generar descripciones de las evidencias.
- Manejar errores de comunicación con Gemini.
- Mantener aislada la dependencia de Gemini del resto de la aplicación.

La API Key de Gemini se almacena de forma global en:

    configuracion_sistema.gemini_api_key_encriptada

La clave utilizada para desencriptarla se obtiene desde:

    APP_ENCRYPTION_KEY

La API Key NO se almacena en texto plano en la base de datos.

Este servicio NO maneja:
- Flask
- SQLAlchemy directamente desde las rutas
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

VARIABLE_CLAVE_ENCRIPTACION = (
    "APP_ENCRYPTION_KEY"
)


# ============================================================
# OBTENER API KEY DESDE BASE DE DATOS
# ============================================================

def _obtener_api_key_desde_bd():
    """
    Obtiene la API Key global de Gemini desde la base de datos
    y la desencripta utilizando APP_ENCRYPTION_KEY.

    La API Key se encuentra almacenada en:

        configuracion_sistema.gemini_api_key_encriptada

    Retorna:
        str:
            API Key desencriptada.

        '':
            Si no existe configuración o no puede
            desencriptarse.

    Importante:
        Nunca devuelve ni imprime la clave de encriptación.
    """

    try:

        # ====================================================
        # IMPORTACIONES LOCALES
        # ====================================================

        from flask import has_app_context

        if not has_app_context():
            return ''

        from models import ConfiguracionSistema

        from cryptography.fernet import (
            Fernet,
            InvalidToken
        )

        # ====================================================
        # OBTENER CLAVE DE ENCRIPTACIÓN
        # ====================================================

        clave_encriptacion = (
            os.environ.get(
                VARIABLE_CLAVE_ENCRIPTACION,
                ''
            )
            .strip()
        )

        if not clave_encriptacion:

            print(
                '[ADVERTENCIA] '
                'APP_ENCRYPTION_KEY no está configurada.'
            )

            return ''

        # ====================================================
        # OBTENER CONFIGURACIÓN GLOBAL
        # ====================================================

        configuracion = (
            ConfiguracionSistema.query
            .order_by(
                ConfiguracionSistema.id.asc()
            )
            .first()
        )

        if not configuracion:

            return ''

        # ====================================================
        # OBTENER VALOR ENCRIPTADO
        # ====================================================

        api_key_encriptada = (
            configuracion.gemini_api_key_encriptada
            or ''
        ).strip()

        if not api_key_encriptada:

            return ''

        # ====================================================
        # CREAR FERNET
        # ====================================================

        try:

            fernet = Fernet(
                clave_encriptacion.encode(
                    'utf-8'
                )
            )

        except Exception as exc:

            print(
                '[ERROR] '
                'APP_ENCRYPTION_KEY no es una clave Fernet válida.'
            )

            return ''

        # ====================================================
        # DESENCRIPTAR
        # ====================================================

        try:

            api_key = fernet.decrypt(
                api_key_encriptada.encode(
                    'utf-8'
                )
            ).decode(
                'utf-8'
            ).strip()

        except InvalidToken:

            print(
                '[ERROR] '
                'No fue posible desencriptar la API Key de Gemini. '
                'Verifique APP_ENCRYPTION_KEY.'
            )

            return ''

        except Exception as exc:

            print(
                '[ERROR] '
                'Error al desencriptar la API Key de Gemini: '
                f'{type(exc).__name__}'
            )

            return ''

        # ====================================================
        # VALIDAR
        # ====================================================

        if not api_key:

            return ''

        return api_key

    except Exception as exc:

        print(
            '[ERROR] '
            'No fue posible obtener la API Key de Gemini '
            f'desde la base de datos: {type(exc).__name__}'
        )

        return ''


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
                API Key opcional.

                Si se proporciona explícitamente, se utiliza
                esa clave.

                Si no se proporciona, se obtiene la API Key
                global desde la base de datos.

            modelo:
                Nombre del modelo Gemini.
        """

        # ====================================================
        # API KEY
        # ====================================================

        self.api_key = (
            api_key
            or _obtener_api_key_desde_bd()
        )

        # ====================================================
        # MODELO
        # ====================================================

        self.modelo = (
            modelo
            or os.environ.get(
                "GEMINI_MODEL",
                DEFAULT_MODEL
            ).strip()
        )

        # ====================================================
        # CLIENTE
        # ====================================================

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
    # RECARGAR API KEY
    # ========================================================

    def recargar_api_key(self):
        """
        Vuelve a cargar la API Key global desde la base de datos.

        Este método permite que una API Key guardada desde la
        pantalla de Configuración del Sistema sea utilizada
        sin necesidad de reiniciar manualmente la aplicación.

        Retorna:
            bool:
                True si la API Key está disponible.
        """

        self.api_key = (
            _obtener_api_key_desde_bd()
        )

        self.client = None

        self._inicializar_cliente()

        return bool(
            self.api_key
            and self.client
        )

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

        # ====================================================
        # ASEGURAR API KEY ACTUALIZADA
        # ====================================================

        if not self.activo:

            self.recargar_api_key()

        # ====================================================
        # VALIDAR GEMINI
        # ====================================================

        if not self.activo:

            return None

        # ====================================================
        # VALIDAR ARCHIVO
        # ====================================================

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

        # ====================================================
        # ANALIZAR
        # ====================================================

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
