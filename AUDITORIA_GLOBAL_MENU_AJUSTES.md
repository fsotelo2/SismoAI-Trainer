# Auditoría global del menú Ajustes

**Repositorio:** `fsotelo2/SismoAI-Trainer`  
**Commit analizado:** `03ce9eb6d1530ce90ef71c4e566ae9833fa164ac`  
**Rama de referencia:** `main` (el commit analizado coincide con `main`)  
**Fecha de auditoría:** 2026-10-02  
**Alcance:** auditoría de solo lectura del código, la interfaz, el puente,
la persistencia y la documentación funcional existente.

> **Criterio de evidencia.** Las afirmaciones marcadas como **Código** se
> basan en la implementación encontrada. Las marcadas como **Especificación**
> proceden de documentación del repositorio. Las **Inferencias** relacionan
> ambas fuentes. Las **Recomendaciones** son decisiones de diseño para una
> fase posterior y no se consideran funcionalidades existentes.

## 1. Resumen ejecutivo

El repositorio contiene nueve entradas de navegación: Proyecto, Datos,
Análisis, Ventanas, Etiquetado, Dataset, Modelos, Exportar y Ajustes.
Proyecto, Datos, Análisis, Ventanas, Etiquetado, Dataset, Modelos y Exportar
tienen vista, JavaScript y operaciones de backend en distinto grado de
completitud. **Ajustes no está implementado:** aparece en el sidebar y en
`VIEW_META`, pero no existe `ui/views/ajustes.html`; tampoco existe un
servicio `settings`, API del bridge o archivo de preferencias globales.

La navegación intenta cargar todas las vistas mediante
`fetch(\`views/${viewName}.html\`)` y muestra «Vista no encontrada» si la
respuesta no es correcta (`ui/js/app.js:337-363`). Por ello, el estado actual
de Ajustes es **declarado en la interfaz, pero no implementado**. La hoja
`ui/css/ajustes.css` solo contiene un comentario (`ui/css/ajustes.css:1`).

La auditoría no identifica ningún parámetro transversal ya implementado que
cumpla simultáneamente estas condiciones: propiedad global, necesidad de
persistencia, ausencia de un propietario funcional mejor y ausencia de
impacto científico o de reproducibilidad. Por tanto, la estructura
funcional justificada para Ajustes en este commit es **ninguna categoría con
controles**. El menú debe mantenerse vacío/no disponible o quedar pendiente
de una decisión de alcance; no deben trasladarse allí parámetros de Análisis,
Ventanas, Dataset, Modelos o Exportar.

La única configuración persistente con alcance global de usuario es la ruta
de la carpeta de datos. Sin embargo, su propietario funcional es Proyecto:
se selecciona allí, se inspecciona allí y se guarda en `project.json`. No es
una preferencia de aplicación y duplicarla en Ajustes produciría dos
propietarios.

El repositorio no tenía cambios de trabajo ni archivos sin seguimiento
relevantes antes de esta auditoría. La única salida de esta tarea es este
informe.

## 2. Inventario de menús

### 2.1 Proyecto

- **Responsabilidad:** seleccionar la carpeta fuente de datos, inspeccionarla
  y mostrar disponibilidad, cantidad de BIN, eventos y última inspección.
- **Interfaz:** selector de carpeta y resumen en
  `ui/views/proyecto.html:1-131`.
- **Acciones/backend:** `select_data_folder`, `get_project_state` y
  `rescan_project` (`ui/js/bridge.js:27-30`;
  `bridge/api_bridge.py:94-172`).
- **Estado:** implementado para selección, restauración e inspección
  asíncrona. `ProjectService` distingue `empty`, `inspecting`, `available`,
  `no_bin`, `unavailable` y `error` (`core/project/service.py:16-110`).
- **Persistencia:** solo la ruta seleccionada, en
  `%APPDATA%\SismoAI Trainer\project.json` en Windows, mediante
  `core/project/persistence.py:3-59`.
- **Clasificación:** configuración de proyecto/sesión (C), no Ajustes.

### 2.2 Datos

- **Responsabilidad:** listar archivos `.BIN`, mostrar metadatos y calidad,
  seleccionar archivos, filtrar, buscar y paginar.
- **Interfaz:** tabla, búsqueda, filtro, selección y tamaño de página en
  `ui/views/datos.html:1-140`; el tamaño visible por defecto es 50
  (`ui/views/datos.html:68-74`).
