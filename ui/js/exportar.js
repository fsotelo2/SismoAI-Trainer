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
      '</td><td>ONNX</td><td>Sin cuantización</td><td>'+esc(x.bytes?Math.ceil(x.bytes/1024)+" KB":"—")+
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
    const status=$("export-stage-message");if(status)status.textContent=done===4?"Conversión ONNX completada.":"Etapa "+(done+1)+" de 4";
  }
  async function run(){
    const id=$("export-experiment")?.value;if(!id||busy)return;
    const name=$("export-name")?.value?.trim(),dir=$("export-directory")?.value?.trim()||"";
    if(!name){log("Error: indica un nombre de exportación.");return;}
    if($("export-quantization")?.value!=="none"){log("La cuantización seleccionada aún no está integrada.");return;}
    setBusy(true);$("export-log").value="Iniciando validación y conversión ONNX…";
    const progress=$(".export-progress-head strong"),track=$(".export-progress-track i");
    if(progress)progress.textContent="En ejecución";if(track)track.style.width="10%";updateStages(0);
    try{
      const r=await Bridge.exportModelOnnx(id,name,dir,$("export-equivalence")?.checked!==false);
      if(!r?.success)throw new Error(r?.error||"Falló la exportación.");
      const x=r.export||{},exp=selectedExperiment();
      log("Validación estructural completada.");log("Exportación ONNX completada.");
      log("Archivo: "+fmt(x.onnx_path));log("Tamaño: "+fmt(x.bytes)+" bytes");log("SHA-256: "+fmt(x.sha256));
      log("Equivalencia PyTorch/ONNX: "+(x.verified?(x.parity?.passed?"Correcta":"Fallida"):"No solicitada"));
      log(x.note||"");
      const values=[x.onnx_path,"No aplicado",x.bytes?Math.ceil(x.bytes/1024)+" KB":"—","No evaluados","No estimada","No estimada",fmt(exp?.training_result?.metrics?.validation?.accuracy!==undefined?(exp.training_result.metrics.validation.accuracy*100).toFixed(1)+"%":"No disponible"),"No aplica"];
      document.querySelectorAll(".export-result-list dd").forEach((el,i)=>{if(values[i]!==undefined)el.textContent=values[i];});
      if(progress)progress.textContent="ONNX completado · siguientes etapas pendientes";
      if(track)track.style.width="25%";updateStages(1);
      const msg=$("export-progress-message");if(msg)msg.textContent="ONNX generado. Cuantización, evaluación y empaquetado ESP32-S3 no ejecutados.";
      await loadHistory();
    }catch(e){log("Error: "+(e?.message||String(e)));if(progress)progress.textContent="Error";const msg=$("export-progress-message");if(msg)msg.textContent=e?.message||String(e);}
    finally{setBusy(false);}
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