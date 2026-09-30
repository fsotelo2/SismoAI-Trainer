"""Phase 8: reproducible logical dataset manifests."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
import tempfile
import uuid

class DatasetError(ValueError):
    pass

def _group_key(window):
    event = window.get("source_event_id")
    if event is None or str(event).strip() == "":
        raise DatasetError("Hay ventanas sin evento de origen; no se puede evitar fuga entre particiones.")
    return f'{window.get("source_file", "")}::{event}'

def build_manifest(items, ratios=(0.70, 0.15, 0.15), seed=42):
    if len(ratios) != 3 or any(not isinstance(x,(int,float)) or x < 0 for x in ratios) or abs(sum(ratios)-1)>1e-6:
        raise DatasetError("Los porcentajes train/validation/test deben sumar 100%.")
    if not items:
        raise DatasetError("No hay ventanas incluidas para construir el dataset.")
    groups=defaultdict(list)
    for item in items:
        w=item.get("window") or {}; label=item.get("label")
        if not w.get("window_id") or not label or label.get("class_code") not in (0,1) or label.get("quality_review")!="confirmed":
            raise DatasetError("Todas las ventanas deben tener etiqueta binaria guardada y revisión confirmada.")
        groups[_group_key(w)].append(item)
    # Stable deterministic group assignment, approximately respecting requested proportions.
    ordered=sorted(groups, key=lambda k: hashlib.sha256(f"{seed}:{k}".encode()).hexdigest())
    targets=[ratios[0]*len(items),ratios[1]*len(items),ratios[2]*len(items)]
    counts=[0,0,0]; parts=[[],[],[]]
    for key in ordered:
        group=groups[key]
        idx=min(range(3), key=lambda j: (counts[j]-targets[j], j))
        parts[idx].extend(group); counts[idx]+=len(group)
    def summarize(rows):
        return {"windows":len(rows),"classes":dict(Counter(str(x["label"]["class_code"]) for x in rows)),
                "events":len({_group_key(x["window"]) for x in rows})}
    warnings=[]
    if len(groups)<10: warnings.append("Pocos eventos independientes: las métricas pueden ser inestables.")
    overall=Counter(str(x["label"]["class_code"]) for x in items)
    if len(overall)<2: warnings.append("El conjunto contiene una sola clase.")
    for name,rows in zip(("train","validation","test"),parts):
        if rows and len({x["label"]["class_code"] for x in rows})<2:
            warnings.append(f"La partición {name} no contiene ambas clases.")
    return {"schema":"sismoai-dataset","schema_version":1,"dataset_id":str(uuid.uuid4()),
      "created_at":datetime.now(timezone.utc).isoformat(),"seed":seed,"ratios":list(ratios),
      "splits":{name:[{"window_id":x["window"]["window_id"],"source_file":x["window"].get("source_file"),
        "source_event_id":x["window"].get("source_event_id"),"class_code":x["label"]["class_code"]} for x in rows]
        for name,rows in zip(("train","validation","test"),parts)},
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
