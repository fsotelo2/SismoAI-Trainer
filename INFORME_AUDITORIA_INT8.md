# Informe de diagnóstico: discrepancia de canales en calibración INT8

## 1. Causa raíz

La causa confirmada tiene dos niveles:

1. El artefacto existente ya era inconsistente: la configuración y el Dataset indicaban GEO + MPU, mientras el modelo persistido declaraba un solo canal.
2. En el flujo de entrenamiento, la validación, interpolación y `channels.append(...)` estaban indentados fuera del bucle que recorre los sensores. El código recorría GEO y MPU, pero solo procesaba y apilaba el último sensor. Por eso un entrenamiento nuevo con `geo_mpu` llegaba a `train_experiment` con forma `(N, 1, 256)` y era rechazado por la validación de contrato.

La corrección aplicada mueve esas operaciones dentro del bucle de sensores. El entrenamiento nuevo debe producir dos canales para `geo_mpu`.

La inconsistencia del artefacto existente se evidencia porque:

- El experimento `cnn_sismos_001` declara `input: "geo_mpu"`.
- El Dataset contiene ventanas con `GEO` y `MPU`.
- Los snapshots físicos contienen `GEO_amplitudes`, `GEO_times`, `MPU_amplitudes` y `MPU_times`.
- La preparación de datos para `geo_mpu` construye tensores con dos canales.
- El modelo persistido declara `channels: 1` e `input_shape: [1, 256]`.
- El ONNX exportado tiene entrada `[batch, 1, 256]`.

Por ello, durante la calibración se obtiene:

```text
Dataset Train: (2, 256)
modelo ONNX:    (1, 256)
```

Evidencias:

- [Dataset](Reference/Dataset/Sismos_Local_v01.json)
- [training_result.json](Reference/Modelos/cnn_sismos_001/training_result.json)
- [architecture.json](Reference/Modelos/cnn_sismos_001/architecture.json)
- [cnn_sismos_001_esp32s3_v1.export.json](Reference/Exportaciones/cnn_sismos_001_esp32s3_v1/cnn_sismos_001_esp32s3_v1.export.json)

La selección GEO + MPU en Ventanas no determina automáticamente la entrada del modelo. Son configuraciones distintas:

1. Ventanas registra los sensores presentes en cada ventana.
2. Modelos selecciona independientemente `config["input"]`.
3. El entrenamiento usa `config["input"]` para decidir qué canales cargar.
4. La CNN usa el número de canales real de `X_train`.

No se observa en el código actual una pérdida de `config["input"]` entre la interfaz y el entrenamiento. El artefacto existente fue creado con una discrepancia que el código actual conserva, o fue producido por una versión anterior del flujo. Los archivos disponibles no permiten distinguir esas posibilidades.

## 2. Flujo de datos: Ventanas hasta ONNX

### 2.1 Selección de sensores en Ventanas

La interfaz construye la selección a partir de los controles GEO y MPU. Puede producir `["GEO"]`, `["MPU"]` o `["GEO", "MPU"]`.

- [ventanas.js](ui/js/ventanas.js)
- [generación de ventanas](bridge/api_bridge.py)

### 2.2 Validación y persistencia de ventanas

El backend valida que los sensores sean `GEO` o `MPU`, calcula las muestras disponibles, guarda los rangos de muestras y construye un `WindowRecord` con `sensors`.

- [engine.py](core/windowing/engine.py)
- [models.py](core/windowing/models.py)
- [api_bridge.py](bridge/api_bridge.py)

La selección queda persistida en `Ventanas/windows.json` y en los manifiestos `sismoai-window-selection`.

### 2.3 Etiquetado

El etiquetado conserva la referencia de la ventana y exige una clase binaria confirmada antes de crear el lote:

- [labeling/service.py](core/labeling/service.py)
- [api_bridge.py](bridge/api_bridge.py)

### 2.4 Generación del Dataset

`generate_dataset`:

1. Obtiene las ventanas etiquetadas.
2. Genera Train, Validation y Test.
3. Conserva sensores, rangos y metadatos.
4. Captura snapshots `.npz` por ventana.
5. Guarda el contrato lógico `["samples", "channels", "points"]`.

Evidencia: [api_bridge.py](bridge/api_bridge.py).

Los snapshots se escriben con claves independientes:

```text
GEO_times
GEO_amplitudes
MPU_times
MPU_amplitudes
```

