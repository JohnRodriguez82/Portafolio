"""
DIAGNOSTICO DE CREDENCIALES GOOGLE OAUTH
Ejecute este script para verificar que las credenciales esten correctas.
"""
import os
from dotenv import load_dotenv

print("=" * 60)
print("DIAGNOSTICO DE CREDENCIALES GOOGLE OAUTH")
print("=" * 60)

# 1. Cargar .env
load_dotenv()
print("\n[1] Archivo .env cargado.")

# 2. Leer variables
client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
secret_key = os.environ.get('SECRET_KEY', '')

print("\n[2] Variables detectadas:")
print("    GOOGLE_CLIENT_ID    : {}".format('OK - Configurado' if client_id else 'VACIO'))
print("    GOOGLE_CLIENT_SECRET: {}".format('OK - Configurado' if client_secret else 'VACIO'))
print("    SECRET_KEY          : {}".format('OK - Configurado' if secret_key else 'VACIO'))

# 3. Mostrar primeros caracteres (sin revelar todo)
if client_id:
    print("\n[3] Client ID (primeros 30 chars): {}...".format(client_id[:30]))
    print("    Longitud total: {} caracteres".format(len(client_id)))
    if ' ' in client_id:
        print("    ADVERTENCIA: El Client ID contiene ESPACIOS.")
    if client_id.startswith('"') or client_id.endswith('"'):
        print("    ADVERTENCIA: El Client ID tiene COMILLAS. Eliminelas.")
    if not client_id.endswith('.apps.googleusercontent.com'):
        print("    ADVERTENCIA: El Client ID NO termina en .apps.googleusercontent.com")
        print("       Puede que este usando una API Key en lugar de un OAuth Client ID.")
else:
    print("\n[3] ERROR: Client ID esta vacio.")

if client_secret:
    print("\n[4] Client Secret (primeros 10 chars): {}...".format(client_secret[:10]))
    print("    Longitud total: {} caracteres".format(len(client_secret)))
    if ' ' in client_secret:
        print("    ADVERTENCIA: El Client Secret contiene ESPACIOS.")
    if client_secret.startswith('"') or client_secret.endswith('"'):
        print("    ADVERTENCIA: El Client Secret tiene COMILLAS. Eliminelas.")
    if len(client_secret) < 20:
        print("    ADVERTENCIA: El Client Secret parece muy corto.")
        print("       Asegurese de copiar el SECRETO DE CLIENTE, no el ID de cliente.")
else:
    print("\n[4] ERROR: Client Secret esta vacio.")

# 5. Verificar archivo .env
print("\n[5] Buscando archivo .env en la carpeta actual...")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    print("    OK - .env encontrado en: {}".format(env_path))
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'GOOGLE_CLIENT_ID' in content:
        print("    OK - GOOGLE_CLIENT_ID esta en el archivo.")
    else:
        print("    ERROR - GOOGLE_CLIENT_ID NO esta en el archivo.")
    if 'GOOGLE_CLIENT_SECRET' in content:
        print("    OK - GOOGLE_CLIENT_SECRET esta en el archivo.")
    else:
        print("    ERROR - GOOGLE_CLIENT_SECRET NO esta en el archivo.")
else:
    print("    ERROR - .env NO encontrado en: {}".format(env_path))
    print("    Asegurese de que el archivo se llame exactamente '.env' (con punto al inicio)")

# 6. Instrucciones
print("\n" + "=" * 60)
print("SOLUCIONES COMUNES")
print("=" * 60)
print("""
1. ERROR invalid_client:
   El Client Secret es incorrecto. Asegurese de copiar el valor
   de la columna Secreto de cliente, NO el ID de cliente.

2. ERROR redirect_uri_mismatch:
   En Google Cloud Console, agregue exactamente esta URI:
   http://127.0.0.1:5000/auth/google/callback

3. ERROR unauthorized_client:
   El Client ID no es de tipo Aplicacion web. Debe crear
   un ID de cliente OAuth 2.0 de tipo Aplicacion web.

4. El .env no se lee:
   El archivo debe llamarse EXACTAMENTE '.env' (punto + env)
   Sin extension .txt
   En la misma carpeta que app.py
   Sin comillas alrededor de los valores
""")

print("=" * 60)
print("Para verificar, abra su .env con el Bloc de notas y asegurese")
print("de que las lineas se vean EXACTAMENTE asi (sin comillas):")
print()
print("GOOGLE_CLIENT_ID=123456789-abc123.apps.googleusercontent.com")
print("GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx")
print("=" * 60)
