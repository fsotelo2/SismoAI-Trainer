# AI Dataset Specification

## 1. Scope

This document describes the format that the Windows tool must read to
convert the current captures into training windows. It does not describe a
new firmware format or implement inference.

The Dataset capture contains raw sensor samples. It does not contain an AI
decision, calculated features, or class labels.

## 2. Name and location

The functional name is `DATASET`, but the firmware generates containers
with this pattern:

```text
/DATASET/VALIDOS/DAT_000001.BIN
/DATASET/VALIDOS/DAT_000002.BIN
...
```

The number is sequential and has six digits. A container can group up to
20 events before being rotated.

Only files under `/DATASET/VALIDOS` must enter the training pipeline.
Incomplete or recovering files must not be processed as valid samples.

## 3. Binary conventions

| Property | Value |
|---|---|
| Writing architecture | ESP32 |
| Current byte order | Native little-endian |
| Serialization | Direct write of the ESP32 native struct |
| Endian conversion | None |
| Time unit | Microseconds |
| Floating-point type | IEEE-754 32-bit `float` |
| SD sector size | 512 bytes |
| CRC | CRC-32 IEEE |

The parser must read integers and floating-point values explicitly as
little-endian. It must not depend on the host language's struct alignment.

## 4. Complete file layout

The file is interpreted sequentially:

```text
ContainerHeader       (24 bytes)
MetadataRecord        (52 bytes)
repeat for each event:
    EventHeader       (44 bytes)
    Payload           (N bytes)
    CrcRecord         (8 bytes)
    CommitRecord      (20 bytes)
```

The first event starts at offset `76`:

```text
24 + 52 = 76
```

The next event's offset is obtained by adding:

```text
44 + tamanoPayload + 8 + 20
```

Do not calculate the number of events by dividing the file size, because
the payload size can vary.

## 5. Container header — 24 bytes

Magic: `C11C`.

| Offset | Size | Type | Field | Description |
|---:|---:|---|---|---|
| 0 | 4 | char[4] | `magia` | `"C11C"` |
| 4 | 1 | uint8 | `version` | Container version; current version is `2` |
| 5 | 1 | uint8 | `dominio` | Operating domain |
| 6 | 2 | uint8[2] | `reservado` | Must be ignored |
| 8 | 4 | uint32 | `contenedor` | Sequential identifier |
| 12 | 8 | uint64 | `creadoUs` | Creation time in microseconds |
| 20 | 4 | uint8[4] | `reservadoFinal` | Must be ignored |

The parser must reject an unknown magic value or an unsupported version.
It may accept version 1 if historical compatibility is implemented, but
version 2 is the current reference.

## 6. Metadata record — 52 bytes

Magic: `META`.

| Offset | Size | Type | Field | Description |
|---:|---:|---|---|---|
| 0 | 4 | char[4] | `magia` | `"META"` |
| 4 | 1 | uint8 | `version` | Metadata version; current version is `1` |
| 5 | 1 | uint8 | `modo` | Capture mode |
| 6 | 1 | uint8 | `indicadores` | Status bits |
| 7 | 1 | uint8 | `reservado` | Ignore |
| 8 | 2 | int16 | `offsetUtcMinutos` | UTC offset |
| 10 | 2 | uint16 | `reservado2` | Reserved |
| 12 | 8 | uint64 | `inicioMonotonicUs` | Monotonic start time |
| 20 | 8 | int64 | `inicioUnixUs` | Unix start time |
| 28 | 4 | int32 | `latitudE6` | Latitude × 1,000,000 |
| 32 | 4 | int32 | `longitudE6` | Longitude × 1,000,000 |
| 36 | 2 | uint16 | `frecuenciaMpuHz` | Configured MPU frequency |
| 38 | 2 | uint16 | `frecuenciaGeofonoHz` | Configured geophone frequency |
| 40 | 2 | uint16 | `preEventoSegundos` | Configured pre-event interval |
| 42 | 2 | uint16 | `postEventoSegundos` | Configured post-event interval |
| 44 | 2 | uint16 | `ventanaStaMs` | STA window |
| 46 | 2 | uint16 | `ventanaLtaMs` | LTA window |
| 48 | 2 | uint16 | `umbralRatioMilli` | Threshold × 1,000 |
| 50 | 2 | uint16 | `duracionDatasetSegundos` | Requested duration |