El Dataset auditado contiene ambas señales en Train, Validation y Test.

### 2.5 Configuración del experimento

Modelos expone las siguientes opciones:

```html
<option value="geo_mpu">GEO + MPU (dos señales)</option>
<option value="geo">GEO</option>
<option value="mpu">MPU</option>
```

Evidencia: [modelos.html](ui/views/modelos.html).

La configuración enviada incluye:

```javascript
input: $("models-input").value
```

Evidencia: [modelos.js](ui/js/modelos.js).

La configuración persistida de `cnn_sismos_001` es `geo_mpu`.

### 2.6 Preparación de tensores para entrenamiento

En `start_model_training`, el modo de entrada se traduce así:

```python
sensors = {
    "geo_mpu": ("GEO", "MPU"),
    "geo": ("GEO",),
    "mpu": ("MPU",),
}.get(sensor_mode)
```

Cada señal se interpola a 256 puntos, se normaliza mediante z-score por ventana y canal, y después se apila con `np.stack(channels)`.

Formas esperadas:

```text
geo_mpu: (n_samples, 2, 256)
geo:     (n_samples, 1, 256)
mpu:     (n_samples, 1, 256)
```

El entrenador valida que todas las particiones compartan canales y puntos.

## 3. Construcción de la CNN y determinación de canales

La CNN recibe explícitamente el número de canales:

```python
model = build_network(
    config["architecture"],
    x_train.shape[1],
    ...
)
```

La primera capa usa ese número:

```python
nn.Conv1d(channels, 16, ...)
```

Por tanto:

- `X_train.shape[1] == 2` produce `Conv1d(in_channels=2, ...)`.
- `X_train.shape[1] == 1` produce `Conv1d(in_channels=1, ...)`.

El archivo `architecture.json` se genera usando la forma original de `X_train`.

- [trainer.py](core/models/trainer.py)

El test de arquitectura existente confirma que un tensor de dos canales produce `input_shape: [2, ...]`.

- [test_models.py](tests/test_models.py)

Con el código actual, un entrenamiento nuevo con `config["input"] == "geo_mpu"` y snapshots válidos de GEO + MPU debería producir:

```json
{
  "channels": 2,
  "input_shape": [2, 256]
}
```

El artefacto existente con `channels: 1` no es consistente con ese recorrido actual.

## 4. Registro de arquitectura y reconstrucción

`architecture.json` es la fuente estructural para reconstruir el modelo:

1. Lee `factory_parameters.channels`.
2. Reconstruye `build_network("1d_cnn", channels, points, classes)`.
3. Verifica las capas registradas.
4. Carga los pesos con `strict=True`.

El archivo persistido declara:

```json
"factory_parameters": {
  "channels": 1,
  "points": 256,
  "classes": 2
}
```

Además, la primera convolución declara:

```json
"in_channels": 1
```

Esto confirma que no se trata solo de un metadato incorrecto: los pesos y la estructura reconstruida corresponden a una CNN de un canal.

Evidencia: [architecture.json](Reference/Modelos/cnn_sismos_001/architecture.json).

## 5. Reconstrucción y exportación ONNX

`export_onnx` toma los canales desde `architecture.json`:

```python
sample_shape = (
    1,
    int(params["channels"]),
    int(params["points"])
)
```

El flujo:

1. Lee `architecture.json`.
2. Reconstruye la CNN.
3. Crea una muestra `[1, channels, points]`.
4. Exporta ONNX.
5. Registra la forma en el reporte.

Evidencia: [exporter.py](core/models/exporter.py).

El ONNX auditado contiene:

```text
[batch, 1, 256]
```

En `export_model_pipeline`, la forma esperada por las etapas posteriores se obtiene del ONNX, no de Ventanas ni de los snapshots.

Evidencia: [api_bridge.py](bridge/api_bridge.py).

## 6. Carga y preparación para calibración INT8

`run_post_onnx_stages` carga Train mediante `_load_split_arrays`.

La función vuelve a interpretar la configuración:

```python
sensor_mode = config.get("input", "geo_mpu")
sensors = {
    "geo_mpu": ("GEO", "MPU"),
    "geo": ("GEO",),
    "mpu": ("MPU",),
}.get(sensor_mode)
```

Para `geo_mpu`:

1. Carga GEO.
2. Carga MPU.
3. Reinterpola cada señal a 256 puntos.
4. Normaliza por ventana y canal.
5. Ejecuta `np.stack(channels)`.

