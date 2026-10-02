/* Phase 8 — Dataset preparation UI */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const setText = (id, value) => {
    const el = $(id);
    if (el) el.textContent = value;
  };
  let items = [],
    filtered = [],
    examplesExpanded = false,
    hasSavedDatasets = false,
    savedDatasetNames = new Set();
  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const w = (x) => x.window || {},
    l = (x) => x.label || {};
  const eventKey = (x) =>
    String(w(x).source_file || "") + "::" + String(w(x).source_event_id ?? "");
  const percent = (n, total) =>
    total ? ((100 * n) / total).toFixed(1).replace(/\.0$/, "") + "%" : "0%";
  const classText = (x) =>
    l(x).class_code === 0
      ? "TEMBLOR"
      : l(x).class_code === 1
        ? "NO_SISMICO"
        : "Pendiente";
  function renderSavedDatasets(list, error) {
    const body = $("ds-saved-rows");
    if (!body) return;
    if (error) {
      body.innerHTML =
        '<tr><td colspan="4">' + esc(error) + "</td></tr>";
      return;
    }
    body.innerHTML = list.length
      ? list
          .map(
            (x) =>
              "<tr><td>" +
              esc(x.name) +
              "</td><td><code>" +
              esc(x.dataset_id) +
              "</code></td><td>" +
              esc(x.windows) +
              '</td><td><button class="btn btn-danger btn-sm" data-ds-action="delete-saved" data-filename="' +
              esc(x.filename) +
              '">Eliminar</button></td></tr>',
          )
          .join("")
      : '<tr><td colspan="4">No hay datasets guardados.</td></tr>';
  }
  async function refreshSavedDatasets() {
    const result = await Bridge.getDatasetCatalog();
    if (!result?.success) {
      hasSavedDatasets = false;
      savedDatasetNames = new Set();
      renderSavedDatasets([], result?.error || "No se pudieron cargar los datasets.");
      updateGenerateButton();
      updateContinueButton();
      return;
    }
    const datasets = result.datasets || [];
    hasSavedDatasets = datasets.length > 0;
    savedDatasetNames = new Set(
      datasets.map((x) =>
        String(x.name || x.filename || "")
          .trim()
          .replace(/\.json$/i, "")
          .toLocaleLowerCase(),
      ),
    );
    renderSavedDatasets(datasets);
    updateGenerateButton();
    updateContinueButton();
  }
  function updateGenerateButton() {
    const button = document.querySelector('[data-ds-action="generate"]');
    const name =
      $("ds-name")?.value?.trim().replace(/\.json$/i, "").toLocaleLowerCase() || "";
    if (!button) return;
    button.disabled = !name || savedDatasetNames.has(name);
    button.title = savedDatasetNames.has(name)
      ? "Ya existe un dataset con ese nombre"
      : "Guardar dataset";
  }
  function updateContinueButton() {
    const button = $("btn-continue-models");
    if (!button) return;
    button.disabled = !hasSavedDatasets;
    button.title = hasSavedDatasets
      ? "Hay datasets guardados disponibles"
      : "Guarda un dataset antes de continuar a Modelos";
  }
  function filterRows() {
    const f = $("ds-filter")?.value || "all";
    filtered = items.filter(
      (x) =>
        f === "all" ||
        (f === "confirmed"
          ? l(x).quality_review === "confirmed" &&
            [0, 1].includes(l(x).class_code)
          : f === "pending"
            ? l(x).quality_review !== "confirmed" ||
              ![0, 1].includes(l(x).class_code)
            : f === "tremor"
              ? l(x).class_code === 0
              : l(x).class_code === 1),
    );
    renderRows();
  }
  function renderRows() {
    const examples = filtered
      .slice(0, examplesExpanded ? filtered.length : 5)
      .map((x) => {
        const win = w(x),
          lab = l(x),
          tone =
            lab.class_code === 0
              ? "tremor"
              : lab.class_code === 1
                ? "nonseismic"
                : "pending";
        const duration = (Number(win.end_us) - Number(win.start_us)) / 1000000;
        const eventNumber = Number(win.source_event_id);
        const eventLabel = Number.isInteger(eventNumber)
          ? String(eventNumber + 1)
          : win.source_event_id ?? "—";
        return (
          "<tr><td>" +
          esc(win.window_id || "—") +
          '</td><td><span class="ds-tag ' +
          tone +
          '">' +
          classText(x) +
          "</span></td><td>" +
          esc(eventLabel) +
          " / " +
          esc(win.source_file || "—") +
          "</td><td>" +
          (Number.isFinite(duration) ? duration.toFixed(1) + " s" : "—") +
          "</td><td>" +
          ((win.sensors || []).length || "—") +
          "</td></tr>"
        );
      })
      .join("");
    $("ds-examples").innerHTML =
      examples || '<tr><td colspan="5">No hay ventanas para mostrar.</td></tr>';
  }
  function validSplit() {
    const vals = ["ds-train", "ds-val", "ds-test"].map((id) =>
      Number($(id).value),
    );
    return (
      vals.every((v) => Number.isFinite(v) && v >= 0 && v <= 100) &&
      vals.reduce((a, b) => a + b, 0) === 100
    );
  }
  function updateSplit() {
    const vals = ["ds-train", "ds-val", "ds-test"].map((id) =>
      Math.max(0, Math.min(100, Number($(id)?.value) || 0)),
    );
    const keys = ["train", "val", "test"],
      total = items.length,
      sum = vals.reduce((a, b) => a + b, 0);
    const rawCounts = vals.map((value) => (total * value) / 100);
    const counts = rawCounts.map(Math.floor);
    let remainder = total - counts.reduce((a, b) => a + b, 0);
    rawCounts
      .map((value, index) => ({
        index,
        remainder: value - counts[index],
      }))
      .sort((a, b) => b.remainder - a.remainder)
      .forEach(({ index }) => {
        if (remainder > 0) {
          counts[index] += 1;
          remainder -= 1;
        }
      });
    vals.forEach((v, i) => {
      const range = $("ds-" + keys[i] + "-range");
      if (range) range.value = v;
      const n = counts[i];
      setText(
        "ds-" + keys[i] + "-count",
        n.toLocaleString("es-ES") + " ventanas aprox.",
      );
      const bar = $("ds-bar-" + keys[i]);
      if (bar) bar.style.width = (sum ? (v / sum) * 100 : 0) + "%";
      setText("ds-bar-" + keys[i], v + "%");
      setText("ds-leg-" + keys[i], n.toLocaleString("es-ES"));
    });
    const ok = validSplit();
    setText(
      "ds-validation",
      ok
        ? "Distribución configurada: " + vals.join(" / ") + "%."
        : "Los porcentajes deben sumar exactamente 100%. Total actual: " +
            sum +
            "%.",
    );
    if ($("ds-validation")) $("ds-validation").classList.toggle("error", !ok);
    return ok;
  }
  function check(title, desc, state, tag) {
    const cls = state === "ok" ? "ok" : state === "warn" ? "warn" : "";
    const symbol = state === "ok" ? "✓" : state === "warn" ? "⚠" : "•";
    return (
      '<article class="ds-check ' +
      cls +
      '"><span class="ds-check-icon">' +
      symbol +
      "</span><div><b>" +
      title +
      "</b><p>" +
      desc +
      '</p></div><span class="ds-pill">' +
      tag +
      "</span></article>"
    );
  }
  function renderStatus() {
    const total = items.length;
    const pending = items.filter(
      (x) =>
        l(x).quality_review !== "confirmed" ||
        ![0, 1].includes(l(x).class_code),
    ).length;
    const events = new Set(items.map(eventKey).filter((k) => !k.endsWith("::")))
      .size;
    const confirmed = items.filter(
      (x) =>
        l(x).quality_review === "confirmed" && [0, 1].includes(l(x).class_code),
    );
    const a = confirmed.filter((x) => l(x).class_code === 0).length,
      b = confirmed.filter((x) => l(x).class_code === 1).length;
    const imbalance =
      !a || !b || Math.max(a, b) > Math.max(1, Math.min(a, b)) * 4;
    const splitOk = updateSplit();
    $("ds-status").innerHTML = [
      check(
        "Etiquetas",
        pending
          ? pending + " ventanas sin confirmar"
          : "Todas las ventanas tienen etiqueta confirmada",
        pending ? "warn" : "ok",
        pending ? "Incompleto" : "Completo",
      ),
      check(
        "División de datos",
        "Configuración " +
          ["ds-train", "ds-val", "ds-test"]
            .map((id) => $(id).value + "%")
            .join(" / "),
        splitOk ? "ok" : "warn",
        splitOk ? "Lista" : "Revisar",
      ),
      check(
        "Balance de clases",
        imbalance
          ? "Distribución desbalanceada"
          : "Ambas clases tienen representación",
        imbalance ? "warn" : "ok",
        imbalance ? "Advertencia" : "Revisado",
      ),
      check(
        "Eventos para evaluación",
        events + " eventos independientes",
        events < 10 ? "warn" : "ok",
        events < 10 ? "Limitado" : "Disponible",
      ),
    ].join("");
    const validEvents = items.every(
      (x) =>
        w(x).source_event_id !== null &&
        w(x).source_event_id !== undefined &&
        String(w(x).source_event_id) !== "",
    );
    document
      .querySelectorAll('[data-ds-action="generate"]')
      .forEach(
        (btn) =>
          (btn.disabled = !total || pending > 0 || !splitOk || !validEvents),
      );
  }
  async function refresh() {
    const r = await Bridge.getDatasetWorkspace();
    if (!r || !r.success) {
      setText("ds-summary", r?.error || "No se pudo cargar Etiquetado.");
      return;
    }
    items = r.items || [];
    const batchSelect = $("ds-label-batch");
    if (batchSelect) {
      const batches = r.label_batches || [],
        activeId = r.active_label_batch?.id || "";
      batchSelect.innerHTML =
        '<option value="">Seleccionar etiquetado…</option>' +
        batches
          .map(
            (b) =>
              '<option value="' +
              esc(b.filename) +
              '" ' +
              (b.id === activeId ? "selected" : "") +
              ">" +
              esc(b.name) +
              " · " +
              esc(b.count) +
              " ventanas</option>",
          )
          .join("");
    }
    const conf = items.filter(
      (x) =>
        l(x).quality_review === "confirmed" && [0, 1].includes(l(x).class_code),
    );
    const a = conf.filter((x) => l(x).class_code === 0).length,
      b = conf.filter((x) => l(x).class_code === 1).length;
    const events = new Set(items.map(eventKey).filter((k) => !k.endsWith("::")))
      .size;
    setText("ds-m-total", items.length.toLocaleString("es-ES"));
    setText("ds-m-events", events.toLocaleString("es-ES"));
    setText("ds-m-confirmed", conf.length.toLocaleString("es-ES"));
    setText("ds-donut-total", items.length.toLocaleString("es-ES"));
    setText(
      "ds-class-0",
      a.toLocaleString("es-ES") + " (" + percent(a, conf.length) + ")",
    );
    setText(
      "ds-class-1",
      b.toLocaleString("es-ES") + " (" + percent(b, conf.length) + ")",
    );
    // Keep the primary binary classes intact, while subdividing NO_SISMICO by its
    // persisted secondary disturbance category for visualization only.
    const categories = ["RUIDO", "VIBRACIONES", "GOLPES", "INDETERMINADO"];
    const categoryColors = {
      RUIDO: "#2563eb",
      VIBRACIONES: "#06b6d4",
      GOLPES: "#8b5cf6",
      INDETERMINADO: "#94a3b8",
      SIN_SUBCATEGORIA: "#cbd5e1",
    };
    const subCounts = {};
    conf
      .filter((x) => l(x).class_code === 1)
      .forEach((x) => {
        const raw = String(l(x).disturbance || "")
          .trim()
          .toUpperCase();
        const key = categories.includes(raw) ? raw : "SIN_SUBCATEGORIA";
        subCounts[key] = (subCounts[key] || 0) + 1;
      });
    const subKeys = [
      ...categories.filter((k) => subCounts[k]),
      ...(subCounts.SIN_SUBCATEGORIA ? ["SIN_SUBCATEGORIA"] : []),
    ];
    const slices = [
      { name: "TEMBLOR", count: a, color: "#ef4444" },
      ...subKeys.map((k) => ({
        name: k === "SIN_SUBCATEGORIA" ? "Sin subcategoría" : k,
        count: subCounts[k],
        color: categoryColors[k],
      })),
    ].filter((x) => x.count > 0);
    let acc = 0;
    const stops = slices.map((s) => {
      const from = acc;
      acc += conf.length ? (100 * s.count) / conf.length : 0;
      return s.color + " " + from + "% " + acc + "%";
    });
    if ($("ds-donut"))
      $("ds-donut").style.background = slices.length
        ? "conic-gradient(" + stops.join(", ") + ")"
        : "#e2e8f0";
    const subTotal = subKeys.reduce((n, k) => n + subCounts[k], 0);
    if ($("ds-legend"))
      $("ds-legend").innerHTML =
        '<div class="ds-legend-primary"><i class="ds-dot tremor"></i><span>TEMBLOR</span><b>' +
        a.toLocaleString("es-ES") +
        " (" +
        percent(a, conf.length) +
        ")</b></div>" +
        '<div class="ds-legend-primary"><i class="ds-dot nonseismic"></i><span>NO_SISMICO</span><b>' +
        b.toLocaleString("es-ES") +
        " (" +
        percent(b, conf.length) +
        ")</b></div>" +
        subKeys
          .map(
            (k) =>
              '<div class="ds-legend-sub"><i class="ds-dot" style="background:' +
              categoryColors[k] +
              '"></i><span>' +
              (k === "SIN_SUBCATEGORIA" ? "Sin subcategoría" : k) +
              "</span><b>" +
              subCounts[k].toLocaleString("es-ES") +
              " (" +
              percent(subCounts[k], conf.length) +
              ")</b></div>",
          )
          .join("");
    if ($("ds-imbalance"))
      $("ds-imbalance").hidden = !(
        conf.length &&
        (!a || !b || Math.max(a, b) > Math.max(1, Math.min(a, b)) * 4)
      );
    const pending = items.length - conf.length;
    setText(
      "ds-summary",
      items.length +
        " ventanas incluidas · " +
        conf.length +
        " confirmadas · " +
        pending +
        " pendientes · " +
        events +
        " eventos",
    );
    filterRows();
    renderStatus();
  }
  async function generate() {
    if (!updateSplit()) return;
    const name = $("ds-name").value.trim();
    if (!name) {
      setText("ds-validation", "Escribe un nombre para el dataset.");
      $("ds-validation").classList.add("error");
      return;
    }
    document
      .querySelectorAll('[data-ds-action="generate"]')
      .forEach((b) => (b.disabled = true));
    const ratios = ["ds-train", "ds-val", "ds-test"].map(
      (id) => Number($(id).value) / 100,
    );
    let result;
    try {
      result = await Bridge.generateDataset(ratios, 42, name);
    } catch (e) {
      result = { success: false, error: e?.message || String(e) };
    }
    if (!result?.success) {
      setText(
        "ds-validation",
        result?.error || result?.error_text || "No se pudo generar el dataset.",
      );
      $("ds-validation").classList.add("error");
      document
        .querySelectorAll('[data-ds-action="generate"]')
        .forEach((b) => (b.disabled = false));
      renderStatus();
      return;
    }
    setText("ds-version-note", "Dataset guardado: " + name);
    await refreshSavedDatasets();
    // Pass the just-created manifest directly to Models; do not depend on a second bridge read.
    window.__pendingModelsDataset = result.dataset || null;
  }
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-ds-action]");
    if (!btn) return;
    if (btn.dataset.dsAction === "refresh") await refresh();
    if (btn.dataset.dsAction === "refresh-saved") await refreshSavedDatasets();
    if (btn.dataset.dsAction === "delete-saved") {
      const filename = btn.dataset.filename;
      if (!filename) return;
      if (!(await window.showConfirmDialog({
        title: "Confirmar eliminación",
        subtitle: "Esta acción no se puede deshacer.",
        message: '¿Deseas eliminar el Dataset "' + filename + '"?',
      }))) return;
      btn.disabled = true;
      try {
        const result = await Bridge.deleteDataset(filename);
        if (!result?.success)
          throw new Error(result?.error || "No se pudo eliminar el Dataset.");
        await refreshSavedDatasets();
      } catch (error) {
        alert(error?.message || String(error));
        btn.disabled = false;
      }
    }
    if (btn.dataset.dsAction === "generate") await generate();
    if (btn.dataset.dsAction === "labeling") await App.navigateTo("etiquetado");
    if (btn.dataset.dsAction === "show-all") {
      examplesExpanded = !examplesExpanded;
      renderRows();
      btn.textContent = examplesExpanded ? "Ver menos" : "Ver más";
      const table = $("ds-example-table");
      if (table) table.classList.toggle("is-expanded", examplesExpanded);
    }
  });
  document.addEventListener("input", (e) => {
    if (e.target?.id === "ds-name") updateGenerateButton();
  });
  document.addEventListener("change", (e) => {
    if (e.target.id === "ds-filter") filterRows();
    if (e.target.id === "ds-label-batch" && e.target.value) {
      Bridge.selectLabelBatch(e.target.value).then((r) => {
        if (r?.success) refresh();
        else setText("ds-summary", r?.error || "No se pudo cargar el lote.");
      });
    }
    const numbers = ["ds-train", "ds-val", "ds-test"],
      ranges = ["ds-train-range", "ds-val-range", "ds-test-range"];
    let i = numbers.indexOf(e.target.id),
      fromRange = false;
    if (i < 0) {
      i = ranges.indexOf(e.target.id);
      fromRange = true;
    }
    if (i >= 0) {
      $(numbers[i]).value = e.target.value;
      $(ranges[i]).value = e.target.value;
      renderStatus();
    }
  });
  window.initDataset = async () => {
    await refresh();
    await refreshSavedDatasets();
  };
})();
