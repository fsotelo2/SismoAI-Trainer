/* Phase 7 — labeling view */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let items=[], filtered=[], index=0, selectedId=null, dirty=false, context=null;
  const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sec = us => (Number(us||0)/1e6).toFixed(2)+' s';
  function labelOf(item){return item?.label||null;}
  function status(item){const l=labelOf(item);return !l||l.class_code==null?'pending':l.quality_review==='pending'?'review':'labeled';}
  function renderList(){
    const list=$('label-window-list');$('label-count').textContent=filtered.length;
    list.innerHTML=filtered.length?filtered.map((item,i)=>{
      const w=item.window,l=labelOf(item),st=status(item),txt=st==='pending'?'Pendiente':st==='review'?'Revisión':(l.class_code===0?'Sísmico':'No sísmico');
      return '<button class="label-window-row '+(w.window_id===selectedId?'active':'')+'" data-label-select="'+esc(w.window_id)+'"><b>'+esc(w.window_id)+'</b><span class="label-row-status '+st+'">'+txt+'</span><small>'+sec(w.start_us)+' – '+sec(w.end_us)+'</small><small>'+esc(w.source_file||'')+'</small></button>';
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
    $('label-window-info').innerHTML='<b>Archivo</b> '+esc(w.source_file)+'　<b>Inicio</b> '+sec(w.start_us)+'　<b>Fin</b> '+sec(w.end_us)+'　<b>Duración</b> '+((w.end_us-w.start_us)/1e6).toFixed(2)+' s　<b>Sensores</b> '+esc((w.sensors||[]).join(' + '))+'　<b>Evento</b> '+esc(w.source_event_id??'—')+'　<b>Calidad</b> '+esc(w.quality?.status||'—');
    document.querySelectorAll('[data-label-action="prev"],[data-label-action="next"]').forEach(b=>b.disabled=filtered.length<2);
    drawSignals(item);
  }
  function renderCounts(counts){
    const c=counts||{total:items.length,pending:0,labeled:0,review:0};
    $('label-summary').textContent=c.total+' ventanas · '+c.pending+' pendientes · '+c.labeled+' etiquetadas · '+c.review+' en revisión';
  }
  function markDirty(){dirty=true;$('label-dirty').textContent='Cambios sin guardar';}
  function current(){return filtered.find(x=>x.window.window_id===selectedId);}
  function filter(){
    const f=$('label-filter').value;
    filtered=items.filter(x=>f==='all'||status(x)===f);
    if(!filtered.some(x=>x.window.window_id===selectedId))selectedId=filtered[0]?.window.window_id||null;
    renderList(); if(selectedId)renderEditor(); else {$('label-position').textContent='Sin ventanas';$('label-window-info').textContent='No hay ventanas para mostrar.';}
  }
  function updateSelected(patch){
    const item=current();if(!item)return;
    item.label={...(item.label||{window_id:selectedId,class_code:null,quality_review:'pending',observations:''}),...patch,window_id:selectedId};
    markDirty();renderList();renderEditor();
  }
  async function save(next=false){
    const item=current();if(!item)return;
    const l=item.label||{};
    if(l.class_code!==0&&l.class_code!==1){$('label-message').textContent='Selecciona una clase principal antes de guardar.';return;}
    const r=await Bridge.saveWindowLabel(selectedId,{class_code:l.class_code,disturbance:l.class_code===1?(l.disturbance||null):null,quality_review:l.quality_review||'pending',observations:l.observations||''});
    if(!r?.success){$('label-message').textContent=r?.error||'No se pudo guardar.';return;}
    item.label=r.label;dirty=false;$('label-dirty').textContent='Sin cambios';$('label-message').textContent='Etiqueta guardada.';
    if(next){const i=filtered.findIndex(x=>x.window.window_id===selectedId);selectedId=filtered[(i+1)%filtered.length]?.window.window_id||selectedId;}
    await load();
  }
  async function load(){
    const r=await Bridge.getLabelingWorkspace();
    if(!r?.success){$('label-window-list').innerHTML='<p class="label-empty">'+esc(r?.error||'No se pudo cargar.')+'</p>';return;}
    items=r.items||[];renderCounts(r.counts);filter();
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
  function drawSignals(item){
    const w=item.window, matches=context?.ready&&context.file_name===w.source_file&&String(context.event_index)===String(w.source_event_id);
    $('label-signal-note').textContent=matches?'Se muestra el contexto del evento seleccionado; la señal de ventanas de otros eventos se habilitará con el extractor por ventana.':'Para visualizar la señal, selecciona en Análisis el mismo archivo y evento de esta ventana.';
    const geo=matches?context.geophone_times.map((t,i)=>({t,y:context.geophone_values[i]})).filter(p=>p.t*1e6>=w.start_us&&p.t*1e6<w.end_us):[];
    const mpu=matches?context.mpu_times.map((t,i)=>({t,y:context.mpu_values[i]})).filter(p=>p.t*1e6>=w.start_us&&p.t*1e6<w.end_us):[];
    draw('label-geo-chart',$('label-show-geo').checked?geo.map(p=>p.t):[],geo.map(p=>p.y),'#2563eb');
    draw('label-mpu-chart',$('label-show-mpu').checked?mpu.map(p=>p.t):[],mpu.map(p=>p.y),'#7c3aed');
  }
  document.addEventListener('click',async e=>{
    const select=e.target.closest('[data-label-select]');if(select){if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?'))return;selectedId=select.dataset.labelSelect;dirty=false;renderList();renderEditor();return;}
    const cls=e.target.closest('[data-label-class]');if(cls){const code=Number(cls.dataset.labelClass);updateSelected({class_code:code,disturbance:code===1?(current()?.label?.disturbance||''):null});return;}
    const review=e.target.closest('[data-label-review]');if(review){updateSelected({quality_review:review.dataset.labelReview});return;}
    const act=e.target.closest('[data-label-action]')?.dataset.labelAction;if(!act)return;
    if(act==='save')await save(false);
    if(act==='save-next')await save(true);
    if(act==='prev'||act==='next'){if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?'))return;const i=filtered.findIndex(x=>x.window.window_id===selectedId),d=act==='next'?1:-1;selectedId=filtered[(i+d+filtered.length)%filtered.length]?.window.window_id||selectedId;dirty=false;renderList();renderEditor();}
  });
  $('label-filter').addEventListener('change',filter);
  $('label-observations').addEventListener('input',e=>updateSelected({observations:e.target.value.slice(0,200)}));
  $('label-show-geo').addEventListener('change',()=>current()&&drawSignals(current()));
  $('label-show-mpu').addEventListener('change',()=>current()&&drawSignals(current()));
  window.initLabeling=async()=>{context=await Bridge.getWindowContext();await load();};
  window.addEventListener('resize',()=>current()&&drawSignals(current()));
})();