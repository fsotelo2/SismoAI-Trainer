/* Ajustes: preferencias globales y catálogo secundario */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  let categories = [], editingId = null, preferences = {theme:"light"};
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function applyTheme(theme){
    const resolved = theme === "system" ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark":"light") : theme;
    document.documentElement.dataset.theme = resolved;
  }
  function renderTheme(){
    document.querySelectorAll("[data-settings-theme]").forEach(b=>b.classList.toggle("selected",b.dataset.settingsTheme===preferences.theme));
    applyTheme(preferences.theme);
  }
  function renderCategories(){
    const body=$("settings-category-rows"); if(!body)return;
    body.innerHTML=categories.length?categories.map(c=>'<tr><td><strong>'+esc(c.name)+'</strong></td><td><span class="category-status '+(c.active?"":"inactive")+'">'+(c.active?"Activa":"Inactiva")+'</span></td><td><button type="button" class="settings-category-edit-button" id="settings-category-edit-'+esc(c.id)+'" data-settings-action="edit-category" data-id="'+esc(c.id)+'" title="Editar">✎</button><button type="button" class="settings-category-toggle-button" id="settings-category-toggle-'+esc(c.id)+'" data-settings-action="toggle-category" data-id="'+esc(c.id)+'" title="'+(c.active?"Desactivar":"Activar")+'">'+(c.active?"◉":"○")+'</button><button type="button" class="settings-category-delete-button" id="settings-category-delete-'+esc(c.id)+'" data-settings-action="delete-category" data-id="'+esc(c.id)+'" title="Eliminar">×</button></td></tr>').join(""):'<tr><td colspan="3">No hay subcategorías configuradas.</td></tr>';
  }
  function editor(show,id=null){
    editingId=id;
    $("settings-category-editor").hidden=!show;
    $("settings-category-error").textContent="";
    if(show){const c=categories.find(x=>x.id===id);$("settings-editor-title").textContent=c?"Editar subcategoría":"Nueva subcategoría";$("settings-category-name").value=c?.name||"";$("settings-category-name").focus();}
  }
  async function saveCategories(){
    const name=$("settings-category-name").value.trim().toUpperCase();
    if(!name){$("settings-category-error").textContent="El nombre es obligatorio.";return;}
    const next=categories.map(x=>({...x}));
    if(editingId){const c=next.find(x=>x.id===editingId);if(c){c.name=name;}}
    else{const id=name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9_-]+/g,"-").replace(/^-|-$/g,"");next.push({id:id||"categoria-"+Date.now(),name,active:true});}
    const result=await Bridge.saveLabelCategories(next);
    if(!result?.success){$("settings-category-error").textContent=result?.error||"No se pudo guardar el catálogo.";return;}
    categories=result.categories||next;renderCategories();editor(false);$("settings-message").textContent="Catálogo guardado.";
  }
  document.addEventListener("click",async e=>{
    const b=e.target.closest("[data-settings-theme]");
    if(b){preferences.theme=b.dataset.settingsTheme;renderTheme();const r=await Bridge.saveAppPreferences(preferences);$("settings-message").textContent=r?.success?"Preferencia guardada.":(r?.error||"No se pudo guardar la preferencia.");return;}
    const action=e.target.closest("[data-settings-action]");if(!action)return;
    const act=action.dataset.settingsAction,id=action.dataset.id;
    if(act==="add-category")editor(true);
    if(act==="cancel-category")editor(false);
    if(act==="edit-category")editor(true,id);
    if(act==="save-category")await saveCategories();
    if(act==="toggle-category"){const next=categories.map(c=>c.id===id?{...c,active:!c.active}:c);const r=await Bridge.saveLabelCategories(next);if(r?.success){categories=r.categories;renderCategories();$("settings-message").textContent="Estado actualizado.";}else $("settings-message").textContent=r?.error||"No se pudo actualizar.";}
    if(act==="delete-category"){const c=categories.find(x=>x.id===id);if(!c)return;if(!confirm("¿Eliminar la subcategoría "+c.name+"?"))return;const r=await Bridge.saveLabelCategories(categories.filter(x=>x.id!==id));if(r?.success){categories=r.categories;renderCategories();$("settings-message").textContent="Subcategoría eliminada.";}else $("settings-message").textContent=r?.error||"No se pudo eliminar.";}
  });
  window.initSettings=async()=>{
    $("settings-message").textContent="";
    const [p,c]=await Promise.all([Bridge.getAppSettings(),Bridge.getLabelCategories()]);
    if(p?.success)preferences=p.preferences||preferences;
    if(c?.success)categories=c.categories||[];
    renderTheme();renderCategories();
  };
  document.addEventListener("change",e=>{if(e.target?.id==="settings-category-name")e.target.value=e.target.value.toUpperCase();});
})();
