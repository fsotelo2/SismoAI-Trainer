"""Post-ONNX stages: INT8 dynamic quantization, test evaluation, and bundle packaging."""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _load_split_arrays(manifest_path: str, config: dict, split_name: str):
    """Load the held-out test split using the same resampling and per-window z-score as training."""
    import numpy as np

    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.is_file():
        raise ValueError("No se encontró el manifiesto del Dataset activo.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != "sismoai-dataset" or manifest.get("schema_version") != 1:
        raise ValueError("El Dataset activo no tiene un manifiesto compatible.")
    rows = (manifest.get("splits") or {}).get(split_name) or []
    if not rows:
        raise ValueError("La partición " + split_name + " está vacía; no se puede procesar.")
    from core.models.trainer import resolve_input_sensors
    sensor_mode, sensors = resolve_input_sensors(config.get("input"))
    root = manifest_file.parent
    xs, ys = [], []
    for item in rows:
        row_sensors = tuple(item.get("sensors") or ())
        missing = [sensor for sensor in sensors if sensor not in row_sensors]
        if missing:
            raise ValueError(
                "La ventana " + str(item.get("window_id")) + " no contiene los sensores "
                + ", ".join(missing) + " requeridos por " + sensor_mode + "."
            )
        rel = item.get("snapshot")
        if not rel:
            raise ValueError("Falta la copia física de una ventana de " + split_name + ": " + str(item.get("window_id")))
        path = (root / rel).resolve()
        if os.path.commonpath([str(root), str(path)]) != str(root):
            raise ValueError("Ruta de snapshot fuera del Dataset.")
        if not path.is_file():
            raise ValueError("No existe el snapshot de " + split_name + ": " + str(path))
        channels = []
        with np.load(path, allow_pickle=False) as stored:
            for sensor in sensors:
                vk, tk = sensor + "_amplitudes", sensor + "_times"
                if vk not in stored or tk not in stored:
                    raise ValueError("Snapshot sin señal " + sensor + ": " + str(item.get("window_id")))
                values = np.asarray(stored[vk], dtype=np.float32)
                times = np.asarray(stored[tk], dtype=np.float64)
                if len(values) < 2 or len(times) != len(values) or not np.isfinite(values).all() or not np.isfinite(times).all():
                    raise ValueError("Señal inválida en ventana de Test: " + str(item.get("window_id")))
                if np.any(np.diff(times) <= 0):
                    raise ValueError("Tiempos no crecientes en ventana de Test.")
                target = np.linspace(float(times[0]), float(times[-1]), 256)
                values = np.interp(target, times, values).astype(np.float32)
                std = float(values.std())
                values = (values - float(values.mean())) / (std if std > 1e-8 else 1.0)
                channels.append(values)
        xs.append(np.stack(channels))
        code = item.get("class_code")
        if isinstance(code, bool) or code not in (0, 1):
            raise ValueError("Etiqueta inválida en conjunto Test.")
        ys.append(int(code))
    return np.stack(xs).astype(np.float32), np.asarray(ys, dtype=np.int64)


def _accuracy(pred, truth):
    import numpy as np
    return float(np.mean(np.asarray(pred) == np.asarray(truth)))


def run_post_onnx_stages(onnx_path: str, output_dir: str, export_name: str,
                         dataset_manifest_path: str, config: dict,
                         expected_input_shape: list, expected_dataset_id: str,
                         calibration_count: int = 200,
                         output_format: str = "onnx",
                         quantization_method: str = "onnx_int8",
                         target: str = "esp32s3",
                         normalization: str = "experiment") -> dict:
    """Run quantization, held-out test evaluation, and create a portable deployment bundle."""
    import numpy as np
    import onnx
    import onnxruntime as ort

    source = Path(onnx_path).resolve()
    out = Path(output_dir).resolve()
    if not source.is_file():
        raise ValueError("No existe el ONNX de entrada.")
    if output_format not in ("onnx", "espdl"):
        raise ValueError("Formato de exportación no soportado: " + str(output_format))
    if normalization != "experiment":
        raise ValueError("La única normalización soportada es la del experimento.")
    out.mkdir(parents=True, exist_ok=True)
    quant_path = out / (export_name + ".int8.onnx")

    # Stage 2: static post-training INT8 quantization calibrated only on Train.
    manifest = json.loads(Path(dataset_manifest_path).read_text(encoding="utf-8"))
    if str(manifest.get("dataset_id")) != str(expected_dataset_id):
        raise ValueError("El Dataset activo no corresponde al experimento entrenado.")
    x_cal, _ = _load_split_arrays(dataset_manifest_path, config, "train")
    expected = tuple(int(v) for v in expected_input_shape)
    from core.models.trainer import resolve_input_sensors
    input_mode, sensors = resolve_input_sensors(config.get("input"))
    if expected[0] != len(sensors):
        raise ValueError(
            "La arquitectura ONNX para " + input_mode + " declara "
            + str(expected[0]) + " canales; se requieren " + str(len(sensors))
            + ". Reentrena el experimento antes de calibrar."
        )
    actual = tuple(int(v) for v in x_cal.shape[1:])
    if actual != expected:
        raise ValueError(
            "Dimensiones incompatibles para calibración INT8: Dataset Train "
            + str(actual) + " (canales, puntos), modelo ONNX "
            + str(expected) + " (canales, puntos). "
            "Revisa la selección de sensores y la configuración del experimento."
        )
    count = max(1, min(int(calibration_count), len(x_cal)))
    indices = np.linspace(0, len(x_cal)-1, count, dtype=np.int64)
    x_cal = x_cal[indices]
    original_session = ort.InferenceSession(str(source), providers=["CPUExecutionProvider"])
    input_name = original_session.get_inputs()[0].name
    quantization = None
    quant_session = original_session
    if output_format == "onnx":
        if quantization_method not in ("none", "onnx_int8"):
            raise ValueError("La cuantización " + str(quantization_method) +
                             " requiere exportación ESP-DL (.espdl).")
        if quantization_method == "onnx_int8":
            from onnxruntime.quantization import (quantize_static, QuantFormat, QuantType,
                                                  CalibrationMethod, CalibrationDataReader)

            class Reader(CalibrationDataReader):
                def __init__(self, samples, input_name):
                    self.samples = samples
                    self.input_name = input_name
                    self.index = 0
                def get_next(self):
                    if self.index >= len(self.samples):
                        return None
                    sample = self.samples[self.index:self.index+1]
                    self.index += 1
                    return {self.input_name: sample}
                def rewind(self):
                    self.index = 0

            quantize_static(str(source), str(quant_path), Reader(x_cal, input_name),
                            quant_format=QuantFormat.QDQ, activation_type=QuantType.QUInt8,
                            weight_type=QuantType.QInt8, calibrate_method=CalibrationMethod.MinMax,
                            op_types_to_quantize=["Conv", "Gemm"])
            quant_graph = onnx.load(str(quant_path))
            onnx.checker.check_model(quant_graph)
            quant_session = ort.InferenceSession(str(quant_path), providers=["CPUExecutionProvider"])
            quantization = {
                "status": "completed",
                "format": "onnx",
                "method": "onnxruntime_static_ptq_int8",
                "calibration_split": "train",
                "calibration_samples": int(count),
                "path": str(quant_path),
                "bytes": quant_path.stat().st_size,
            }
        else:
            quantization = {
                "status": "skipped",
                "format": "onnx",
                "method": "none",
                "calibration_split": None,
                "calibration_samples": 0,
            }
    else:
        if quantization_method not in ("w8a8", "w8a16", "w16a16", "none"):
            raise ValueError("Esquema ESP-PPQ no soportado: " + str(quantization_method))
        from core.models.espressif import export_espdl
        quantization = export_espdl(
            source, out, export_name, x_cal, list(expected), target,
            quantization_method, count,
        )

    # Stage 3: evaluate original and quantized graphs on the reserved Test split.
    x_test, y_test = _load_split_arrays(dataset_manifest_path, config, "test")
    expected = tuple(int(v) for v in expected_input_shape)
    if tuple(x_test.shape[1:]) != expected:
        raise ValueError("La forma de entrada del conjunto Test no coincide con el modelo.")
    input_name = original_session.get_inputs()[0].name
    original_logits = original_session.run(None, {input_name: x_test})[0]
    q_input = quant_session.get_inputs()[0].name
    original_pred = np.argmax(original_logits, axis=1)
    original_acc = _accuracy(original_pred, y_test)
    evaluation = {
        "status": "completed",
        "split": "test",
        "samples": int(len(y_test)),
        "original_accuracy": original_acc,
        "quantized_accuracy": None,
        "accuracy_delta": None,
        "original_correct": int(np.sum(original_pred == y_test)),
        "quantized_correct": None,
        "quantized_evaluation": "not_available" if output_format == "espdl" else "completed",
    }
    if output_format == "onnx" and quantization_method == "onnx_int8":
        q_input = quant_session.get_inputs()[0].name
        quant_logits = quant_session.run(None, {q_input: x_test})[0]
        quant_pred = np.argmax(quant_logits, axis=1)
        quant_acc = _accuracy(quant_pred, y_test)
        evaluation.update(
            quantized_accuracy=quant_acc,
            accuracy_delta=quant_acc - original_acc,
            quantized_correct=int(np.sum(quant_pred == y_test)),
        )

    # Stage 4: portable deployment bundle. It is not firmware/a compiled ESP32-S3 binary.
    report = {
        "schema": "sismoai-export-pipeline",
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": export_name,
        "format": output_format,
        "target": target,
        "stages": {
            "onnx": {"status": "completed", "path": str(source)},
            "quantization": quantization,
            "evaluation": evaluation,
            "package": {"status": "completed", "type": "portable_model_bundle",
                        "executable": False},
        },
        "limitations": [
            "La compatibilidad ESP32-S3 requiere validar ESP-DL/ESP-PPQ y el runtime objetivo.",
            "El paquete contiene artefactos y metadatos; no es firmware ni binario ejecutable.",
            "La compilación final requiere ESP-IDF y un componente ESP-DL compatible."
        ],
    }
    report_path = out / (export_name + ".pipeline.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = (
        "# SismoAI — paquete de modelo\n\n"
        f"Modelo: {export_name}\nFormato: {output_format}\nDestino previsto: {target}\n\n"
        "Contenido: artefactos de exportación y reportes de validación.\n"
        "Este paquete no es un binario ejecutable ni firmware. Verifique operadores, memoria, "
        "runtime y conversión específica del microcontrolador antes del despliegue.\n"
    )
    package_path = out / (export_name + "_esp32s3_bundle.zip")
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, source.name)
        if quant_path is not None and quant_path.is_file():
            archive.write(quant_path, quant_path.name)
        if output_format == "espdl":
            espdl_path = Path(quantization["espdl_path"])
            archive.write(espdl_path, espdl_path.name)
            for artifact in quantization.get("artifacts", {}).values():
                archive.write(artifact["path"], Path(artifact["path"]).name)
        archive.write(report_path, report_path.name)
        onnx_report = source.parent / (export_name + ".export.json")
        if onnx_report.is_file():
            archive.write(onnx_report, onnx_report.name)
        archive.writestr("README.md", readme)
    report["stages"]["package"].update(path=str(package_path), bytes=package_path.stat().st_size,
        sha256=hashlib.sha256(package_path.read_bytes()).hexdigest())
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
