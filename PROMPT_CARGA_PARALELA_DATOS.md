# SismoAI Trainer — Prompt de Mejora: Carga Paralela de Archivos BIN en DataService

> **Documento de especificación técnica y directiva de ejecución para agente de desarrollo.**
> Mejora interna del módulo `core/datos/service.py` para soportar cientos de archivos BIN
> sin bloquear la UI ni romper ningún contrato de arquitectura existente.

---

## 1. Contexto y motivación

`DataService._load_files_sync` carga cada archivo BIN de forma secuencial. Para cada
archivo ejecuta dos operaciones costosas:

1. `parse_file(entry.path)` — parsea el binario completo (CPU + I/O).
2. `_sha256(entry.path)` — lee todo el archivo para calcular el hash SHA-256 (I/O puro).

Con pocos archivos de referencia esto es aceptable. Con cientos de archivos el hilo
principal de Python queda bloqueado durante decenas de segundos, congelando la respuesta
del puente a JavaScript.

**Objetivo:** reemplazar `_load_files_sync` por una estrategia de carga paralela con
progreso incremental y hash perezoso, sin modificar ningún contrato de arquitectura,
ninguna firma de método público del puente, ni ningún archivo fuera de
`core/datos/service.py` y `core/datos/records.py`.

---

## 2. Reglas obligatorias

1. **No romper contratos existentes.** Las firmas públicas de `DataService`, `BinFileRow`
   y `EventRow` deben permanecer compatibles con el puente (`bridge/api_bridge.py`) y
   con los modelos (`core/datos/models.py`). No se modifica ningún archivo fuera de
   `core/datos/service.py` y `core/datos/records.py`.

2. **No inventar datos.** Si un archivo aún no ha sido procesado, su fila en la tabla
   debe mostrar textos `"Cargando…"` explícitos, nunca valores ficticios.

3. **Preservar cancelación de petición obsoleta.** El mecanismo `_request_id` ya
   existente debe seguir funcionando: si el usuario selecciona otra carpeta mientras la
   carga está en curso, los resultados de la petición anterior se descartan en silencio.

4. **Thread-safety.** Todas las mutaciones a `self._records` deben ocurrir bajo
   `self._lock` (threading.Lock ya declarado en el servicio o a añadir).

5. **Arquitectura de estado.** El estado del servicio debe pasar correctamente por:
   `LOADING → READY` (éxito) o `LOADING → ERROR` (fallo total). Nunca debe quedar
   en `LOADING` indefinidamente.

6. **No dependencias nuevas.** Sólo usar `concurrent.futures.ThreadPoolExecutor` y
   `threading.Lock` de la biblioteca estándar de Python. No añadir nada a
   `requirements.txt`.

---

## 3. Diseño de la solución

### 3.1 Hash perezoso en `BinFileRow`

`BinFileRow` es un `dataclass(frozen=True)`. El campo `sha256_text` actualmente se
calcula en `_build_file_row` llamando a `_sha256(path)`.

**Cambio en `core/datos/records.py`:**

Añadir el valor centinela `SHA256_PENDING = "Calculando…"` como constante de módulo.
El campo `sha256_text` no cambia de tipo ni de nombre; simplemente puede contener
este valor centinela mientras el hash aún no se ha calculado.

```python
# records.py — añadir al inicio del módulo
SHA256_PENDING = "Calculando…"
```

No se modifica ningún campo de `BinFileRow` ni de `EventRow`.

### 3.2 Nueva función `_build_file_row_fast`

En `core/datos/service.py`, añadir una variante de `_build_file_row` que **omite el
cálculo del SHA-256** y devuelve `sha256_text=SHA256_PENDING`. Esta función se usa
durante la carga paralela inicial.

```python
def _build_file_row_fast(entry, result):
    """Como _build_file_row pero sin calcular SHA-256 (hash perezoso)."""
    from .records import SHA256_PENDING
    # Mismo cuerpo que _build_file_row, salvo:
    #   digest_text = SHA256_PENDING   (omitir llamada a _sha256)
    # El resto del cuerpo permanece idéntico.
    ...
```

La función `_build_file_row` original **no se modifica ni se elimina**; se conserva
para el cálculo bajo demanda al seleccionar un archivo.

### 3.3 Nueva función `_read_entry_fast`

