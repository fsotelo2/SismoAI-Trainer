"""Channel series extraction with traceability (spec section 8 + p.85).

Geophone is the primary signal (velocity mm/s, voltage mV, ADC counts);
MPU contributes magnitude only (stored datos[3], m/s2). Series preserve
source order and carry (file, event offset, secuencia, sample index) so
every value traces back to its record. Findings from analysis travel
with the series; nothing is corrected.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import layout as L
from .analysis import EventAnalysis, Finding
from .records import EventResult

CHANNEL_VELOCITY = "velocity"
CHANNEL_VOLTAGE = "voltage"
CHANNEL_ADC = "adc"
CHANNEL_MAGNITUDE = "magnitude"


@dataclass(frozen=True)
class Sample:
    source_index: int
    timestamp_us: int
    secuencia: int
    value: float


@dataclass(frozen=True)
class Series:
    sensor: int
    channel: str
    unit: str
    samples: List[Sample]
    source_file: str
    event_offset: int
    event_secuencia: int
    findings: List[Finding] = field(default_factory=list)

    @property
    def values(self) -> List[float]:
        return [s.value for s in self.samples]

    @property
    def timestamps(self) -> List[int]:
        return [s.timestamp_us for s in self.samples]


def _collect(event: EventResult, sensor: int, channel: str, unit: str,
             pick, analysis: Optional[EventAnalysis] = None) -> Series:
    samples = [
        Sample(source_index=idx,
               timestamp_us=rec.timestamp_us,
               secuencia=rec.secuencia,
               value=pick(rec))
        for idx, rec in enumerate(event.records)
        if rec.tipo_sensor == sensor
    ]
    findings: List[Finding] = []
    if analysis is not None and sensor in analysis.sensors:
        findings = list(analysis.sensors[sensor].findings)
    return Series(
        sensor=sensor,
        channel=channel,
        unit=unit,
        samples=samples,
        source_file=event.archivo,
        event_offset=event.offset,
        event_secuencia=event.secuencia,
        findings=findings,
    )


def geophone_velocity(event: EventResult,
                      analysis: Optional[EventAnalysis] = None) -> Series:
    return _collect(event, L.SENSOR_GEOFONO, CHANNEL_VELOCITY, "mm/s",
                    lambda r: r.datos[1], analysis)


def geophone_voltage(event: EventResult,
                     analysis: Optional[EventAnalysis] = None) -> Series:
    return _collect(event, L.SENSOR_GEOFONO, CHANNEL_VOLTAGE, "mV",
                    lambda r: r.datos[0], analysis)


def geophone_adc(event: EventResult,
                 analysis: Optional[EventAnalysis] = None) -> Series:
    return _collect(event, L.SENSOR_GEOFONO, CHANNEL_ADC, "counts",
                    lambda r: float(r.codigo), analysis)


def mpu_magnitude_series(event: EventResult,
                         analysis: Optional[EventAnalysis] = None) -> Series:
    return _collect(event, L.SENSOR_MPU, CHANNEL_MAGNITUDE, "m/s2",
                    lambda r: r.datos[3], analysis)


def event_series(event: EventResult,
                 analysis: Optional[EventAnalysis] = None) -> Dict[str, Series]:
    return {
        CHANNEL_VELOCITY: geophone_velocity(event, analysis),
        CHANNEL_VOLTAGE: geophone_voltage(event, analysis),
        CHANNEL_ADC: geophone_adc(event, analysis),
        CHANNEL_MAGNITUDE: mpu_magnitude_series(event, analysis),
    }
