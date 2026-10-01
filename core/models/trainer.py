"""Reproducible CPU training and evaluation for Phase 9.

Input contract: float32 arrays shaped (samples, channels, points), labels int64.
ESP32-S3 compatibility is not implied by successful PC training.
"""
from __future__ import annotations

import json
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


def train_experiment(config: dict, arrays: dict, output_dir: str,
                     progress: Callable[[dict], None] | None = None) -> dict:
    torch, nn = _torch()
    training = config["training"]
    seed = int(training["seed"])
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    x_train, y_train = arrays["train"]
    x_val, y_val = arrays["validation"]
    x_test, y_test = arrays["test"]
    if len(x_train) == 0 or len(x_val) == 0:
        raise ValueError("Train y Validation deben contener muestras.")
    if len(set(map(int, y_train))) < 2:
        raise ValueError("Train debe contener ambas clases para entrenar clasificación binaria.")
    if len(set(map(int, y_val))) < 2:
        # Still score available class distribution; do not fabricate missing labels.
        pass
    model = build_network(config["architecture"], x_train.shape[1], x_train.shape[2])
    optimizer_name = training.get("optimizer", "adam").lower()
    if optimizer_name == "sgd":
        optimizer = torch.optim.SGD(model.parameters(), lr=float(training["learning_rate"]))
    elif optimizer_name == "adamw":
        optimizer = torch.optim.AdamW(model.parameters(), lr=float(training["learning_rate"]))
    else:
        optimizer = torch.optim.Adam(model.parameters(), lr=float(training["learning_rate"]))
    criterion = nn.CrossEntropyLoss()
    xt = torch.from_numpy(np.asarray(x_train, dtype=np.float32))
    yt = torch.from_numpy(np.asarray(y_train, dtype=np.int64))
    xv = torch.from_numpy(np.asarray(x_val, dtype=np.float32))
    yv = torch.from_numpy(np.asarray(y_val, dtype=np.int64))
    history = []
    best_loss = float("inf")
    best_state = None
    stale = 0
    epochs = int(training["epochs"])
    batch_size = int(training["batch_size"])
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
    result={"status":"trained","created_at":datetime.now(timezone.utc).isoformat(),
            "epochs_completed":len(history),"history":history,"metrics":metrics,
            "weights_path":str(weights),"weights_bytes":weights.stat().st_size,
            "input_shape":list(x_train.shape[1:]),"preprocessing":"resample lineal a longitud fija; z-score por ventana y canal",
            "elapsed_seconds":time.time()-start}
    with open(out/"training_result.json","w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    return result
