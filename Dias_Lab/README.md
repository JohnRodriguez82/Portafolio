# 📊 Dashboard de Análisis de Días Laborales

Aplicación analítica desarrollada en Streamlit para evaluar tiempos de proceso en entornos operativos (salud/laboratorio).

## 🚀 Highlights

- Limpieza avanzada de fechas (Excel + texto)
- Cálculo de días laborales con festivos
- KPI operativos
- Visualización interactiva
- Exportación de resultados

## 🧠 Arquitectura

El proyecto sigue principios de separación de responsabilidades:

- `processing.py`: lógica de negocio
- `utils.py`: funciones reutilizables
- `visuals.py`: visualización
- `main.py`: interfaz

## ▶️ Ejecutar

```bash
pip install -r requirements.txt
streamlit run app/main.py
