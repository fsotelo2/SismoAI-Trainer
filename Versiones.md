# SismoAI Trainer — Version History



## [v0.1.0] — Shell inicial





**Date:** 2026-09-25

**Branch:** `feature/fase-02-shell`

**Commit:** `db330dc75a9920774ef1f5512ef2bc488eef4eeb`



### Objective



Static application Shell as the visual and structural baseline: window frame, sidebar navigation layout, topbar, workspace, status bar, and module view stubs. No behavior, no data processing.



### Architecture changes



None (initial commit chain `aa9ea1c` → `db330dc`). Structure created:



* `main.py` — thin entry, delegates to `shell/window.py`.

* `shell/` — `window.py` (QGuiApplication + QQmlApplicationEngine, `nav` context property), `navigation.py` (`NavigationController`: 9 fixed modules, `currentModule`/`currentView`/`setModule`, unknown modules ignored).

* `qml/Main.qml` — 1440x900 literal geometry, sidebar/topbar/workspace/status bar, bundled Inter font.

* `qml/views/*.qml` — 9 stubs over a static `ModulePlaceholder` card.

* `assets/icons/`, `fonts/`, `SismoAITrainer.qmlproject*`.



### Functional changes



None beyond static rendering. Known baseline behavior (verified by inspection):



* Sidebar items and theme toggle have no click handlers; `nav` is exposed but never referenced in QML.

* Active module, topbar title, status pill (`Listo`) and status bar (`Sistema listo`) are hardcoded.

* The QML root is a bare `Rectangle`, so the baseline launches an event loop with no visible OS window.



### UI/QML changes



Initial Shell per Penpot structure. No dynamic bindings, models, or actions.



### Tests performed and exact results



* `python -m unittest discover -s tests` (baseline `tests/test_navigation.py`): **6/6 OK** (verified 2026-09-26 at this commit).

* `python tests/smoke_qml.py` (offscreen): `rootObjects: 1`, **QML_SMOKE_OK**, zero warnings (verified 2026-09-26 at this commit).



### GUI verification



No display-based visual verification performed; headless evidence only (see above). Baseline renders no OS window by construction.



### Known issues and limitations



* Navigation unwired (clicks do nothing); duplicate-navigation risk if QML adds its own controller — banned by architecture.

* Dead theme-toggle control (no handler, no owner).

* No project, data, analysis, or downstream functionality.



### Protected files and data integrity



* `Reference/Especificacion_Dataset.md`, `Reference/DATASET_FORMATO.md`, `Reference/DAT_000001.BIN`, `Diseños/` contents intact.

* No parser or scientific code exists at this commit; nothing to preserve beyond the reference materials.



### Next milestone



Phase 0 architecture definition → Phase 2 Shell + AppState (Python-owned navigation and global status, one `app` QML object, focused tests, real GUI verification).

## [v0.1.1] — 1180x740 Views (baseline)





**Date:** 2026-09-26

**Branch:** `feature/fase-02-shell`

**Commit:** (uncommitted working-tree change on top of `db330dc`; no commit per project rules)



### Objective



Fix the root size of all module views to the workspace content area (1180x740) as the visual baseline for future screens.



### Architecture changes



None.



### Files and modules created, modified, or removed



Modified (root size only, behavior untouched):



* `qml/views/Proyecto.qml`, `Datos.qml`, `Analisis.qml`, `Ventanas.qml`, `Etiquetado.qml`, `Dataset.qml`, `Modelos.qml`, `Exportar.qml`, `Ajustes.qml` — each root now declares `width: 1180`, `height: 740` before the existing `anchors.fill: parent`.



### Functional changes



None. Explicit sizes match the `workspaceContent` area (1180x740) already defined in `qml/Main.qml`; at runtime `anchors.fill` still governs layout.



### UI/QML changes



View roots carry an explicit 1180x740 size (relevant for Qt Design Studio canvases). No geometry, color, typography, or structure changes.



### Tests performed and exact results



* `python -m unittest discover -s tests`: **6/6 OK**.

* `python tests/smoke_qml.py` (offscreen): `rootObjects: 1`, **QML_SMOKE_OK**, zero warnings.