### Known indicators

| Bit | Meaning |
|---:|---|
| 0 | Time synchronized |
| 1 | GPS coordinates available |
| 3 | Event associated with the Censado mode |

Unknown bits must be preserved during import, but must not be interpreted
as an AI class.

## 7. Event header — 44 bytes

Magic: `EVT1`.

| Offset | Size | Type | Field | Description |
|---:|---:|---|---|---|
| 0 | 4 | char[4] | `magia` | `"EVT1"` |
| 4 | 1 | uint8 | `version` | Current version is `1` |
| 5 | 1 | uint8 | `dominio` | Event domain |
| 6 | 2 | uint16 | `tamanoHeader` | Must be `44` |
| 8 | 4 | uint32 | `secuencia` | Event sequence |
| 12 | 8 | uint64 | `inicioUs` | Monotonic start time |
| 20 | 8 | uint64 | `finUs` | Monotonic end time |
| 28 | 4 | uint32 | `flags` | Flags; in Dataset, encodes frequencies |
| 32 | 4 | uint32 | `tamanoPayload` | Payload size in bytes |
| 36 | 8 | uint8[8] | `reservado` | Must be ignored |

For Dataset, the firmware constructs `flags` as follows:

```text
bits 31..16 = frecuenciaMpuHz
bits 15..0  = frecuenciaGeofonoHz
```

The parser must use `frecuenciaMpuHz` and `frecuenciaGeofonoHz` from
`META` as the session reference and compare them with `flags` to detect
inconsistencies.

## 8. Dataset payload

New Dataset files use the same 76-byte `RegistroSensorCientifico` as
Censado. The `0x04` bit in `META.indicadores` is set. Older captures
without that bit may contain the historical 40-byte record described in
section 8.1 and must not be mixed without conversion.

```text
tamanoPayload % 76 == 0
cantidadRegistros = tamanoPayload / 76
```

### `RegistroSensorCientifico` — 76 bytes

The record is declared as `packed` and is shared by Dataset and Censado:

| Offset | Size | Type | Field | Description |
|---:|---:|---|---|---|
| 0 | 1 | uint8 | `tipoSensor` | `1` MPU, `2` geophone |
| 1 | 3 | uint8[3] | `reservado` | Must be ignored |
| 4 | 8 | uint64 | `timestampUs` | Sample timestamp |
| 12 | 4 | uint32 | `secuencia` | Sample sequence |
| 16 | 48 | float32[12] | `datos` | Physical and derived channels |
| 64 | 4 | int32 | `codigo` | Geophone ADC code |
| 68 | 1 | uint8 | `evento` | In Dataset: `0` |
| 69 | 4 | uint32 | `flags` | Sample validity |
| 73 | 3 | uint8[3] | `reservadoFinal` | Must be ignored |

The `datos` offsets above are relative to the record: `datos[0]` is at
offset 16, `datos[1]` at 20, through `datos[11]` at 60. The record ends at
offset 76.

### Per-sensor fields

For the MPU:

```text
datos[0] = X in m/s²
datos[1] = Y in m/s²
datos[2] = Z in m/s²
datos[3] = sqrt(X² + Y² + Z²)
datos[4] = 0  // STA not calculated in Dataset
datos[5] = 0  // LTA not calculated in Dataset
datos[6] = 0  // RATIO not calculated in Dataset
codigo = 0
```

For the geophone:

```text
datos[0] = voltage in mV
datos[1] = corrected velocity in mm/s
datos[2..6] = 0  // STA, LTA, RATIO, and non-applicable fields
codigo = ADC value
```