```python
def _read_entry_fast(entry):
    """Parsea el BIN y construye la fila sin calcular el hash."""
    if entry.status != "ok":
        return _build_file_row_fast(entry, None)
    result = parse_file(entry.path)
    return _build_file_row_fast(entry, result)
```

### 3.4 Reemplazar `_load_files_sync` por `_load_files_async`

En `DataService`, reemplazar el método `_load_files_sync` por `_load_files_async`.
La llamada en `_session_changed` pasa de:

```python
self._load_files_sync(request_id, summary.files)
```

a:

```python
thread = threading.Thread(
    target=self._load_files_async,
    args=(request_id, summary.files),
    daemon=True,
)
thread.start()
```

**Implementación de `_load_files_async`:**

```python
def _load_files_async(self, request_id, entries):
    """
    Carga los archivos BIN en paralelo con ThreadPoolExecutor.
    - Máximo 4 hilos simultáneos (balance I/O + GIL).
    - Notifica progreso a la UI cada BATCH_SIZE archivos completados.
    - Descarta resultados si el request_id ya no es válido (carpeta cambiada).
    - Al finalizar, calcula el SHA-256 de cada archivo en segundo plano.
    """
    BATCH_SIZE = 10   # notificar UI cada N archivos completados
    MAX_WORKERS = 4

    n = len(entries)
    # Reservar lista de tamaño fijo para preservar el orden original.
    rows = [None] * n

    def worker(index, entry):
        return index, _read_entry_fast(entry)

    completed = 0

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(worker, i, entry): i
                for i, entry in enumerate(entries)
            }
            for future in as_completed(futures):
                # Cancelar si el usuario eligió otra carpeta.
                with self._lock:
                    if request_id != self._request_id:
                        return

                try:
                    idx, row = future.result()
                    with self._lock:
                        rows[idx] = row
                    completed += 1
                except Exception as exc:
                    idx = futures[future]
                    entry = entries[idx]
                    failed = replace(entry, status="error",
                                     error="No se pudo leer: %s" % exc)
                    with self._lock:
                        rows[idx] = _build_file_row_fast(failed, None)
                    completed += 1

                # Publicar progreso parcial cada BATCH_SIZE archivos.
                if completed % BATCH_SIZE == 0 or completed == n:
                    with self._lock:
                        if request_id != self._request_id:
                            return
                        self._records = [r for r in rows if r is not None]
                    self._refresh_models()

    except Exception as exc:
        with self._lock:
            if request_id != self._request_id:
                return
            self._records = []
            self._error = "No se pudieron cargar los archivos BIN: %s" % exc
            self._state = self.ERROR
        self._refresh_models()
        return

    # Carga completada — pasar a READY con todos los registros.
    with self._lock:
        if request_id != self._request_id:
            return
        self._records = list(rows)
        self._state = self.READY
        self._error = ""
    self._page = 0
    self._refresh_models()

    # Iniciar cálculo de hashes en segundo plano (no bloquea READY).
    hash_thread = threading.Thread(
        target=self._compute_hashes_async,
        args=(request_id,),
        daemon=True,
    )
    hash_thread.start()
```

### 3.5 Cálculo de hashes en segundo plano: `_compute_hashes_async`

Una vez que el estado es `READY` y la tabla ya es visible, calcular los SHA-256 uno
por uno en un hilo separado y actualizar cada fila con `dataclasses.replace`.

```python
def _compute_hashes_async(self, request_id):
    """
    Calcula SHA-256 de cada archivo en orden y actualiza la fila correspondiente.
    Se detiene si el request_id cambia (nueva carpeta seleccionada).
    """
    from .records import SHA256_PENDING

    with self._lock:
        paths_to_process = [
            (i, row.path)
            for i, row in enumerate(self._records)
            if row is not None and row.sha256_text == SHA256_PENDING
        ]

    for i, path in paths_to_process:
        with self._lock:
            if request_id != self._request_id:
                return

        try:
            digest = _sha256(path)
        except OSError:
            digest = "—"

        with self._lock:
            if request_id != self._request_id:
                return
            if i < len(self._records) and self._records[i] is not None:
                self._records[i] = replace(self._records[i], sha256_text=digest)

        # Publicar actualización sólo si el archivo seleccionado cambió su hash.
        with self._lock:
            selected = self._selected_path
        if self._records[i] is not None and self._records[i].path == selected:
            self._refresh_models()

    # Publicar actualización final una sola vez al terminar todos los hashes.
    with self._lock:
        if request_id != self._request_id:
            return
    self._refresh_models()
```

