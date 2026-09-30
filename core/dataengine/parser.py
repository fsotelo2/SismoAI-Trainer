"""DATASET BIN v2 sequential parser (spec section 10).

Reads only; never modifies the source file. Walks the file strictly in
order: container (24) + metadata (52), then per event header (44) +
payload + CRC (8) + commit (20). A trailing incomplete event marks the
file truncated without inventing samples. Historical 40-byte layouts
(bit 0x04 clear) are reported, never silently converted.
"""

import os
import struct

from . import layout as L
from .crc import crc32_ieee
from .records import (
    ContainerHeader,
    EventHeader,
    EventResult,
    FileResult,
    FrequencyCheck,
    Metadata,
    SensorRecord,
)


def _u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def _i16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<h", buf, off)[0]


def _i32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<i", buf, off)[0]


def _i64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<q", buf, off)[0]


def parse_container(buf: bytes):
    if len(buf) < L.CONTAINER_SIZE:
        return None, ["contenedor incompleto"]
    if buf[0:4] != L.CONTAINER_MAGIC:
        return None, ["magic de contenedor desconocido"]
    version = buf[4]
    if version not in L.CONTAINER_VERSIONS:
        return None, ["version de contenedor no soportada: %d" % version]
    return ContainerHeader(
        version=version,
        dominio=buf[5],
        contenedor=_u32(buf, 8),
        creado_us=_u64(buf, 12),
    ), []


def parse_metadata(buf: bytes):
    if len(buf) < L.METADATA_SIZE:
        return None, ["metadatos incompletos"]
    if buf[0:4] != L.METADATA_MAGIC:
        return None, ["magic de metadatos desconocido"]
    if buf[4] != L.METADATA_VERSION:
        return None, ["version de metadatos no soportada: %d" % buf[4]]
    return Metadata(
        version=buf[4],
        modo=buf[5],
        indicadores=buf[6],
        offset_utc_minutos=_i16(buf, 8),
        inicio_monotonic_us=_u64(buf, 12),
        inicio_unix_us=_i64(buf, 20),
        latitud_e6=_i32(buf, 28),
        longitud_e6=_i32(buf, 32),
        frecuencia_mpu_hz=_u16(buf, 36),
        frecuencia_geofono_hz=_u16(buf, 38),
        pre_evento_segundos=_u16(buf, 40),
        post_evento_segundos=_u16(buf, 42),
        ventana_sta_ms=_u16(buf, 44),
        ventana_lta_ms=_u16(buf, 46),
        umbral_ratio_milli=_u16(buf, 48),
        duracion_dataset_segundos=_u16(buf, 50),
    ), []


def parse_record(buf: bytes, off: int) -> SensorRecord:
    datos = struct.unpack_from("<12f", buf, off + 16)
    return SensorRecord(
        tipo_sensor=buf[off],
        timestamp_us=_u64(buf, off + 4),
        secuencia=_u32(buf, off + 12),
        datos=tuple(datos),
        codigo=_i32(buf, off + 64),
        evento=buf[off + 68],
        flags=_u32(buf, off + 69),
    )


