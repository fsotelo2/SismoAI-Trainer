/* Fase 9: configuración, entrenamiento PC y seguimiento del experimento. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id),
    esc = (v) =>
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
  let dataset = null,
    pollHandle = null,
    active = false,
    hasSavedExperiments = false;
  const names = {
    "1d_cnn": "1D-CNN",
    feature_classifier: "Clasificador de características",
    baseline: "Baseline lineal",
  };
  function config() {
    return {
      name: $("models-name").value.trim(),
      architecture: $("models-architecture").value,
      framework: $("models-framework").value,
      input: $("models-input").value,
      description: $("models-description").value.trim(),
      training: {
        epochs: Number($("models-epochs").value),
        batch_size: Number($("models-batch").value),
        learning_rate: Number($("models-lr").value),
        seed: Number($("models-seed").value),
        optimizer: $("models-optimizer").value,
        loss: $("models-loss").value,
        early_stopping: $("models-early-stop").checked,
        save_best: $("models-best").checked,
        class_weighting: $("models-weighted").checked,
      },
    };
  }
  function renderModelSummary() {
    const values = {
      "models-summary-architecture": $("models-architecture")?.selectedOptions[0]?.textContent || "—",
      "models-summary-input": $("models-input")?.selectedOptions[0]?.textContent || "—",
    };
    Object.entries(values).forEach(([id, value]) => {
      const element = $(id);
      if (element) element.textContent = value;
    });
  }
  function validate(c) {
    if (!c.name) return "Indica el nombre del experimento.";
    if (
      !Number.isInteger(c.training.epochs) ||
      c.training.epochs < 1 ||
      c.training.epochs > 10000
    )
      return "Épocas: entero entre 1 y 10000.";
    if (
      !Number.isInteger(c.training.batch_size) ||
      c.training.batch_size < 1 ||
      c.training.batch_size > 4096
    )
      return "Batch size: entero entre 1 y 4096.";
    if (
      !Number.isFinite(c.training.learning_rate) ||
      c.training.learning_rate <= 0 ||
      c.training.learning_rate > 1
    )
      return "Learning rate debe estar entre 0 y 1.";
    if (!Number.isInteger(c.training.seed) || c.training.seed < 0)
      return "Semilla: entero no negativo.";
    return "";
  }
  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("es-CO", {
      timeZone: "America/Bogota",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    }).format(date);
  }
  function datasetRender(r) {
    const d = r?.active_dataset || r?.dataset || r?.manifest || null,
      b = $("models-dataset-badge"),
      selector = $("models-dataset");
    dataset = null;
    const available = Array.isArray(r?.datasets) ? r.datasets : [];
    selector.innerHTML = available.length
      ? available
          .map(
            (x) =>
              '<option value="' +
              esc(x.filename) +
              '"' +
              (d && x.dataset_id === d.dataset_id ? " selected" : "") +
              ">" +
              esc(x.name || x.filename) +
              " · " +
              esc(formatDate(x.created_at)) +
              "</option>",
          )
          .join("")
      : '<option value="">No hay archivos Dataset disponibles</option>';
    selector.disabled = available.length === 0;
    if (!r?.success) {
      b.textContent = "Error de consulta";
      b.className = "badge badge-warning";
      $("models-dataset-summary").textContent =
        r?.error || "No se pudo consultar la carpeta Dataset.";
      $("models-partition").innerHTML = "<span>Sin datos</span>";
      return;
    }
    if (!d) {
      b.textContent = available.length
        ? "Seleccione un Dataset"
        : "Sin Dataset";
      b.className = "badge badge-warning";
      $("models-dataset-summary").textContent = available.length
        ? "Hay " +
          available.length +
          " manifiesto(s) guardado(s). Seleccione uno para cargarlo."
        : "No hay manifiesto activo ni archivos JSON válidos en ./Dataset/.";
      $("models-partition").innerHTML = "<span>Sin datos</span>";
      return;
    }
    if (typeof d !== "object" || !d.dataset_id) {
      b.textContent = "Respuesta no reconocida";
      b.className = "badge badge-warning";
      $("models-dataset-summary").textContent =
        "El backend respondió, pero no entregó un manifiesto válido (se esperaba dataset_id, summary y splits).";
      $("models-partition").innerHTML =
        "<span>Manifiesto con estructura no válida</span>";
      return;
    }
    dataset = d;
    b.textContent = "Seleccionado";
    b.className = "badge badge-success";
    const s = d.summary || {},
      all = s.all || {},
      tr = s.train || {},
      va = s.validation || {},
      te = s.test || {};
    $("models-dataset-summary").innerHTML =
      "<b>Nombre:</b> " +
      esc(d.name || "—") +
      "<br><b>ID:</b> " +
      esc(d.dataset_id || "—") +
      "<br><b>Ventanas:</b> " +
      (all.windows ?? "—") +
      "<br><b>Eventos independientes:</b> " +
      (all.events ?? "—") +
      "<br><b>Train / Validation / Test:</b> " +
      (tr.windows ?? "—") +
      " / " +
      (va.windows ?? "—") +
      " / " +
      (te.windows ?? "—");
    const total = Number(all.windows || 0),
      parts = [
        ["train", Number(tr.windows || 0), "Train", "#1677e8"],
        ["validation", Number(va.windows || 0), "Validation", "#19b99a"],
        ["test", Number(te.windows || 0), "Test", "#f59e0b"],
      ];
    $("models-partition").innerHTML = total
      ? parts
          .map(
            (p) =>
              '<i class="' +
              p[0] +
              '" style="width:' +
              (p[1] / total) * 100 +
              '%"></i>',
          )
          .join("")
      : "<span>Particiones no informadas</span>";
    $("models-partition-legend").innerHTML = parts
      .map(
        (p) =>
          '<span><i style="background:' +
          p[3] +
          '"></i>' +
          p[2] +
          ": " +
          p[1] +
          (total ? " (" + ((p[1] / total) * 100).toFixed(1) + "%)" : "") +
          "</span>",
      )
      .join("");
    $("models-summary-dataset").textContent = d.name || "—";
    $("models-summary-split").textContent =
      (tr.windows ?? "—") + " / " + (va.windows ?? "—") + " / " + (te.windows ?? "—");
    renderModelSummary();
  }
  function renderLibrary(r) {
    const list = r?.experiments || [];
    hasSavedExperiments = list.length > 0;
    updateExportButton();
    $("models-library-body").innerHTML = list.length
      ? list
          .map((x) => {
            const m = x.training_result?.metrics?.validation;
            const state =
              x.status === "trained"
                ? "Entrenado"
                : x.status === "error"
                  ? "Error"
                  : x.status === "running"
                    ? "Entrenando"
                    : "Configuración";
            const id = esc(x.experiment_id || "");
            const count = Array.isArray(x.runs)
              ? x.runs.length
              : x.training_result
                ? 1
                : 0;
            return (
              "<tr><td>" +
              esc(x.config?.name || "—") +
              "</td><td>" +
              esc(
                names[x.config?.architecture] || x.config?.architecture || "—",
              ) +
              "</td><td>" +
              esc(x.dataset_name || "—") +
              "</td><td>" +
              esc(formatDate(x.created_at) || "—") +
              "</td><td>" +
              esc(state) +
              (count ? " · " + count + " ejec." : "") +
              "</td><td>" +
              (m && Number.isFinite(Number(m.accuracy))
                ? (100 * m.accuracy).toFixed(1) + "% val."
                : "—") +
              '</td><td class="models-row-actions"><button class="btn btn-secondary" data-model-action="detail" data-id="' +
              id +
              '">Detalle</button> <button class="btn btn-secondary" data-model-action="load" data-id="' +
              id +
              '">Cargar</button> <button class="btn btn-danger" data-model-action="delete" data-id="' +
              id +
              '">Eliminar</button></td></tr>'
            );
          })
          .join("")
      : '<tr><td colspan="7">No hay experimentos guardados.</td></tr>';
  }
  function updateExportButton() {
    const button = $("btn-continue-exportar");
    if (!button) return;
    button.disabled = !hasSavedExperiments;
    button.title = hasSavedExperiments
      ? "Hay experimentos guardados disponibles"
      : "Guarda un experimento antes de continuar a Exportar";
  }
  async function refresh() {
    const r = await Promise.race([
      Bridge.getModelExperiments(),
      new Promise((resolve) =>
        setTimeout(
          () =>
            resolve({
              success: false,
              error: "Tiempo de espera agotado al consultar los experimentos.",
            }),
          12000,
        ),
      ),
    ]);
    if (r?.success === false || r?.error) {
      hasSavedExperiments = false;
      updateExportButton();
      $("models-library-body").innerHTML =
        '<tr><td colspan="6">Error al consultar biblioteca: ' +
        esc(r.error || "desconocido") +
        "</td></tr>";
      return;
    }
    renderLibrary(r);
  }
  async function save() {
    const c = config(),
      err = validate(c);
    $("models-form-message").textContent = err;
    if (err) return null;
    if (!dataset?.dataset_id) {
      $("models-form-message").textContent =
        "Primero genera un dataset activo.";
      return null;
    }
    $("models-save-status").textContent = "Guardando…";
    try {
      const r = await Bridge.saveModelExperiment(
        c,
        dataset.dataset_id,
        dataset.name || "Dataset",
      );
      if (!r?.success) {
        $("models-save-status").textContent = "Error al guardar";
        $("models-form-message").textContent =
          r?.error || r?.error_text || "Error de persistencia";
        return null;
      }
      $("models-save-status").textContent =
        "Configuración guardada · " + r.experiment_id;
      $("models-form-message").textContent = "";
      await refresh();
      return r;
    } catch (e) {
      $("models-save-status").textContent = "Error al guardar";
      $("models-form-message").textContent =
        "No se pudo guardar: " + (e?.message || String(e));
      return null;
    }
  }
  async function getExperiment(id) {
    const r = await Bridge.getModelExperiments();
    if (!r?.success)
      throw new Error(r?.error || "No se pudo leer el registro.");
    return (r.experiments || []).find((x) => x.experiment_id === id);
  }
  function showExperimentDetail(id) {
    getExperiment(id)
      .then((x) => {
        if (!x) throw new Error("Experimento no encontrado.");
        let dlg = document.getElementById("models-experiment-dialog");
        if (!dlg) {
          dlg = document.createElement("dialog");
          dlg.id = "models-experiment-dialog";
          dlg.className = "models-experiment-dialog";
          document.body.appendChild(dlg);
        }
        const c = x.config || {},
          t = c.training || {};
        dlg.innerHTML =
          '<form method="dialog"><header style="display:flex;justify-content:space-between;align-items:center;gap:12px"><h2 style="margin:0">Detalle del experimento</h2><button class="btn btn-secondary">Cerrar</button></header></form><p><b>' +
          esc(c.name || "—") +
          "</b> · " +
          esc(names[c.architecture] || c.architecture || "—") +
          "</p><p>Dataset: " +
          esc(x.dataset_name || "—") +
          " · Estado: " +
          esc(x.status || "—") +
          " · Creado: " +
          esc(formatDate(x.created_at) || "—") +
          '</p><h3>Configuración</h3><pre style="white-space:pre-wrap;overflow:auto;max-height:35vh;font-size:12px">' +
          esc(
            JSON.stringify(
              {
                framework: c.framework,
                input: c.input,
                description: c.description,
                training: t,
              },
              null,
              2,
            ),
          ) +
          '</pre><h3>Resultados e historial</h3><pre style="white-space:pre-wrap;overflow:auto;max-height:35vh;font-size:12px">' +
          esc(
            JSON.stringify(
              x.runs?.length
                ? x.runs
                : x.training_result
                  ? [{ training_result: x.training_result }]
                  : [],
              null,
              2,
            ),
          ) +
          "</pre>";
        dlg.showModal();
      })
      .catch((err) => alert(err.message));
  }
  async function loadExperiment(id) {
    try {
      const x = await getExperiment(id);
      if (!x) throw new Error("Experimento no encontrado.");
      const catalog = await Bridge.getDatasetCatalog();
      if (!catalog?.success)
        throw new Error(
          catalog?.error || "No se pudo consultar el inventario de Datasets.",
        );
      const savedDataset = (catalog.datasets || []).find(
        (d) => String(d.dataset_id) === String(x.dataset_id),
      );
      if (!savedDataset)
        throw new Error(
          "El Dataset asociado a este experimento ya no está disponible. No se cargó la configuración.",
        );
      const selected = await Bridge.selectDataset(savedDataset.filename);
      if (!selected?.success)
        throw new Error(
          selected?.error || "No se pudo activar el Dataset del experimento.",
        );
      datasetRender({
        success: true,
        active_dataset: selected.active_dataset,
        datasets: selected.datasets,
        manifest_path: selected.manifest_path,
      });
      const c = x.config || {},
        t = c.training || {};
      const set = (key, val) => {
        const el = $(key);
        if (el && val !== undefined && val !== null) el.value = val;
      };
      set("models-name", c.name);
      set("models-architecture", c.architecture);
      set("models-framework", c.framework);
      set("models-input", c.input);
      set("models-description", c.description);
      set("models-epochs", t.epochs);
      set("models-batch", t.batch_size);
      set("models-lr", t.learning_rate);
      set("models-seed", t.seed);
      set("models-optimizer", t.optimizer);
      set("models-loss", t.loss);
      for (const [id2, k] of [
        ["models-early-stop", "early_stopping"],
        ["models-best", "save_best"],
        ["models-weighted", "class_weighting"],
      ])
        if ($(id2) && t[k] !== undefined) $(id2).checked = !!t[k];
      $("models-form-message").textContent =
        "Configuración y Dataset asociados cargados. Puedes iniciar una nueva ejecución; se conservará el historial de este experimento.";
    } catch (err) {
      alert(err.message);
    }
  }
  async function deleteExperiment(id) {
    try {
      const x = await getExperiment(id);
      if (!x) throw new Error("Experimento no encontrado.");
      const name = x.config?.name || id;
      if (
        !confirm(
          '¿Eliminar el experimento "' +
            name +
            '"? Se eliminará el registro y su historial, pero no los archivos de pesos del modelo.',
        )
      )
        return;
      const r = await Bridge.deleteModelExperiment(id);
      if (!r?.success) throw new Error(r?.error || "No se pudo eliminar.");
      await refresh();
    } catch (err) {
      alert(err.message);
    }
  }
  function renderChart(history) {
    const host = document.querySelector(".models-chart-empty");
    if (!host || !Array.isArray(history) || !history.length) return;
    const w = 560,
      h = 105,
      pad = 10,
      values = history
        .flatMap((x) => [Number(x.train_loss), Number(x.validation_loss)])
        .filter(Number.isFinite);
    if (!values.length) return;
    let min = Math.min(...values),
      max = Math.max(...values);
    if (max === min) {
      max += 1;
      min = Math.max(0, min - 1);
    }
    const y = (v) => h - pad - ((v - min) / (max - min)) * (h - 2 * pad),
      x = (i) =>
        pad +
        (history.length === 1 ? 0 : i / (history.length - 1)) * (w - 2 * pad);
    const line = (key) =>
      history
        .map((r, i) =>
          Number.isFinite(Number(r[key]))
            ? x(i) + "," + y(Number(r[key]))
            : null,
        )
        .filter(Boolean)
        .join(" ");
    host.classList.remove("models-chart-empty");
    host.innerHTML =
      '<svg viewBox="0 0 ' +
      w +
      " " +
      h +
      '" role="img" aria-label="Curvas de pérdida de entrenamiento y validación" style="width:100%;height:105px"><line x1="' +
      pad +
      '" y1="' +
      (h - pad) +
      '" x2="' +
      (w - pad) +
      '" y2="' +
      (h - pad) +
      '" stroke="currentColor" opacity=".25"/><polyline fill="none" stroke="#1677e8" stroke-width="2" points="' +
      line("train_loss") +
      '"/><polyline fill="none" stroke="#f59e0b" stroke-width="2" points="' +
      line("validation_loss") +
      '"/></svg><div class="models-muted">Azul: Train loss · Naranja: Validation loss · ' +
      history.length +
      " épocas registradas</div>";
  }
  function updateProgress(s) {
    const p = s.progress || {},
      epoch = Number(s.epoch || 0),
      total = Number(s.epochs || 0),
      completed = s.status === "completed",
      pct = completed
        ? 100
        : total
          ? Math.min(100, Math.round((epoch / total) * 100))
          : 0;
    $("models-progress-label").textContent = "Época: " + epoch + " / " + total;
    $("models-progress-percent").textContent =
      s.status === "error" ? "Error" : pct + "%";
    $("models-progress-bar").style.width = pct + "%";
    $("models-progress-detail").textContent =
      s.error ||
      (completed
        ? "Entrenamiento finalizado" +
          (total && epoch < total
            ? " antes de alcanzar el máximo de épocas."
            : " correctamente.")
        : p.elapsed_seconds != null
          ? "Tiempo transcurrido: " +
            Number(p.elapsed_seconds).toFixed(1) +
            " s"
          : "Estado: " + s.status);
    const note = $("models-progress-note");
    if (note)
      note.textContent = completed
        ? "Ejecución completada."
        : s.status === "error"
          ? "La ejecución terminó con error."
          : s.status === "running"
            ? "Entrenamiento en curso."
            : s.status === "preparing"
              ? "Preparando datos para entrenar."
              : "El entrenamiento aún no se ha ejecutado.";
    if (p.train_loss != null)
      $("models-live-train").textContent = Number(p.train_loss).toFixed(5);
    if (p.validation_loss != null)
      $("models-live-val").textContent = Number(p.validation_loss).toFixed(5);
    if (p.validation_accuracy != null)
      $("models-live-acc").textContent =
        (100 * p.validation_accuracy).toFixed(2) + "%";
    if (s.status === "completed" && s.result) {
      renderChart(s.result.history);
      const m = s.result.metrics || {},
        v = m.validation || {},
        t = m.test || {};
      const dds = document.querySelectorAll(".models-final-metrics dd");
      const vals = [
        m.train?.loss ?? "—",
        v.loss ?? "—",
        t.accuracy != null ? (100 * t.accuracy).toFixed(2) + "%" : "—",
        t.f1_macro != null ? t.f1_macro.toFixed(4) : "—",
      ];
      dds.forEach(
        (el, i) =>
          (el.textContent =
            typeof vals[i] === "number" ? vals[i].toFixed(5) : vals[i]),
      );
      const matrix = t.confusion_matrix;
      const matrixBody = $("models-confusion-matrix");
      if (matrixBody) {
        const matrixRows = Array.isArray(matrix)
            ? matrix.map((row) => (Array.isArray(row) ? row : [row]))
            : [];
        const maxValue = Math.max(
            1,
            ...matrixRows.flat().map((value) => Number(value) || 0),
        );
        matrixBody.innerHTML = matrixRows.length
            ? matrixRows
                .map(
                  (row) =>
                    "<tr>" +
                    row
                      .map((value) => {
                        const numeric = Number(value) || 0;
                        const intensity = 0.18 + (numeric / maxValue) * 0.72;
                        return (
                          '<td style="background:rgba(37,99,235,' +
                          intensity.toFixed(2) +
                          ');color:' +
                          (intensity > 0.58 ? "#fff" : "#172554") +
                          '">' +
                          esc(value) +
                          "</td>"
                        );
                      })
                      .join("") +
                    "</tr>",
                )
                .join("")
            : "<tr><td>—</td></tr>";
      }
    }
  }
  async function poll() {
    if (!active) return;
    let s;
    try {
      s = await Bridge.getModelTrainingState();
    } catch (e) {
      $("models-progress-detail").textContent =
        "Error consultando progreso: " + e.message;
      active = false;
      return;
    }
    if (s?.success) updateProgress(s);
    if (s?.status === "completed" || s?.status === "error") {
      active = false;
      clearTimeout(pollHandle);
      $("models-save-status").textContent =
        s.status === "completed"
          ? "Entrenamiento completado"
          : "Entrenamiento con error";
      await refresh();
      return;
    }
    pollHandle = setTimeout(poll, 1200);
  }
  async function train() {
    if (active) return;
    const saved = await save();
    if (!saved) return;
    $("models-form-message").textContent = "Preparando ventanas y particiones…";
    let r;
    try {
      r = await Bridge.startModelTraining(config(), dataset.dataset_id);
    } catch (e) {
      $("models-form-message").textContent =
        "Error iniciando entrenamiento: " + e.message;
      return;
    }
    if (!r?.success) {
      $("models-form-message").textContent =
        r?.error || "No se pudo iniciar el entrenamiento.";
      return;
    }
    $("models-form-message").textContent =
      "Entrenamiento en PC iniciado. La preparación de señales puede tardar.";
    $("models-save-status").textContent = "Entrenamiento en preparación";
    active = true;
    updateProgress({
      status: "preparing",
      epoch: 0,
      epochs: config().training.epochs,
    });
    poll();
  }
  function reset() {
    if (active)
      return alert(
        "No se pueden restablecer parámetros durante el seguimiento de una ejecución.",
      );
    if (!confirm("¿Restablecer parámetros?")) return;
    $("models-name").value = "cnn_sismos_001";
    $("models-architecture").value = "1d_cnn";
    $("models-framework").value = "pytorch";
    $("models-input").value = "geo_mpu";
    $("models-description").value = "";
    $("models-epochs").value = 50;
    $("models-batch").value = 32;
    $("models-lr").value = ".001";
    $("models-seed").value = 42;
    $("models-optimizer").value = "adam";
    $("models-loss").value = "cross_entropy";
    $("models-early-stop").checked = true;
    $("models-best").checked = true;
    $("models-weighted").checked = false;
    $("models-form-message").textContent = "";
    $("models-save-status").textContent = "Parámetros restablecidos";
  }
  document.addEventListener("change", async (e) => {
    if (
      e.target?.id === "models-architecture" ||
      e.target?.id === "models-input"
    ) {
      renderModelSummary();
    }
    if (e.target?.id !== "models-dataset") return;
    const filename = e.target.value;
    if (!filename) return;
    const select = e.target;
    select.disabled = true;
    $("models-dataset-summary").textContent = "Cargando Dataset seleccionado…";
    try {
      const r = await Bridge.selectDataset(filename);
      if (!r?.success)
        throw new Error(r?.error || "No se pudo seleccionar el Dataset.");
      datasetRender({
        success: true,
        active_dataset: r.active_dataset,
        datasets: r.datasets,
        manifest_path: r.manifest_path,
      });
      $("models-form-message").textContent = "";
    } catch (err) {
      $("models-dataset-summary").textContent =
        "Error: " + (err?.message || String(err));
    } finally {
      select.disabled = !(select.options.length && select.options[0].value);
    }
  });
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-model-action]");
    if (!b) return;
    const a = b.dataset.modelAction;
    if (a === "save") save();
    if (a === "train") train();
    if (a === "reset") reset();
    if (a === "refresh") refresh();
    if (a === "detail") showExperimentDetail(b.dataset.id);
    if (a === "load") loadExperiment(b.dataset.id);
    if (a === "delete") deleteExperiment(b.dataset.id);
  });
  window.initModels = async (datasetHint = null) => {
    if (!datasetHint && window.__pendingModelsDataset) {
      datasetHint = window.__pendingModelsDataset;
      window.__pendingModelsDataset = null;
    }
    if (pollHandle) clearTimeout(pollHandle);
    active = false;
    const summary = $("models-dataset-summary"),
      badge = $("models-dataset-badge"),
      selector = $("models-dataset");
    summary.textContent = "Consultando manifiesto activo…";
    badge.textContent = "Consultando";
    selector.disabled = true;
    // Show the just-generated manifest immediately; the inventory request must not block the view.
    if (datasetHint)
      datasetRender({
        success: true,
        active_dataset: datasetHint,
        datasets: [],
      });
    try {
      const result = await Promise.race([
        Bridge.getDatasetCatalog(),
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                success: false,
                error:
                  "Tiempo de espera agotado al consultar los archivos JSON de Dataset.",
              }),
            12000,
          ),
        ),
      ]);
      if (result?.success) {
        if (datasetHint) {
          result.active_dataset = datasetHint;
          datasetRender(result);
        } else if (
          !result.active_dataset &&
          Array.isArray(result.datasets) &&
          result.datasets.length
        ) {
          // If no active manifest was restored, load the first available saved JSON.
          const first = result.datasets[0].filename;
          const loaded = await Bridge.selectDataset(first);
          if (loaded?.success)
            datasetRender({
              success: true,
              active_dataset: loaded.active_dataset,
              datasets: loaded.datasets,
              manifest_path: loaded.manifest_path,
            });
          else
            datasetRender({
              ...result,
              active_dataset: null,
              error: loaded?.error || "No se pudo cargar el primer Dataset.",
            });
        } else {
          datasetRender(result);
        }
      } else if (datasetHint) {
        badge.textContent = "Dataset generado";
        badge.className = "badge badge-warning";
        summary.textContent =
          (datasetHint.name || "Dataset") +
          " · Manifiesto recibido. No se pudo consultar el inventario: " +
          (result?.error || "respuesta no válida");
      } else {
        datasetRender({
          success: false,
          error:
            result?.error ||
            "No se pudo consultar el Dataset. Verifica la conexión con el backend.",
        });
      }
    } catch (e) {
      if (datasetHint) {
        badge.textContent = "Dataset generado";
        badge.className = "badge badge-warning";
        summary.textContent =
          (datasetHint.name || "Dataset") +
          " · Manifiesto recibido. Error consultando inventario: " +
          (e?.message || String(e));
      } else
        datasetRender({
          success: false,
          error: "Error al cargar el Dataset: " + (e?.message || String(e)),
        });
    } finally {
      selector.disabled = !(
        selector.options.length && selector.options[0].value
      );
    }
    try {
      await refresh();
    } catch (e) {
      $("models-library-body").innerHTML =
        '<tr><td colspan="6">Error al consultar experimentos: ' +
        esc(e?.message || String(e)) +
        "</td></tr>";
    }
    try {
      const state = await Promise.race([
        Bridge.getModelTrainingState(),
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                success: false,
                error: "Tiempo de espera agotado al consultar el estado.",
              }),
            12000,
          ),
        ),
      ]);
      if (state?.status === "preparing" || state?.status === "running") {
        active = true;
        poll();
      } else if (state?.status === "completed" || state?.status === "error")
        updateProgress(state);
    } catch (e) {
      $("models-progress-detail").textContent =
        "No se pudo consultar el estado: " + (e?.message || String(e));
    }
  };
})();
