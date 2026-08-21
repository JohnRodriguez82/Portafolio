# Reporte de Cumplimiento de Obligaciones Contractuales

Aplicación web ligera desarrollada en Python con Flask, arquitectura MVC y SQLite para la gestión y generación de reportes mensuales de cumplimiento de obligaciones contractuales.

## Características Principales

- **Configuración de contrato**: Define fechas de inicio y fin del contrato.
- **Obligaciones contractuales**: Registra obligaciones con número y descripción (las mismas durante todo el contrato).
- **Actividades dinámicas**: Cada imagen de evidencia que se carga se convierte automáticamente en una actividad con número consecutivo.
- **Visión por Inteligencia Artificial**: El sistema analiza automáticamente cada imagen cargada usando **Google Gemini Vision** para describir lo que se observa visualmente.
- **Descripción automática enriquecida**: El sistema combina tres fuentes para generar el párrafo descriptivo:
  1. **Descripción visual de la IA** (lo que Gemini "ve" en la imagen)
  2. **Anuncio del usuario** (contexto breve que usted escribe)
  3. **Obligación reportada** (número y descripción de la obligación contractual)
- **Anuncio oculto**: El anuncio que el usuario escribe al cargar la imagen es solo entrada para el sistema y **NO aparece** en la tabla ni en el PDF.
- **Reportes mensuales**: Genera reportes por obligación y mes, con rango de fechas personalizable.
- **Cuadrícula de evidencias**: Visualiza en tabla las columnas: **# | Actividad | Fecha | Evidencia**
- **Generación de PDF**: Exporta cada reporte en PDF con la estructura oficial del formato de ejemplo.
- **Base de datos SQLite**: Ligera, sin necesidad de servidor de base de datos externo.

## Cómo Funciona el Análisis Visual con IA

Cuando carga una imagen como evidencia, el sistema puede analizarla automáticamente con Google Gemini Vision:

1. **Usted escribe un anuncio** (ej: *"Presentación del estado de avance de proyectos"*)
2. **Usted carga la imagen** (pantallazo, documento, foto de reunión, etc.)
3. **La IA analiza la imagen** y describe lo que ve (ej: *"Pantallazo de una presentación de PowerPoint con gráficos de avance de proyectos estratégicos"*)
4. **El sistema combina todo** y genera un párrafo formal haciendo referencia a la obligación contractual

> **Nota:** El análisis visual con IA es opcional. Si no configura una API key, el sistema generará descripciones usando solo el anuncio del usuario y la obligación.

## Estructura de la Tabla (Web y PDF)

| # | Actividad realizada | Fecha | Evidencia |
|---|---------------------|-------|-----------|
| 1 | *Párrafo descriptivo generado automáticamente combinando lo que la IA vio en la imagen, el anuncio del usuario y la referencia a la obligación contractual No. X...* | 13-07-2026 | [Imagen] |
| 2 | *...* | 21-07-2026 | [Imagen] |

## Estructura del Proyecto (MVC)

```
├── app                      
│   ├── __init__.py         
│   ├── blueprints         
│       ├── __init__.py       
│       ├── autenticacion.py  
│       ├── auth.py           
│       ├── cargas.py         
│       ├── configuracion.py  
│       ├── contratos.py      
│       ├── inicio.py         
│       ├── reportes.py       
│   ├── services              
│       ├── __init__.py               
│       ├── archivo_service.py        
│       ├── carga_masiva_service.py   
│       ├── contrato_service.py       
│       ├── evidencia_service.py      
│       ├── excel_service.py          
│       ├── gemini_service.py         
│       ├── job_service.py           
│       ├── plantilla_service.py      
│       ├── reporte_service.py         
│   ├── static                        
│   ├── templates                    
│        ├── __init__.py              
│        ├── base.html                      
│        ├── login.html                      
│        ├── registro.html                
│        ├── carga_masiva.html          
│        ├── index.html               
│        ├── config.html              
│        ├── reportes.html            
│        ├── ver_reporte.html         
│        ├── nuevo_reporte.html       
│        ├── carga_masiva_mes.html    
│        ├── contratos.html           
│        ├── inicio.html              
│   ├── utils
├── .env                          
├── README.md                          
├── app.py                             
├── config.py                          
├── diagnostico_gemini.py              
├── diagnostico_google.py               
├── models.py                          
├── pdf_generator.py                   
├── requiriments.txt                   
├── run.py                             
├── vision_analyzer.py
```