def _parse_event(buf: bytes, pos: int, archivo: str,
                 metadata):
    """(EventResult, consumed_bytes). Zero consumption means the extent
    is unknowable (bad magic / short header): the caller must stop."""
    ev = EventResult(archivo=archivo, offset=pos)
    if len(buf) - pos < L.EVENT_HEADER_SIZE:
        ev.truncado = True
        ev.razones.append("encabezado de evento incompleto")
        return ev, 0
    head = buf[pos:pos + L.EVENT_HEADER_SIZE]
    if head[0:4] != L.EVENT_MAGIC:
        ev.razones.append("magic de evento desconocido")
        return ev, 0
    header = EventHeader(
        version=head[4],
        dominio=head[5],
        secuencia=_u32(head, 8),
        inicio_us=_u64(head, 12),
        fin_us=_u64(head, 20),
        flags=_u32(head, 28),
        tamano_payload=_u32(head, 32),
    )
    ev.secuencia = header.secuencia
    ev.inicio_us = header.inicio_us
    ev.fin_us = header.fin_us
    if head[4] != L.EVENT_VERSION:
        ev.razones.append("version de evento no soportada")
    if _u16(head, 6) != L.EVENT_HEADER_SIZE:
        ev.razones.append("tamano de encabezado invalido")
    total = L.EVENT_HEADER_SIZE + header.tamano_payload + L.CRC_SIZE + L.COMMIT_SIZE
    if len(buf) - pos < total:
        ev.truncado = True
        ev.razones.append("evento incompleto: faltan %d bytes"
                          % (total - (len(buf) - pos)))
        return ev, 0
    payload = buf[pos + L.EVENT_HEADER_SIZE:
                  pos + L.EVENT_HEADER_SIZE + header.tamano_payload]
    crc_off = pos + L.EVENT_HEADER_SIZE + header.tamano_payload
    cmt_off = crc_off + L.CRC_SIZE
    crc_rec = buf[crc_off:crc_off + L.CRC_SIZE]
    cmt_rec = buf[cmt_off:cmt_off + L.COMMIT_SIZE]
    if crc_rec[0:4] != L.CRC_MAGIC:
        ev.razones.append("registro CRC ausente")
    else:
        calc = crc32_ieee(payload)
        ev.crc_valido = (_u32(crc_rec, 4) == calc)
        if not ev.crc_valido:
            ev.razones.append("CRC no coincide")
    if cmt_rec[0:4] != L.COMMIT_MAGIC:
        ev.razones.append("registro commit ausente")
    else:
        cmt_seq = _u32(cmt_rec, 4)
        cmt_bytes = _u32(cmt_rec, 8)
        cmt_crc = _u32(cmt_rec, 12)
        stored_crc = _u32(crc_rec, 4) if crc_rec[0:4] == L.CRC_MAGIC else None
        ev.commit_valido = (
            cmt_seq == header.secuencia
            and cmt_bytes == total
            and stored_crc is not None
            and cmt_crc == stored_crc
        )
        if cmt_seq != header.secuencia:
            ev.razones.append("secuencia de commit no coincide")
        if cmt_bytes != total:
            ev.razones.append("bytesEvento no coincide")
        if stored_crc is not None and cmt_crc != stored_crc:
            ev.razones.append("crc de commit no coincide")
    nuevo = bool(metadata is not None and metadata.usa_layout_nuevo)
    if not nuevo:
        ev.layout_historico = True
        ev.razones.append("layout historico de 40 bytes: sin conversion")
    elif header.tamano_payload % L.RECORD_SIZE != 0:
        ev.razones.append("payload no es multiplo de 76")
    else:
        try:
            ev.records = [
                parse_record(payload, o)
                for o in range(0, len(payload), L.RECORD_SIZE)
            ]
        except struct.error:
            ev.razones.append("registros ilegibles")
            ev.records = []
        ev.record_count = len(ev.records)
    if metadata is not None:
        ref_mpu = metadata.frecuencia_mpu_hz
        ref_geo = metadata.frecuencia_geofono_hz
        ev.frequency_check = FrequencyCheck(
            mpu_referencia=ref_mpu,
            geo_referencia=ref_geo,
            mpu_flags=header.frecuencia_mpu_flags,
            geo_flags=header.frecuencia_geofono_flags,
            consistente=(header.frecuencia_mpu_flags == ref_mpu
                         and header.frecuencia_geofono_flags == ref_geo),
        )
        if not ev.frequency_check.consistente:
            ev.razones.append("flags de frecuencia inconsistentes con META")
    ev.valido = (not ev.truncado and not ev.razones
                 and ev.crc_valido and ev.commit_valido
                 and ev.record_count > 0)
    return ev, total


def parse_file(path: str) -> FileResult:
    """Parse one BIN file; the file is only read, never modified."""
    with open(path, "rb") as f:
        buf = f.read()
    res = FileResult(archivo=os.path.abspath(path))
    container, reasons = parse_container(buf)
    res.container = container
    res.razones.extend(reasons)
    if container is None:
        return res
    metadata, reasons = parse_metadata(buf[L.CONTAINER_SIZE:])
    res.metadata = metadata
    res.razones.extend(reasons)
    if metadata is None:
        return res
    pos = L.CONTAINER_SIZE + L.METADATA_SIZE
    while pos < len(buf):
        ev, consumed = _parse_event(buf, pos, res.archivo, metadata)
        res.events.append(ev)
        if consumed <= 0:
            res.truncado = True
            if not ev.truncado:
                ev.razones.append("extension indeterminable: resto truncado")
            break
        pos += consumed
    res.valido = (not res.truncado and not res.razones
                  and len(res.events) > 0
                  and all(e.valido for e in res.events))
    return res