### 3.6 Hash bajo demanda al seleccionar un archivo

En `DataService.select_file`, si el registro seleccionado aún tiene
`sha256_text == SHA256_PENDING`, calcular el hash de forma síncrona (el archivo ya
estaba parseado; sólo falta el hash) antes de publicar el cambio de selección:

```python
def select_file(self, path):
    from .records import SHA256_PENDING

    if not any(row.path == path for row in self._records):
        return

    # Si el hash aún está pendiente, calcularlo ahora (el usuario lo verá de inmediato).
    with self._lock:
        for i, row in enumerate(self._records):
            if row is not None and row.path == path and row.sha256_text == SHA256_PENDING:
                try:
                    digest = _sha256(path)
                except OSError:
                    digest = "—"
                self._records[i] = replace(row, sha256_text=digest)
                break

    self._selected_path = path
    self._file_model.set_selected_path(path)
    self._refresh_models()
```

### 3.7 Añadir `_lock` al constructor de `DataService`

Si `self._lock` no existe aún en `DataService.__init__`, añadirlo:

```python
import threading
# En __init__, junto al resto de atributos privados:
self._lock = threading.Lock()
```

Y añadir `from concurrent.futures import ThreadPoolExecutor, as_completed` al bloque
de importaciones del módulo.

---

## 4. Cambios por archivo — resumen

| Archivo | Cambio |
|---|---|
| `core/datos/records.py` | Añadir constante `SHA256_PENDING = "Calculando…"` |
| `core/datos/service.py` | Añadir importaciones `ThreadPoolExecutor`, `as_completed`; añadir `self._lock`; añadir `_build_file_row_fast`; añadir `_read_entry_fast`; reemplazar `_load_files_sync` por `_load_files_async`; añadir `_compute_hashes_async`; modificar `select_file` para hash bajo demanda |
| Todos los demás archivos | **Sin modificaciones** |

---

## 5. Criterios de aceptación

Ejecutar la aplicación con `python main.py` y verificar:

1. **Carga progresiva visible:** al seleccionar una carpeta con ≥10 archivos BIN, la
   tabla en la vista "Datos" comienza a mostrar filas antes de que todos los archivos
   estén procesados. El estado de la aplicación muestra `LOADING` mientras la carga
   está en curso.

2. **Columna SHA-256 pendiente:** durante la carga paralela, el campo hash muestra
   `"Calculando…"` y se actualiza automáticamente cuando el hilo de hashes termina
   cada archivo.

3. **Hash inmediato al seleccionar:** si el usuario selecciona un archivo antes de que
   el hilo de hashes lo haya procesado, el panel de detalle muestra el hash correcto
   inmediatamente (no `"Calculando…"`).

4. **Cancelación limpia:** si el usuario selecciona otra carpeta mientras la carga está
   en curso, los hilos de la carga anterior terminan silenciosamente y no publican
   resultados obsoletos.

5. **Estado READY correcto:** cuando todos los archivos han sido procesados (parse +
   carga de fila), el estado pasa a `READY`. El hilo de hashes puede seguir corriendo
   en segundo plano sin cambiar el estado a `LOADING`.

6. **Sin regresiones:** los archivos de referencia en `Reference/` continúan
   cargándose correctamente con sus métricas, eventos y calidad exactamente igual que
   antes de la mejora.

7. **BIN originales intactos:** confirmar que ningún archivo `.BIN` ha sido modificado
   (sus hashes deben coincidir con los calculados antes del cambio).

---

## 6. Lo que NO se debe hacer

- No modificar `bridge/api_bridge.py`.
- No modificar `core/datos/models.py`.
- No modificar `core/datos/records.py` más allá de añadir `SHA256_PENDING`.
- No modificar ningún archivo de `ui/`, `core/dataengine/`, `core/analysis/`,
  `core/project/`, `bridge/` ni `main.py`.
- No añadir dependencias a `requirements.txt`.
- No introducir `asyncio`; el modelo de concurrencia del proyecto es `threading`.
- No exponer el estado de progreso individual de cada archivo al puente — la UI
  sólo necesita saber si está en `LOADING` o `READY`.
