# Fase 7 — Etiquetado

**Estado:** contrato funcional inicial  
**Rama:** `feature/fase-7-etiquetado`  
**Dependencia:** Fase 6 — Ventaneo (v0.2.0)

## 1. Objetivo

Asignar etiquetas semánticas a ventanas derivadas, con revisión humana, confianza, calidad y trazabilidad completa hasta el archivo BIN y el evento fuente. El módulo no modifica los BIN originales ni recalcula el ventaneo.

## 2. Clases oficiales

| Código | Clase |
|---|---|
| `0` | `TEMBLOR` |
| `1` | `NO_SISMICO` |
| `2` | `INDETERMINADO` |

Los códigos son estables y no deben depender del orden visual de las clases.

## 3. Contrato de transferencia Ventanas → Etiquetado

La acción **Continuar a Etiquetado** crea o recupera un conjunto de trabajo a partir de las ventanas con `selection_status = include`.

### 3.1 Manifiesto por ventana

Cada elemento conserva, como mínimo:

- `window_id`: identidad estable de la ventana.
- `source_file`, `source_event_id`: procedencia BIN y evento.
- `origin_mode`: `fixed`, `sliding` o `manual`.
- `start_us`, `end_us`: límites temporales en microsegundos.
- `sensors`, `samples`, `sample_ranges`, `sampling_info`: sensores y ubicación de las muestras.
- `quality.status` y `quality.findings`: calidad técnica e incidencias.
- `window_config`, `extractor_version`, `source_hash`, `event_interval`, `notes`: configuración y procedencia adicional disponible.

No duplicar campos derivados si pueden consultarse desde el registro canónico de Ventanas.

### 3.2 Señal por demanda

El manifiesto conserva las referencias a los BIN y rangos; los valores de señal se recuperan al abrir una ventana. Mantener caché temporal acotada y descartar sus datos cuando ya no sean necesarios. No interpolar, remuestrear ni modificar silenciosamente las muestras originales en esta fase.

La lectura debe comprobar que el archivo y los rangos siguen siendo válidos. Si la identidad/hash de origen no está disponible o no coincide, marcar la ventana como fuente no verificada y requerir revisión; nunca asociar una etiqueta a datos distintos sin advertencia.

### 3.3 Filtro de entrada y calidad

- Solo las ventanas con selección `include` ingresan al conjunto de trabajo.
- Calidad `accepted`: se muestra como técnicamente aceptada.
- Calidad `review`: se transfiere con indicador de revisión pendiente.
- Calidad `blocked`: se excluye del flujo ordinario. Una acción explícita de excepción podrá incorporarla, conservando la advertencia y el motivo.
- Selección `review` o `exclude`: no se transfiere hasta que el usuario cambie su selección en Ventanas.

La calidad técnica no determina automáticamente la clase semántica.

## 4. Unidad y registro de etiquetado

La unidad primaria es **una etiqueta por ventana**. GEO y MPU son modalidades/sensores asociados a la misma ventana; se permiten atributos específicos por sensor cuando sean necesarios, sin duplicar la identidad ni la etiqueta primaria.

Registro propuesto:

| Campo | Descripción |
|---|---|
| `window_id` | Clave de la ventana etiquetada. |
| `class_code` | `0`, `1`, `2` o nulo mientras no esté etiquetada. |
| `label_source` | `human` o `automatic`. |
| `confidence` | Confianza opcional, en escala normalizada de 0 a 1. |
| `disturbance` | Tipo de perturbación, si aplica; catálogo pendiente de definir. |
| `quality_review` | Estado de revisión de la anotación, separado de la calidad técnica de la señal. |
| `reviewer` | Identificador/nombre del anotador, si está configurado. |
| `observations` | Notas libres de la anotación. |
| `created_at`, `updated_at` | Marcas temporales de auditoría. |
| `schema_version` | Versión del formato de anotación. |

Una sugerencia automática debe conservar `label_source = automatic` y no se considera verdad de terreno verificada por defecto. La confirmación humana debe quedar registrada como cambio auditable, no sobrescribir el origen de forma opaca.

## 5. Persistencia y versionado

- Persistir el manifiesto del conjunto de trabajo y las anotaciones en archivos versionados separados de los BIN.
- Asociar el conjunto a los identificadores de ventanas y a la versión/hash de su origen.
- Guardar cambios de anotación de forma atómica.
- Si una ventana cambia de límites, sensores o procedencia, invalidar su anotación asociada o crear una nueva identidad/versionado; no reutilizarla silenciosamente.
- Permitir reabrir y continuar el etiquetado sin repetir el ventaneo.

## 6. Flujo de usuario previsto

1. Pulsar **Continuar a Etiquetado** desde Ventanas.
2. Validar selección, archivos fuente, rangos y estados de calidad.
3. Crear/recuperar el conjunto de trabajo y mostrar resumen de ventanas incluidas, pendientes de revisión y excluidas por bloqueo.
4. Abrir la vista Etiquetado con una lista navegable de ventanas y el detalle de la señal seleccionada.
5. Asignar clase, confianza, fuente, perturbación y observaciones; guardar y marcar revisión.
6. Mantener visible la trazabilidad al evento, archivo, intervalo y sensores.

## 7. Criterios de aceptación iniciales

- No se habilita la continuación si no hay ventanas `include`.
- El conjunto no incluye ventanas `review`/ `exclude` de selección ni `blocked` sin excepción explícita.
- Los registros mantienen procedencia e identidad estables.
- Los datos se cargan bajo demanda y se comprueba la vigencia de la fuente.
- Una etiqueta no se asigna automáticamente por calidad, STA/LTA u otra métrica.
- La anotación humana y cualquier sugerencia automática son distinguibles.
- Las etiquetas sobreviven al cierre y reapertura de la aplicación.
- Los BIN originales permanecen intactos.

## 8. Fuera de alcance en este primer incremento

- Entrenamiento o inferencia de modelos.
- Definición de catálogo completo de perturbaciones.
- Etiquetado temporal por subintervalos dentro de una ventana.
- Particiones train/validation/test (Fase 8).
- Exportación del dataset consolidado (Fase 8/10 según formato).
