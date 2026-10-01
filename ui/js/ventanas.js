/* Phase 6 — Windows view controller */
(() => {
  "use strict";
  let context = null,
    windows = [],
    mode = "fixed",
    dragStart = null,
    dragEnd = null,
    manualContextKey = null;
  const manualRanges = new Map();
  const $ = (id) => document.getElementById(id);
  const sec = (us) => (us / 1e6).toFixed(1);
  const RANGE_STEP = 0.1;
  const roundRange = (value) => Math.round(value / RANGE_STEP) * RANGE_STEP;
  const sensors = (manual) =>
    [
      $(manual ? "wm-geo" : "w-geo").checked ? "GEO" : null,
      $(manual ? "wm-mpu" : "w-mpu").checked ? "MPU" : null,
    ].filter(Boolean);
  function setMode(next) {
    mode = next;
    $("w-auto-controls").style.display = next === "manual" ? "none" : "flex";
    $("w-manual-controls").style.display = next === "manual" ? "flex" : "none";
    $("w-mode-title").textContent =
      next === "manual"
        ? "Selección manual de intervalo"
        : "Configuración de segmentación";
    $("w-mode-subtitle").textContent =
      next === "manual"
        ? "Selecciona un intervalo específico del evento."
        : "Genera ventanas fijas o deslizantes.";
    document.querySelectorAll('[data-w-action="mode"]').forEach((b) => {
      b.classList.toggle("btn-primary", b.dataset.mode === next);
      b.classList.toggle("btn-secondary", b.dataset.mode !== next);
    });
  }
  function draw(canvas, times, values, color, select) {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect(),
      dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.max(1, Math.round(rect.width * dpr)),
      pixelHeight = Math.max(1, Math.round(150 * dpr));
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    const c = canvas.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    const w = rect.width,
      h = 150,
      p = { l: 42, r: 10, t: 10, b: 25 },
      pw = w - p.l - p.r,
      ph = h - p.t - p.b;
    c.clearRect(0, 0, w, h);
    c.strokeStyle = "#e2e8f0";
    c.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = p.t + (ph * i) / 4;
      c.beginPath();
      c.moveTo(p.l, y);
      c.lineTo(w - p.r, y);
      c.stroke();
    }
    const maxT = Math.max(context?.duration_seconds || 0, 1),
      minV = Math.min(0, ...values),
      maxV = Math.max(0, ...values);
    const span = maxV - minV || 1;
    c.fillStyle = "#64748b";
    c.font = "11px sans-serif";
    c.fillText("0 s", p.l, h - 5);
    c.fillText(maxT.toFixed(1) + " s", w - 45, h - 5);
    c.strokeStyle = color;
    c.lineWidth = 1;
    c.beginPath();
    const n = Math.min(times.length, values.length),
      stride = Math.max(1, Math.floor(n / 2500));
    for (let i = 0; i < n; i += stride) {
      const x = p.l + (times[i] / maxT) * pw,
        y = p.t + (1 - (values[i] - minV) / span) * ph;
      if (i === 0) c.moveTo(x, y);
      else c.lineTo(x, y);
    }
    c.stroke();
    if (select) {
      const a = Math.max(0, Math.min(maxT, Number($("w-start")?.value) || 0));
      const b = Math.max(a, Math.min(maxT, Number($("w-end")?.value) || 0));
      const x1 = p.l + (a * pw) / maxT,
        x2 = p.l + (b * pw) / maxT;
      c.fillStyle = "rgba(16,185,129,.18)";
      c.fillRect(x1, p.t, x2 - x1, ph);
      c.save();
      c.setLineDash([5, 4]);
      c.strokeStyle = "#059669";
      c.lineWidth = 1.5;
      [x1, x2].forEach((x) => {
        c.beginPath();
        c.moveTo(x, p.t + 3);
        c.lineTo(x, p.t + ph);
        c.stroke();
      });
      c.restore();
      [x1, x2].forEach((x) => {
        c.fillStyle = "#059669";
        c.beginPath();
        c.moveTo(x - 8, p.t - 1);
        c.lineTo(x + 8, p.t - 1);
        c.lineTo(x, p.t + 13);
        c.closePath();
        c.fill();
        c.strokeStyle = "#ffffff";
        c.lineWidth = 1;
        c.stroke();
      });
      canvas.style.cursor = "ew-resize";
      if (!canvas.dataset.manualHandles) {
        canvas.dataset.manualHandles = "1";
        let activeHandle = null;
        const coords = (e) => {
          const r = canvas.getBoundingClientRect();
          return e.clientX - r.left;
        };
        const geometry = () => {
          const r = canvas.getBoundingClientRect(),
            width = r.width,
            plotL = 42,
            plotR = 10,
            plotW = width - plotL - plotR,
            dt = Math.max(context?.duration_seconds || 0, 1),
            start = Number($("w-start").value) || 0,
            end = Number($("w-end").value) || 0;
          return {
            plotL,
            plotW,
            dt,
            xStart: plotL + (start * plotW) / dt,
            xEnd: plotL + (end * plotW) / dt,
          };
        };
        canvas.addEventListener("pointerdown", (e) => {
          const g = geometry(),
            x = coords(e),
            d1 = Math.abs(x - g.xStart),
            d2 = Math.abs(x - g.xEnd);
          const lo = Math.min(g.xStart, g.xEnd),
            hi = Math.max(g.xStart, g.xEnd);
          const width = hi - lo;
          if (width <= 32 && x > lo + 4 && x < hi - 4) activeHandle = "move";
          else if (Math.min(d1, d2) <= 12)
            activeHandle = d1 <= d2 ? "start" : "end";
          else if (x > lo + 8 && x < hi - 8) activeHandle = "move";
          else return;
          const startValue = Number($("w-start").value) || 0,
            endValue = Number($("w-end").value) || 0;
          canvas.dataset.moveStart = String(startValue);
          canvas.dataset.moveEnd = String(endValue);
          canvas.dataset.movePointer = String(((x - g.plotL) * g.dt) / g.plotW);
          canvas.setPointerCapture(e.pointerId);
          e.preventDefault();
        });
        canvas.addEventListener("pointermove", (e) => {
          if (!activeHandle) return;
          const g = geometry(),
            x = coords(e),
            value = Math.max(
              0,
              Math.min(g.dt, ((x - g.plotL) * g.dt) / g.plotW),
            );
          const start = $("w-start"),
            end = $("w-end"),
            ss = $("w-start-slider"),
            es = $("w-end-slider");
          if (activeHandle === "start") {
            const v = Math.min(value, Number(end.value) - RANGE_STEP);
            start.value = roundRange(Math.max(0, v)).toFixed(1);
          } else if (activeHandle === "end") {
            const v = Math.max(value, Number(start.value) + RANGE_STEP);
            end.value = roundRange(Math.min(g.dt, v)).toFixed(1);
          } else if (activeHandle === "move") {
            const delta = value - Number(canvas.dataset.movePointer);
            const width =
              Number(canvas.dataset.moveEnd) - Number(canvas.dataset.moveStart);
            const movedStart = roundRange(
              Math.max(
                0,
                Math.min(
                  g.dt - width,
                  Number(canvas.dataset.moveStart) + delta,
                ),
              ),
            );
            start.value = movedStart.toFixed(1);
            end.value = (movedStart + width).toFixed(1);
          }
          renderContext();
        });
        const stop = () => {
          activeHandle = null;
        };
        canvas.addEventListener("pointerup", stop);
        canvas.addEventListener("pointercancel", stop);
      }
    } else {
      canvas.style.cursor = "default";
    }
  }
  function renderContext() {
    const fileSelect = $("w-file-select");
    if (
      fileSelect &&
      context?.file_name &&
      fileSelect.value !== context.file_name
    )
      fileSelect.value = context.file_name;
    $("w-event").textContent = context?.event_counter_text || "—";
    document.querySelector('[data-w-action="prev-event"]').disabled =
      !context?.can_select_previous_event;
    document.querySelector('[data-w-action="next-event"]').disabled =
      !context?.can_select_next_event;
    $("w-status").textContent = context?.ready
      ? "Evento listo"
      : context?.message || "Sin contexto";
    $("w-geo-freq").textContent = context?.geophone_frequency_text || "—";
    $("w-mpu-freq").textContent = context?.mpu_frequency_text || "—";
    if (!context?.ready) return;
    const duration = Math.max(0.001, Number(context.duration_seconds) || 5);
    const endInput = $("w-end"),
      startInput = $("w-start"),
      startSlider = $("w-start-slider"),
      endSlider = $("w-end-slider");
    startInput.max = duration.toFixed(1);
    endInput.max = duration.toFixed(1);
    const key =
      String(context.file_name || "") + ":" + String(context.event_index ?? "");
    if (manualContextKey !== key) {
      manualContextKey = key;
      const saved = manualRanges.get(key);
      startInput.value = saved ? String(saved.start) : "0.0";
      endInput.value = saved ? String(saved.end) : duration.toFixed(1);
    }
    [startSlider, endSlider].filter(Boolean).forEach((el) => {
      el.max = duration.toFixed(1);
    });
    let start = Math.min(Number(startInput.value) || 0, duration);
    let end = Math.min(
      Math.max(start + RANGE_STEP, Number(endInput.value) || duration),
      duration,
    );
    start = roundRange(start);
    end = roundRange(end);
    if (end <= start) start = Math.max(0, end - RANGE_STEP);
    startInput.value = start.toFixed(1);
    endInput.value = end.toFixed(1);
    if (startSlider) startSlider.value = String(start);
    if (endSlider) endSlider.value = String(end);
    if ($("w-start-slider-value"))
      $("w-start-slider-value").textContent = start.toFixed(1) + " s";
    if ($("w-end-slider-value"))
      $("w-end-slider-value").textContent = end.toFixed(1) + " s";
    // Draw only after the selected event's range has been restored and normalized.
    draw(
      $("w-chart-geo"),
      context.geophone_times || [],
      context.geophone_values || [],
      "#2563eb",
      mode === "manual",
    );
    draw(
      $("w-chart-mpu"),
      context.mpu_times || [],
      context.mpu_values || [],
      "#7c3aed",
      mode === "manual",
    );
  }
  function escapeHtml(value) {
    return String(value).replace(
      /[&<>"']/g,
      (ch) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[ch],
    );
  }
  async function saveSelection() {
    const name = $("win-selection-name")?.value?.trim();
    if (!name) {
      if ($("win-version-note"))
        $("win-version-note").textContent = "Escribe un nombre para guardar.";
      return null;
    }
    const btn = document.querySelector('[data-w-action="save-selection"]');
    if (btn) btn.disabled = true;
    try {
      const r = await Bridge.createWindowSelection(name);
      if (!r?.success) {
        if ($("win-version-note"))
          $("win-version-note").textContent = r?.error || "No se pudo guardar.";
        return null;
      }
      if ($("win-version-note"))
        $("win-version-note").textContent =
          "Guardado: " +
          r.selection.name +
          " · ID " +
          r.selection.id.slice(0, 8);
      await refreshSavedSelections();
      return r;
    } finally {
      if (btn) btn.disabled = false;
    }
  }
  window.saveWindowSelectionAndContinue = async function () {
    if (!windows.some((w) => w.selection_status === "include")) {
      if ($("win-version-note"))
        $("win-version-note").textContent = "Incluye al menos una ventana.";
      return;
    }
    const saved = await Bridge.getWindowSelections();
    if (!saved?.active_filename) {
      if ($("win-version-note"))
        $("win-version-note").textContent =
          "Guarda la selección antes de continuar a Etiquetado.";
      return;
    }
    await App.navigateTo("etiquetado");
  };
  function renderRows() {
    const continueBtn = document.getElementById("btn-continue-labeling");
    if (continueBtn)
      continueBtn.disabled = !windows.some(
        (w) => w.selection_status === "include",
      );
    $("w-count").textContent = windows.length + " ventanas";
    $("w-rows").innerHTML = windows.length
      ? windows
          .map((w) => {
            const q = w.quality?.status || "accepted",
              label =
                q === "accepted"
                  ? "Aceptada"
                  : q === "review"
                    ? "Revisión"
                    : "Inválida";
            const eventNumber = Number(w.source_event_id);
            const eventLabel = Number.isInteger(eventNumber)
              ? String(eventNumber + 1).padStart(2, "0")
              : "—";
            return (
              "<tr><td>" +
              w.window_id +
              "</td><td>" +
              escapeHtml(w.source_file || "—") +
              "</td><td>" +
              eventLabel +
              "</td><td>" +
              sec(w.start_us) +
              "</td><td>" +
              sec(w.end_us) +
              "</td><td>" +
              ((w.end_us - w.start_us) / 1e6).toFixed(1) +
              "</td><td>" +
              w.sensors.join(" + ") +
              "</td><td>" +
              w.origin_mode +
              '</td><td><span class="status-pill ' +
              q +
              '">' +
              label +
              '</span></td><td><select class="form-select" data-w-action="selection" data-id="' +
              w.window_id +
              '"><option value="include" ' +
              (w.selection_status === "include" ? "selected" : "") +
              '>Incluir</option><option value="review" ' +
              (w.selection_status === "review" ? "selected" : "") +
              '>Revisar</option><option value="exclude" ' +
              (w.selection_status === "exclude" ? "selected" : "") +
              ">Excluir</option></select></td></tr>"
            );
          })
          .join("")
      : '<tr><td colspan="10" class="text-center">No hay ventanas extraídas.</td></tr>';
  }
  async function loadFileOptions() {
    const select = $("w-file-select");
    if (!select) return;
    const files = await Bridge.getAnalysisFiles();
    select.innerHTML = "";
    (Array.isArray(files) ? files : [])
      .filter((f) => f && f.name)
      .forEach((f) => {
        const option = document.createElement("option");
        option.value = f.name;
        option.textContent = f.name;
        select.appendChild(option);
      });
    if (!select.options.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No hay BIN válidos";
      select.appendChild(option);
    }
    return Array.from(select.options)
      .filter((option) => option.value)
      .map((option) => option.value);
  }
  async function waitForAnalysis() {
    for (let i = 0; i < 40; i++) {
      const state = await Bridge.getAnalysisState();
      if (
        state &&
        !state.loading &&
        (state.has_selection ||
          state.state === "error" ||
          state.state === "unavailable")
      )
        return;
      await new Promise((resolve) => setTimeout(resolve, 150));
    }
  }
  async function refreshSavedSelections() {
    const body = $("w-saved-rows");
    if (!body) return;
    const r = await Bridge.getWindowSelections(),
      items = r?.items || [];
    if (!r?.success) {
      body.innerHTML =
        '<tr><td colspan="4">No se pudieron cargar las selecciones.</td></tr>';
      return;
    }
    body.innerHTML = items.length
      ? items
          .map(
            (x) =>
              "<tr><td>" +
              escapeHtml(x.name) +
              "</td><td><code>" +
              escapeHtml(x.id) +
              "</code></td><td>" +
              x.count +
              '</td><td><button class="btn btn-secondary btn-sm" data-w-action="delete-saved" data-filename="' +
              escapeHtml(x.filename) +
              '">Eliminar</button></td></tr>',
          )
          .join("")
      : '<tr><td colspan="4" class="text-center">No hay selecciones guardadas.</td></tr>';
  }
  async function refresh() {
    const files = await loadFileOptions();
    let state = await Bridge.getAnalysisState();
    // The first visible option is not necessarily loaded in Analysis yet.
    // Bootstrap the engine once when entering Windows without an active event.
    if (files.length && !state?.has_selection && !state?.loading) {
      const preferred = state?.selected_file_name;
      const initialFile = files.includes(preferred) ? preferred : files[0];
      const result = await Bridge.selectAnalysisFile(initialFile);
      if (result?.success) await waitForAnalysis();
      state = await Bridge.getAnalysisState();
    } else if (state?.loading) {
      await waitForAnalysis();
    }
    context = await Bridge.getWindowContext();
    windows = await Bridge.getWindows();
    renderContext();
    renderRows();
    await refreshSavedSelections();
  }
  async function action(e) {
    const b = e.target.closest("[data-w-action]");
    if (!b) return;
    const a = b.dataset.wAction;
    if (a === "mode") {
      setMode(b.dataset.mode);
      renderContext();
    }
    if (a === "refresh") await refresh();
    if (a === "refresh-saved") await refreshSavedSelections();
    if (a === "delete-saved") {
      const filename = b.dataset.filename;
      if (
        !confirm(
          '¿Eliminar la selección guardada "' +
            filename +
            '"? Esta acción no se puede deshacer.',
        )
      )
        return;
      const result = await Bridge.deleteWindowSelection(filename);
      if (!result?.success) {
        alert(result?.error || "No se pudo eliminar la selección.");
        return;
      }
      await refreshSavedSelections();
    }
    if (a === "prev-event" || a === "next-event") {
      const index = Number(context?.event_index);
      if (Number.isInteger(index) && index >= 0) {
        const r = await Bridge.selectAnalysisEvent(
          index + (a === "next-event" ? 1 : -1),
        );
        if (r?.success) await refresh();
        else if (r?.error) alert(r.error);
      }
    }
    if (a === "clear") {
      const r = await Bridge.clearWindows();
      if (r.success) await refresh();
    }
    if (a === "generate") {
      const d = Number($("w-duration").value),
        s = Number($("w-step").value);
      if (!(d > 0 && s > 0) || !sensors(false).length) {
        alert("Verifica duración, paso y sensores.");
        return;
      }
      const r = await Bridge.generateWindows({
        mode: $("w-kind").value,
        duration_seconds: d,
        step_seconds: s,
        sensors: sensors(false),
      });
      if (!r.success) alert(r.error || "No se pudieron generar ventanas.");
      await refresh();
    }
    if (a === "add-manual") {
      const start = Number($("w-start").value),
        end = Number($("w-end").value);
      if (!(end > start) || !sensors(true).length) {
        alert("Verifica el intervalo y selecciona al menos un sensor.");
        return;
      }
      const r = await Bridge.addManualWindow({
        start_seconds: start,
        end_seconds: end,
        sensors: sensors(true),
      });
      if (!r.success) alert(r.error || "No se pudo añadir la ventana.");
      await refresh();
    }
  }
  function syncManualRange(source) {
    const start = $("w-start"),
      end = $("w-end"),
      ss = $("w-start-slider"),
      es = $("w-end-slider");
    if (!ss || !es) return;
    const max = Number(ss.max) || 5;
    if (source === "start-slider") {
      const v = Math.min(Number(ss.value), Number(es.value) - 0.001);
      ss.value = String(Math.max(0, v));
      start.value = Number(ss.value).toFixed(1);
    } else if (source === "end-slider") {
      const v = Math.max(Number(es.value), Number(ss.value) + 0.001);
      es.value = String(Math.min(max, v));
      end.value = Number(es.value).toFixed(1);
    } else if (source === "start") {
      ss.value = String(Math.min(max, Math.max(0, Number(start.value) || 0)));
      if (Number(ss.value) >= Number(es.value)) {
        es.value = String(Math.min(max, Number(ss.value) + 0.001));
        end.value = Number(es.value).toFixed(1);
      }
    } else if (source === "end") {
      es.value = String(
        Math.min(
          max,
          Math.max(Number(ss.value) + 0.001, Number(end.value) || 0),
        ),
      );
    }
    $("w-start-slider-value").textContent = Number(ss.value).toFixed(1) + " s";
    $("w-end-slider-value").textContent = Number(es.value).toFixed(1) + " s";
    if (source === "end-slider" || source === "end")
      end.value = Number(es.value).toFixed(1);
    if (source === "start-slider" || source === "start")
      start.value = Number(ss.value).toFixed(1);
  }
  const updateManualField = (e) => {
    if (!context?.ready || mode !== "manual") return;
    const duration = Math.max(0, Number(context.duration_seconds) || 0);
    const start = $("w-start"),
      end = $("w-end");
    start.max = duration.toFixed(1);
    end.max = duration.toFixed(1);
    let value = Number(e.target.value);
    if (e.target.value.trim() === "" || !Number.isFinite(value)) return;
    value = roundRange(Math.max(0, Math.min(duration, value)));
    const startValue = Number(start.value) || 0,
      endValue = Number(end.value) || duration;
    if (e.target === start) {
      value = Math.min(value, Math.max(0, endValue - RANGE_STEP));
      start.value = value.toFixed(1);
    } else {
      value = Math.max(value, startValue + RANGE_STEP);
      value = Math.min(duration, value);
      end.value = roundRange(value).toFixed(1);
    }
    // Keep a separate manual interval for each file/event.
    const key =
      String(context.file_name || "") + ":" + String(context.event_index ?? "");
    manualRanges.set(key, {
      start: Number(start.value),
      end: Number(end.value),
    });
    // Draw directly from the current fields; do not depend on a context refresh.
    const geo = $("w-chart-geo"),
      mpu = $("w-chart-mpu");
    draw(
      geo,
      context.geophone_times || [],
      context.geophone_values || [],
      "#2563eb",
      true,
    );
    draw(
      mpu,
      context.mpu_times || [],
      context.mpu_values || [],
      "#7c3aed",
      true,
    );
    if ($("w-start-slider")) $("w-start-slider").value = start.value;
    if ($("w-end-slider")) $("w-end-slider").value = end.value;
    if ($("w-start-slider-value"))
      $("w-start-slider-value").textContent = start.value + " s";
    if ($("w-end-slider-value"))
      $("w-end-slider-value").textContent = end.value + " s";
  };
  // The Windows view is injected dynamically, so bind through document delegation.
  ["input", "change", "keyup"].forEach((type) =>
    document.addEventListener(type, (e) => {
      if (e.target?.id === "w-start" || e.target?.id === "w-end")
        updateManualField(e);
    }),
  );
  document.addEventListener("click", (e) => {
    const save = e.target.closest('[data-w-action="save-selection"]');
    if (save) {
      saveSelection();
      return;
    }
    action(e);
  });
  document.addEventListener("change", async (e) => {
    if (e.target.id === "w-file-select") {
      if (!e.target.value) return;
      const result = await Bridge.selectAnalysisFile(e.target.value);
      if (!result?.success) {
        alert(result?.error || "No se pudo seleccionar el archivo.");
        return;
      }
      context = { ready: false, message: "Cargando archivo BIN…" };
      renderContext();
      await waitForAnalysis();
      await refresh();
      return;
    }
    const el = e.target.closest('[data-w-action="selection"]');
    if (!el) return;
    await Bridge.setWindowSelection(el.dataset.id, el.value);
    await refresh();
  });
  window.addEventListener("resize", () => {
    if (context?.ready) renderContext();
  });
  window.initWindows = async function () {
    const reset = await Bridge.beginWindowSession();
    if (!reset?.success) {
      alert(reset?.error || "No se pudo reiniciar la sesión de ventanas.");
      return;
    }
    windows = [];
    await refresh();
  };
  setMode("fixed");
})();