Resultado:

```text
x_cal.shape[1:] == (2, 256)
```

Después se compara con la forma del modelo:

```python
expected = tuple(int(v) for v in expected_input_shape)
actual = tuple(int(v) for v in x_cal.shape[1:])
```

Evidencia: [export_pipeline.py](core/models/export_pipeline.py).

La comparación falla antes de llamar a `quantize_static`. Por tanto, la calibración INT8 no es la fuente de la discrepancia; únicamente la detecta.

## 7. Punto de discrepancia

### Primer punto observable

El primer punto donde aparece una discrepancia persistida es el artefacto del modelo:

```text
Experimento: config.input = geo_mpu
Dataset:      snapshots con GEO + MPU
Modelo:       architecture.json channels = 1
```

### Punto donde se manifiesta

La discrepancia se detecta en la comparación de formas de `run_post_onnx_stages`, antes de la cuantización.

### Dónde se pierde la configuración

No hay evidencia suficiente para afirmar que `config["input"]` se pierda en el código actual. El flujo conserva la configuración a través de:

1. UI Modelos.
2. Registro del experimento.
3. `start_model_training`.
4. `train_experiment`.
5. `export_model_pipeline`.
6. `_load_split_arrays`.

Las causas históricas posibles son:

- entrenamiento realizado con una versión anterior;
- ejecución con otra selección y posterior asociación con `geo_mpu`;
- actualización parcial del artefacto o registro;
- asociación con un Dataset diferente al usado originalmente.

No es posible distinguirlas con los archivos disponibles.

## 8. Impacto

El experimento afectado confirmado es `cnn_sismos_001`:

- [cnn_sismos_001.json](Reference/Modelos/cnn_sismos_001.json)
- [training_result.json](Reference/Modelos/cnn_sismos_001/training_result.json)
- [architecture.json](Reference/Modelos/cnn_sismos_001/architecture.json)

También está afectada su exportación `cnn_sismos_001_esp32s3_v1`:

- [cnn_sismos_001_esp32s3_v1.export.json](Reference/Exportaciones/cnn_sismos_001_esp32s3_v1/cnn_sismos_001_esp32s3_v1.export.json)

Si la intención real era utilizar GEO + MPU, el modelo existente requiere reentrenamiento porque:

- la CNN tiene `Conv1d(in_channels=1)`;
- los pesos fueron entrenados para una entrada de un canal;
- el ONNX tiene entrada de un canal;
- no es válido reutilizar esos pesos como modelo de dos canales.

Si la intención real era utilizar solo GEO o solo MPU, primero debe verificarse cuál sensor se utilizó originalmente. Esa intención no puede inferirse con certeza del artefacto actual.

## 9. Corrección propuesta

Sin implementarla en esta fase, los cambios mínimos deberían:

1. Validar la coherencia entre `config["input"]` y la forma de las particiones antes de entrenar.
2. Persistir en `training_result.json` y `architecture.json` el modo de entrada, el orden de sensores, la forma `[channels, points]` y el Dataset ID.
3. Comparar configuración, `architecture.json`, Dataset y ONNX antes de exportar.
4. Mantener la validación de forma previa a calibración y complementarla con una validación explícita de `config.input`.
5. Regenerar el modelo afectado mediante un entrenamiento nuevo si el objetivo es GEO + MPU.

No se recomienda:

- eliminar canales del Dataset;
- truncar `(2, 256)` a `(1, 256)`;
- modificar manualmente `architecture.json`;
- forzar la entrada del ONNX.

Esas acciones romperían la correspondencia entre datos, pesos y arquitectura.

### Correcciones aplicadas

La implementación incorporó las siguientes validaciones y metadatos:

- El entrenamiento resuelve `input`, valida el número esperado de canales y rechaza particiones incompatibles.
- El entrenamiento verifica que cada ventana contenga los sensores solicitados por la configuración.
- `architecture.json` registra `input_mode`, sensores ordenados y `dataset_id`.
- `training_result.json` registra el mismo contrato de entrada.
- La reconstrucción valida la coherencia entre `input_mode`, sensores y `channels` cuando esos metadatos están presentes.
- La exportación ONNX bloquea modelos cuyo número de canales no coincide con la configuración del experimento.
- La calibración INT8 bloquea explícitamente una arquitectura incompatible antes de ejecutar la cuantización.
- La carga de Train y Test verifica que cada ventana contenga los sensores requeridos.

