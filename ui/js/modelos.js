/* Modelos — lectura del manifiesto activo */
(() => {
 window.initModels=async()=>{
  const el=document.getElementById('model-dataset-state');if(!el)return;
  const r=await Bridge.getDatasetWorkspace();
  if(!r?.success){el.textContent=r?.error||'No se pudo consultar el dataset.';return;}
  const d=r.active_dataset;
  if(!d){el.textContent='No hay un dataset generado. Vuelve a Dataset para prepararlo.';return;}
  const s=d.summary||{};
  el.innerHTML='<b>Nombre:</b> '+String(d.name||'Dataset sin nombre')+'<br><b>ID:</b> '+String(d.dataset_id||'')+'<br><b>Ventanas:</b> '+(s.all?.windows??0)+'<br><b>Eventos independientes:</b> '+(s.all?.events??0)+'<br><b>Train / Validation / Test:</b> '+(s.train?.windows??0)+' / '+(s.validation?.windows??0)+' / '+(s.test?.windows??0);
 };
})();