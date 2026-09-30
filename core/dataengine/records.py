"""Plain data containers for parsed DATASET BIN v2 content.

No validation or calculation here; the parser fills these, analysis and
quality consume them. Everything is read-only after construction.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ContainerHeader:
    version: int
    dominio: int
    contenedor: int
    creado_us: int


@dataclass(frozen=True)
class Metadata:
    version: int
    modo: int
    indicadores: int
    offset_utc_minutos: int
    inicio_monotonic_us: int
    inicio_unix_us: int
    latitud_e6: int
    longitud_e6: int
    frecuencia_mpu_hz: int
    frecuencia_geofono_hz: int
    pre_evento_segundos: int
    post_evento_segundos: int
    ventana_sta_ms: int
    ventana_lta_ms: int
    umbral_ratio_milli: int
    duracion_dataset_segundos: int

    @property
    def usa_layout_nuevo(self) -> bool:
        from .layout import LAYOUT_NUEVO_BIT
        return bool(self.indicadores & LAYOUT_NUEVO_BIT)


@dataclass(frozen=True)
class EventHeader:
    version: int
    dominio: int
    secuencia: int
    inicio_us: int
    fin_us: int
    flags: int
    tamano_payload: int

    @property
    def frecuencia_mpu_flags(self) -> int:
        return (self.flags >> 16) & 0xFFFF

    @property
    def frecuencia_geofono_flags(self) -> int:
        return self.flags & 0xFFFF


@dataclass(frozen=True)
class SensorRecord:
    tipo_sensor: int
    timestamp_us: int
    secuencia: int
    datos: Tuple[float, ...]
    codigo: int
    evento: int
    flags: int


@dataclass(frozen=True)
class FrequencyCheck:
    mpu_referencia: int
    geo_referencia: int
    mpu_flags: int
    geo_flags: int
    consistente: bool


@dataclass
class EventResult:
    archivo: str = ""
    offset: int = 0
    secuencia: int = 0
    inicio_us: int = 0
    fin_us: int = 0
    record_count: int = 0
    crc_valido: bool = False
    commit_valido: bool = False
    valido: bool = False
    truncado: bool = False
    layout_historico: bool = False
    records: List[SensorRecord] = field(default_factory=list)
    frequency_check: Optional[FrequencyCheck] = None
    razones: List[str] = field(default_factory=list)


@dataclass
class FileResult:
    archivo: str = ""
    container: Optional[ContainerHeader] = None
    metadata: Optional[Metadata] = None
    events: List[EventResult] = field(default_factory=list)
    valido: bool = False
    truncado: bool = False
    razones: List[str] = field(default_factory=list)

    @property
    def records_by_sensor(self) -> Dict[int, int]:
        counts: Dict[int, int] = {}
        for ev in self.events:
            for r in ev.records:
                counts[r.tipo_sensor] = counts.get(r.tipo_sensor, 0) + 1
        return counts
