"""Reproducible CPU training and evaluation for Phase 9.

Input contract: float32 arrays shaped (samples, channels, points), labels int64.
ESP32-S3 compatibility is not implied by successful PC training.
"""
from __future__ import annotations

import json
import hashlib
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np


def _torch():
    try:
        import torch
        from torch import nn
        return torch, nn
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch no está instalado. Instala las dependencias de requirements.txt "
            "en el entorno de la aplicación."
        ) from exc


def _extract_features(x: np.ndarray) -> np.ndarray:
    """Compute six deterministic per-channel statistics from each normalized window."""
    x = np.asarray(x, dtype=np.float32)
    return np.stack((x.mean(axis=2), x.std(axis=2),
                     np.sqrt(np.mean(np.square(x), axis=2)),
                     np.max(np.abs(x), axis=2),
                     np.ptp(x, axis=2),
                     np.mean(np.abs(np.diff(x, axis=2)), axis=2)), axis=2).astype(np.float32)


def build_network(architecture: str, channels: int, points: int, classes: int = 2):
    torch, nn = _torch()
    if architecture == "1d_cnn":
        class CNN1D(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv1d(channels, 16, kernel_size=7, padding=3),
                    nn.ReLU(),
                    nn.MaxPool1d(2),
                    nn.Conv1d(16, 32, kernel_size=5, padding=2),
                    nn.ReLU(),
                    nn.AdaptiveAvgPool1d(8),
                    nn.Flatten(),
                )
                self.classifier = nn.Sequential(nn.Linear(32 * 8, 32), nn.ReLU(), nn.Linear(32, classes))
            def forward(self, x):
                return self.classifier(self.features(x))
        return CNN1D()
    if architecture == "feature_classifier":
        class FeatureMLP(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(nn.Flatten(), nn.Linear(channels * points, 64),
                                         nn.ReLU(), nn.Linear(64, classes))
            def forward(self, x):
                return self.net(x)
        return FeatureMLP()
    if architecture == "baseline":
        class LinearBaseline(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(nn.Flatten(), nn.Linear(channels * points, classes))
            def forward(self, x):
                return self.net(x)
        return LinearBaseline()
    raise ValueError("Arquitectura no soportada.")


def _metrics(y_true, y_pred, class_count=2):
    cm = [[0 for _ in range(class_count)] for _ in range(class_count)]
    for truth, pred in zip(y_true, y_pred):
        cm[int(truth)][int(pred)] += 1
    total = sum(map(sum, cm))
    accuracy = sum(cm[i][i] for i in range(class_count)) / total if total else 0.0
    per_class = []
    for i in range(class_count):
        tp = cm[i][i]
        fp = sum(cm[row][i] for row in range(class_count)) - tp
        fn = sum(cm[i]) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class.append({"class_code": i, "support": sum(cm[i]), "precision": precision,
                          "recall": recall, "f1": f1})
    return {"accuracy": accuracy, "precision_macro": sum(x["precision"] for x in per_class)/class_count,
            "recall_macro": sum(x["recall"] for x in per_class)/class_count,
            "f1_macro": sum(x["f1"] for x in per_class)/class_count,
            "per_class": per_class, "confusion_matrix": cm, "samples": total}



def _validate_arrays(arrays: dict) -> None:
    """Fail fast on malformed, non-finite, or out-of-contract split tensors."""
    required = ("train", "validation", "test")
    shapes = []
    for split in required:
        if split not in arrays or not isinstance(arrays[split], (tuple, list)) or len(arrays[split]) != 2:
            raise ValueError("Cada partición debe contener (X, y): " + split)
        x, y = arrays[split]
        x = np.asarray(x)
        y = np.asarray(y)
        if x.ndim != 3:
            raise ValueError("X debe tener forma (muestras, canales, puntos): " + split)
        if y.ndim != 1 or len(x) != len(y):
            raise ValueError("X e y no están alineados en la partición: " + split)
        if x.shape[1] < 1 or x.shape[2] < 2:
            raise ValueError("Se requiere al menos un canal y dos puntos por muestra.")
        if not np.issubdtype(y.dtype, np.integer) or np.issubdtype(y.dtype, np.bool_):
            raise ValueError("Las etiquetas deben ser enteros 0/1: " + split)
        if len(y) and not np.isin(y, (0, 1)).all():
            raise ValueError("Se encontraron códigos de clase fuera de 0/1: " + split)
        if not np.isfinite(x).all():
            raise ValueError("La señal contiene NaN o infinito en: " + split)
        shapes.append(x.shape[1:])
    if len(set(shapes)) != 1:
        raise ValueError("Las particiones deben compartir canales y longitud de entrada.")


def train_experiment(config: dict, arrays: dict, output_dir: str,
                     progress: Callable[[dict], None] | None = None) -> dict:
    torch, nn = _torch()
    if not isinstance(config, dict) or not isinstance(config.get("training"), dict):
        raise ValueError("La configuración de entrenamiento no es válida.")
    training = config["training"]
    seed_value = training.get("seed", 42)
    if isinstance(seed_value, bool) or not isinstance(seed_value, int) or seed_value < 0:
        raise ValueError("La semilla debe ser un entero no negativo.")
    seed = seed_value
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    _validate_arrays(arrays)
    x_train, y_train = arrays["train"]
    x_val, y_val = arrays["validation"]
    x_test, y_test = arrays["test"]
    if len(x_train) == 0 or len(x_val) == 0:
        raise ValueError("Train y Validation deben contener muestras.")
    epochs = int(training.get("epochs", 0))
    batch_size = int(training.get("batch_size", 0))
    learning_rate = float(training.get("learning_rate", 0))
    if epochs < 1 or batch_size < 1 or not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Épocas, batch size y learning rate deben ser positivos.")
    if config.get("architecture") not in ("1d_cnn", "feature_classifier", "baseline"):
        raise ValueError("Arquitectura no soportada.")
    optimizer_value = training.get("optimizer", "adam")
    if not isinstance(optimizer_value, str) or optimizer_value.lower() not in ("adam", "adamw", "sgd"):
        raise ValueError("Optimizador no soportado.")
    if training.get("loss", "cross_entropy") != "cross_entropy":
        raise ValueError("La única función de pérdida implementada es cross_entropy.")
    if len(set(map(int, y_train))) < 2:
        raise ValueError("Train debe contener ambas clases para entrenar clasificación binaria.")
    if len(set(map(int, y_val))) < 2:
        # Still score available class distribution; do not fabricate missing labels.
        pass
    original_shape = list(x_train.shape[1:])
    if config["architecture"] == "feature_classifier":
        x_train, x_val, x_test = (_extract_features(x) for x in (x_train, x_val, x_test))
    model = build_network(config["architecture"], x_train.shape[1], 6 if config["architecture"] == "feature_classifier" else x_train.shape[2])
    optimizer_name = training.get("optimizer", "adam").lower()
    if optimizer_name == "sgd":
        optimizer = torch.optim.SGD(model.parameters(), lr=float(training["learning_rate"]))
    elif optimizer_name == "adamw":
        optimizer = torch.optim.AdamW(model.parameters(), lr=float(training["learning_rate"]))
    else:
        optimizer = torch.optim.Adam(model.parameters(), lr=float(training["learning_rate"]))
    if training.get("class_weighting"):
        counts = np.bincount(np.asarray(y_train, dtype=np.int64), minlength=2).astype(np.float32)
        weights = np.where(counts > 0, len(y_train) / np.maximum(counts, 1) / 2.0, 0.0)
        criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32))
    else:
        criterion = nn.CrossEntropyLoss()
    xt = torch.from_numpy(np.asarray(x_train, dtype=np.float32))
    yt = torch.from_numpy(np.asarray(y_train, dtype=np.int64))
    xv = torch.from_numpy(np.asarray(x_val, dtype=np.float32))
    yv = torch.from_numpy(np.asarray(y_val, dtype=np.int64))
    history = []
    best_loss = float("inf")
    best_state = None
    stale = 0
    start = time.time()
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(xt))
        train_loss_sum = 0.0
        seen = 0
        for offset in range(0, len(order), batch_size):
            ids = order[offset:offset+batch_size]
            optimizer.zero_grad()
            logits = model(xt[ids])
            loss = criterion(logits, yt[ids])
            loss.backward()
            optimizer.step()
            count = len(ids)
            train_loss_sum += float(loss.item()) * count
            seen += count
        model.eval()
        with torch.no_grad():
            val_logits = model(xv)
            val_loss = float(criterion(val_logits, yv).item())
            val_pred = val_logits.argmax(dim=1).cpu().numpy()
        row = {"epoch": epoch+1, "train_loss": train_loss_sum/max(seen,1),
               "validation_loss": val_loss,
               "validation_accuracy": _metrics(y_val, val_pred)["accuracy"]}
        history.append(row)
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if progress:
            progress({"epoch": epoch+1, "epochs": epochs, **row, "elapsed_seconds": time.time()-start})
        if training.get("early_stopping") and stale >= 10:
            break
    if training.get("save_best", True) and best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    def predict(x):
        if len(x)==0:return np.asarray([],dtype=np.int64)
        with torch.no_grad():
            return model(torch.from_numpy(np.asarray(x,dtype=np.float32))).argmax(1).cpu().numpy()
    train_pred=predict(x_train); val_pred=predict(x_val); test_pred=predict(x_test)
    metrics={"train":_metrics(y_train,train_pred),"validation":_metrics(y_val,val_pred),
             "test":_metrics(y_test,test_pred) if len(y_test) else None}
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    weights=out/"weights.pt"
    torch.save(model.state_dict(),weights)
    with torch.no_grad():
        final_train_loss=float(criterion(model(xt),yt).item())
        final_val_loss=float(criterion(model(xv),yv).item())
    metrics["train"]["loss"]=final_train_loss
    metrics["validation"]["loss"]=final_val_loss
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    result={"status":"trained","created_at":datetime.now(timezone.utc).isoformat(),
            "epochs_completed":len(history),"history":history,"metrics":metrics,
            "weights_path":str(weights),"weights_bytes":weights.stat().st_size,"weights_sha256":digest,
            "config":config,
            "input_shape":original_shape,"preprocessing":"resample lineal a 256 puntos; z-score por ventana y canal" + ("; seis estadísticas por canal" if config["architecture"] == "feature_classifier" else ""),
            "elapsed_seconds":time.time()-start}
    with open(out/"training_result.json","w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    return result
