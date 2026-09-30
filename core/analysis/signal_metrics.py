"""Transparent, event-level support metrics for the Signals view.

Definitions used here:
* peak amplitude is max(abs(sample)) in the selected physical channel;
* RMS is sqrt(mean(sample**2)) over the complete event, without detrending;
* estimated SNR uses the first META pre-event interval as noise and the
  remaining event as signal. Both intervals are mean-removed before RMS;
* timing jitter is the population standard deviation of positive timestamp
  intervals between consecutive sample sequence numbers, in milliseconds.

BIN v2 does not define saturation flags/ADC rails or a signal-quality
classification. Those are deliberately reported as undefined, not zero or
"good". Dominant frequency belongs to the Frequency analysis block.
"""

import math
import statistics
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignalMetrics:
    peak_amplitude: Optional[float]
    rms: Optional[float]
    snr_db: Optional[float]
    jitter_ms: Optional[float]
    findings_text: str


def _rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values)) \
        if values else None


def _ac_rms(values):
    if not values:
        return None
    mean = statistics.fmean(values)
    return _rms([value - mean for value in values])


def calculate_signal_metrics(series, pre_event_seconds, findings=()):
    """Calculate supported metrics without repairing or resampling samples."""
    samples = list(series.samples)
    finite = all(math.isfinite(sample.value) for sample in samples)

    peak = (max(abs(sample.value) for sample in samples)
            if samples and finite else None)
    rms = _rms([sample.value for sample in samples]) if samples and finite else None

    snr = None
    if (samples and finite and pre_event_seconds is not None
            and pre_event_seconds > 0):
        first_sample_us = min(sample.timestamp_us for sample in samples)
        pre_event_end = first_sample_us + int(pre_event_seconds * 1_000_000)
        noise = [sample.value for sample in samples
                 if sample.timestamp_us < pre_event_end]
        signal = [sample.value for sample in samples
                  if sample.timestamp_us >= pre_event_end]
        noise_rms = _ac_rms(noise)
        signal_rms = _ac_rms(signal)
        if noise_rms is not None and signal_rms is not None and noise_rms > 0:
            snr = 20.0 * math.log10(signal_rms / noise_rms) if signal_rms > 0 else None

    # Include only intervals that are sequential in the original sensor
    # record stream. Gaps/reversals are reported separately as findings.
    intervals_us = []
    for left, right in zip(samples, samples[1:]):
        delta = right.timestamp_us - left.timestamp_us
        if right.secuencia == left.secuencia + 1 and delta > 0:
            intervals_us.append(delta)
    jitter = (statistics.pstdev(intervals_us) / 1000.0
              if len(intervals_us) >= 2 else None)

    finding_count = len(list(findings))
    findings_text = ("Sin hallazgos de continuidad" if finding_count == 0
                     else "Revisar (%d hallazgo%s)" % (
                         finding_count, "" if finding_count == 1 else "s"))
    return SignalMetrics(peak, rms, snr, jitter, findings_text)
