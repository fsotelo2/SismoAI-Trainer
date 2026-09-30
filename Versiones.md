# SismoAI Trainer — Historial de versiones

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
