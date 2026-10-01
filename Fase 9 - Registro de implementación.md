# Fase 9 — Registro de implementación

**Rama:** `Fase-9-Modelos`  
**Alcance de esta entrega:** configuración, persistencia y entrenamiento inicial en PC.

## Implementado en el repositorio

- Interfaz Modelos integrada al cargador de vistas existente.
- Consulta del manifiesto Dataset activo y visualización de conteos de particiones y etiquetas binarias.
- Configuración de experimento con validación de hiperparámetros, arquitectura, sensores, semilla y opciones.
- Registro persistente de experimentos en `model_experiments.json`, sin sobrescribir registros previos.
- Preparación de tensores desde las ventanas referenciadas por el manifiesto: remuestreo lineal a longitud fija (256 puntos) y normalización z-score por ventana/canal.
- Entrenamiento CPU en segundo plano con PyTorch: 1D-CNN, clasificador denso y baseline lineal.
- Seguimiento de época, pérdidas y accuracy de validation; parada temprana opcional.
- Evaluación separada de train, validation y test; matriz de confusión y métricas macro/por clase.
- Checkpoint `weights.pt`, historial y `training_result.json` por experimento.
- Pruebas unitarias para métricas, formas de salida y ejecución sintética.
- Workflow de GitHub Actions para ejecutar las pruebas en push/PR.

## Límites explícitos

La ejecución de entrenamiento es PC-only. El entrenamiento correcto no demuestra compatibilidad con ESP32-S3.

Pendiente antes de cerrar Fase 9:
1. Ejecutar y corregir la suite CI, incluyendo instalación efectiva de PyTorch.
2. Verificar la interfaz y el puente PyWebView en el PC con un Dataset real del proyecto.
3. Fijar versiones concretas de ESP-IDF, ESP-DL y ESP-PPQ y documentar el entorno reproducible.
4. Implementar y probar la ruta de exportación y cuantización que soporte esa combinación de versiones; validar operador por operador, formato, tolerancias y metadatos.
5. Incorporar reporte de compatibilidad estática, hashes de todos los artefactos y comparación fuente/cuanti­zado.
6. Verificar contrato de entrega hacia Fase 10. Las mediciones físicas quedan para Fase 11.

## Cómo ejecutar pruebas localmente

Desde la raíz del repositorio y en el entorno virtual del proyecto:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

La verificación visual/integral requiere abrir la aplicación de escritorio en el PC. En particular, comprobar carga del menú, lectura del Dataset activo, guardado de configuración, inicio del worker, progreso, persistencia y visualización de resultados.