- **Acciones/backend:** `scan_files`, `get_quality_summary`,
  `get_file_events`, `select_file` y `get_data_state`
  (`ui/js/bridge.js:33-38`; `bridge/api_bridge.py:192-340`).
- **Estado:** implementado sobre datos reales; la lista y sus métricas son
  derivadas del parser. No se encontró persistencia de filtros, búsqueda,
  página o selección.
- **Clasificación:** filtros y paginación son estado temporal de módulo (B);
  calidad, procedencia y métricas son información de diagnóstico (E).

### 2.3 Análisis

- **Responsabilidad:** inspeccionar señales de eventos válidos, métricas,
  STA/LTA, espectro y espectrograma.
- **Interfaz:** la especificación define los submenús Señales, STA-LTA,
  Espectrograma y Frecuencia (`fase 4 - Estructura menu Análisis.md:15-25`);
  la interfaz activa submenús mediante acciones en `ui/js/app.js:181-260`
  y controles de la vista `ui/views/analisis.html`.
- **Acciones/backend:** series y cálculos por
  `get_channel_series`, `run_stalta`, `run_spectrum` y
  `run_spectrogram` (`ui/js/bridge.js:40-53`;
  `bridge/api_bridge.py:345-570`).
- **Parámetros reales:** STA/LTA, tipo de cálculo, función de ventana,
  rango frecuencial, duración y solapamiento del espectrograma.
  `AnalysisService` los inicializa en memoria
  (`core/analysis/service.py:101-135`) y los modifica mediante
  `set_stalta_parameters`, `set_spectrum_parameters` y
  `set_spectrogram_parameters` (`bridge/api_bridge.py:835-901`).
- **Persistencia:** no se encontró almacenamiento de estos parámetros;
  se pierden al cerrar/recrear el servicio.
- **Clasificación:** configuración propia del análisis (B); los resultados
  y frecuencias son diagnóstico (E). No deben convertirse en Ajustes.

### 2.4 Ventanas

- **Responsabilidad:** generar ventanas fijas/deslizantes o añadir
  intervalos manuales, elegir sensores, revisar calidad y guardar
  selecciones.
- **Interfaz:** modo, archivo/evento, duración, paso, inicio, fin y sensores
  en `ui/views/ventanas.html:1-211`. Los valores visibles iniciales son
  duración 5.0 s, paso 5.0 s, inicio 0.0 s y fin 5.0 s.
- **Acciones/backend:** `generate_windows`, `add_manual_window`,
  `get_windows`, `save_window_selection` y operaciones de selección
  (`ui/js/bridge.js:55-79`; `bridge/api_bridge.py:1600-1815`).
- **Reglas:** `WindowSpec` exige duración y paso positivos, paso igual a
  duración en modo fijo y paso no mayor que duración en modo deslizante
  (`core/windowing/engine.py:23-40`). Las ventanas parciales finales se
  descartan (`core/windowing/engine.py:64-76`) y los sensores válidos son
  GEO y MPU (`core/windowing/engine.py:79-91`).
- **Persistencia:** metadatos derivados en `windows.json`, con configuración,
  procedencia, tiempos, sensores y calidad
  (`core/windowing/persistence.py:1-51`;
  `core/windowing/models.py:42-70`). Las selecciones y manifiestos se
  guardan bajo la carpeta del proyecto cuando existe
  (`bridge/api_bridge.py:1048-1110`).
- **Clasificación:** configuración de operación/proyecto (C); no Ajustes.

### 2.5 Etiquetado

- **Responsabilidad:** revisar cada ventana, asignar clase binaria, categoría
  secundaria cuando aplica, estado de revisión y observaciones.
- **Interfaz:** selección, filtro, sensores visibles, clase, categoría,
  revisión y observaciones en `ui/views/etiquetado.html:1-176`.
- **Acciones/backend:** `get_labeling_workspace`, `get_window_signal`,
  `save_window_label`, lotes y selección de lotes
  (`ui/js/bridge.js:63-79`; `bridge/api_bridge.py:1100-1600`).
- **Reglas:** solo existen `0 = TEMBLOR` y `1 = NO_SISMICO`; la etiqueta
  nula representa pendiente; `INDETERMINADO` solo es categoría secundaria
  de NO_SISMICO (`core/labeling/models.py:1-91`;
  `Fase 7 - Estructura menu Etiquetado.md:8-28`).
- **Persistencia:** JSON versionado y atómico en `labeling.json`
  (`core/labeling/persistence.py:1-53`), además de manifiestos de lotes
  bajo `Etiquetados` (`core/pipeline/manifests.py:51-111`).
