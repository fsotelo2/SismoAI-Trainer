(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let experiments = [], datasets = [], busy = false;
  const fmt = (v) => v === null || v === undefined || v === "" ? "—" : String(v);
  const shape = (v) => Array.isArray(v) ? "[" + v.join(", ") + "]" : "—";
  function log(message) { const el=$("export-log"); if(el) el.value += "\n"+message; }
  function setBusy(value) {
    busy=value;
    const selected=!!$("export-experiment")?.value;
    ["btn-generate-export-package","btn-start-export"].forEach(id=>{const b=$(id);if(b)b.disabled=busy||!selected;});
    const reset=$("btn-reset-export"); if(reset)reset.disabled=busy;
  }
  function selectedExperiment(){return experiments.find(x=>x.experiment_id===$("export-experiment")?.value);}
  function renderExperiment(){
    const x=selectedExperiment(), box=$("export-model-summary");
    if(!box)return;
    if(!x){box.textContent="Selecciona un experimento para consultar arquitectura, dataset, dimensiones, accuracy y estado de validación.";setBusy(false);return;}
    const tr=x.training_result||{}, metrics=tr.metrics||{}, cfg=x.config||{};
    const acc=metrics.validation?.accuracy??metrics.validation_accuracy??metrics.accuracy??metrics.val_accuracy;
    box.innerHTML="<strong>Experimento:</strong> "+esc(cfg.name||x.experiment_id)+
      "<br><strong>Arquitectura:</strong> "+esc(cfg.architecture||"—")+
      "<br><strong>Dataset:</strong> "+esc(x.dataset_name||x.dataset_id||"—")+
      "<br><strong>Entrada:</strong> "+esc(shape(tr.input_shape))+
      "<br><strong>Salida:</strong> "+esc(shape(tr.output_shape))+
      "<br><strong>Accuracy (validación):</strong> "+esc(typeof acc==="number"?(acc*100).toFixed(1)+"%":fmt(acc))+
      "<br><strong>Estado:</strong> <span class='export-status-ok'>Entrenado · se validará antes de exportar</span>";
    setBusy(false);
  }
  async function loadDatasets(){
    const sel=$("export-calibration-dataset"), summary=$("export-calibration-summary");
    if(!sel)return;
    try{
      const r=await Bridge.getDatasetCatalog();
      datasets=r?.success?(r.datasets||[]):[];
      sel.innerHTML='<option value="">Selecciona un dataset...</option>'+datasets.map(d=>'<option value="'+esc(d.dataset_id)+'">'+esc(d.name||d.dataset_id)+'</option>').join("");
      const exp=selectedExperiment(), match=datasets.find(d=>d.dataset_id===exp?.dataset_id);
      if(match)sel.value=match.dataset_id;
      if(summary)summary.textContent=match?
        "Dataset del experimento: "+(match.name||match.dataset_id)+". Ventanas registradas: "+fmt(match.windows)+". Reservado para una futura calibración; no se usa en la exportación ONNX actual.":
        "No hay datos de calibración aplicados en esta versión. La partición de prueba permanece reservada.";
      sel.disabled=true;
      const count=$("export-calibration-count");if(count)count.disabled=true;
    }catch(e){if(summary)summary.textContent="No se pudo consultar el catálogo de datasets: "+(e.message||e);}
  }
  function renderHistory(rows){
    const body=$("export-history-body");if(!body)return;
    if(!rows?.length){body.innerHTML='<tr><td colspan="8">Aún no hay exportaciones registradas.</td></tr>';return;}
    body.innerHTML=rows.map((x,i)=>'<tr><td>'+esc(x.name)+'</td><td>'+esc(x.experiment_name||x.experiment_id||"—")+
      '</td><td>ONNX</td><td>'+esc(x.quantization==='int8_static_ptq'?'INT8 estático PTQ':'Sin cuantización')+'</td><td>'+esc(x.bytes?Math.ceil(x.bytes/1024)+" KB":"—")+
      '</td><td>'+esc(x.created_at||"—")+'</td><td><span class="export-status-ok">Completado</span></td><td><button class="btn btn-secondary btn-sm" data-export-view="'+i+'">Ver</button></td></tr>').join("");
    body._exportRows=rows;
  }
  async function loadHistory(){
    const body=$("export-history-body");if(body)body.innerHTML='<tr><td colspan="8">Actualizando historial...</td></tr>';
    try{const r=await Bridge.getExportHistory();if(!r?.success)throw new Error(r?.error||"No se pudo leer historial.");renderHistory(r.exports||[]);}
    catch(e){if(body)body.innerHTML='<tr><td colspan="8">Error al consultar historial: '+esc(e.message||e)+'</td></tr>';}
  }
  async function load(){
    const select=$("export-experiment");if(!select)return;
    select.innerHTML='<option value="">Consultando experimentos...</option>';
    try{
      const r=await Bridge.getModelExperiments();
      if(!r?.success)throw new Error(r?.error||"No se pudieron consultar experimentos.");
      experiments=(r.experiments||[]).filter(x=>x.status==="trained");
      select.innerHTML='<option value="">Selecciona un experimento entrenado...</option>'+experiments.map(x=>'<option value="'+esc(x.experiment_id)+'">'+esc(x.config?.name||x.experiment_id)+' · '+esc(x.experiment_id.slice(0,8))+'</option>').join("");
      select.disabled=false;select.onchange=()=>{renderExperiment();loadDatasets();};
      renderExperiment();await loadDatasets();await loadHistory();
    }catch(e){select.innerHTML='<option value="">Error al consultar experimentos</option>';const box=$("export-model-summary");if(box)box.textContent=e.message||String(e);}
  }
  function updateStages(done){
    document.querySelectorAll(".export-pipeline-step").forEach((el,i)=>{el.classList.toggle("active",i===done);el.classList.toggle("complete",i<done);});
    const status=$("export-stage-message");if(status)status.textContent=done===4?"4 de 4 etapas completadas":"Etapa "+(done+1)+" de 4";
  }
  async function run(){
    const id=$("export-experiment")?.value;if(!id||busy)return;
    const name=$("export-name")?.value?.trim(),dir=$("export-directory")?.value?.trim()||"";
    if(!name){log("Error: indica un nombre de exportación.");return;}
    setBusy(true);$("export-log").value="Iniciando flujo completo de exportación…";
    const progress=$(".export-progress-head strong"),track=$(".export-progress-track i");
    if(progress)progress.textContent="En ejecución";if(track)track.style.width="5%";
    updateStages(0);
    const msg=$("export-progress-message");
    if(msg)msg.textContent="Ejecutando ONNX, cuantización INT8, evaluación del conjunto Test y empaquetado.";
    try{
      const r=await Bridge.exportModelPipeline(id,name,dir,$("export-equivalence")?.checked!==false);
      if(!r?.success)throw new Error(r?.error||"Falló el flujo de exportación.");
      const x=r.export||{},p=r.pipeline||{},st=p.stages||{},q=st.quantization||{},ev=st.evaluation||{},pkg=st.package||{};
      log("Etapa 1/4 — ONNX: completada.");
      log("Archivo: "+fmt(x.onnx_path));log("Tamaño: "+fmt(x.bytes)+" bytes");
      log("SHA-256: "+fmt(x.sha256));
      log("Equivalencia PyTorch/ONNX: "+(x.verified?(x.parity?.passed?"Correcta":"Fallida"):"No solicitada"));
      log("Etapa 2/4 — Cuantización INT8 estática PTQ: completada.");
      log("Modelo cuantizado: "+fmt(q.path));log("Tamaño INT8: "+fmt(q.bytes)+" bytes");
      log("Etapa 3/4 — Evaluación con Test: completada.");
      log("Muestras Test: "+fmt(ev.samples));
      log("Accuracy original: "+(Number.isFinite(ev.original_accuracy)?(ev.original_accuracy*100).toFixed(2)+"%":"—"));
      log("Accuracy INT8: "+(Number.isFinite(ev.int8_accuracy)?(ev.int8_accuracy*100).toFixed(2)+"%":"—"));
      log("Diferencia accuracy: "+(Number.isFinite(ev.accuracy_delta)?(ev.accuracy_delta*100).toFixed(2)+" pp":"—"));
      log("Etapa 4/4 — Paquete portable: completada.");
      log("Paquete: "+fmt(pkg.path));log("Tamaño paquete: "+fmt(pkg.bytes)+" bytes");
      log("El paquete no es firmware ni binario ejecutable ESP32-S3.");
      const values=[x.onnx_path,q.path,
        x.bytes&&q.bytes?Math.ceil(q.bytes/1024)+" KB (INT8)": "—",
        "Compatibilidad ESP32-S3 pendiente de conversión específica",
        "No estimada","No estimada",
        Number.isFinite(ev.original_accuracy)?(ev.original_accuracy*100).toFixed(2)+"%":"—",
        Number.isFinite(ev.int8_accuracy)?(ev.int8_accuracy*100).toFixed(2)+"%":"—"];
      document.querySelectorAll(".export-result-list dd").forEach((el,i)=>{if(values[i]!==undefined)el.textContent=values[i];});
      if(progress)progress.textContent="4 de 4 etapas completadas";
      if(track)track.style.width="100%";updateStages(4);
      if(msg)msg.textContent="Flujo completado. Se generó el paquete portable; no es firmware ejecutable.";
      await loadHistory();
    }catch(e){
      log("Error: "+(e?.message||String(e)));
      if(progress)progress.textContent="Proceso incompleto";
      if(msg)msg.textContent=e?.message||String(e);
    }finally{setBusy(false);}
  }
  document.addEventListener("click",e=>{
    const target=e.target.closest("button");if(!target)return;
    if(target.id==="btn-generate-export-package"||target.id==="btn-start-export"){run();return;}
    if(target.id==="btn-reset-export"){
      $("export-log").value="Esperando inicio…";document.querySelectorAll(".export-result-list dd").forEach(el=>el.textContent="—");
      const p=$(".export-progress-head strong");if(p)p.textContent="Sin iniciar";const t=$(".export-progress-track i");if(t)t.style.width="0%";
      const m=$("export-progress-message");if(m)m.textContent="La conversión ONNX se ejecuta después de validar la reconstrucción del modelo.";
      updateStages(0);return;
    }
    if(target.id==="btn-refresh-export-history"){loadHistory();return;}
    if(target.dataset.exportView!==undefined){
      const rows=$("export-history-body")._exportRows||[],item=rows[Number(target.dataset.exportView)];
      if(item){$("export-log").value="Exportación: "+item.name+"\nExperimento: "+(item.experiment_name||item.experiment_id||"—")+"\nArchivo: "+(item.onnx_path||"—")+"\nSHA-256: "+(item.sha256||"—")+"\nEstado: "+item.status;}
    }
  });
  window.initExportar=load;
})();