* Verified 18/18 dimension lines (9 × width + 9 × height) across the 9 views.



### GUI verification



Headless only (see above). No display-based verification; baseline launches no OS window by construction.



### Known issues and limitations



Same as v0.1.0 (navigation unwired, dead theme toggle, no domain functionality).



### Protected files and data integrity



No specs, Penpot files, or BIN files touched. `git status` shows only the 9 view files modified (plus pre-existing protected/working-tree entries).



### Next milestone



Phase 0 architecture approval → Phase 2 Shell + AppState.



## [v0.2.0] — AppState and Shell integration





**Date:** 2026-09-26

**Branch:** `feature/fase-02-shell`

**Commit:** `93712d6d09d2105bdba2849281527dc1a79938aa`

**Tag:** `v0.2.0`



### Objective



Python-owned application state, functional navigation, global status, and a visible Qt desktop window, per `docs/ARCHITECTURE.md` and approved decisions D1–D5.



### Architecture changes



* New `app/` package: `app/state.py` (`AppState`, single `app` QML context object; owns `NavigationController`, global status/error, service registry; no domain logic).

* `shell/window.py`: `QQuickView` host (1440x900, titled), exposes only `app`, explicit QML error reporting.

* `qml/Main.qml`: all 9 sidebar clicks → `app.setModule`; active styling, topbar title, status pill/bar bound to Python; dead theme toggle removed; workspace `Loader` bound to `app.currentView`. Geometry, colors, typography unchanged.

* `REGLAS_AGENTE.md` does not exist in the repository; architecture doc + task directive were used instead.



### Files and modules created, modified, or removed



* Created: `app/__init__.py`, `app/state.py`, `tests/test_appstate.py`, 9 icon state variants under `assets/icons/` (`*-active.svg` blue + `Proyecto-inactive.svg` gray; mechanical fill swap, originals untouched).

* Modified: `shell/window.py` (QQuickView host, `app`-only context, resizable window), `qml/Main.qml` (bindings + icon state swap + fluid width layout), `qml/components/ModulePlaceholder.qml` (blue module logo left of the module name; structure and texts unchanged), `tests/smoke_qml.py` (uses `app` context), `docs/ARCHITECTURE.md` (§3 contract + rules reflect implementation), `Versiones.md` (this entry).

* Removed: theme-toggle block from `qml/Main.qml`; `nav` QML context object.



### Functional changes



* Sidebar navigation works end-to-end (Python-owned).

* Invalid module requests keep state and report `errorText="Módulo desconocido: <name>"` (status bar shows it, pill turns red).

* Status pill/bar reflect `statusText`/`statusKind`/`statusDetail`/error state.



### UI/QML changes



Bindings only (see above). No new screens, no mock content, no redesign. v0.1.1 view dimensions (1180x740) preserved.



### Tests performed and exact results



* `python -m unittest discover -s tests`: **18/18 OK** (6 navigation + 12 AppState: defaults, valid/invalid navigation + notifications, status/error/busy notifications, service registry, context exposes only `app`, window dimensions, sidebar-click navigation, status binding, zero QML warnings).

* `python tests/smoke_qml.py`: `rootObjects: 1`, **QML_SMOKE_OK**, zero warnings.



### GUI verification



Display-based verification performed in this environment:



* Window exposed and visible at 1440x900 via `QQuickView`; window resizable with fluid layout — sidebar fixed at 240px left, topbar/workspace/loader/statusbar stretch right; status bar pinned to the bottom keeping 72px height while the workspace grows (verified maximized at 1920x1010: workspace 850px, statusbar y=938, clicks navigate).

* Real synthetic click on the Datos sidebar item → module `Datos`, topbar updated, workspace loader holds a live item; active icon swaps to blue `*-active.svg`, inactive icons stay gray.

* Invalid `setModule` keeps state; status bar displays the error text.

* No runtime errors or QML warnings during the above.



### Known issues and limitations



* No domain services yet (Phase 3+); `busy` flag and service registry unused.

* View stubs unchanged (placeholders only).

* `SismoAITrainer.qmlproject.qtds` carries a pre-existing local modification, untouched.



### Protected files and data integrity



