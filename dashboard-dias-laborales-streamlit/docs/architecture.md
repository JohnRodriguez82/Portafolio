# 📐 Arquitectura de la Aplicación

## 1. Visión General

Esta aplicación es un dashboard interactivo desarrollado en **Streamlit** para el análisis de cumplimiento de SLA baseado en días laborales, con soporte opcional para limpieza de duplicados y evaluación de su impacto sobre los indicadores.

El sistema está diseñado con una arquitectura modular, priorizando:
- separación clara de responsabilidades,
- facilidad de mantenimiento,
- extensibilidad para futuras versiones,
- y comportamiento consistente en escenarios con y sin eliminación de duplicados.

---

## 2. Tecnologías Principales

- **Python 3.10+**
- **Streamlit** para la interfaz de usuario
- **Pandas / NumPy** para procesamiento de datos
- **Altair** para visualización
- **Session State de Streamlit** para manejo de estado

---

## 3. Estructura del Proyecto

```text
src/
├── config/
│   └── settings.py          # Configuración general de la página
│
├── data/
│   └── processing.py        # Limpieza básica y cálculo de días laborales
│
├── utils/
│   ├── dates.py             # Manejo de fechas y festivos
│   ├── deduplicacion.py     # Eliminación de registros duplicados
│   ├── business_rules.py    # Reglas de SLA y Dentro/Fuera de oportunidad
│   ├── kpis.py              # Cálculo y visualización de KPIs
│   └── export.py            # Exportación a Excel
│
├── visuals/
│   └── charts.py            # Gráficas (Altair)
│
├── app.py                   # Orquestación principal de la aplicación
└── requirements.txt
```
## 4. Flujo General de Datos

### 4.1. El usuario carga un archivo Excel desde el sidebar.
4.2. Se aplican filtros opcionales (sede, sección, estudio).
4.3. El usuario configura:
- columnas de fecha,
- reglas de días laborales,
- tipo de SLA,
- opción de eliminación de duplicados.
4.4. Al presionar Procesar:
- se valida la configuración,
- se ejecuta opcionalmente la deduplicación,
- se calculan días laborales,
- se aplican reglas de negocio (SLA),
- se calculan KPIs generales y condicionales.
4.5. Los resultados se almacenan en st.session_state.
4.6. Se presentan:
- KPIs generales,
- KPIs relacionados con duplicados (si aplica),
- gráficas,
- tablas finales,
- y opción de descarga.

## 5. Manejo de Duplicados
La eliminación de duplicados es opcional y controlada por el usuario.
Reglas clave:
- Los KPIs y tablas relacionadas con duplicados solo se muestran si la opción está activada.
- El valor None se usa para representar métricas que no aplican.
- No se muestran métricas con valor 0 cuando la eliminación no fue solicitada.
Esto evita confusión y mantiene coherencia semántica en el dashboard.

## 6. Manejo de Estado (Session State)
st.session_state se utiliza para:
- almacenar resultados procesados,
- conservar métricas entre renders,
- controlar qué vistas deben mostrarse.

## 7. Separación de Responsabilidades
- app.py: Orquestación y control de flujo.
- processing.py: Cálculo de días laborales.
- business_rules.py: Definición de cumplimiento.
- kpis.py: Métricas e indicadores.
- charts.py: Visualizaciones.
- deduplicacion.py: Limpieza de datos.
Esta separación permite modificar una parte sin afectar las demás.

## 8. Decisiones de Diseño Relevantes
- No forzar estilos visuales para permitir compatibilidad con tema claro/oscuro.
- Usar KPIs comparativos para explicar impactos (no solo valores absolutos).
- Ocultar vistas que no aplican en ciertos escenarios (por ejemplo, duplicados).
- Priorizar estabilidad sobre complejidad visual.

## 9. Limitaciones Conocidas
- Altair no hereda completamente estilos dinámicos del tema de Streamlit.
- El comportamiento de textos en gráficas está limitado por Vega-Lite.
- No se implementa aún interacción directa (click-to-filter) en gráficas.
Estas limitaciones son aceptadas en la V1 por estabilidad y claridad.

## 10. Consideraciones para Futuras Versiones
Posibles extensiones:
- Drill-down interactivo por sección.
- Comparación visual con y sin deduplicación.
- Exportes comparativos.
- Tests automáticos de KPIs.
La arquitectura actual soporta estas extensiones sin refactor mayor.

