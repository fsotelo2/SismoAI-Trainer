# SismoAI Trainer — Historial de versiones

## [v0.7.0] — Exportación y empaquetado para ESP32-S3

**Fecha:** 2026-10-02  
**Rama de integración:** `main`  
**Rama de origen:** `fase-10-exportar`  
**Versión anterior:** 0.6.0  
**Tipo:** MINOR

**Justificación:** se amplía la exportación intermedia ONNX con un pipeline de cuantización y generación de artefactos para el flujo de despliegue en ESP32-S3.

**Cambios**
- **Added:** exportación ONNX de modelos 1D-CNN reconstruidos desde sus manifiestos y pesos, con comprobación del grafo y paridad numérica opcional frente a PyTorch.
- **Added:** pipeline de exportación para ESP-DL mediante ESP-PPQ, con selección de objetivo y configuración de cuantización, incluyendo W8A8, W8A16 y W16A16 según compatibilidad.
- **Added:** calibración y generación del artefacto cuantizado `.espdl`, junto con archivos de configuración, información y reportes.
- **Added:** evaluación del modelo original sobre el conjunto Test y registro del estado de evaluación cuantizada cuando no está disponible.
- **Added:** empaquetado portable de los artefactos y metadatos de exportación.
- **Added:** módulo Exportar integrado en la navegación, con consulta del experimento, opciones de formato/objetivo, ejecución y detalle de resultados.
- **Changed:** validaciones del contrato de entrada y de los canales GEO/MPU para reducir inconsistencias entre Dataset, modelo, calibración y exportación.

**Verificación**
- Exportación real reportada con objetivo ESP32-S3, formato ESP-DL y cuantización W8A16.
- Artefacto `.espdl` generado (19.216 bytes); entrada declarada `[1, 2, 256]`; calibración con 6 muestras.
- El reporte ONNX indica verificación correcta y paridad numérica aprobada, con error absoluto máximo de aproximadamente `2.38e-7`.
- Evaluación del modelo original en Test: 0 aciertos de 2 muestras. La evaluación del modelo cuantizado figura como no disponible; no se declara equivalencia predictiva.
- El paquete generado es portable, no ejecutable ni firmware. No se declara prueba de inferencia en hardware ESP32-S3 ni ejecución automatizada de pruebas en esta entrega.

**Compatibilidad y límites**
- ESP-DL/ESP-PPQ produce un artefacto destinado al flujo de integración con ESP-IDF; el paquete requiere el entorno y componentes compatibles.
- La exportación completada acredita la generación de artefactos, no el rendimiento, precisión generalizable ni funcionamiento en hardware.
- La evaluación predictiva requiere un conjunto Test representativo y una evaluación del modelo cuantizado; el resultado actual es insuficiente para concluir sobre su precisión.

---

## [v0.6.0] — Registro, reconstrucción y validación estructural de modelos

**Fecha:** 2026-10-01  
**Rama de integración:** `main`  
**Rama de origen:** `fase-10.1-registro-arquitectura`  
**Versión anterior:** 0.5.0  
**Tipo:** MINOR

**Justificación:** se incorpora la base de trazabilidad y reconstrucción de modelos entrenados, como preparación para la exportación posterior a ESP32-S3.

**Cambios**

- **Added:** manifiesto de arquitectura para registrar la estructura del modelo y vincularla con sus artefactos.
- **Added:** reconstrucción de modelos 1D-CNN desde el manifiesto y carga estricta de los pesos guardados.
- **Added:** acción «Validar» para experimentos entrenados, con comprobación del manifiesto, carga de pesos, paso de inferencia y salida finita.
- **Added:** ventana de resultado de validación integrada visualmente en el módulo Modelos.

**Verificación**

- El usuario compartió evidencia de una validación completada con entrada `[1, 256]`, salida `[2]` y los cuatro controles reportados como correctos.
- Se confirmó por consulta al repositorio la presencia del método de validación, su conexión en el puente y la interfaz.
- No se declara ejecución de pruebas automatizadas ni verificación visual posterior al último ajuste del encabezado del modal.