- **Clasificación:** configuración y datos de etiquetado (C); no Ajustes.

### 2.6 Dataset

- **Responsabilidad:** elegir ventanas etiquetadas válidas, mostrar
  distribución y advertencias, fijar train/validation/test y generar un
  manifiesto reproducible.
- **Interfaz:** filtros, lote, métricas, distribución, porcentajes y nombre
  en `ui/views/dataset.html:1-249`. Los porcentajes iniciales son 70/15/15.
- **Acciones/backend:** `get_dataset_workspace`, `get_dataset_catalog`,
  `generate_dataset` y selección/eliminación de manifiestos
  (`ui/js/bridge.js:75-100`; `bridge/api_bridge.py:1326-1598`).
- **Reglas:** los ratios deben ser tres valores no negativos que sumen 1;
  la semilla efectiva por defecto es 42; las ventanas se agrupan por
  archivo/evento para evitar fuga cuando hay eventos independientes
  (`core/dataset/service.py:15-67`).
- **Persistencia:** manifiestos JSON con `dataset_id`, `seed`, `ratios`,
  particiones, ventanas, sensores, configuración y advertencias;
  escritura atómica (`core/dataset/service.py:69-115`,
  `bridge/api_bridge.py:1048-1190`).
- **Clasificación:** configuración de dataset/experimento (C); no Ajustes.

### 2.7 Modelos

- **Responsabilidad:** seleccionar dataset, configurar arquitectura y entrada,
  guardar un experimento, entrenar en PC y consultar resultados/historial.
- **Interfaz:** `ui/views/modelos.html:1-318`. Incluye arquitectura,
  framework, sensores, épocas, batch, learning rate, semilla,
  optimizador, pérdida, parada temprana, mejor modelo y ponderación de
  clases.
- **Valores visibles:** nombre `cnn_sismos_001`, arquitectura `1d_cnn`,
  framework `pytorch`, entrada `geo_mpu`, épocas 50, batch 32,
  learning rate 0.001, semilla 42, optimizador Adam, pérdida
  `cross_entropy`, parada temprana activada, mejor modelo activado y
  ponderación desactivada (`ui/views/modelos.html:42-166`;
  `ui/js/modelos.js:20-86,719-727`).
- **Acciones/backend:** `save_model_experiment`, `start_model_training`,
  `get_model_training_state`, `get_model_experiments` y validación
  (`ui/js/bridge.js:80-90`; `bridge/api_bridge.py:1881-2220`).
- **Persistencia:** cada experimento conserva configuración, pesos,
  arquitectura, métricas, historial y resultado en `Modelos/<id>`; el
  entrenamiento registra el contrato de entrada y dataset
  (`core/models/trainer.py:230-390`;
  `Fase 9 - Registro de implementación.md:4-16`).
- **Clasificación:** configuración de experimento/modelo (C); no Ajustes.

### 2.8 Exportar

- **Responsabilidad:** elegir experimento validado, exportar ONNX o ESP-DL,
  cuantizar, calibrar con Train, evaluar con Test, empaquetar y consultar
  historial.
- **Interfaz:** formato, destino, nombre, cantidad de calibración,
  cuantización, normalización y verificación en
  `ui/views/exportar.html:1-167`.
- **Valores/opciones:** destino implementado ESP32-S3; formatos ONNX y
  ESP-DL; cuantización `none`, `onnx_int8`, `w8a8`, `w8a16`, `w16a16`;
  calibración inicial 200 muestras; normalización `experiment` y
  verificación activada (`ui/views/exportar.html:19-87`;
  `ui/js/exportar.js:78-96`).
- **Acciones/backend:** `export_model_onnx`, `export_model_pipeline`,
  `get_export_history`, `delete_export` y `open_export_directory`
  (`ui/js/bridge.js:90-98`; `bridge/api_bridge.py:2258-2465`).
- **Persistencia:** reportes y artefactos bajo `Exportaciones`; el pipeline
  registra formato, destino, cuantización, evaluación y limitaciones
  (`core/models/export_pipeline.py:80-260`).
- **Clasificación:** configuración de exportación/artefacto (C); no Ajustes.

### 2.9 Ajustes

- **Declaración visual:** entrada en `ui/index.html:221-240` y metadatos
  `ui/js/app.js:15-29`.
