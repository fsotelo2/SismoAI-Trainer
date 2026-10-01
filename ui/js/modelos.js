/* Fase 9 — interfaz de configuración y registro de experimentos. */
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 let initial=null;
 const architectureNames={1d_cnn:'1D-CNN',feature_classifier:'Clasificador de características',baseline:'Baseline'};
 function currentConfig(){
  return {name:$('models-name').value.trim(),architecture:$('models-architecture').value,framework:$('models-framework').value,target:$('models-target-select').value,input:$('models-input').value,description:$('models-description').value.trim(),training:{epochs:Number($('models-epochs').value),batch_size:Number($('models-batch').value),learning_rate:Number($('models-lr').value),seed:Number($('models-seed').value),optimizer:$('models-optimizer').value,loss:$('models-loss').value,early_stopping:$('models-early-stop').checked,save_best:$('models-best').checked,class_weighting:$('models-weighted').checked}};
 }
 function validate(c){
  if(!c.name)return 'Indica un nombre para el experimento.';
  if(!Number.isInteger(c.training.epochs)||c.training.epochs<1||c.training.epochs>10000)return 'Épocas debe ser un entero entre 1 y 10000.';
  if(!Number.isInteger(c.training.batch_size)||c.training.batch_size<1||c.training.batch_size>4096)return 'Batch size debe ser un entero entre 1 y 4096.';
  if(!Number.isFinite(c.training.learning_rate)||c.training.learning_rate<=0||c.training.learning_rate>1)return 'Learning rate debe ser mayor que 0 y máximo 1.';
  if(!Number.isInteger(c.training.seed)||c.training.seed<0)return 'La semilla debe ser un entero no negativo.';
  return '';
 }
 function renderDataset(r){
  const d=r?.active_dataset, sel=$('models-dataset'), badge=$('models-dataset-badge');
  if(!r?.success){badge.textContent='Error';$('models-dataset-summary').textContent=r?.error||'No se pudo consultar Dataset.';return;}
  if(!d){badge.textContent='No disponible';badge.className='badge badge-warning';$('models-dataset-summary').textContent='No hay un dataset generado. Genera y verifica un dataset en el menú Dataset antes de configurar el entrenamiento.';$('models-partition').innerHTML='<span>Sin dataset activo</span>';return;}
  sel.disabled=true;sel.innerHTML='<option>'+esc(d.name||'Dataset activo')+'</option>';
  badge.textContent='Seleccionado';badge.className='badge badge-success';
  const s=d.summary||{},all=s.all||{},tr=s.train||{},va=s.validation||{},te=s.test||{};
  $('models-dataset-summary').innerHTML='<b>Nombre:</b> '+esc(d.name||'Dataset sin nombre')+'<br><b>ID:</b> '+esc(d.dataset_id||'—')+'<br><b>Ventanas:</b> '+(all.windows??'—')+'<br><b>Eventos independientes:</b> '+(all.events??'—')+'<br><b>Train / Validation / Test:</b> '+(tr.windows??'—')+' / '+(va.windows??'—')+' / '+(te.windows??'—');
  const total=Number(all.windows||0),parts=[['train',Number(tr.windows||0),'Train'],['validation',Number(va.windows||0),'Validation'],['test',Number(te.windows||0),'Test']];
  $('models-partition').innerHTML=total?parts.map(p=>'<i class="'+p[0]+'" style="width:'+Math.max(0,p[1]/total*100)+'%"></i>').join(''):'<span>Particiones vacías o no informadas</span>';
  $('models-partition-legend').innerHTML=parts.map(p=>'<span><i class="'+p[0]+'" style="background:'+(p[0]==='train'?'#1677e8':p[0]==='validation'?'#19b99a':'#f59e0b')+'"></i>'+p[2]+': '+p[1]+(total?' ('+(p[1]/total*100).toFixed(1)+'%)':'')+'</span>').join('');
  const classes=d.classes||d.labels||[];
  const rows=Array.isArray(classes)&&classes.length?classes.map((cl,i)=>'<tr><td>'+esc(cl.code??i)+'</td><td>'+esc(cl.name||cl.label||cl)+'</td><td>'+esc(cl.description||'—')+'</td></tr>').join(''):'<tr><td>0</td><td>TEMBLOR</td><td>Evento sísmico</td></tr><tr><td>1</td><td>NO_SISMICO</td><td>Ruido, vibración u otro</td></tr>';
  $('models-labels').innerHTML=rows;
  initial={dataset_id:d.dataset_id||'',dataset_name:d.name||''};
 }
 async function refresh(){
  $('models-library-body').innerHTML='<tr><td colspan="6">Cargando…</td></tr>';
  try{const r=await Bridge.getModelExperiments();const list=r?.experiments||[];$('models-library-body').innerHTML=list.length?list.map(x=>'<tr><td>'+esc(x.config?.name||'Sin nombre')+'</td><td>'+esc(architectureNames[x.config?.architecture]||x.config?.architecture||'—')+'</td><td>'+esc(x.dataset_name||'—')+'</td><td>'+esc(x.created_at||'—')+'</td><td><span class="badge badge-secondary">Configuración</span></td><td>—</td></tr>').join(''):'<tr><td colspan="6" class="text-muted">No hay configuraciones guardadas.</td></tr>';}
  catch(e){$('models-library-body').innerHTML='<tr><td colspan="6">Error: '+esc(e.message)+'</td></tr>';}
 }
 async function save(){
  const c=currentConfig(),error=validate(c);$('models-form-message').textContent=error;
  if(error)return;
  if(!initial?.dataset_id){$('models-form-message').textContent='No se puede guardar: primero genera un dataset activo.';return;}
  $('models-save-status').textContent='Guardando…';
  const r=await Bridge.saveModelExperiment(c,initial.dataset_id,initial.dataset_name);
  if(!r?.success){$('models-save-status').textContent='No se pudo guardar';$('models-form-message').textContent=r?.error||'Error al guardar.';return;}
  $('models-save-status').textContent='Configuración guardada · '+(r.experiment_id||'');$('models-form-message').textContent='';await refresh();
 }
 function reset(){if(!confirm('¿Restablecer los parámetros del formulario?'))return;$('models-name').value='cnn_sismos_001';$('models-architecture').value='1d_cnn';$('models-framework').value='pytorch';$('models-target-select').value='esp32s3';$('models-input').value='geo_mpu';$('models-description').value='';$('models-epochs').value=50;$('models-batch').value=32;$('models-lr').value='0.001';$('models-seed').value=42;$('models-optimizer').value='adam';$('models-loss').value='cross_entropy';$('models-early-stop').checked=true;$('models-best').checked=true;$('models-weighted').checked=false;$('models-form-message').textContent='';$('models-save-status').textContent='Parámetros restablecidos';}
 document.addEventListener('click',e=>{const b=e.target.closest('[data-model-action]');if(!b)return;const a=b.dataset.modelAction;if(a==='save')save();if(a==='reset')reset();if(a==='refresh')refresh();});
 window.initModels=async()=>{initial=null;$('models-dataset-summary').textContent='Consultando manifiesto activo…';try{const r=await Bridge.getDatasetWorkspace();renderDataset(r);}catch(e){$('models-dataset-summary').textContent='Error al consultar Dataset: '+e.message;}await refresh();};
})();