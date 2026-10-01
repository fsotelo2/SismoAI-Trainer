/* Phase 7 — labeling view */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let items=[], filtered=[], index=0, selectedId=null, dirty=false, context=null, signalCache={}, activeFilter='all';
  const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sec = us => (Number(us||0)/1e6).toFixed(2)+' s';
  function labelOf(item){return item?.label||null;}
  function status(item){const l=labelOf(item);return !l||l.class_code==null?'pending':l.quality_review==='pending'?'review':'labeled';}
  function renderList(){
    const list=$('label-window-list');$('label-count').textContent=filtered.length;
    list.innerHTML=filtered.length?filtered.map((item,i)=>{
      const w=item.window,l=labelOf(item),st=status(item),txt=st==='pending'?'Pendiente':st==='review'?'Revisión':(l.class_code===0?'Sísmico':'No sísmico');
      const secondary=l?.class_code===1&&l?.disturbance?'<small class="label-row-secondary">'+esc(l.disturbance)+'</small>':'';
      const classTone=l?.class_code===1?'nonsismic':l?.class_code===0?'seismic':'';
      return '<button class="label-window-row '+(w.window_id===selectedId?'active':'')+'" data-label-select="'+esc(w.window_id)+'"><span class="label-row-heading"><b>'+esc(w.window_id)+'</b><span class="label-row-status '+st+' '+classTone+'">'+txt+'</span></span>'+secondary+'<small>'+sec(w.start_us)+' – '+sec(w.end_us)+'</small><small>'+esc(w.source_file||'')+'</small></button>';
    }).join(''):'<p class="label-empty">No hay ventanas en este filtro.</p>';
  }
  function renderEditor(){
    const item=filtered.find(x=>x.window.window_id===selectedId); if(!item)return;
    const l=labelOf(item)||{};
    document.querySelectorAll('[data-label-class]').forEach(b=>b.classList.toggle('chosen',String(l.class_code)===b.dataset.labelClass));
    $('label-category').disabled=l.class_code!==1;
    $('label-category').value=l.disturbance||'';
    document.querySelectorAll('[data-label-review]').forEach(b=>b.classList.toggle('selected',b.dataset.labelReview===(l.quality_review||'pending')));
    $('label-observations').value=l.observations||'';
    $('label-char-count').textContent=($('label-observations').value||'').length;
    $('label-position').textContent='Ventana '+(filtered.findIndex(x=>x.window.window_id===selectedId)+1)+' de '+filtered.length;
    const w=item.window;
    const eventRaw=w.source_event_id;const eventNum=eventRaw!==null&&eventRaw!==undefined&&String(eventRaw).trim()!==''&&Number.isFinite(Number(eventRaw))?String(Number(eventRaw)+1):'—';
    $('label-window-info').innerHTML='<b>Archivo</b> '+esc(w.source_file)+'　<b>Inicio</b> '+sec(w.start_us)+'　<b>Fin</b> '+sec(w.end_us)+'　<b>Duración</b> '+((w.end_us-w.start_us)/1e6).toFixed(2)+' s　<b>Sensores</b> '+esc((w.sensors||[]).join(' + '))+'　<b>Evento</b> '+esc(eventNum)+'　<b>Calidad</b> '+esc(w.quality?.status||'—');
    document.querySelectorAll('[data-label-action="prev"],[data-label-action="next"]').forEach(b=>b.disabled=filtered.length<2);
    drawSignals(item);
  }
  function renderCounts(counts){
    const c=counts||{total:items.length,pending:0,labeled:0,review:0};
    $('label-summary').textContent=c.total+' ventanas · '+c.pending+' pendientes · '+c.labeled+' etiquetadas · '+c.review+' en revisión';
    updateDatasetButton();
  }
  function updateDatasetButton(){
    const button=$('btn-continue-dataset');
    if(!button)return;
    const ready=items.length>0&&items.every(item=>{
      // Gate progression only on the last persisted label, never unsaved editor state.
      const l=item._savedLabel;
      return l&&(l.class_code===0||l.class_code===1)&&l.quality_review==='confirmed';
    });
    button.disabled=!ready;
    button.title=ready?'Todas las ventanas están etiquetadas y confirmadas':'Confirma todas las etiquetas para continuar a Dataset';
    button.setAttribute('aria-disabled',String(!ready));
  }
  function markDirty(){dirty=true;$('label-dirty').textContent='Cambios sin guardar';}
  function discardChanges(){if(!dirty)return;const active=items.find(x=>x.window.window_id===selectedId);if(active)active.label=active._savedLabel?JSON.parse(JSON.stringify(active._savedLabel)):null;dirty=false;$('label-dirty').textContent='Sin cambios';}
  function current(){return filtered.find(x=>x.window.window_id===selectedId);}
  function filter(){
    if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?')){$('label-filter').value=activeFilter;renderEditor();return;}
    discardChanges();
    const f=$('label-filter').value;activeFilter=f;
    filtered=items.filter(x=>f==='all'||status(x)===f);
    if(!filtered.some(x=>x.window.window_id===selectedId))selectedId=filtered[0]?.window.window_id||null;
    renderList(); if(selectedId)renderEditor(); else { $('label-position').textContent='Sin ventanas'; $('label-window-info').textContent='No hay ventanas para mostrar.'; $('label-signal-note').textContent=''; $('label-message').textContent=''; document.querySelectorAll('[data-label-class]').forEach(b=>b.classList.remove('chosen')); document.querySelectorAll('[data-label-review]').forEach(b=>b.classList.toggle('selected',b.dataset.labelReview==='pending')); $('label-category').value=''; $('label-category').disabled=true; $('label-observations').value=''; $('label-char-count').textContent='0'; draw('label-geo-chart',[],[],'#2563eb'); draw('label-mpu-chart',[],[],'#7c3aed'); }
  }
  function updateSelected(patch){
    const item=current();if(!item)return;
    item.label={...(item.label||{window_id:selectedId,class_code:null,quality_review:'confirmed',observations:''}),...patch,window_id:selectedId};
    markDirty();renderList();renderEditor();updateDatasetButton();
  }
  async function save(next=false){
    const item=current();if(!item)return;
    const l=item.label||{};
    if(l.class_code!==0&&l.class_code!==1){$('label-message').textContent='Selecciona una clase principal antes de guardar.';return;}
    const r=await Bridge.saveWindowLabel(selectedId,{class_code:l.class_code,disturbance:l.class_code===1?(l.disturbance||null):null,quality_review:l.quality_review||'pending',observations:l.observations||''},item.window.window_ref);
    if(!r?.success){$('label-message').textContent=r?.error||'No se pudo guardar.';return;}
    item.label=r.label;item._savedLabel=JSON.parse(JSON.stringify(r.label));dirty=false;updateDatasetButton();$('label-dirty').textContent='Sin cambios';$('label-message').textContent='Etiqueta guardada.';
    if(next){const i=filtered.findIndex(x=>x.window.window_id===selectedId);selectedId=filtered[(i+1)%filtered.length]?.window.window_id||selectedId;}
    await load();
  }
  window.saveLabelBatch=async function(){
    const name=$('label-batch-name')?.value?.trim();
    const feedback=$('label-batch-feedback');
    const showError=(message)=>{if(feedback)feedback.textContent=message;$('label-message').textContent=message;};
    if(!name){showError('Escribe un nombre para el lote de etiquetado.');$('label-batch-name')?.focus();return;}
    const filename=(name.toLowerCase().endsWith('.json')?name:name+'.json').toLocaleLowerCase();
    const existing=await Bridge.getLabelBatches();
    if(existing?.success&&(existing.items||[]).some(x=>String(x.filename||'').toLocaleLowerCase()===filename||String(x.name||'').trim().toLocaleLowerCase()===name.toLocaleLowerCase())){
      showError('Ya existe un etiquetado con ese nombre. Usa otro nombre.');
      $('label-batch-name')?.focus();$('label-batch-name')?.select();return;
    }
    if(!items.length||!items.every(x=>x._savedLabel&&(x._savedLabel.class_code===0||x._savedLabel.class_code===1)&&x._savedLabel.quality_review==='confirmed')){
      showError('Guarda y confirma todas las etiquetas antes de continuar.');return;
    }
    if(feedback)feedback.textContent='';
    const r=await Bridge.createLabelBatch(name);
    if(!r?.success){
      const message=r?.error||'No se pudo guardar el lote.';
      showError(message);
      if(message.toLowerCase().includes('ya existe')||message.toLowerCase().includes('mismo nombre')){
        $('label-batch-name')?.focus();$('label-batch-name')?.select();
      }
      return;
    }
    $('label-message').textContent='Lote guardado: '+r.batch.name+' · ID '+r.batch.id.slice(0,8);
    if(feedback)feedback.textContent='Etiquetado guardado correctamente: '+r.filename;
    await refreshLabelBatches();
  };
  async function refreshWindowSelections(){
    const body=$('label-window-selection-rows');if(!body)return;
    const r=await Bridge.getWindowSelections(),list=r?.items||[];
    if(!r?.success){body.innerHTML='<tr><td colspan="4">No se pudieron cargar las selecciones.</td></tr>';return;}
    const active=r.active_filename||window.__activeWindowSelectionFilename||'';
    body.innerHTML=list.length?list.map(x=>{
      const isActive=x.filename===active;
      return '<tr><td>'+esc(x.name)+(isActive?' <strong>(Activa)</strong>':'')+'</td><td><code>'+esc(x.id)+'</code></td><td>'+esc(x.count)+'</td><td><button class="btn btn-secondary btn-sm" data-label-action="delete-window-selection" data-filename="'+esc(x.filename)+'">Eliminar</button></td></tr>';
    }).join(''):'<tr><td colspan="4">No hay selecciones guardadas.</td></tr>';
  }
  async function refreshLabelBatches(){
    const body=$('label-batch-rows');if(!body)return;
    const r=await Bridge.getLabelBatches(),list=r?.items||[];
    if(!r?.success){body.innerHTML='<tr><td colspan="4">No se pudieron cargar los etiquetados.</td></tr>';return;}
    body.innerHTML=list.length?list.map(x=>'<tr><td>'+esc(x.name)+'</td><td><code>'+esc(x.id)+'</code></td><td>'+esc(x.count)+'</td><td><button class="btn btn-secondary btn-sm" data-label-action="delete-batch" data-filename="'+esc(x.filename)+'">Eliminar</button></td></tr>').join(''):'<tr><td colspan="4">No hay etiquetados guardados.</td></tr>';
  }
  async function load(){
    $('label-window-list').innerHTML='<p class="label-empty">Cargando ventanas…</p>';
    const selections=await Bridge.getWindowSelections();
    const select=$('label-window-selection');
    if(select){
      const list=selections?.items||[],active=selections?.active_filename||window.__activeWindowSelectionFilename||'';
      select.innerHTML='<option value="">Selección activa</option>'+list.map(s=>'<option value="'+esc(s.filename)+'" '+(s.filename===active?'selected':'')+'>'+esc(s.name)+' · '+esc(s.count)+' ventanas</option>').join('');
    }
    const r=await Bridge.getLabelingWorkspace();
    if(!r?.success){$('label-window-list').innerHTML='<p class="label-empty">'+esc(r?.error||'No se pudo cargar.')+'</p>';return;}
    items=r.items||[];updateDatasetButton();items.forEach(x=>{x._savedLabel=x.label?JSON.parse(JSON.stringify(x.label)):null;});renderCounts(r.counts);filter();await refreshWindowSelections();await refreshLabelBatches();
  }
  function draw(canvasId,ts,ys,color){
    const canvas=$(canvasId);if(!canvas)return;
    const width=canvas.clientWidth||500,height=150,dpr=window.devicePixelRatio||1;
    canvas.width=width*dpr;canvas.height=height*dpr;
    const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,width,height);
    const p={l:42,r:10,t:10,b:24},pw=width-p.l-p.r,ph=height-p.t-p.b;
    c.strokeStyle='#e2e8f0';c.fillStyle='#64748b';c.font='11px sans-serif';
    for(let i=0;i<=4;i++){let y=p.t+i*ph/4;c.beginPath();c.moveTo(p.l,y);c.lineTo(width-p.r,y);c.stroke();}
    const n=Math.min(ts?.length||0,ys?.length||0);
    if(!n){c.fillText('Señal no disponible en el contexto activo',p.l+8,height/2);return;}
    const t0=ts[0],t1=ts[n-1],min=Math.min(0,...ys.slice(0,n)),max=Math.max(0,...ys.slice(0,n)),span=max-min||1;
    c.strokeStyle=color;c.lineWidth=1;c.beginPath();const stride=Math.max(1,Math.floor(n/2200));
    for(let i=0;i<n;i+=stride){const x=p.l+(ts[i]-t0)/(t1-t0||1)*pw,y=p.t+(1-(ys[i]-min)/span)*ph;if(i===0)c.moveTo(x,y);else c.lineTo(x,y);}c.stroke();
  }
  async function drawSignals(item){
    const id=item.window.window_id;
    const ref=item.window.window_ref||id;
    let data=signalCache[ref];
    if(!data){
      $('label-signal-note').textContent='Cargando señal de la ventana…';
      data=await Bridge.getWindowSignal(id,ref);
      if(selectedId!==id)return;
      signalCache[ref]=data;
    }
    const signals=data?.signals||{};
    const geo=signals.GEO||{},mpu=signals.MPU||{};
    $('label-signal-note').textContent=data?.success?'Señales recortadas al intervalo de la ventana.':(data?.error||'Señal no disponible.');
    draw('label-geo-chart',$('label-show-geo').checked?(geo.times||[]):[],geo.amplitudes||[],'#2563eb');
    draw('label-mpu-chart',$('label-show-mpu').checked?(mpu.times||[]):[],mpu.amplitudes||[],'#7c3aed');
  }
  document.addEventListener('click',async e=>{
    const select=e.target.closest('[data-label-select]');if(select){if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?'))return;discardChanges();selectedId=select.dataset.labelSelect;renderList();renderEditor();return;}
    const cls=e.target.closest('[data-label-class]');if(cls){const code=Number(cls.dataset.labelClass);updateSelected({class_code:code,disturbance:code===1?(current()?.label?.disturbance||''):null});return;}
    const review=e.target.closest('[data-label-review]');if(review){updateSelected({quality_review:review.dataset.labelReview});return;}
    const act=e.target.closest('[data-label-action]')?.dataset.labelAction;if(!act)return;
    if(act==='save')await save(false);
    if(act==='save-batch'){await window.saveLabelBatch();}
    if(act==='save-next')await save(true);
    if(act==='refresh-batches')await refreshLabelBatches();
    if(act==='refresh-window-selections')await refreshWindowSelections();
    if(act==='delete-window-selection'){
      const filename=e.target.closest('[data-label-action]')?.dataset.filename;
      if(!filename||!confirm('¿Eliminar la selección guardada "'+filename+'"? Esta acción no se puede deshacer.'))return;
      const result=await Bridge.deleteWindowSelection(filename);
      if(!result?.success){$('label-message').textContent=result?.error||'No se pudo eliminar la selección.';return;}
      $('label-message').textContent='Selección eliminada: '+filename;
      await refreshWindowSelections();
      await load();
    }
    if(act==='delete-batch'){
      const filename=e.target.closest('[data-label-action]')?.dataset.filename;
      if(!filename||!confirm('¿Eliminar el etiquetado guardado "'+filename+'"? Esta acción no se puede deshacer.'))return;
      const result=await Bridge.deleteLabelBatch(filename);
      if(!result?.success){$('label-message').textContent=result?.error||'No se pudo eliminar el etiquetado.';return;}
      $('label-message').textContent='Etiquetado eliminado: '+filename;
      await refreshLabelBatches();
    }
    if(act==='prev'||act==='next'){if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?'))return;discardChanges();const i=filtered.findIndex(x=>x.window.window_id===selectedId),d=act==='next'?1:-1;selectedId=filtered[(i+d+filtered.length)%filtered.length]?.window.window_id||selectedId;dirty=false;renderList();renderEditor();}
  });
  let boundRoot=null;
  function bindViewControls(){
    const root=$('label-filter')?.closest('.labeling-view')||document;
    if(boundRoot===root)return;
    boundRoot=root;
    $('label-filter')?.addEventListener('change',filter);
    $('label-window-selection')?.addEventListener('change',async e=>{
      if(!e.target.value)return;
      if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?')){e.target.value=window.__activeWindowSelectionFilename||'';return;}
      discardChanges();
      const result=await Bridge.selectWindowSelection(e.target.value);
      if(result?.success){window.__activeWindowSelectionFilename=e.target.value;await load();}
      else $('label-message').textContent=result?.error||'No se pudo cargar la selección.';
    });
    $('label-category')?.addEventListener('change',e=>updateSelected({disturbance:e.target.value||null}));
    $('label-observations')?.addEventListener('input',e=>{const item=current();if(!item)return;item.label={...(item.label||{window_id:selectedId,class_code:null,quality_review:'confirmed'}),observations:e.target.value.slice(0,200)};markDirty();$('label-char-count').textContent=e.target.value.length;});
    $('label-show-geo')?.addEventListener('change',()=>current()&&drawSignals(current()));
    $('label-show-mpu')?.addEventListener('change',()=>current()&&drawSignals(current()));
  }
  window.initLabeling=async()=>{try{bindViewControls();context=null;await load();}catch(err){console.error('[Etiquetado] Error de inicialización:',err);const list=$('label-window-list');if(list)list.innerHTML='<p class="label-empty">Error al cargar ventanas: '+esc(err?.message||err)+'</p>';const summary=$('label-summary');if(summary)summary.textContent='No se pudo cargar el espacio de etiquetado.';}};
  window.addEventListener('resize',()=>current()&&drawSignals(current()));
})();