- **Implementación:** inexistente. No hay `ui/views/ajustes.html`; no hay
  inicializador de vista ni controles.
- **Backend:** no hay servicio, modelo, archivo de configuración ni
  métodos `get_settings`, `set_settings`, `save_settings` o equivalentes.
- **Estado:** pendiente/no implementado (F), no un menú funcional.

## 3. Matriz global de parámetros

La columna «Ubicación» identifica la fuente donde el parámetro es
realmente aceptado o utilizado. Un valor mostrado únicamente en HTML no se
considera persistente hasta que el backend lo recibe y lo registra.

| Parámetro | Tipo/opciones y valor observado | Propietario y ubicación | Alcance/persistencia | Clasificación |
|---|---|---|---|---|
| Carpeta de datos | Ruta; sin valor inicial | Proyecto; `project/service.py:118-217`, `project/persistence.py:31-59` | Global por usuario, pero representa el proyecto/sesión; `project.json` | C |
| Búsqueda y filtro de Datos | Texto, estado y página; página 50 | Datos; `datos/service.py:688-712`, `views/datos.html:68-74` | Estado temporal; no persistido | B |
| STA | `float`, 0.5 s | Análisis; `analysis/service.py:117`, `api_bridge.py:431` | Por análisis/evento; memoria | B |
| LTA | `float`, 5.0 s | Análisis; `analysis/service.py:118`, `api_bridge.py:432` | Por análisis/evento; memoria | B |
| Umbral activación STA/LTA | `float`, 3.0 | Análisis; `analysis/service.py:119`, `api_bridge.py:433` | Por análisis/evento; memoria | B |
| Umbral desactivación | `float`, 1.5 | Análisis; `analysis/service.py:120`, `api_bridge.py:434` | Por análisis/evento; memoria | B |
| Método STA/LTA | `absolute` o `rms`; `absolute` | Análisis; `analysis/service.py:121`, `stalta.py:48-79` | Por análisis/evento; memoria | B |
| Ventana espectral | `hann`, `hamming`, `rectangular`; `hann` | Análisis; `analysis/service.py:123`, `api_bridge.py:865-878` | Por análisis; memoria | B |
| Rango espectral | 20, 40 o Nyquist; 40 Hz observado | Análisis; `analysis/service.py:45-49,125` | Por análisis/evento; memoria | B |
| Duración espectrograma | `float`, 1.0 s | Análisis; `analysis/service.py:133`, `api_bridge.py:892-901` | Por análisis/evento; memoria | B |
| Solapamiento espectrograma | 0–1; 0.5 | Análisis; `analysis/service.py:134-135`, `spectrogram.py:108-115` | Por análisis/evento; memoria | B |
| Sensor de métricas | `geophone` o `mpu`; geophone | Análisis; `analysis/service.py:109`, `api_bridge.py:903-916` | Estado temporal; memoria | B |
| Submenú activo | `senales`, `sta_lta`, `espectrograma`, `frecuencia` | Análisis; `analysis/service.py:110`, `api_bridge.py:918-931` | Estado temporal; memoria | B |
| Modo de ventana | `fixed`/`sliding`; fixed | Ventanas; `windowing/engine.py:23-40`, `api_bridge.py:1684-1707` | Por operación; queda en `window_config` | C |
| Duración de ventana | Segundos positivos; 5.0 s visible | Ventanas; `views/ventanas.html:49-57` | Por operación/proyecto; metadata de ventana | C |
| Paso de ventana | Segundos positivos; 5.0 s visible | Ventanas; `views/ventanas.html:58-66` | Por operación/proyecto; metadata de ventana | C |
| Inicio/fin manual | Segundos dentro del evento; 0.0/5.0 | Ventanas; `views/ventanas.html:76-94`, `engine.py:51-62` | Por ventana; metadata | C |
| Sensores de ventana | GEO/MPU; ambos seleccionados | Ventanas; `engine.py:79-91` | Por ventana; metadata | C |
| Estado de selección | include/review/exclude | Ventanas; `views/ventanas.html:350-375` de `js/ventanas.js` | Por ventana/selección; manifiesto | C |
| Clase principal | 0 TEMBLOR, 1 NO_SISMICO | Etiquetado; `labeling/models.py:8-24` | Por ventana; `labeling.json`/manifiesto | C |
| Categoría secundaria | Texto, solo NO_SISMICO; catálogo UI actual | Etiquetado; `labeling/models.py:60-70`, `views/etiquetado.html:84-93` | Por etiqueta; persistido | C/F para catálogo definitivo |
| Estado de revisión | pending/confirmed/rejected; pendiente inicial | Etiquetado; `labeling/models.py:25-59` | Por etiqueta; persistido | C |
| Observaciones | Texto hasta 200 caracteres | Etiquetado; `labeling/models.py:72-73`, `views/etiquetado.html:99-111` | Por etiqueta; persistido | C |
| Ratios de partición | Tres no negativos, suma 1; 0.70/0.15/0.15 | Dataset; `dataset/service.py:29-43`, `views/dataset.html:128-184` | Por dataset; manifiesto | C |
| Semilla de dataset | Entero; 42 | Dataset; `dataset/service.py:39,81` y `api_bridge.py:1326` | Por dataset; manifiesto | C |
| Nombre de dataset | Texto sanitizado, hasta 80 | Dataset; `api_bridge.py:1058-1070,1326-1360` | Identidad/versionado del dataset | C |
| Arquitectura | 1D-CNN, feature classifier, baseline | Modelos; `views/modelos.html:50-58`, `trainer.py:61-89` | Por experimento; archivos del modelo | C |
| Entrada/sensores | geo_mpu, geo, mpu | Modelos; `trainer.py:17-27`, `views/modelos.html:66-72` | Contrato del experimento/modelo | C |
| Épocas | Entero 1–10000; 50 | Modelos; `views/modelos.html:96-105`, `trainer.py:278-285` | Por experimento; persistido | C |
| Batch size | Entero 1–4096; 32 | Modelos; `views/modelos.html:106-115`, `trainer.py:286-289` | Por experimento; persistido | C |
| Learning rate | Finito >0 y ≤1; 0.001 | Modelos; `views/modelos.html:116-126`, `trainer.py:290-293` | Por experimento; persistido | C |
| Semilla de entrenamiento | Entero no negativo; 42 | Modelos; `views/modelos.html:127-137`, `trainer.py:266-274` | Por experimento; persistido | C |
| Optimizador | Adam/SGD/AdamW; Adam | Modelos; `views/modelos.html:139-146`, `trainer.py:300-310` | Por experimento; persistido | C |
| Pérdida | `cross_entropy` implementada | Modelos; `views/modelos.html:147-153`, `trainer.py:294-298` | Por experimento; persistido | C |
| Parada/mejor/ponderación | Booleanos; true/true/false | Modelos; `views/modelos.html:157-166`, `trainer.py:350-356` | Por experimento; persistido | C |
| Formato de exportación | ONNX/ESP-DL; ONNX | Exportar; `views/exportar.html:19-31`, `export_pipeline.py:80-93` | Por exportación; reportes/artefactos | C |
| Destino | ESP32-S3 | Exportar; `views/exportar.html:32-40` | Por exportación/artefacto | C |
| Nombre de exportación | Texto, hasta 100; valor visible definido en UI | Exportar; `views/exportar.html:41-45` | Identidad del artefacto | C |
| Muestras de calibración | Entero 1–10000; 200 | Exportar; `views/exportar.html:57-63`, `export_pipeline.py:39-45` | Por exportación; reporte | C |
| Método de cuantización | none/onnx_int8/w8a8/w8a16/w16a16 | Exportar; `views/exportar.html:72-78`, `export_pipeline.py:105-147` | Por exportación/modelo | C |
| Normalización | `experiment` | Exportar; `views/exportar.html:80-83`, `export_pipeline.py:94-96` | Contrato del modelo/exportación | C |
| Verificación equivalencia | Booleano; activada | Exportar; `views/exportar.html:84` | Por exportación; reporte | C |
| Cursor, zoom y paneo | Números de viewport | Análisis; `api_bridge.py:933-1019` | Estado temporal de UI | B |
| Conteos, frecuencias, calidad, métricas | Valores calculados | Datos/Análisis/Ventanas/Dataset | Consulta; no modificables | E |
| `APPDATA`, schema, límites técnicos y formato JSON | Constantes internas | Servicios de persistencia y dominio | Código; no controles de usuario | D |