No specs, Penpot files, or BIN files touched. v0.1.1 view changes intact (9 files still modified with identical dimension lines).



### Next milestone



Phase 3 — Data Engine (per `Arquitectura de trabajo.md`), only after Phase 2 approval.



### Validation



**Status: VALIDATED and APPROVED as v0.2.0** — Initial Shell + Phase 2 approved by the project owner on 2026-09-26 (visual check on the running app, navigation, fluid layout, icon states, and header logos confirmed). Release closed; next changes target `0.3.0`.



## [0.3.0] — Data Engine





**Date:** 2026-09-26

**Branch:** `feature/fase-02-shell`

**Tag:** `v0.3.0`

**Status: VALIDATED and APPROVED** — validated against the 3 Reference BINs (43 valid events, CRC/commit 100%); specs updated with the verified corpus under explicit owner authorization.



### Objective



Validated Python BIN v2 processing layer per `Reference/Especificacion_Dataset.md`: parse, validate, analyze, and summarize the 3 Reference BINs without modifying them.



### Architecture changes



New `dataengine/` package (read-only pipeline, no UI, no state):



* `layout.py` — sizes, magics, versions, sensor ids.

* `records.py` — `ContainerHeader`, `Metadata`, `EventHeader`, `SensorRecord`, `EventResult`, `FileResult`, `FrequencyCheck`.

* `crc.py` — CRC-32 IEEE.

* `parser.py` — sequential `parse_file`; trailing incomplete events mark truncation without inventing samples; historical 40-byte layouts reported, never converted.

* `analysis.py` — per-sensor separation, sequence gaps, timestamp reversals, interval stats, span-based observed frequency, MPU magnitude check (report-only findings with file/event traceability).

* `quality.py` — `EventQuality`/`FileQuality` counts (valid/invalid/truncated, CRC/commit failures, records by sensor, per-event frequencies).

* `series.py` — geophone velocity/voltage/ADC + MPU magnitude series with sample-level traceability.

* `session.py` — `discover` + `load_session` multi-file aggregation (malformed files reported, unrelated files ignored).



### Files and modules created, modified, or removed



Created: `dataengine/` (8 modules), `tests/test_bin_parser.py`, `tests/test_data_analysis.py`, `tests/test_signal_series.py`, `tests/test_quality_summary.py`, `tests/test_session.py`.



### Functional changes



None in the application (Shell untouched). New engine capability only.



### UI/QML changes



None.



### Tests performed and exact results



* `python -m unittest discover -s tests`: **70/70 OK** (6 navigation + 64 engine: 20 parser incl. 9 acceptance rules, 8 analysis, 11 series, 9 quality, 7 session, plus synthetic edge cases for every rule).

* Real-data verification (read-only): 20+20+3 = 43 valid events, 90204 records, CRC/commit 100%, no truncation, geo 88.22–88.23 Hz, MPU ~100 Hz span-based with bursty jitter (median misleading — documented in code), zero findings in BIN 1, BIN mtimes/sizes unchanged.

* `python tests/smoke_qml.py`: **QML_SMOKE_OK**, zero warnings.



### GUI verification



Not applicable (no UI changes; Shell launch path untouched).



### Known issues and limitations



* `aggregate_entries` re-parses files once for per-event frequencies (documented; Phase 4 can thread analyses through).

* Spec §9 rule 3 says the payload must be a "multiple of 40" while §8/§10 require 76 for the new layout; the parser enforces 76 when `META.indicadores & 0x04` is set (true for all 3 BINs). Spec text untouched — flagged, not fixed.

* Spec §12 says DAT_000001.BIN has "five events"; the file parses to 20 valid events. Spec text untouched — flagged, not fixed.

* No JSON session serialization yet (deferred to Phase 4 if needed).



### Protected files and data integrity



No specs, Penpot files, or BIN files modified (sizes/mtimes verified unchanged). `main.py`, `shell/`, `app/`, `qml/` untouched.



### Next milestone



Phase 4 — Project and Data (per `Arquitectura de trabajo.md`), only after approval.



## [v0.4.0] — Project: source folder



**Date:** 2026-09-26

**Branch:** `feature/fase-02-shell`