**Compatibilidad**

- Esta fase establece la reconstrucción y validación estructural; no implementa todavía la conversión intermedia, cuantización ni empaquetado para ESP32-S3.
- La prueba de inferencia es una comprobación básica de ejecución, no una evaluación de rendimiento predictivo ni una demostración de equivalencia numérica con el modelo original.

---

## [v0.5.0] — Entrenamiento de modelos y estructura oficial del workspace

**Fecha:** 2026-10-01  
**Rama de integración:** `main`  
**Rama de origen:** `Fase-9-Modelos`  
**Versión anterior:** 0.4.0  
**Tipo:** MINOR

**Justificación:** se incorpora la fase 9, correspondiente al módulo de Modelos y su integración con el Dataset preparado. Se consolida además la estructura de interfaz actualmente validada como oficial.

**Cambios**

- **Added:** módulo Modelos integrado en la navegación y conectado con el Dataset activo.
- **Added:** flujo de configuración y entrenamiento de modelos, con registro de resultados y artefactos asociados.
- **Added:** integración de backend, puente de aplicación y componentes de interfaz para la fase 9.
- **Changed:** actualización de la estructura visual del workspace y de la distribución de las vistas, incluyendo Ventanas, Etiquetado, Dataset y Modelos.
- **Added:** documentación de arquitectura del layout y registros de implementación y validación de la fase 9.

**Verificación**

- Fase 9 validada funcionalmente por el usuario en ejecución local.
- No se declara una nueva ejecución automatizada de pruebas como parte de esta integración.

**Compatibilidad**

- La fase 9 consume el Dataset preparado en la fase anterior.
- Se conserva como oficial la implementación actual de la interfaz validada en la rama de origen.

---

# SismoAI Trainer — Historial de versiones

## [v0.4.0] — Preparación y generación de Dataset

**Fecha:** 2026-09-30  
**Rama de integración:** `main`  
**Rama de origen:** `feature/fase-8-dataset`  
**Versión anterior:** 0.3.0  
**Tipo:** MINOR

**Justificación:** se incorpora el módulo Dataset como nueva etapa del flujo de preparación de datos, posterior a Ventanas y Etiquetado, para organizar las ventanas confirmadas y definir una partición reproducible para entrenamiento, validación y prueba.

**Cambios**

- **Added:** módulo Dataset integrado en la navegación de SismoAI Trainer.
- **Added:** consulta de ventanas existentes y etiquetas confirmadas desde Etiquetado, con métricas de ventanas, clases y eventos de origen.
- **Added:** distribución de clases que refleja las clases principales y las subcategorías de NO_SISMICO.
- **Added:** vista de ejemplos con tabla expandible y desplazamiento interno, sin desplazar las demás secciones del workspace.
- **Added:** filtros visibles de ventanas para consultar todas, confirmadas, pendientes o por clase.
- **Added:** configuración porcentual de entrenamiento, validación y prueba.
- **Changed:** la partición se realiza por evento de origen para mantener juntas las ventanas relacionadas y reducir fuga de información entre conjuntos.
- **Added:** validaciones de preparación, advertencias sobre desbalance de clases y cantidad limitada de eventos independientes.
- **Added:** generación de manifiesto de Dataset con configuración y asignaciones reproducibles, como entrada para la etapa Modelos.
- **Added:** pantalla inicial de Modelos para consultar el Dataset activo.

**Verificación**

- Fase validada funcionalmente por el usuario en ejecución local.
- No se declara una nueva ejecución automatizada de pruebas como parte de esta actualización.

**Compatibilidad**

- Dataset organiza ventanas ya generadas y etiquetadas; no modifica los archivos BIN originales.
- La división se establece por evento de origen, no por ventana individual.
- La etapa Modelos recibe el Dataset preparado; el entrenamiento del modelo no forma parte de esta versión.

---

## [v0.3.0] — Etiquetado de ventanas

**Fecha:** 2026-09-30
**Rama de integración:** `main`
**Rama de origen:** `feature/fase-7-etiquetado`
**Integración:** Pull request #2, merge commit `a92188fd911b178fe40112b3fe8289d90b351037`

