"""Post-ONNX stages: INT8 dynamic quantization, test evaluation, and bundle packaging."""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _load_test_arrays(manifest_path: str, config: dict):
    """Load the held-out test split using the same resampling and per-window z-score as training."""
    import numpy as np

    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.is_file():
        raise ValueError("No se encontró el manifiesto del Dataset activo.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != "sismoai-dataset" or manifest.get("schema_version") != 1:
        raise ValueError("El Dataset activo no tiene un manifiesto compatible.")
    rows = (manifest.get("splits") or {}).get("test") or []
    if not rows:
        raise ValueError("La partición Test está vacía; no se puede evaluar el modelo.")
    sensor_mode = config.get("input", "geo_mpu")
    sensors = {"geo_mpu": ("GEO", "MPU"), "geo": ("GEO",), "mpu": ("MPU",)}.get(sensor_mode)
    if not sensors:
        raise ValueError("Configuración de sensores no reconocida para evaluación.")
    root = manifest_file.parent
    xs, ys = [], []
    for item in rows:
        rel = item.get("snapshot")
        if not rel:
            raise ValueError("Falta la copia física de una ventana del conjunto Test: " + str(item.get("window_id")))
        path = (root / rel).resolve()
        if os.path.commonpath([str(root), str(path)]) != str(root):
            raise ValueError("Ruta de snapshot fuera del Dataset.")
        if not path.is_file():
            raise ValueError("No existe el snapshot de Test: " + str(path))
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
                         expected_input_shape: list) -> dict:
    """Run quantization, held-out test evaluation, and create a portable deployment bundle."""
    import numpy as np
    import onnx
    import onnxruntime as ort
    from onnxruntime.quantization import quantize_dynamic, QuantType

    source = Path(onnx_path).resolve()
    out = Path(output_dir).resolve()
    if not source.is_file():
        raise ValueError("No existe el ONNX de entrada.")
    out.mkdir(parents=True, exist_ok=True)
    quant_path = out / (export_name + ".int8.onnx")

    # Stage 2: dynamic INT8 quantization. This method does not require calibration data.
    quantize_dynamic(str(source), str(quant_path), weight_type=QuantType.QInt8,
                     op_types_to_quantize=["Conv", "Gemm"])
    quant_graph = onnx.load(str(quant_path))
    onnx.checker.check_model(quant_graph)
    quant_session = ort.InferenceSession(str(quant_path), providers=["CPUExecutionProvider"])
    original_session = ort.InferenceSession(str(source), providers=["CPUExecutionProvider"])
    quant_bytes = quant_path.stat().st_size

    # Stage 3: evaluate original and quantized graphs on the reserved Test split.
    x_test, y_test = _load_test_arrays(dataset_manifest_path, config)
    expected = tuple(int(v) for v in expected_input_shape)
    if tuple(x_test.shape[1:]) != expected:
        raise ValueError("La forma de entrada del conjunto Test no coincide con el modelo.")
    input_name = original_session.get_inputs()[0].name
    original_logits = original_session.run(None, {input_name: x_test})[0]
    q_input = quant_session.get_inputs()[0].name
    quant_logits = quant_session.run(None, {q_input: x_test})[0]
    original_pred = np.argmax(original_logits, axis=1)
    quant_pred = np.argmax(quant_logits, axis=1)
    original_acc = _accuracy(original_pred, y_test)
    quant_acc = _accuracy(quant_pred, y_test)
    evaluation = {
        "status": "completed",
        "split": "test",
        "samples": int(len(y_test)),
        "original_accuracy": original_acc,
        "int8_accuracy": quant_acc,
        "accuracy_delta": quant_acc - original_acc,
        "original_correct": int(np.sum(original_pred == y_test)),
        "int8_correct": int(np.sum(quant_pred == y_test)),
    }

    # Stage 4: portable deployment bundle. It is not firmware/a compiled ESP32-S3 binary.
    report = {
        "schema": "sismoai-export-pipeline",
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": export_name,
        "target": "esp32s3",
        "stages": {
            "onnx": {"status": "completed", "path": str(source)},
            "quantization": {"status": "completed", "method": "onnxruntime_dynamic_int8",
                             "path": str(quant_path), "bytes": quant_bytes},
            "evaluation": evaluation,
            "package": {"status": "completed", "type": "portable_model_bundle",
                        "executable": False},
        },
        "limitations": [
            "La cuantización INT8 dinámica de ONNX no garantiza compatibilidad con ESP32-S3.",
            "El paquete contiene artefactos y metadatos; no es firmware ni binario ejecutable.",
            "La compilación final requiere conversión y runtime compatibles con el entorno ESP-IDF/ESP-DL."
        ],
    }
    report_path = out / (export_name + ".pipeline.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = (
        "# SismoAI — paquete de modelo\n\n"
        f"Modelo: {export_name}\nDestino previsto: ESP32-S3\n\n"
        "Contenido: modelo ONNX original, modelo ONNX cuantizado dinámicamente a INT8 y reportes.\n"
        "Este paquete no es un binario ejecutable ni firmware. Verifique operadores, memoria, "
        "runtime y conversión específica del microcontrolador antes del despliegue.\n"
    )
    package_path = out / (export_name + "_esp32s3_bundle.zip")
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, source.name)
        archive.write(quant_path, quant_path.name)
        archive.write(report_path, report_path.name)
        onnx_report = source.parent / (export_name + ".export.json")
        if onnx_report.is_file():
            archive.write(onnx_report, onnx_report.name)
        archive.writestr("README.md", readme)
    report["stages"]["package"].update(path=str(package_path), bytes=package_path.stat().st_size,
        sha256=hashlib.sha256(package_path.read_bytes()).hexdigest())
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