## Requisitos

- Python 3.8 o superior
- pip
- Conexión a Internet (solo si usa el análisis visual con IA)

## Instalación

1. Descomprima el archivo en la carpeta deseada.

2. Cree un entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Active el entorno virtual:
   - Windows:
   ```bash
   venv\Scripts\activate
   ```
   - Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

4. Instale las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración de la API Key de Gemini (Opcional pero Recomendada)

Para activar el análisis visual automático de imágenes con Inteligencia Artificial:

1. Vaya a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Inicie sesión con su cuenta de Google
3. Genere una API key gratuita
4. En la aplicación, vaya a **Configuración** → **Inteligencia Artificial**
5. Pegue la API key y guarde

> El tier gratuito de Gemini permite **15 peticiones por minuto**, más que suficiente para el uso típico de reportes mensuales.

## Uso

1. Inicie la aplicación:
```bash
python run.py
```

2. Abra su navegador en:
```
http://localhost:5000
```

3. **Configurar API key de IA** (opcional pero recomendado):
   - Vaya a "Configuración" → "Inteligencia Artificial"
   - Ingrese su API key de Gemini para activar el análisis visual automático

4. **Configurar contrato**:
   - En "Configuración", ingrese las fechas de inicio y fin del contrato
   - Agregue las obligaciones contractuales (número y descripción)

5. **Crear reportes mensuales**:
   - En el Dashboard, seleccione una obligación y haga clic en "Nuevo Reporte"
   - Seleccione el mes y año
   - Defina el rango de fechas del reporte (ej: 01-07 al 31-07)
   - Cree el reporte

6. **Cargar evidencias (actividades dinámicas)**:
   - Dentro del reporte, escriba un **anuncio** (contexto breve) describiendo la actividad realizada
   - Cargue la imagen de evidencia
   - Si tiene API key configurada, la IA analizará automáticamente la imagen y describirá lo que ve
   - El sistema genera automáticamente el **párrafo descriptivo formal** combinando la descripción visual de la IA, su anuncio y la referencia a la obligación
   - Cada imagen se convierte en una actividad con número consecutivo (1, 2, 3...)
   - **El anuncio NO aparece en la tabla ni en el PDF**

7. **Visualizar**:
   - Vea las actividades en tabla con columnas: **# | Actividad | Fecha | Evidencia**
   - Si la IA analizó la imagen, verá un recuadro con "IA vio: ..." debajo de cada actividad
   - También disponible en vista de cuadrícula con tarjetas

8. **Generar PDF**:
   - Haga clic en "Descargar PDF" para exportar el reporte con la estructura oficial
   - El PDF incluye: metadatos, descripción de obligación, tabla de actividades/evidencias con imágenes y descripciones automáticas, y guía de diligenciamiento

## Flujo de Trabajo con IA

```
Contrato (fechas)
   └── Obligaciones (No. + descripción) [siempre las mismas cada mes]
          └── Reporte Mensual (mes, año, rango fechas)
                 └── Evidencia/Actividad 1
                       ├── Imagen cargada
                       ├── Anuncio del usuario [oculto en reporte]
                       ├── Descripción visual de la IA [oculta en reporte, usada para generar párrafo]
                       └── Párrafo descriptivo automático (IA vio + anuncio + obligación)
                 └── Evidencia/Actividad 2
                 └── ...
```

## Notas Importantes

- Las imágenes se almacenan en `static/uploads/evidencias/`
- Los PDFs generados se guardan en `static/pdfs/generados/`
- La base de datos SQLite (`reportes.db`) se crea automáticamente al iniciar
- Las obligaciones se configuran una sola vez y se reutilizan para todos los meses
- Las actividades se generan dinámicamente: **cada imagen cargada = una actividad**
- El número de actividad es consecutivo automático (1, 2, 3...) dentro de cada reporte
- Si se elimina una evidencia, los números se reordenan automáticamente
- El **anuncio del usuario** y la **descripción visual de la IA** son entradas internas y no se muestran en el PDF final
- Sin API key configurada, el sistema funciona normalmente usando solo el anuncio del usuario

## Licencia

Uso interno - Agencia Nacional de Tierras (ANT)
