"""Phase 8: reproducible logical dataset manifests."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
import json
import os
import tempfile
import uuid

class DatasetError(ValueError):
    pass

def _event_index(value):
    """Return the source event's zero-based index when the ID is numeric."""
    try:
        index = int(value)
        return index if index >= 0 else None
    except (TypeError, ValueError):
        return None

def _group_key(window):
    event = window.get("source_event_id")
    if event is None or str(event).strip() == "":
        raise DatasetError("Hay ventanas sin evento de origen; no se puede evitar fuga entre particiones.")
    return f'{window.get("source_file", "")}::{event}'

def _target_counts(total, ratios):
    """Allocate every window exactly once using largest remainders."""
    raw = [total * ratio for ratio in ratios]
    counts = [math.floor(value) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True):
        if sum(counts) >= total:
            break
        counts[index] += 1
    return counts

def build_manifest(items, ratios=(0.70, 0.15, 0.15), seed=42):
    if len(ratios) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in ratios) or abs(sum(ratios)-1)>1e-6:
        raise DatasetError("Los porcentajes train/validation/test deben sumar 100%.")
    if not items:
        raise DatasetError("No hay ventanas incluidas para construir el dataset.")
    groups=defaultdict(list)
    for item in items:
        w=item.get("window") or {}; label=item.get("label")
        if (not w.get("window_id") or not label or isinstance(label.get("class_code"), bool)
                or not isinstance(label.get("class_code"), int) or label.get("class_code") not in (0, 1)
                or label.get("quality_review") != "confirmed"):
            raise DatasetError("Todas las ventanas deben tener etiqueta binaria guardada y revisión confirmada.")
        groups[_group_key(w)].append(item)
    # Preserve event isolation whenever there are enough independent events.
    ordered=sorted(groups, key=lambda k: hashlib.sha256(f"{seed}:{k}".encode()).hexdigest())
    targets=[ratios[0]*len(items),ratios[1]*len(items),ratios[2]*len(items)]
    counts=[0,0,0]; parts=[[],[],[]]
    if len(groups) == 1 and len(items) > 1:
        # A single event cannot be isolated across all three partitions.
        # Split windows so the requested dataset is usable, and report the trade-off.
        target_counts = _target_counts(len(items), ratios)
        offset = 0
        for index, target in enumerate(target_counts):
            parts[index].extend(items[offset:offset + target])
            offset += target
    else:
        for key in ordered:
            group=groups[key]
            idx=min(range(3), key=lambda j: (counts[j]-targets[j], j))
            parts[idx].extend(group); counts[idx]+=len(group)
    def summarize(rows):
        return {"windows":len(rows),"classes":dict(Counter(str(x["label"]["class_code"]) for x in rows)),
                "events":len({_group_key(x["window"]) for x in rows})}
    warnings=[]
    if len(groups)<10: warnings.append("Pocos eventos independientes: las métricas pueden ser inestables.")
    if len(groups) == 1 and len(items) > 1:
        warnings.append("Solo hay un evento independiente; las ventanas se repartieron individualmente y pueden compartir origen entre particiones.")
    overall=Counter(str(x["label"]["class_code"]) for x in items)
    if len(overall)<2: warnings.append("El conjunto contiene una sola clase.")
    for name,rows in zip(("train","validation","test"),parts):
        if rows and len({x["label"]["class_code"] for x in rows})<2:
            warnings.append(f"La partición {name} no contiene ambas clases.")
    return {"schema":"sismoai-dataset","schema_version":1,"dataset_id":str(uuid.uuid4()),
      "created_at":datetime.now(timezone.utc).isoformat(),"seed":seed,"ratios":list(ratios),
      "splits":{name:[{
        "window_id":x["window"]["window_id"],
        "source_file":x["window"].get("source_file"),
        "source_event_id":x["window"].get("source_event_id"),
        "event_index":_event_index(x["window"].get("source_event_id")),
        "start_us":x["window"].get("start_us"),
        "end_us":x["window"].get("end_us"),
        "duration_us":((x["window"].get("end_us") or 0)-(x["window"].get("start_us") or 0)),
        "time_reference":"event_relative",
        "sensors":list(x["window"].get("sensors") or []),
        "sample_ranges":x["window"].get("sample_ranges") or {},
        "sampling_info":x["window"].get("sampling_info") or {},
        "source_hash":x["window"].get("source_hash"),
        "event_interval":x["window"].get("event_interval"),
        "origin_mode":x["window"].get("origin_mode"),
        "window_config":x["window"].get("window_config") or {},
        "class_code":x["label"]["class_code"]
      } for x in rows] for name,rows in zip(("train","validation","test"),parts)},
      "summary":{"all":summarize(items),"train":summarize(parts[0]),"validation":summarize(parts[1]),"test":summarize(parts[2])},
      "warnings":warnings}

def save_manifest(path, manifest):
    folder=os.path.dirname(path) or "."
    os.makedirs(folder,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".dataset-",suffix=".tmp",dir=folder)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(manifest,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return os.path.abspath(path)