**Commit:** `7c84d6ff38ebffd27c9adae63329f749098e041b`

**Tag:** `v0.4.0` (annotated; local only)

**Status:** VALIDATED AND APPROVED by the project owner on 2026-09-26. The release is committed and tagged locally; it has not been pushed because no Git remote is configured.



### Objective



Implement the approved Project screen for selecting and retaining the BIN source folder, and report its availability and the summaries already produced by existing modules.



### Architecture and behavior



* `ProjectService` owns the path, persistence, states, inspection, and summary values. The folder path is stored as JSON in the application's configuration location; only the path is persisted, never BIN contents.

* The folder is inspected at startup when a saved path exists and after each selection. The timestamp is updated only after a successful inspection; there is no periodic refresh.

* Content inspection runs in a worker so it does not block the interface. BIN files are read through `dataengine` and are not modified.

* Project contains only the header, folder block, and four summary cards. BIN and event counts come from the existing engine; windows and labels remain pending until their modules produce those values.

* `AppState` exposes the Project service and reflects inspection through `busy`; QML renders the values and forwards folder-selection actions.



### Files created or modified



* Created: `qml/components/SummaryCard.qml`, `assets/icons/{FolderOutline,BinFile,Eventos,VentanaResumen,EtiquetaResumen}.svg`, `tests/test_project.py`.

* Modified: `project/service.py`, `app/state.py`, `qml/views/Proyecto.qml`, `Versiones.md`.

* Other files that were already modified or untracked in the working tree were preserved unchanged.



### Tests and GUI verification



* `python -m unittest discover -s tests`: **77/77 OK**.

* `python -m tests.smoke_qml`: **QML_SMOKE_OK**, one root loaded, no warnings.

* The integration test creates and exposes the QQuickView window in offscreen mode and verifies the panels and cards. No manual visual review on a real desktop was performed.



### Versioning and data integrity



* **Previous version:** `0.3.0` (tagged as `v0.3.0`).

* **New version:** `0.4.0`, a **MINOR** increment for a new backward-compatible feature.

* **Release status:** committed and annotated with `v0.4.0` locally; it cannot be pushed until a remote is configured.

* No BIN files were modified as part of this implementation. Pre-existing BIN changes in the working tree were preserved.



### Remaining validation



* Windows and labels remain pending until their modules exist; they are not shown as zero.



### Approval



Phase 4 — Project was approved by the owner on 2026-09-26. Work on the next phase may begin when requested. The local tag does not constitute a remote publication.



## [0.5.0] — Data module (final)



**Date:** 2026-09-26

**Branch:** `feature/fase-02-shell`

**Status:** FINAL, VALIDATED, AND APPROVED by the project owner on 2026-09-26.

**Commit:** `8f5d8b531a92f6c8d94db376a1cd29ef3ed2aad0`

**Release:** Committed locally. No tag or remote publication was requested.



### Objective



Implement Phase 5 — Data using the approved Data screen design: browse and validate BIN files from the Project source folder, show details for the file selected by its checkbox, and show that file's events.



### Architecture and behavior



* Added `DataService`, exposed through the single `AppState` object as `app.data`. It consumes the Project service's session result and keeps file/event selection, search, status filtering, pagination, and validation state in Python.

* Added Python `QAbstractTableModel` models for BIN files and events. QML renders model roles; it does not assemble dynamic rows or calculate domain values.

* Aligned the Data page header position and structure with Project; page-heading icons use the same `#2563EB` blue.

* Removed the impractical manual “Validate file” action. BIN files are validated during the folder scan; only the compact “View in Analysis” action remains, with a white high-contrast icon.

* Kept a single small file icon in the “File details” heading; removed the redundant icon next to the selected BIN name.

* Vertically centered the file-search input text and placeholder to match the field design.

* File and event inspection runs in background workers. Details come from BIN v2 parser/quality outputs and real filesystem metadata; SHA-256 is read-only. Original BIN files are not modified.

* Selecting a file checkbox updates the detail panel and the Events table to that file. Both tables provide vertical scrollbars; the file table also supports Python-owned page sizing and navigation.

* File-table columns expand to use available horizontal space when the application window is resized.