### 3.1 Resultado de la clasificación A–F

- **A. Ajustes globales:** ninguno justificado por la implementación actual.
- **B. Configuración propia del módulo:** filtros temporales de Datos,
  parámetros científicos de Análisis, estado visual de Análisis y controles
  de operación no registrados como entidad de proyecto.
- **C. Configuración de proyecto/experimento:** carpeta y contexto de
  Proyecto, ventanas y selecciones, etiquetas, datasets, experimentos y
  exportaciones.
- **D. Constantes internas:** nombres de schema, límites de validación,
  formatos de archivo, valores técnicos del motor y reglas de seguridad de
  rutas.
- **E. Información de diagnóstico:** estados, conteos, frecuencias,
  métricas, advertencias, calidad, compatibilidad y resultados.
- **F. Pendiente de definición:** catálogo definitivo de categorías
  secundarias, criterios de elegibilidad, tolerancias de conversión,
  decisiones científicas de ventanas/calidad y cualquier futuro alcance de
  preferencias globales.

## 4. Configuraciones transversales identificadas

### 4.1 No existe una configuración transversal implementada

El documento raíz describe un futuro paquete `settings/` en la arquitectura
objetivo (`Arquitectura_Raiz_SismoAI.md:30-45`), pero el directorio no existe
en el commit auditado. El puente implementado expone operaciones de Proyecto,
Análisis, Ventanas, Dataset, Modelos y Exportar, pero no una API de ajustes
globales (`ui/js/bridge.js:27-117`; `bridge/api_bridge.py:48-81`).