**Versión anterior:** 0.2.0  
**Tipo:** MINOR  
**Justificación:** se incorpora el módulo de Etiquetado como nueva capacidad del flujo de preparación de datos, manteniendo las fases anteriores.

**Cambios**

- **Added:** módulo de Etiquetado con modelos de datos, servicio de dominio y persistencia JSON versionada.
- **Added:** integración del backend con PyWebView mediante el puente de API para consultar el espacio de trabajo, recuperar señales por ventana y guardar etiquetas.
- **Added:** vista de Etiquetado integrada en la navegación de la aplicación.
- **Added:** listado de ventanas incluidas desde Ventanas, con filtros de pendientes, etiquetadas y en revisión.
- **Added:** visualización de señales GEO (geófono) y MPU (acelerómetro), con controles independientes.
- **Added:** clasificación principal binaria: `0 = TEMBLOR` y `1 = NO_SISMICO`.
- **Added:** categorías secundarias iniciales para NO_SISMICO: `RUIDO`, `VIBRACIONES`, `GOLPES` e `INDETERMINADO`; el modelo admite categorías textuales extensibles para futuras opciones configurables.
- **Added:** estados de anotación, observaciones de hasta 200 caracteres y acciones para guardar o guardar y continuar con la siguiente ventana.
- **Changed:** presentación de la categoría secundaria en una segunda línea del elemento de ventana cuando aplica.
- **Changed:** codificación visual de clases: sísmico en verde y no sísmico en naranja.
- **Fixed:** numeración visible de eventos desde 1, manteniendo los índices internos desde 0.
- **Fixed:** al limpiar la lista de ventanas, los IDs se reinician desde `W-001` y se eliminan las etiquetas asociadas a los IDs borrados para evitar herencias al reutilizarlos.
- **Added:** botón «Continuar a Dataset», visible en Etiquetado y habilitado únicamente cuando todas las ventanas tienen una clase principal guardada y confirmada.
- **Added:** validaciones de clase, categoría secundaria, estado, observaciones y versión del esquema de etiqueta.
- **Added:** persistencia atómica, restauración de datos compatibles y manejo de cambios sin guardar.
- **Added:** pruebas unitarias para modelos, servicio y restauración.

**Verificación**

- Fase validada funcionalmente por el usuario en ejecución local.
- No se declara una nueva ejecución automatizada de pruebas como parte de esta actualización documental.

**Compatibilidad**

- Se conserva el flujo de trabajo de las fases anteriores; Etiquetado consume las ventanas generadas en la fase Ventanas.

---


## [v0.2.0] — Ventaneo y ajustes de interfaz de Análisis

**Fecha:** 2026-09-30
**Rama de integración:** `main`
**Rama de origen:** `feature/fase-6-ventanas`
**Commits de interfaz recientes:** `4f2e4a4712f4840abdaa0e6831c927162f009c05`, `f0c381e295992c50efa63964f9d12b0543844764`, `eda723b6b822d4006be5343d8776b9d47e14facc`, `6f2d1ff3e5c173a203b8e8334bd3c8c4997d667d`, `44750a1d250acac4e8c3a65744b041847f9056eb`

**Versión anterior:** 0.1.2  
**Tipo:** MINOR  
**Justificación:** se incorpora el módulo de Ventanas como capacidad nueva y compatible, manteniendo las interfaces anteriores.

**Cambios**

- **Added:** módulo de Ventanas con generación de ventanas fijas, deslizantes y selección manual.
- **Added:** configuración de duración, inicio/fin y solapamiento; ventanas vinculadas al archivo, evento e intervalo temporal de origen.
- **Added:** sincronización temporal GEO/MPU y conservación de timestamps originales, sin interpolación.
- **Added:** persistencia JSON versionada de la configuración y resultados de ventaneo, con integración mediante el bridge.
- **Added:** distinción entre selección de ventana (incluir, revisar, excluir) y calidad de señal (aceptada, revisar, bloqueada), con incidencias visibles.
- **Changed:** navegación e iconografía del top bar adaptadas al módulo activo.
- **Changed:** organización de los controles superiores de Análisis en una sola línea cuando el ancho disponible lo permite.
- **Changed:** panel lateral de Análisis adaptable a la pestaña activa, aprovechando el alto disponible; filas más compactas y tipografía ligeramente mayor.
- **Fixed:** eliminación de la acción duplicada «Ver en Análisis» dentro de Datos.
- **Fixed:** ajuste vertical de los botones de la barra inferior a `-7px`.