* Added search and status filtering, automatic validation during the folder scan, and analysis navigation only for valid files. Analysis calculations remain deferred to Phase 6.

* The Data screen intentionally has no “Import BIN” button; its source is the folder selected in Project.

* Rejected or unavailable values are shown as unavailable/error states rather than fabricated values.



### Files created and modified



* Created: `datos/__init__.py`, `datos/records.py`, `datos/models.py`, `datos/service.py`, `assets/icons/EventosHeading.svg`, `assets/icons/AnalisisWhite.svg`, `qml/components/DataDetailRow.qml`, `qml/components/VerticalTableScrollBar.qml`, `tests/test_data_service.py`.

* Modified: `app/state.py`, `dataengine/analysis.py`, `dataengine/__init__.py`, `qml/views/Proyecto.qml`, `qml/views/Datos.qml`, `tests/test_appstate.py`, `tests/test_data_analysis.py`, `tests/test_project.py`, `Arquitectura de trabajo.md`, `Diseños/SismoAI_Trainer_Plan_Estrategico.md`, `Versiones.md`.



### Tests and GUI verification



* `python -m unittest discover -s tests`: **83/83 OK**, including real BIN read-only checks, Data model/service tests, filtering, validation, header alignment, responsive table sizing, and QML integration.

* `python -m tests.smoke_qml`: **QML_SMOKE_OK**, one root loaded, no warnings.

* `python -m compileall -q app dataengine datos project shell`: passed.

* `git diff --check`: passed. A QQuickView offscreen capture verified the Data layout with real parser-derived metadata and events; no manual desktop display review has been performed.



### Versioning and data integrity



* **Previous:** `0.4.0` (`v0.4.0`, local annotated tag).

* **Version:** `0.5.0`, **MINOR** increment for a compatible new Data module.

* No BIN files or dataset-format specifications were changed by the Data implementation. Pre-existing user changes in the working tree were preserved.

* The existing `v0.4.0` tag has not been pushed because no Git remote is configured. No tag was created for `0.5.0`.



### Approval and next phase



Phase 5 — Data and version `0.5.0` are final, validated, approved, and committed. Phase 6 — Analysis remains pending a separate sign-off to continue.



## [v0.6.0] — Analysis (Análisis)



**Date:** 2026-09-27

**Branch:** `feature/fase-02-shell`

**Status:** FINAL, VALIDATED, AND APPROVED by the project owner on 2026-09-27.

**Commit:** `fa6ece1573deeec0369cb7027c7ea3be1adf44c3`

**Release:** Committed locally. No tag or remote publication was requested.



### Objective

Complete the Phase 6 — Analysis implementation with all four submenús fully operational: Señales (preserved behavior), STA-LTA (with parameter editing and actions), Frecuencia (spectrum visualizations, metrics, and cursor tracking), and Espectrograma (STFT heatmap with cursor). This release integrates spectrum calculations, metrics panels, parameter editing (window type, thresholds), cursor snapping/tracking adapted from Señales, and unified layout across all submenús without destructive modifications. The spectral visualizations and parameters are functional; the other three submenus remain accessible from the same menu structure without destructive modifications.

The four submenus are now fully operational: Señales, STA-LTA, Frecuencia, and Espectrograma. Spectral visualizations and parameters are functional; the other submenus remain accessible from the same menu structure without destructive modifications.

---

## Aprobación — Punto de control de interfaz de Análisis

**Fecha:** 2026-09-29  
**Rama:** `fix/analysis-loading-refresh`  
**Estado:** VALIDADO Y APROBADO por el propietario del proyecto.  
**Commit base aprobado:** `e67e82d9caee839a357178a0622ac72adc52db42`

### Alcance aprobado

Se aprueba el estado alcanzado hasta este punto de la interfaz de Análisis, incluyendo la disposición común de las pestañas y gráficas y el contraste visual de la pestaña activa.

Este registro fija el punto de control para continuar el desarrollo. Los cambios posteriores deberán conservar esta base aprobada y registrarse en commits separados.

### Versionado

Registro documental de aprobación; no modifica software ni interfaces. No se incrementa la versión SemVer.