No se encontraron preferencias persistentes de tema, idioma, densidad,
formato de interfaz, directorios por defecto, comportamiento de inicio,
confirmaciones o logging. Proponerlas como controles confirmados violaría el
alcance de la auditoría: serían diseño nuevo, no funcionalidades auditadas.

### 4.2 Ruta de datos: global por almacenamiento, propia de Proyecto

`project.json` está ubicado en la configuración del usuario y sobrevive a
sesiones (`core/project/persistence.py:31-59`). Eso le da alcance global de
almacenamiento, pero no lo convierte en una preferencia transversal:
Proyecto lo selecciona, lo valida, lo restaura y lo usa para configurar las
carpetas derivadas (`core/project/service.py:118-217`;
`bridge/api_bridge.py:1048-1090`). La propiedad debe permanecer en Proyecto.

### 4.3 Parámetros de Análisis compartidos entre cálculos, pero no globales

El servicio de Análisis reutiliza su estado para STA/LTA, espectro y
espectrograma y conserva un contexto de archivo/evento
(`core/analysis/service.py:101-135`). Esto es transversal **dentro de
Análisis**, no entre módulos. Son parámetros científicos dependientes de una
señal y pueden cambiar la interpretación o la detección candidata; deben
seguir en Análisis y, si algún día se persisten, hacerlo como configuración
del análisis/evento.

### 4.4 Identidad y trazabilidad de pipeline

Ventanas, etiquetas, datasets, modelos y exportaciones intercambian
manifiestos y referencias de procedencia. `core/pipeline/manifests.py:51-111`
genera identificadores y archivos inmutables de fase. Esta relación es
transversal como arquitectura de datos, pero no es una preferencia: forma
parte de la trazabilidad y reproducibilidad (C).

## 5. Duplicidades y conflictos

| Posible solapamiento | Evidencia | Propietario recomendado | Riesgo |
|---|---|---|---|
| Carpeta de datos en Proyecto vs Ajustes | Solo Proyecto tiene selector, restauración y `project.json` (`project/service.py:118-217`) | Proyecto | Dos rutas activas o divergencia entre sesión y preferencia |
| Semilla 42 de Dataset vs semilla 42 de Modelos | `dataset/service.py:39` y UI de Modelos `views/modelos.html:127-137` | Dataset para particionado; Modelos para entrenamiento | Confundir reproducibilidad de particiones con reproducibilidad de pesos |
| Ratios Dataset vs particiones mostradas en Modelos | Dataset genera y guarda `ratios`; Modelos declara que consume la partición (`views/modelos.html:17-33`) | Dataset | Redistribución accidental y pérdida de trazabilidad |
| Sensores de Ventanas vs entrada de Modelos | Ventanas conserva sensores por ventana; Modelos resuelve `geo_mpu`, `geo`, `mpu` (`trainer.py:17-27`) | Ventanas registra disponibilidad; Modelo fija su contrato | Entradas incompatibles; el backend ya valida canales |
| Normalización en Exportar vs preprocesamiento del experimento | Exportar solo acepta `experiment` (`export_pipeline.py:94-96`); entrenamiento registra preprocesamiento (`trainer.py:369-390`) | Experimento/Exportar como copia validada | Alterar datos de exportación sin una nueva versión |
| Categorías UI de Etiquetado vs taxonomía documentada | UI ofrece RUIDO, VIBRACIONES, GOLPES e INDETERMINADO (`views/etiquetado.html:84-93`), mientras la especificación dice que el catálogo está pendiente (`Fase 7 - Estructura menu Etiquetado.md:36-48`) | Etiquetado, sujeto a aprobación | Convertir ejemplos en catálogo oficial |
| `labeling.json` global vs lotes dentro del proyecto | Servicio por defecto usa configuración de usuario (`labeling/persistence.py:10-15`); `ApiBridge` configura etiquetas dentro de `Etiquetados` cuando hay proyecto (`api_bridge.py:1048-1090`) | Etiquetado/proyecto | Dos fuentes de verdad si se mezclan restauración global y manifiestos |
| `windows.json` global vs `Ventanas/windows.json` del proyecto | `windowing/persistence.py:10-15` define ruta global; `ApiBridge` reemplaza la ruta al seleccionar proyecto (`api_bridge.py:1048-1068`) | Ventanas/proyecto | Estado anterior disponible fuera del proyecto activo |

