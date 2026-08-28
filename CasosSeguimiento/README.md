# 📋 Seguimiento de Casos v2 - Sistema de Alertas por Correo

Sistema completo en Python para monitorear casos profesionales con **campos parametrizables**, soporte para **Excel y CSV**, **actualización incremental** de casos existentes, y alertas automáticas por correo electrónico.

---

## ✨ Novedades de la v2

- **📋 Campos parametrizables**: Agrega, quita o modifica las columnas del archivo de entrada desde la configuración.
- **📁 Excel y CSV**: Soporta ambos formatos. Configurable desde el inicio.
- **🔍 Filtro de nombre de adjunto**: Define un patrón (ej: `reporte_casos*`) para que el sistema solo descargue archivos específicos del correo.
- **🔄 Actualización incremental**: Cada nuevo archivo compara los casos por número de caso y actualiza solo los cambios (fechas de validación, estados, profesionales, campos extra).
- **📥 Carga manual**: Sube archivos Excel o CSV directamente desde el dashboard.
- **📜 Log de procesamiento**: Historial completo de cada archivo procesado con cambios detectados.

---

## 🚀 Instalación y Ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
streamlit run app.py
```

### Primera ejecución
La aplicación te guiará por **4 pasos de configuración**:
1. **Correo y Encargado**: Credenciales IMAP/SMTP y datos del encargado.
2. **Campos del Archivo**: Define qué columnas esperas. Puedes agregar campos personalizados.
3. **Tipo de Archivo y Adjunto**: Selecciona Excel o CSV, y define un filtro de nombre para los adjuntos del correo.
4. **Profesionales**: Lista de profesionales a monitorear.

> **Nota (Gmail):** Usa una **App Password** en lugar de tu contraseña normal.

---

## 📁 Configuración de Campos Parametrizables

Cada campo tiene:
- **ID**: Identificador interno (ej: `numero_caso`, `observacion`).
- **Nombre visible**: Lo que se muestra en el dashboard.
- **Sinónimos**: Variantes de nombres de columna que el sistema buscará en el archivo (ej: `sede,ubicación,lugar`).
- **Tipo**: `texto`, `fecha` o `numero`.
- **Obligatorio**: Si es requerido para procesar el archivo.

Los campos base recomendados son:
- `numero_caso` (obligatorio)
- `fecha_ingreso` (obligatorio)
- `profesional` (obligatorio)
- `fecha_validacion` (para determinar si está resuelto)
- `estado` (opcional, se infiere si no viene)

**Campos extra** (personalizados) se almacenan en formato JSON y se muestran en el dashboard automáticamente.

---

## 📅 Reglas de Alertas

| Día desde ingreso | Acción automática por correo |
|-------------------|------------------------------|
| **Día 8** | ⚠️ **Alerta Preventiva**: "Faltan 2 días para vencer el caso X" |
| **Día 11+** | 🚨 **Alerta Vencido**: "El caso X ha superado los 10 días" |
| **Cada hora** | 📊 **Resumen ejecutivo** si hay casos críticos |

---

## 🔒 Seguridad

- Credenciales encriptadas con **Fernet (AES-128)**.
- Archivos sensibles en `data/` (ignorados por `.gitignore`).

---

## 📄 Licencia

Uso interno. Desarrollado para automatización de seguimiento de casos profesionales.