Dataset and Censado therefore retain the same physical sensor information.
The only additional information in Censado is STA, LTA, and RATIO, along
with its trigger indicators.

## 9. CRC and commit

### `RegistroCrc` — 8 bytes

Magic: `CRC1`.

| Offset | Size | Type | Field |
|---:|---:|---|---|
| 0 | 4 | char[4] | `"CRC1"` |
| 4 | 4 | uint32 | `valor` |

The CRC is calculated over the payload only:

```text
CRC-32 IEEE
polynomial       0xEDB88320
initial value    0xFFFFFFFF
final value      crc XOR 0xFFFFFFFF
```

### `RegistroCommit` — 20 bytes

Magic: `CMT1`.

| Offset | Size | Type | Field |
|---:|---:|---|---|
| 0 | 4 | char[4] | `"CMT1"` |
| 4 | 4 | uint32 | `secuencia` |
| 8 | 4 | uint32 | `bytesEvento` |
| 12 | 4 | uint32 | `crc` |
| 16 | 4 | uint32 | `reservado` |

The parser must accept an event only if:

1. `EVT1` is valid;
2. `tamanoHeader == 44`;
3. `tamanoPayload` is reasonable and a multiple of the record size for the
   applicable layout: 76 for the new layout (`META.indicadores & 0x04`),
   40 only for the historical layout (no conversion; see 8.1);
4. `CRC1` is present;
5. the calculated CRC matches;
6. `CMT1` is present;
7. the commit sequence matches;
8. `bytesEvento` matches `44 + tamanoPayload + 8 + 20`;
9. the commit is fully written.

## 10. Recommended parser algorithm

```text
open binary file
read and validate ContainerHeader
read and validate MetadataRecord
while bytes remain:
    remember the event's starting offset
    read EventHeader
    validate magic, version, and size
    read tamanoPayload bytes
    read CrcRecord
    calculate the payload CRC
    read CommitRecord
    validate commit and bytesEvento
    validate payload is a multiple of 76 for new Dataset layout
    decode 76-byte records
    emit valid event
if an incomplete event remains:
    mark file as truncated; do not invent samples
```

At a minimum, the parser result must include:

```text
file
eventOffset
eventSequence
startUs
endUs
recordCount
crcValid
commitValid
truncated
```

## 11. Conversion to training windows

The tool must separate records by `tipoSensor`, sort them by `timestampUs`,
and detect discontinuities in `secuencia`.

Each window must store:

- source file and event;
- start and end offsets;
- start and end timestamps;
- sensors present;
- observed frequency;
- discarded samples;
- discard reason, if applicable;
- human label;
- extractor version;
- source file hash.

Samples from different events must not be combined in a training window,
unless the experiment explicitly declares otherwise.

## 12. Observed validation in `DAT_000001.BIN`

The reference file contains twenty valid events (sequences 1–20), with no truncation and with valid CRC and COMMIT records. Its
payload matches the real alignment layout described in section 8.

Verified reference corpus (read-only):
`DAT_000001.BIN` 20 events.,

The effective frequency must be calculated from each sensor's timestamps:

- the geophone provides approximately 88.23 Hz although `META` indicates
  90 Hz;
- the geophone has low jitter;
- the MPU approaches 100 Hz but has high jitter;
- samples must be separated by `tipoSensor` before sorting by `timestampUs`;
- a window with discontinuities must be marked as defective, not silently
  corrected.

## 13. Known limitations of format v2

- It has no formal endianness identifier.
- It has no per-record CRC.
- It has no explicit lost-sample counter.
- It contains no class labels.
- It contains no model version or inference result.
- It contains no calculated features.
- Per-sample timestamps require jitter and continuity validation.
- It has no random-access index.

These limitations must be addressed in the Windows pipeline or in a v3
format, without retroactively modifying v2 captures. Future firmware must
initialize the complete record so padding bytes are deterministic.
