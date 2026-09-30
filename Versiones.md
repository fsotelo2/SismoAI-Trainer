# SismoAI Trainer — Historial de versiones

## [v0.3.0] — Etiquetado de ventanas

**Fecha:** 2026-09-30  
**Rama de origen:** `feature/fase-7-etiquetado`  
**Integración:** Pull request #2, merge commit `a92188fd911b178fe40112b3fe8289d90b351037`

**Tipo:** MINOR

**Cambios**
- **Added:** módulo de Etiquetado con modelos, servicio de dominio, persistencia JSON versionada e integración mediante PyWebView.
- **Added:** listado de ventanas incluidas, filtros de estado y visualización sincronizada de señales GEO/MPU.
- **Added:** clasificación binaria `0 = TEMBLOR` y `1 = NO_SISMICO`, estados de anotación y observaciones.
- **Added:** categorías secundarias iniciales para NO_SISMICO: `RUIDO`, `VIBRACIONES`, `GOLPES` e `INDETERMINADO`; modelo preparado para admitir categorías personalizadas.
- **Added:** categoría secundaria visible en una segunda línea del listado de ventanas.
- **Added:** botón «Continuar a Dataset», habilitado únicamente cuando todas las ventanas tienen etiquetas guardadas y confirmadas.
- **Changed:** identificación visual de NO_SISMICO en naranja y TEMBLOR en verde.
- **Fixed:** numeración de eventos presentada desde 1 sin alterar los índices internos.
- **Fixed:** «Limpiar lista» reinicia los IDs de ventanas desde `W-001` y elimina las etiquetas ligadas a los IDs limpiados.
- **Improved:** control de cambios sin guardar, restauración y validación de esquema.

**Verificación**
- Fase validada funcionalmente por el usuario en ejecución local.
- Se incorporaron pruebas unitarias para modelos y servicio de etiquetado. No se ejecutó una nueva corrida automatizada durante esta integración.

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