La corrección no modifica ni adapta automáticamente modelos existentes. El artefacto `cnn_sismos_001` debe reentrenarse si se confirma que su entrada prevista era GEO + MPU.

## 10. Pruebas necesarias

### Caso A: solo GEO

Entrada:

```text
config.input = "geo"
```

Esperado:

```text
Dataset:    (N, 1, 256)
CNN:        channels = 1
Arquitectura: [1, 256]
ONNX:       [batch, 1, 256]
Calibración: exitosa
```

### Caso B: solo MPU

Entrada:

```text
config.input = "mpu"
```

Esperado:

```text
Dataset:    (N, 1, 256)
CNN:        channels = 1
Arquitectura: [1, 256]
ONNX:       [batch, 1, 256]
Calibración: exitosa
```

Debe verificarse que GEO no se cargue accidentalmente por defecto.

### Caso C: GEO + MPU

Entrada:

```text
config.input = "geo_mpu"
```

Esperado:

```text
Dataset:    (N, 2, 256)
CNN:        channels = 2
Arquitectura: [2, 256]
ONNX:       [batch, 2, 256]
Calibración: exitosa
```

El orden debe ser estable:

```text
canal 0: GEO
canal 1: MPU
```

### Casos de rechazo adicionales

1. `geo_mpu` con snapshots que solo contienen GEO.
2. `geo` con un ONNX de dos canales.
3. `geo_mpu` con `architecture.json` de un canal.
4. Dataset y experimento con IDs diferentes.
5. Particiones Train, Validation y Test con formas diferentes.
6. Ventanas con sensores distintos dentro del mismo Dataset.

## 11. Archivos involucrados

| Archivo | Responsabilidad |
|---|---|
| [ui/js/ventanas.js](ui/js/ventanas.js) | Captura y envía la selección GEO/MPU |
| [core/windowing/engine.py](core/windowing/engine.py) | Valida sensores, intervalos y calidad |
| [core/windowing/models.py](core/windowing/models.py) | Define `WindowRecord` y conserva `sensors` |
| [bridge/api_bridge.py](bridge/api_bridge.py) | Genera y persiste ventanas, señales y Dataset |
| [core/pipeline/manifests.py](core/pipeline/manifests.py) | Persiste manifiestos de fases |
| [core/labeling/service.py](core/labeling/service.py) | Persiste etiquetas |
| [core/dataset/service.py](core/dataset/service.py) | Construye particiones y manifiesto |
| [ui/views/modelos.html](ui/views/modelos.html) | Expone las opciones de entrada |
| [ui/js/modelos.js](ui/js/modelos.js) | Construye y envía la configuración |
| [core/models/trainer.py](core/models/trainer.py) | Construye, entrena y registra la CNN |
| [core/models/exporter.py](core/models/exporter.py) | Reconstruye y exporta ONNX |
| [core/models/export_pipeline.py](core/models/export_pipeline.py) | Prepara calibración INT8 y evaluación |
| [Reference/Dataset/Sismos_Local_v01.json](Reference/Dataset/Sismos_Local_v01.json) | Dataset auditado |
| [Reference/Modelos/cnn_sismos_001/architecture.json](Reference/Modelos/cnn_sismos_001/architecture.json) | Arquitectura persistida |
| [Reference/Modelos/cnn_sismos_001/training_result.json](Reference/Modelos/cnn_sismos_001/training_result.json) | Resultado y configuración del entrenamiento |
| [Reference/Exportaciones/cnn_sismos_001_esp32s3_v1/cnn_sismos_001_esp32s3_v1.export.json](Reference/Exportaciones/cnn_sismos_001_esp32s3_v1/cnn_sismos_001_esp32s3_v1.export.json) | Metadatos del ONNX |

## Conclusión

La causa está confirmada tanto en el estado persistido como en el código que generaba los tensores: el Dataset y la configuración indican GEO + MPU, pero el artefacto existente indica un solo canal y el flujo de entrenamiento solo apilaba el último sensor debido a una indentación incorrecta. La discrepancia se detectaba durante la validación del contrato antes de entrenar o calibrar. Con la corrección aplicada, `geo_mpu` procesa y apila GEO y MPU; el artefacto antiguo debe reentrenarse si se confirma que su entrada prevista era GEO + MPU.