No se recomienda centralizar estos parámetros en Ajustes. Cuando hay una
configuración heredada o un valor por defecto, debe copiarse al registro de
la operación si forma parte de su reproducibilidad, no mantenerse como una
referencia mutable global.

## 6. Persistencia y arquitectura

### 6.1 Mecanismos existentes

1. **Configuración de usuario:** JSON versionado en `%APPDATA%\SismoAI
   Trainer`, utilizado por Proyecto y, por defecto, por Ventanas y
   Etiquetado (`core/project/persistence.py:31-59`;
   `core/windowing/persistence.py:10-51`;
   `core/labeling/persistence.py:10-53`).
2. **Datos dependientes del proyecto:** carpetas `Ventanas`, `Etiquetados`,
   `Dataset`, `Modelos` y `Exportaciones`, configuradas a partir de la ruta
   seleccionada (`bridge/api_bridge.py:1048-1090`).
3. **Manifiestos de fase:** JSON con schema, versión, identificador,
   procedencia y registros; escritura atómica en
   `core/pipeline/manifests.py:36-111`.
4. **Artefactos de modelos y exportación:** configuración, pesos,
   arquitectura, métricas y reportes en el árbol del proyecto
   (`core/models/trainer.py:369-390`;
   `core/models/export_pipeline.py:242-260`).

### 6.2 Consecuencias para un futuro Ajustes

Si posteriormente se aprueba una preferencia global real, el patrón
existente sugiere un JSON versionado bajo `%APPDATA%\SismoAI Trainer`, con
lectura tolerante de ausencia/versión incompatible y escritura atómica. No
es necesario introducir una tecnología nueva. La implementación tendría que
definir primero:

- esquema y versión de preferencias;
- qué valores son preferencias de UI y cuáles son defaults de operación;
- precedencia entre preferencia, proyecto y experimento;
- migración y restablecimiento;
- API explícita del bridge y pruebas.

Esto es una dependencia técnica futura, no una recomendación para exponer
ahora los parámetros existentes.

## 7. Estructura propuesta de Ajustes

### Resultado auditado

**No se propone ninguna categoría funcional con controles en este commit.**

La razón no es que falten candidatos técnicos, sino que todos los
parámetros modificables encontrados ya tienen propietario:

- los parámetros científicos pertenecen a Análisis;
- duración, paso y sensores pertenecen a Ventanas;
- ratios y semilla de particionado pertenecen a Dataset;
- arquitectura, hiperparámetros y semilla de entrenamiento pertenecen al
  experimento de Modelos;
- cuantización, calibración, destino y formato pertenecen a Exportar;
- etiquetas y estados pertenecen a Etiquetado;
- la ruta de datos pertenece a Proyecto.

La UI de Ajustes puede permanecer fuera del flujo hasta que exista una
decisión aprobada que introduzca una preferencia transversal respaldada por
una necesidad concreta. Si se conserva la entrada de navegación durante
esta fase, el criterio mínimo de aceptación debería ser no presentar
controles ficticios ni valores que no tengan API y persistencia.

### Dependencias para cualquier implementación posterior

1. Aprobación explícita del parámetro global y de su alcance.
2. Servicio `settings` separado de Proyecto y de los servicios científicos.
3. Esquema JSON versionado y persistencia atómica reutilizando los patrones
   existentes.
4. Métodos `get_settings`/`set_settings` o contrato equivalente en
   `bridge/api_bridge.py` y `ui/js/bridge.js`.
