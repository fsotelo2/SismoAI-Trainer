# Fase 9 — Registro de implementación

**Rama:** `Fase-9-Modelos`  
**Alcance de esta entrega:** configuración, persistencia y entrenamiento inicial en PC.

## Implementado en el repositorio

- Interfaz Modelos integrada al cargador de vistas existente.
- Consulta del manifiesto Dataset activo y visualización de conteos de particiones y etiquetas binarias.
- Configuración de experimento con validación de hiperparámetros, arquitectura, sensores, semilla y opciones.
- Registro persistente de experimentos en `model_experiments.json`, sin sobrescribir registros previos.
- Preparación de tensores desde las ventanas referenciadas por el manifiesto en el mismo worker de fondo que entrena: remuestreo lineal a longitud fija (256 puntos), normalización z-score por ventana/canal y validación de tiempos finitos, estrictamente crecientes y etiquetas binarias. La interfaz recibe el estado «preparing» sin esperar a que termine esta etapa.
- Entrenamiento CPU en segundo plano con PyTorch: 1D-CNN, clasificador denso y baseline lineal.
- Seguimiento de época, pérdidas y accuracy de validation; parada temprana opcional.
- Evaluación separada de train, validation y test; matriz de confusión y métricas macro/por clase.
- Checkpoint `weights.pt`, historial y `training_result.json` por experimento.
- Pruebas unitarias para métricas, formas de salida y ejecución sintética.
- Registro de configuración completa y hash SHA-256 del checkpoint por ejecución.
- Validación explícita de opciones realmente implementadas; por ahora la pérdida admitida es `cross_entropy`.

## Endurecimiento adicional

- El entrenador valida tipos estrictos y límites de épocas (1–10000), batch size (1–4096) y learning rate finito (0–1], incluso si se invoca fuera de la interfaz.
- La arquitectura baseline se identifica en la interfaz como clasificador lineal, evitando describirla como un sistema de reglas.
- La interfaz informa errores de comunicación al iniciar, guardar configuración o consultar el progreso, en lugar de dejar fallar la operación sin explicación.
- El puente evita iniciar una segunda ejecución simultánea, actualiza el estado compartido con bloqueo y no sobrescribe un registro de experimentos ilegible como si estuviera vacío.

## Correcciones derivadas de CI

Se corrigieron los siguientes problemas detectados por la ejecución de GitHub Actions:

- Error de sintaxis en `core/models/trainer.py` causado por secuencias `\\n` literales.
- Pruebas de `test_labeling_models.py` migradas de pytest a `unittest` para ajustarse al comando de CI y a la dependencia declarada.
- Pruebas de etiquetado alineadas con el contrato vigente: dos clases principales; la taxonomía secundaria sigue abierta hasta su aprobación.
- `WindowRecord.to_dict()` ahora incluye `duration_ms`, campo requerido por la prueba de forma común del registro.

Las pruebas automatizadas en GitHub Actions se desactivaron por solicitud del usuario. Las correcciones y los cambios posteriores quedan pendientes de verificación local en el PC; no se declara la suite como aprobada.

## Revisión de cierre de código

- Se trasladó la lectura y preparación de señales al worker para evitar bloquear la interfaz durante el procesamiento del Dataset.
- Se reforzó la actualización del registro para fallar explícitamente ante corrupción o ausencia del experimento, en vez de reemplazar silenciosamente el contenido.
- La suite no se ha ejecutado en este entorno; la comprobación final de importaciones, comportamiento de PyWebView y entrenamiento con Dataset real corresponde a la validación local descrita abajo.

## Límites explícitos

La ejecución de entrenamiento es PC-only. El entrenamiento correcto no demuestra compatibilidad con ESP32-S3.

Pendiente antes de cerrar Fase 9:
1. Ejecutar y corregir localmente la suite de pruebas, incluyendo instalación efectiva de PyTorch.
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


## Ajustes de interfaz y carga de Dataset

- Se retiró la selección de destino ESP32-S3 de la vista Modelos; el alcance actual es entrenamiento local en PC.
- Se eliminó la dependencia del campo `target` en la validación del backend para guardar e iniciar experimentos.
- Se añadió un tiempo máximo de espera y mensajes visibles al consultar el Dataset, la biblioteca de experimentos y el estado de entrenamiento, para evitar que la vista permanezca indefinidamente en estado de carga.
- Pendiente: validar en ejecución local el flujo Dataset → Modelos con un Dataset real y confirmar la respuesta del puente PyWebView.

- Se añadió un traspaso directo del manifiesto recién generado desde Dataset hacia Modelos, evitando depender de una segunda consulta al puente para mostrar el Dataset activo.
- Si falla la generación, se reactiva el botón «Generar dataset» y se muestra el error devuelto por el puente.


## Persistencia del Dataset para Modelos

- `Generar Dataset` guarda el manifiesto activo en `Dataset/dataset_activo.json`, dentro del directorio de datos persistentes de la aplicación.
- El JSON incluye `dataset_id`, `name`, `seed`, `ratios`, `splits` (train/validation/test), `summary`, `warnings` y `model_contract`.
- `model_contract` define clasificación binaria, clases 0/1, framework PyTorch, modos de entrada, forma de tensor, 256 puntos por ventana, normalización y particiones requeridas.
- Modelos consume el manifiesto activo desde el backend; las filas del manifiesto referencian ventanas persistidas por `window_id`, y el backend obtiene sus señales fuente al preparar el entrenamiento.
- En el primer arranque con un manifiesto antiguo en `dataset.json`, se intenta migrarlo al nuevo destino sin eliminar el archivo anterior.
- Pendiente de validación local: confirmar que la ruta de datos y la restauración funcionan en la instalación del usuario y ejecutar entrenamiento de extremo a extremo.
