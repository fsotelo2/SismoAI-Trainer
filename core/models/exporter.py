"""ONNX export and numerical parity checks for registered SismoAI CNN models."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path


def export_onnx(model_dir: str | Path, output_dir: str | Path, export_name: str,
                verify: bool = True) -> dict:
    """Reconstruct a registered 1D-CNN, export ONNX, and optionally verify parity."""
    import numpy as np
    import torch
    import onnx
    import onnxruntime as ort
    from .trainer import reconstruct_model

    name = str(export_name or "").strip()
    if not name or len(name) > 100 or any(c in name for c in '/\\\0'):
        raise ValueError("Nombre de exportación no válido.")
    root = Path(model_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if out == root or root in out.parents:
        raise ValueError("El destino de exportación no puede estar dentro del directorio del modelo.")
    model, manifest = reconstruct_model(root)
    params = manifest["factory_parameters"]
    sample_shape = (1, int(params["channels"]), int(params["points"]))
    model.eval()
    target = out / f"{name}.onnx"
    sample = torch.zeros(sample_shape, dtype=torch.float32)
    torch.onnx.export(model, sample, str(target), input_names=["signal"],
                      output_names=["logits"], opset_version=17,
                      dynamic_axes={"signal": {0: "batch"}, "logits": {0: "batch"}},
                      do_constant_folding=True)
    graph = onnx.load(str(target))
    onnx.checker.check_model(graph)
    session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
    parity = None
    if verify:
        rng = np.random.default_rng(42)
        test_input = rng.normal(size=sample_shape).astype(np.float32)
        with torch.no_grad():
            expected = model(torch.from_numpy(test_input)).cpu().numpy()
        actual = session.run(["logits"], {"signal": test_input})[0]
        max_abs = float(np.max(np.abs(expected - actual)))
        parity = {"passed": bool(np.allclose(expected, actual, rtol=1e-4, atol=1e-5)),
                  "max_absolute_error": max_abs}
        if not parity["passed"]:
            raise ValueError(f"Falló equivalencia PyTorch/ONNX (error máximo {max_abs:.8g}).")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    report = {"status": "completed", "name": name, "format": "onnx",
              "target": "esp32s3", "onnx_path": str(target),
              "bytes": target.stat().st_size, "sha256": digest,
              "input_shape": list(sample_shape), "output_shape": [1, int(params["classes"])],
              "opset": 17, "verified": bool(verify), "parity": parity,
              "quantization": "none",
              "note": "ONNX es un formato intermedio; no constituye un binario ejecutable para ESP32-S3."}
    (out / f"{name}.export.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
