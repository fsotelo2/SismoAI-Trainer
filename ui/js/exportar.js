(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let experiments = [];
  function log(message) {
    const el=$("export-log"); if(el) el.value += "\n"+message;
  }
  function setBusy(busy) {
    const btn=$("btn-generate-export-package");
    if(btn) btn.disabled=busy || !$("export-experiment")?.value;
    const start=document.querySelector(".export-toolbar .btn-primary");
    if(start) start.disabled=busy || !$("export-experiment")?.value;
  }
  async function load() {
    const select=$("export-experiment");
    if(!select) return;
    select.innerHTML='<option value="">Consultando experimentos...</option>';
    const r=await Bridge.getModelExperiments();
    if(!r?.success) { select.innerHTML='<option value="">No se pudieron consultar</option>'; return; }
    experiments=(r.experiments||[]).filter(x=>x.status==="trained");
    select.innerHTML='<option value="">Selecciona un experimento entrenado...</option>'+experiments.map(x=>'<option value="'+esc(x.experiment_id)+'">'+esc(x.config?.name||x.experiment_id)+' · '+esc(x.experiment_id)+'</option>').join("");
    select.disabled=false;
    select.onchange=()=>{
      const item=experiments.find(x=>x.experiment_id===select.value);
      $("export-model-summary").textContent=item ? "Experimento: "+(item.config?.name||item.experiment_id)+" · Arquitectura: "+(item.config?.architecture||"—")+" · Estado: entrenado. Se comprobará su reconstrucción antes de exportar." : "Selecciona un experimento para consultar arquitectura, dataset, dimensiones y estado.";
      setBusy(false);
    };
    setBusy(false);
  }
  async function run() {
    const id=$("export-experiment")?.value;
    if(!id) return;
    const name=$("export-name")?.value?.trim();
    const dir=$("export-directory")?.value?.trim()||"";
    if(!name) { log("Error: indica un nombre de exportación."); return; }
    setBusy(true);
    $("export-log").value="Iniciando exportación ONNX…";
    const buttons=document.querySelectorAll(".export-toolbar button");
    buttons.forEach(b=>b.disabled=true);
    try {
      const r=await Bridge.exportModelOnnx(id,name,dir,$("export-equivalence")?.checked!==false);
      if(!r?.success) throw new Error(r?.error||"Falló la exportación.");
      const x=r.export||{};
      log("Exportación completada.");
      log("Archivo: "+x.onnx_path);
      log("Tamaño: "+x.bytes+" bytes");
      log("SHA-256: "+x.sha256);
      log("Equivalencia: "+(x.parity?.passed===true?"correcta":"no solicitada"));
      log(x.note||"");
      const rows=document.querySelectorAll(".export-result-list dd");
      const values=[x.onnx_path,"No aplicado",x.bytes+" bytes","No evaluado","No estimada","No estimada","No evaluada",x.parity?.max_absolute_error ?? "—"];
      rows.forEach((el,i)=>{if(values[i]!==undefined)el.textContent=values[i];});
      const status=document.querySelector(".export-progress-head strong");
      if(status)status.textContent="Completado";
      const track=document.querySelector(".export-progress-track i");
      if(track)track.style.width="100%";
    } catch(e) { log("Error: "+(e?.message||String(e))); }
    finally { buttons.forEach(b=>b.disabled=false); setBusy(false); }
  }
  document.addEventListener("click",e=>{
    if(e.target.closest("#btn-generate-export-package") || e.target.closest(".export-toolbar .btn-primary")) run();
    if(e.target.closest(".export-toolbar .btn-secondary")) { if($("export-log"))$("export-log").value="Esperando exportación."; load(); }
  });
  window.initExportar=load;
})();