**Verificación**
- Validación funcional de Ventanas y persistencia reportada durante la revisión de la fase.
- Validación visual de los ajustes recientes de Análisis confirmada por el usuario.
- No se ejecutó una nueva corrida automatizada de pruebas como parte de esta consolidación.

**Compatibilidad**
- No se identifican cambios incompatibles en las interfaces existentes.
- Los archivos BIN originales se mantienen intactos; las ventanas son una colección derivada y trazable.

---

## [v0.1.2] — Limpieza de interacciones en gráficas

**Fecha:** 2026-09-30
**Rama:** `main`
**Commits de código:** `66d1f7bd505f65f70253708cda325f0e2ddffbe5`, `68e508b6a86c4f6050cb055ff1b99707026ed742`

**Tipo:** PATCH

**Cambios**
- **Fixed:** se añadió `Charts.cleanupCanvas()` para cancelar arrastres y liberar la captura del puntero.
- **Fixed:** se añadió limpieza global de interacciones y grupos de sincronización obsoletos.
- **Fixed:** la limpieza se ejecuta antes de cambiar de pestaña, archivo o evento en Análisis.

**Verificación**
- Pruebas automatizadas y validación funcional: no ejecutadas en esta entrega.

---

## [v0.1.1] — Correcciones de compatibilidad en Datos y Análisis

**Fecha:** 2026-09-30
**Rama:** `main`
**Commit de código:** `369f0b7c0f476ede48a7d8bc816458d5c22c882d`
**Commit del registro:** `1ffe3a2536dc12ab836d5b5459ddb8556a1b445e`

**Tipo:** PATCH

**Cambios**
- **Changed:** se implementó la carga paralela de archivos BIN, con progreso incremental y cálculo de hashes en segundo plano.
- **Fixed:** se añadió el alias `errorText` para mantener compatibilidad con `AnalysisService`.
- **Fixed:** se añadió el alias `selectedFilePath` para permitir que `AnalysisService` acceda a la ruta seleccionada.
- Se conserva la compatibilidad de los nombres internos existentes.

**Verificación**
- Pruebas automatizadas y validación funcional con archivos BIN: no ejecutadas en esta entrega.

---

## [v0.1.0] — Shell inicial

**Fecha:** 2026-09-25
**Rama:** `feature/fase-02-shell`
**Commit:** `db330dc75a9920774ef1f5512ef2bc488eef4eeb`

**Descripción**

Versión de partida del proyecto. Desde esta base se ha avanzado en la implementación de las fases iniciales de SismoAI Trainer, incorporando progresivamente la arquitectura de la aplicación, la navegación y el estado global, el motor de datos BIN y los módulos de Proyecto, Datos y Análisis.

**Fases implementadas**

Fase 0 — Arquitectura: definición de la arquitectura técnica y de las reglas de organización del proyecto.

Fase 1 — Sistema de diseño: definición de la estructura visual y los componentes de interfaz con Penpot.

Fase 2 — Shell y estado global: ventana de escritorio, navegación funcional y estado centralizado en Python.

Fase 3 — Motor de datos: lectura, validación y análisis de archivos BIN, con pruebas sobre los archivos de referencia.

Fase 4 — Proyecto y Datos: selección de carpeta fuente, inspección de archivos y visualización de información y eventos.

Fase 5 — Análisis: herramientas de análisis de señales, STA-LTA, frecuencia y espectrograma.

**Estado**

La versión 0.1.0 se conserva como referencia histórica del Shell inicial. Las fases posteriores y sus funcionalidades se registran como evolución del proyecto, no como parte del contenido original de este commit.