5. Precedencia documentada y pruebas de reinicio, cambio de proyecto y
   compatibilidad de versiones.

## 8. Parámetros excluidos de Ajustes

- **Carpeta de datos:** ya es propiedad de Proyecto y su modificación
  cambia el contexto de datos, no una preferencia visual.
- **STA/LTA, espectro y espectrograma:** son parámetros científicos y
  dependientes del evento; moverlos rompería la trazabilidad de análisis.
- **Duración, paso, modo y sensores de Ventanas:** definen la unidad de
  datos y se guardan en la configuración de cada ventana.
- **Clases, categorías, revisión y observaciones:** forman parte de la
  anotación y de su auditoría.
- **Ratios y semilla del Dataset:** afectan la composición reproducible de
  train/validation/test.
- **Arquitectura, canales, épocas, batch, learning rate, optimizador,
  pérdida, parada temprana, ponderación y semilla:** constituyen el
  experimento y deben conservarse con el modelo.
- **Formato, destino, calibración, cuantización, normalización y
  equivalencia de Exportar:** describen el artefacto de salida y su
  compatibilidad; no son preferencias generales.
- **Rangos, páginas, zoom, paneo, cursor, conteos, frecuencias, calidad y
  métricas:** son estado temporal o información de diagnóstico.
- **Límites, nombres de schema, rutas sanitizadas y valores de seguridad:**
  son constantes internas y no controles de usuario.
- **Tema, idioma, densidad, directorios por defecto, confirmaciones y
  logging:** no se encontraron implementados; no se incorporan como
  opciones confirmadas por analogía con otras aplicaciones.

## 9. Pendientes de definición

1. Decidir si el menú Ajustes debe retirarse temporalmente, mostrarse como
   no disponible o implementarse solo cuando exista una preferencia global
   aprobada.
2. Si se pretende añadir preferencias futuras, definirlas una por una con
   alcance, persistencia, precedencia y propietario.
3. Resolver la diferencia entre persistencia global por defecto de
   `windows.json`/`labeling.json` y la persistencia bajo la carpeta del
   proyecto que configura `ApiBridge`.
4. Aprobar el catálogo de categorías secundarias de Etiquetado. La
   especificación lo deja abierto, aunque la interfaz ya muestra opciones.
5. Definir criterios definitivos de elegibilidad y tratamiento de calidad
   para Dataset.
6. Validar valores científicos de ventanas, sincronización, calidad y
   tolerancias de exportación antes de convertirlos en configuraciones
   reproducibles.
7. Resolver las discrepancias documentales de arquitectura: el documento
   raíz describe una arquitectura objetivo con `settings/`, mientras el
   código actual usa HTML/CSS/JavaScript en PyWebView y no contiene ese
   servicio (`Arquitectura_Raiz_SismoAI.md:6-45`;
   `ui/index.html:1-18`; `ui/js/bridge.js:1-8`).

## 10. Recomendación de implementación

### Alcance mínimo recomendado

No implementar controles de Ajustes en la siguiente fase. Mantener la
propiedad actual de los parámetros y corregir, como decisión de producto,
la navegación hacia una vista inexistente antes de presentar el menú como
funcional.

### Orden de trabajo

1. Aprobar el resultado de esta auditoría y decidir el estado visual del
   menú.
2. Si se decide conservarlo, eliminar la apariencia de funcionalidad no
   implementada o crear una vista explícitamente informativa sin controles
   ficticios.
3. Solo tras aprobar una preferencia transversal concreta, crear su
   servicio, esquema, bridge, vista y pruebas.
4. Registrar los valores efectivos en el manifiesto de proyecto,
   experimento o exportación cuando afecten reproducibilidad; no depender
   de una preferencia mutable para reconstruir resultados históricos.

### Criterios de aceptación

- Cada control de Ajustes tiene una API backend, validación, persistencia y
  propietario documentado.
- Ningún parámetro científico o de reproducibilidad aparece duplicado en
  Ajustes y en su módulo.
- Cambiar de proyecto no mezcla preferencias con datos, ventanas,
  etiquetas, datasets o modelos.
- Reiniciar la aplicación restaura únicamente configuraciones autorizadas y
  no inventa valores ante archivos ausentes o incompatibles.
- Los manifiestos históricos siguen siendo autosuficientes y no dependen
  de la configuración global actual.
- Si no se aprueba ningún parámetro transversal, Ajustes no muestra
  controles.

