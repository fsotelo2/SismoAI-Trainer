/* Phase 8 — logical dataset preparation */
(() => {
 'use strict';
 const $=id=>document.getElementById(id); let items=[],counts={};
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 async function refresh(){
  const r=await Bridge.getDatasetWorkspace();
  if(!r?.success){$('ds-summary').textContent=r?.error||'No se pudo cargar';return;}
  items=r.items||[];counts=r.counts||{};
  $('ds-summary').textContent=`${counts.total||0} ventanas incluidas · ${counts.labeled||0} confirmadas · ${counts.pending||0} pendientes · ${counts.events||0} eventos`;
  $('ds-rows').innerHTML=items.length?items.map(x=>{const w=x.window,l=x.label||{},cl=l.class_code===0?'TEMBLOR':l.class_code===1?'NO_SISMICO':'Pendiente';return '<tr><td>'+esc(w.window_id)+'</td><td>'+esc(w.source_file)+'</td><td>'+esc(w.source_event_id??'—')+'</td><td>'+cl+'</td><td>'+esc(l.quality_review||'sin etiqueta')+'</td></tr>'}).join(''):'<tr><td colspan="5">No hay ventanas incluidas.</td></tr>';
  const msgs=[];if(counts.pending)msgs.push('Hay ventanas sin etiqueta confirmada; la generación está bloqueada.');
  if(counts.events<10)msgs.push('Pocos eventos independientes: las métricas pueden ser inestables.');
  if(!counts.total)msgs.push('No hay ventanas para formar el dataset.');
  $('ds-status').textContent=msgs.join(' ')||'Integridad básica: ventanas disponibles y listas para validar.';
  $('ds-generate').disabled=!!counts.pending||!counts.total;
 }
 async function action(e){const b=e.target.closest('[data-ds-action]');if(!b)return;
  if(b.dataset.dsAction==='refresh')await refresh();
  if(b.dataset.dsAction==='generate'){
   const vals=['ds-train','ds-val','ds-test'].map(id=>Number($(id).value)/100);
   if(vals.some(x=>!Number.isFinite(x)||x<0)||Math.abs(vals.reduce((a,b)=>a+b,0)-1)>1e-6){$('ds-validation').textContent='Error: los porcentajes deben sumar 100%.';return;}
   const seed=Number($('ds-seed').value)||42;b.disabled=true;
   const r=await Bridge.generateDataset(vals,seed);
   if(!r?.success){$('ds-validation').textContent=r?.error||'No se pudo generar.';b.disabled=false;return;}
   await App.navigateTo('modelos');
  }
 }
 document.addEventListener('click',action);
 window.initDataset=refresh;
})();