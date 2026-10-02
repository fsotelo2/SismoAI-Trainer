"""ESP-DL/ESP-PPQ export integration for validated ONNX models."""
from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path


SUPPORTED_TARGETS = ("esp32s3",)
SUPPORTED_QUANT_TYPES = ("w8a8", "w8a16", "w16a16", "none")


def _load_esp_ppq():
    try:
        from esp_ppq.api import espdl_quantize_onnx
    except ImportError as exc:
        raise RuntimeError(
            "ESP-PPQ no está instalado. Instala la versión validada para "
            "ESP-DL 3.3.13 antes de exportar .espdl."
        ) from exc
    try:
        version = importlib.metadata.version("esp-ppq")
    except importlib.metadata.PackageNotFoundError:
        version = "desconocida"
    return espdl_quantize_onnx, version


def export_espdl(onnx_path: str | Path, output_dir: str | Path,
                 export_name: str, calibration_samples, input_shape: list[int],
                 target: str, quant_type: str, calibration_count: int) -> dict:
    """Quantize an ONNX model with ESP-PPQ and export ESP-DL artifacts."""
    import numpy as np
    import torch
    from torch.utils.data import DataLoader

    if target not in SUPPORTED_TARGETS:
        raise ValueError("Destino Espressif no soportado: " + str(target))
    if quant_type not in SUPPORTED_QUANT_TYPES:
        raise ValueError("Esquema ESP-PPQ no soportado: " + str(quant_type))
    source = Path(onnx_path).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise ValueError("No existe el ONNX de entrada.")
    samples = np.asarray(calibration_samples, dtype=np.float32)
    if samples.ndim != 3 or tuple(samples.shape[1:]) != tuple(input_shape):
        raise ValueError("Las muestras de calibración no coinciden con la entrada ONNX.")
    if len(samples) < 1:
        raise ValueError("Se requiere al menos una muestra de calibración.")
    espdl_quantize_onnx, esp_ppq_version = _load_esp_ppq()
    tensor = torch.from_numpy(samples)
    dataloader = DataLoader(tensor, batch_size=1, shuffle=False)

    def collate_fn(batch):
        return batch.to(dtype=torch.float32)

    target_path = output / (str(export_name).strip() + ".espdl")
    espdl_quantize_onnx(
        onnx_import_file=str(source),
        espdl_export_file=str(target_path),
        calib_dataloader=dataloader,
        calib_steps=min(int(calibration_count), len(samples)),
        input_shape=[1, *[int(value) for value in input_shape]],
        target=target,
        quant_type=quant_type,
        collate_fn=collate_fn,
        device="cpu",
        error_report=True,
        skip_export=False,
        export_test_values=True,
        verbose=1,
    )
    if not target_path.is_file():
        raise RuntimeError("ESP-PPQ no produjo el archivo .espdl esperado.")
    artifacts = {}
    for suffix in (".info", ".json"):
        candidate = output / (str(export_name).strip() + suffix)
        if candidate.is_file():
            artifacts[suffix[1:]] = {
                "path": str(candidate),
                "bytes": candidate.stat().st_size,
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            }
    return {
        "status": "completed",
        "format": "espdl",
        "target": target,
        "quantization": quant_type,
        "esp_ppq_version": esp_ppq_version,
        "espdl_path": str(target_path),
        "bytes": target_path.stat().st_size,
        "sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
        "input_shape": [1, *[int(value) for value in input_shape]],
        "calibration_samples": int(min(int(calibration_count), len(samples))),
        "artifacts": artifacts,
    }
