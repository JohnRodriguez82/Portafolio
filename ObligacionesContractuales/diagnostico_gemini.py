"""
DIAGNÓSTICO DE API KEY DE GOOGLE GEMINI
Ejecute este script para saber exactamente qué está pasando con su API key.
"""
import google.generativeai as genai
import sys

API_KEY = input("Pegue su API key de Gemini y presione Enter: ").strip()

if not API_KEY:
    print("❌ No ingresó ninguna key.")
    sys.exit(1)

print("\n" + "="*60)
print("🔍 DIAGNÓSTICO DE API KEY GOOGLE GEMINI")
print("="*60)
print(f"Key recibida (primeros 15 chars): {API_KEY[:15]}...")
print(f"Longitud total: {len(API_KEY)} caracteres")

# 1. Configurar
print("\n1. Configurando API key...")
try:
    genai.configure(api_key=API_KEY)
    print("   ✅ Key configurada correctamente")
except Exception as e:
    print(f"   ❌ Error al configurar: {e}")
    sys.exit(1)

# 2. Listar modelos disponibles
print("\n2. Consultando modelos disponibles en su proyecto...")
try:
    models = list(genai.list_models())
    print(f"   ✅ Se encontraron {len(models)} modelos en total")
    gemini_models = []
    for m in models:
        name = m.name
        if 'gemini' in name.lower():
            supports_vision = 'generateContent' in m.supported_generation_methods
            vision_tag = " (✅ soporta imágenes)" if supports_vision else " (❌ solo texto)"
            print(f"      • {name}{vision_tag}")
            gemini_models.append({'name': name, 'vision': supports_vision})

    if not gemini_models:
        print("   ⚠️  No se encontraron modelos Gemini en su proyecto.")
        print("   💡 Solución: Vaya a https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
        print("      y habilite la 'Generative Language API'. Espere 5-10 minutos.")
        sys.exit(1)

except Exception as e:
    error = str(e).lower()
    if "permission" in error:
        print("   ❌ Sin permisos. La API 'Generative Language API' no está habilitada.")
        print("   💡 Solución: Vaya a https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
        print("      Seleccione su proyecto → clic en 'Habilitar' → espere 5-10 minutos.")
    elif "api key not valid" in error:
        print("   ❌ API key inválida para este servicio.")
        print("   💡 Asegúrese de que la key la generó en: https://aistudio.google.com/app/apikey")
    else:
        print(f"   ❌ Error al listar modelos: {e}")
    sys.exit(1)

# 3. Probar cada modelo
print("\n3. Probando modelos que soportan imágenes...")
modelo_funcional = None
for modelo_info in gemini_models:
    nombre = modelo_info['name']
    if not modelo_info['vision']:
        continue
    try:
        model = genai.GenerativeModel(nombre)
        response = model.generate_content("Hola")
        print(f"   ✅ {nombre}: FUNCIONA")
        modelo_funcional = nombre
        break
    except Exception as e:
        err = str(e).lower()
        if "not found" in err or "404" in err:
            print(f"   ❌ {nombre}: No disponible (404)")
        elif "quota" in err:
            print(f"   ⚠️  {nombre}: Cuota excedida")
        else:
            print(f"   ❌ {nombre}: {str(e)[:80]}")

print("\n" + "="*60)
if modelo_funcional:
    print(f"✅ DIAGNÓSTICO: Todo listo. Modelo funcional: {modelo_funcional}")
    print("   Puede usar este modelo en la aplicación.")
else:
    print("❌ DIAGNÓSTICO: Ningún modelo funciona.")
    print("   💡 Solución más común: Habilite la API y espere 5-10 minutos.")
print("="*60)
