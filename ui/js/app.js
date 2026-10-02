/**
 * App module: Navigation, view loading, and UI event handling.
 * Uses data-action attributes for all interactive elements (no CSS class queries).
 */

const App = (() => {
  "use strict";

  // View titles and subtitles
  const VIEW_META = {
    proyecto: {
      title: "Proyecto",
      subtitle: "Selecciona una carpeta de datos",
    },
    datos: { title: "Datos", subtitle: "Archivos BIN y métricas de calidad" },
    analisis: {
      title: "Análisis",
      subtitle: "Visualizador de señales sísmicas",
    },
    etiquetado: {
      title: "Etiquetado",
      subtitle: "Revisión y clasificación de ventanas de señal",
    },
    ventanas: { title: "Ventanas", subtitle: "Configuración de ventanas" },
    dataset: { title: "Dataset", subtitle: "Preparación de dataset" },
    modelos: { title: "Modelos", subtitle: "Entrenamiento de modelo" },
    exportar: { title: "Exportar", subtitle: "Exportar resultados" },
    ajustes: { title: "Ajustes", subtitle: "Configuración de la aplicación" },
  };

  // Current state
  let currentView = "proyecto";
  let projectState = null;
  let dataState = null;
  let analysisState = null;

  /**
   * Initialize the application
   */
  async function init() {
    console.log("[App] Initializing...");

    // Setup navigation
    setupNavigation();

    // Setup global event delegation
    setupEventDelegation();
    setupLayoutInspector();

    // Re-renderizar canvas al cambiar tamaño (normal/maximizada)
    window.addEventListener("resize", () => {
      if (currentView === "analisis" && analysisState) {
        const container = document.getElementById("view-container");
        if (container) renderAnalysisState(container, analysisState);
      }
    });

    // Load initial view
    await navigateTo("proyecto");

    // Load initial project state
    await refreshProjectState();

    console.log("[App] Initialized");
  }

  /**
   * Setup navigation click handlers
   */
  function setupNavigation() {
    const navItems = document.querySelectorAll('[data-action="navigate"]');
    navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const view = item.getAttribute("data-view");
        if (view) navigateTo(view);
      });
    });
  }

  /**
   * Setup global event delegation for data-action elements
   */
  function setupEventDelegation() {
    document.addEventListener("click", handleAction);
    document.addEventListener("change", handleChange);
    document.addEventListener("input", handleInput);
  }

  /**
   * Handle click events on data-action elements
   */
  async function handleAction(e) {
    const target = e.target.closest("[data-action]");
    if (!target) return;

    const action = target.getAttribute("data-action");
    const view = target.getAttribute("data-view");

    // Navigation
    if (action === "navigate" && view) {
      e.preventDefault();
      await navigateTo(view);
      return;
    }

    // Project actions
    if (action === "select-folder") {
      await selectFolder();
      return;
    }

    if (action === "rescan") {
      await rescanProject();
      return;
    }

    // Data actions
    if (action === "select-file") {
      const fileName = target.getAttribute("data-file");
      if (fileName) await selectFile(fileName);
      return;
    }

    if (action === "footer-analyze") {
      const fileName = target.getAttribute("data-file");
      if (fileName) await analyzeFile(fileName);
      return;
    }

    if (action === "footer-windows") {
      await navigateTo("ventanas");
      return;
    }

    if (action === "footer-continue-labeling") {
      if (window.saveWindowSelectionAndContinue)
        await window.saveWindowSelectionAndContinue();
      return;
    }

    if (action === "footer-continue-dataset") {
      await navigateTo("dataset");
      return;
    }

    if (action === "footer-continue-models") {
      await navigateTo("modelos");
      return;
    }

    if (action === "footer-continue-exportar") {
      await navigateTo("exportar");
      return;
    }

    if (action === "analyze-file") {
      const fileName = target.getAttribute("data-file");
      if (fileName) await analyzeFile(fileName);
      return;
    }

    // Analysis actions
    if (action === "select-analysis-file") {
      const fileName = target.getAttribute("data-file");
      if (fileName) await selectAnalysisFile(fileName);
      return;
    }

    if (action === "prev-event") {
      await previousEvent();
      return;
    }

    if (action === "next-event") {
      await nextEvent();
      return;
    }

    if (action === "select-submenu") {
      const submenu = target.getAttribute("data-submenu");
      if (submenu) await selectSubmenu(submenu);
      return;
    }

    if (action === "set-sensor") {
      const sensor = target.getAttribute("data-sensor");
      if (sensor) await setMetricSensor(sensor);
      return;
    }

    if (action === "reset-viewport") {
      await resetViewport();
      return;
    }

    if (action === "clear-cursor") {
      await clearCursor();
      return;
    }
  }

  /**
   * Handle change events on form elements
   */
  async function handleChange(e) {
    const target = e.target.closest("[data-action]");
    if (!target) return;

    const action = target.getAttribute("data-action");

    if (action === "select-analysis-file") {
      const fileName = target.value;
      if (fileName) await selectAnalysisFile(fileName);
      return;
    }

    if (action === "set-stalta-param") {
      const param = target.getAttribute("data-param");
      const rawValue = parseFloat(target.value);
      if (param && !isNaN(rawValue)) {
        const value = Math.round(rawValue * 10) / 10;
        target.value = value.toFixed(1);
        await setStaltaParameter(param, value);
      }
      return;
    }

    if (action === "set-spectrum-window") {
      await setSpectrumWindow(target.value);
      return;
    }

    if (action === "set-spectrum-range") {
      await setSpectrumRange(parseFloat(target.value));
      return;
    }

    if (action === "set-spectrogram-window") {
      await setSpectrogramWindow(target.value);
      return;
    }

    if (action === "set-spectrogram-duration") {
      await setSpectrogramDuration(parseFloat(target.value));
      return;
    }

    if (action === "set-spectrogram-overlap") {
      await setSpectrogramOverlap(parseFloat(target.value));
      return;
    }

    if (action === "set-spectrogram-range") {
      await setSpectrogramRange(parseFloat(target.value));
      return;
    }

    if (action === "set-stalta-method") {
      await setStaltaMethod(target.value);
      return;
    }
  }

  /**
   * Handle input events (sliders, etc.)
   */
  async function handleInput(e) {
    const target = e.target.closest("[data-action]");
    if (!target) return;

    const action = target.getAttribute("data-action");

    if (action === "cursor-time") {
      const time = parseFloat(target.value);
      if (!isNaN(time)) {
        await setCursorTime(time);
      }
      return;
    }
  }

  /**
   * Navigate to a view
   */
  async function navigateTo(viewName) {
    console.log(`[App] Navigating to: ${viewName}`);

    // Update nav active state
    document.querySelectorAll(".nav-item").forEach((item) => {
      item.classList.toggle(
        "active",
        item.getAttribute("data-view") === viewName,
      );
    });

    // Update topbar
    const meta = VIEW_META[viewName] || { title: viewName, subtitle: "" };
    const titleEl = document.getElementById("topbar-title");
    const subtitleEl = document.getElementById("topbar-subtitle");
    if (titleEl) titleEl.textContent = meta.title;
    const topbarIcon = document.querySelector(".topbar-heading-icon");
    const iconPaths = {
      proyecto:
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
      datos:
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
      analisis: '<polyline points="2 12 5 12 8 4 12 20 16 4 19 12 22 12"/>',
      ventanas:
        '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
      etiquetado:
        '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7.5" cy="7.5" r="1"/>',
      dataset:
        '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
      modelos:
        '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
      exportar:
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
      ajustes:
        '<circle cx="12" cy="12" r="3"/><path d="M19 13.5a7.8 7.8 0 0 0 0-3l2-1.2-2-3.4-2.2 1a7.8 7.8 0 0 0-2.6-1.5L14 3h-4l-.3 2.4A7.8 7.8 0 0 0 7 7L4.8 6l-2 3.4 2 1.2a7.8 7.8 0 0 0 0 3l-2 1.2 2 3.4 2.2-1a7.8 7.8 0 0 0 2.6 1.5L10 21h4l.3-2.4a7.8 7.8 0 0 0 2.2-1.1l2.2 1 2-3.4z"/>',
    };
    if (topbarIcon)
      topbarIcon.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        (iconPaths[viewName] || iconPaths.proyecto) +
        "</svg>";
    if (subtitleEl) subtitleEl.textContent = meta.subtitle;

    // Show/hide rescan button
    const rescanBtn = document.getElementById("btn-rescan");
    if (rescanBtn) {
      rescanBtn.style.display =
        viewName === "proyecto" ? "inline-flex" : "none";
    }

    // Load view content
    const container = document.getElementById("view-container");
    if (!container) return;

    currentView = viewName;
    const datasetFooter = document.getElementById("ds-footer-controls");
    if (datasetFooter) datasetFooter.hidden = viewName !== "dataset";
    const labelFooter = document.getElementById("label-batch-footer");
    if (labelFooter) labelFooter.hidden = viewName !== "etiquetado";
    const windowsFooter = document.getElementById("win-footer-controls");
    if (windowsFooter) windowsFooter.hidden = viewName !== "ventanas";
    const continueLabelingBtn = document.getElementById(
      "btn-continue-labeling",
    );
    if (continueLabelingBtn)
      continueLabelingBtn.hidden = viewName !== "ventanas";
    const continueDatasetBtn = document.getElementById("btn-continue-dataset");
    if (continueDatasetBtn)
      continueDatasetBtn.hidden = viewName !== "etiquetado";
    const footerAnalysis = document.getElementById("btn-footer-analysis");
    const footerWindows = document.getElementById("btn-footer-windows");
    if (footerAnalysis) footerAnalysis.hidden = viewName !== "datos";
    if (footerWindows) footerWindows.hidden = viewName !== "analisis";

    // Load view HTML
    try {
      const response = await fetch(`views/${viewName}.html`);
      if (response.ok) {
        const html = await response.text();
        container.innerHTML = html;

        // Initialize view-specific content
        await initView(viewName);
        updateLayoutInspector();
      } else {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <div class="empty-state-title">Vista no encontrada</div>
            <div class="empty-state-text">La vista "${viewName}" no está disponible</div>
          </div>
        `;
      }
    } catch (err) {
      console.error(`[App] Error loading view ${viewName}:`, err);
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">❌</div>
          <div class="empty-state-title">Error al cargar</div>
          <div class="empty-state-text">${err.message}</div>
        </div>
      `;
    }
  }

  const LAYOUT_REGIONS = [
    ".project-data-card",
    ".project-summary-card",
    ".datos-panel",
    ".datos-detail",
    "#analysis-content",
    "#analysis-content > .analysis-header",
    "#analysis-content .analysis-visual-panel",
    "#analysis-content .analysis-tabs",
    "#analysis-content .submenu-content",
    "#analysis-content .analysis-chart-card",
    "#analysis-content .analysis-sidebar",
    "#analysis-content .analysis-sidebar > .analysis-info-card",
    ".windows-config",
    ".windows-charts",
    ".windows-extracted-region",
    ".windows-saved-region",
    ".label-toolbar",
    ".label-layout",
    ".label-list-panel",
    ".label-signal-panel",
    ".label-editor",
    ".label-footer",
    ".label-batches-panel",
    ".dataset-view > .ds-section:nth-child(1)",
    ".dataset-view > .ds-section:nth-child(2)",
    ".dataset-view > .ds-section:nth-child(3)",
    ".dataset-view > .ds-section:nth-child(4)",
    ".export-card-model",
    ".export-card-config",
    ".export-card-calibration",
    ".export-card-advanced",
    ".export-card-execution",
    ".export-card-results",
    ".export-history",
    ".models-config-grid",
    ".models-execution",
    ".models-library",
  ];
  const LAYOUT_CONTENT = [
    "button",
    "input",
    "select",
    "textarea",
    "canvas",
    "table",
    ".card-header",
    ".card-body",
    ".panel-heading",
    ".form-group",
    ".summary-card",
    ".analysis-chart-card",
    ".label-chart-wrap",
  ].join(", ");
  const GLOBAL_LAYOUT_REGIONS = [
    ".sidebar",
    ".sidebar-header",
    ".sidebar-nav",
    ".nav-item",
    ".main-content",
    ".topbar",
    ".topbar-heading",
    ".topbar-status",
    ".view-container",
  ];
  const VIEW_STYLE_SOURCES = {
    proyecto: "ui/css/proyecto.css",
    datos: "ui/css/datos.css",
    analisis: "ui/css/analisis.css",
    ventanas: "ui/css/ventanas.css",
    etiquetado: "ui/css/etiquetado.css",
    dataset: "ui/css/dataset.css",
    modelos: "ui/css/modelos.css",
    exportar: "ui/css/exportar.css",
    ajustes: "ui/css/ajustes.css",
  };

  function setupLayoutInspector() {
    document.addEventListener("keydown", (event) => {
      if (event.key !== "F7") return;
      event.preventDefault();
      document.body.classList.toggle("layout-inspector-active");
      updateLayoutInspector();
    });
  }

  function updateLayoutInspector() {
    document.querySelectorAll("[data-layout-ref]").forEach((element) => {
      element.removeAttribute("data-layout-ref");
    });
    document.querySelectorAll("[data-layout-label]").forEach((element) => {
      element.removeAttribute("data-layout-label");
      element.removeAttribute("data-layout-inspector-content");
      if (element.hasAttribute("data-layout-inspector-title")) {
        const originalTitle = element.getAttribute(
          "data-layout-inspector-title",
        );
        if (originalTitle) {
          element.setAttribute("title", originalTitle);
        } else {
          element.removeAttribute("title");
        }
        element.removeAttribute("data-layout-inspector-title");
      }
    });

    const activeView = document.querySelector(".workspace-view");
    if (activeView) {
      LAYOUT_REGIONS.forEach((selector) => {
        activeView.querySelectorAll(selector).forEach((element) => {
          setLayoutLabel(element, selector, false, true);
        });
      });

      activeView.querySelectorAll(LAYOUT_CONTENT).forEach((element) => {
        setLayoutLabel(element, getElementSelector(element), true, false);
      });
    }

    GLOBAL_LAYOUT_REGIONS.forEach((selector) => {
      document.querySelectorAll(selector).forEach((element) => {
        setLayoutLabel(element, selector, false, false);
      });
    });

    document.querySelectorAll(LAYOUT_CONTENT).forEach((element) => {
      if (!activeView || !activeView.contains(element)) {
        setLayoutLabel(element, getElementSelector(element), true, false);
      }
    });

    document
      .querySelectorAll(".workspace-inline-actions *")
      .forEach((element) => {
        setLayoutLabel(element, getElementSelector(element), true, false);
      });

    renderLayoutInspectorPanel(activeView);
  }

  function renderLayoutInspectorPanel(activeView) {
    const existingPanel = document.getElementById("layout-inspector-panel");
    if (existingPanel) existingPanel.remove();
    if (!document.body.classList.contains("layout-inspector-active")) return;

    const panel = document.createElement("aside");
    panel.id = "layout-inspector-panel";
    panel.className = "layout-inspector-panel";
    panel.setAttribute("aria-label", "Capas del layout");

    const heading = document.createElement("div");
    heading.className = "layout-inspector-panel-heading";
    heading.innerHTML = `<strong>Capas: ${currentView || "vista activa"}</strong>`;

    const close = document.createElement("button");
    close.type = "button";
    close.className = "layout-inspector-panel-close";
    close.textContent = "Cerrar";
    close.addEventListener("click", () => {
      document.body.classList.remove("layout-inspector-active");
      updateLayoutInspector();
    });
    heading.appendChild(close);
    panel.appendChild(heading);
    enableLayoutInspectorDragging(panel, heading);

    const help = document.createElement("p");
    help.className = "layout-inspector-panel-help";
    help.textContent =
      "Selecciona una capa para localizarla. Los contenedores aparecen antes que su contenido.";
    panel.appendChild(help);

    const list = document.createElement("div");
    list.className = "layout-inspector-panel-list";
    const elements = activeView
      ? Array.from(activeView.querySelectorAll("[data-layout-label]"))
      : [];

    elements.forEach((element, index) => {
      element.setAttribute("data-layout-inspector-index", String(index));
      const item = document.createElement("button");
      item.type = "button";
      item.className = "layout-inspector-item";
      item.dataset.targetIndex = String(index);

      const selector = document.createElement("strong");
      selector.textContent = getElementSelector(element);
      const details = document.createElement("span");
      details.textContent = element.getAttribute("data-layout-label") || "";
      item.append(selector, details);
      item.addEventListener("click", () => {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        element.setAttribute("data-layout-inspector-focus", "true");
        window.setTimeout(
          () => element.removeAttribute("data-layout-inspector-focus"),
          1200,
        );
      });
      list.appendChild(item);
    });

    panel.appendChild(list);
    document.body.appendChild(panel);
  }

  function enableLayoutInspectorDragging(panel, handle) {
    let dragging = false;
    let offsetX = 0;
    let offsetY = 0;

    handle.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button")) return;

      const rect = panel.getBoundingClientRect();
      dragging = true;
      offsetX = event.clientX - rect.left;
      offsetY = event.clientY - rect.top;
      panel.style.left = `${rect.left}px`;
      panel.style.top = `${rect.top}px`;
      panel.style.right = "auto";
      handle.setPointerCapture(event.pointerId);
      panel.classList.add("is-dragging");
    });

    handle.addEventListener("pointermove", (event) => {
      if (!dragging) return;

      const maxLeft = Math.max(0, window.innerWidth - panel.offsetWidth);
      const maxTop = Math.max(0, window.innerHeight - panel.offsetHeight);
      const left = Math.min(
        maxLeft,
        Math.max(0, event.clientX - offsetX),
      );
      const top = Math.min(maxTop, Math.max(0, event.clientY - offsetY));
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
    });

    const stopDragging = (event) => {
      if (!dragging) return;
      dragging = false;
      if (handle.hasPointerCapture(event.pointerId)) {
        handle.releasePointerCapture(event.pointerId);
      }
      panel.classList.remove("is-dragging");
    };

    handle.addEventListener("pointerup", stopDragging);
    handle.addEventListener("pointercancel", stopDragging);
  }

  function setLayoutLabel(
    element,
    selector,
    isContent = false,
    isWorkspaceRegion = false,
  ) {
    const styles = getComputedStyle(element);
    const coordinates = ["--x", "--y", "--w", "--h"]
      .map((property) => styles.getPropertyValue(property).trim() || "auto")
      .join(" | ");
    const viewSource = currentView || "vista-activa";
    const styleSelector = isWorkspaceRegion
      ? selector
      : getDimensionSelector(element);
    const cssSource = getStyleSource(viewSource, styleSelector);
    const reference = isWorkspaceRegion
      ? `${cssSource} | ${styleSelector} | X/Y/W/H: ${coordinates}`
      : `${cssSource} | ${styleSelector} | X/Y: --layout-x/--layout-y | W/H: width/height`;
    const rect = element.getBoundingClientRect();
    const elementCoordinates = `X:${Math.round(rect.x)} Y:${Math.round(rect.y)} W:${Math.round(rect.width)} H:${Math.round(rect.height)}`;
    const label = isWorkspaceRegion
      ? reference
      : `HTML: ui/views/${viewSource}.html | CSS: ${cssSource} | ${styleSelector} | Posición real ${elementCoordinates} | Coordenadas CSS: --x/--y | Ajuste: --layout-x/--layout-y | Tamaño: width/height`;
    element.setAttribute("data-layout-ref", selector);
    if (!document.body.classList.contains("layout-inspector-active")) return;
    if (!element.hasAttribute("data-layout-inspector-title")) {
      element.setAttribute(
        "data-layout-inspector-title",
        element.getAttribute("title") || "",
      );
    }
    element.setAttribute("data-layout-label", label);
    element.setAttribute("title", label);
    if (isContent)
      element.setAttribute("data-layout-inspector-content", "true");
  }

  function getElementSelector(element) {
    if (element.id) return `#${element.id}`;
    if (element.classList.length > 0) {
      return `.${Array.from(element.classList).join(".")}`;
    }
    return element.tagName.toLowerCase();
  }

  function getDimensionSelector(element) {
    if (element.id) return `#${element.id}`;
    if (element.classList.length > 0) {
      const genericClasses = new Set([
        "btn",
        "btn-primary",
        "btn-secondary",
        "btn-sm",
        "form-control",
        "form-input",
        "form-select",
      ]);
      const specificClass = Array.from(element.classList).find(
        (className) => !genericClasses.has(className),
      );
      if (specificClass) return `.${specificClass}`;
      return `.${element.classList.item(0)}`;
    }
    return element.tagName.toLowerCase();
  }

  function getStyleSource(viewName, selector) {
    const sources = [
      VIEW_STYLE_SOURCES[viewName],
      "ui/css/workspace.css",
      "ui/css/layout.css",
      "ui/css/components.css",
      "ui/css/variables.css",
    ].filter(Boolean);

    return (
      sources.find((source) => stylesheetContainsSelector(source, selector)) ||
      VIEW_STYLE_SOURCES[viewName] ||
      "ui/css/components.css"
    );
  }

  function stylesheetContainsSelector(source, selector) {
    const stylesheets = Array.from(document.styleSheets);
    const stylesheet = stylesheets.find((item) =>
      item.href ? new URL(item.href).pathname.endsWith(source) : false,
    );
    if (!stylesheet) return false;

    try {
      return Array.from(stylesheet.cssRules || []).some((rule) => {
        if (!rule.selectorText) return false;
        return rule.selectorText
          .split(",")
          .some((candidate) => candidate.trim() === selector);
      });
    } catch (error) {
      console.warn(`[Layout Inspector] Cannot read ${source}:`, error);
      return false;
    }
  }

  /**
   * Initialize view-specific content
   */
  async function initView(viewName) {
    switch (viewName) {
      case "proyecto":
        await refreshProjectState();
        break;
      case "datos":
        await refreshDataState();
        break;
      case "analisis":
        await refreshAnalysisState();
        break;
      case "ventanas":
        if (window.initWindows) await window.initWindows();
        break;
      case "etiquetado":
        if (window.initLabeling) await window.initLabeling();
        break;
      case "dataset":
        if (window.initDataset) await window.initDataset();
        break;
      case "modelos":
        if (window.initModels) await window.initModels();
        break;
      case "exportar":
        if (window.initExportar) await window.initExportar();
        break;
      case "ajustes":
        if (window.initSettings) await window.initSettings();
        break;
      default:
        // Placeholder views
        break;
    }
  }

  // ===================================================================
  // Project actions
  // ===================================================================

  async function selectFolder() {
    console.log("[App] Selecting folder...");
    const result = await Bridge.selectDataFolder();
    if (result.error) {
      alert("Error: " + result.error);
      return;
    }
    if (result.status === "ok") {
      await refreshProjectState();
    }
  }

  async function rescanProject() {
    console.log("[App] Rescanning project...");
    const result = await Bridge.rescanProject();
    if (result.error) {
      alert("Error: " + result.error);
      return;
    }
    await refreshProjectState();
  }

  async function refreshProjectState() {
    const state = await Bridge.getProjectState();
    projectState = state;

    const container = document.getElementById("view-container");
    if (!container) return;

    // Update project view if visible
    if (currentView === "proyecto") {
      renderProjectState(container, state);
    }
  }

  function renderProjectState(container, state) {
    const folderPath = state.folder_path || "Selecciona una carpeta...";
    const fileCount = state.file_count || "0";
    const eventCount = state.event_count || "0";
    const availableText = state.available_text || "Sin carpeta seleccionada";
    const lastScan = state.last_scan_text || "—";

    // Update folder path
    const folderPathEl = document.getElementById("project-folder-path");
    if (folderPathEl) folderPathEl.textContent = folderPath;

    // Update status text
    const statusTextEl = document.getElementById("project-status-text");
    if (statusTextEl) statusTextEl.textContent = availableText;

    // Update file count text
    const fileCountTextEl = document.getElementById("project-file-count-text");
    if (fileCountTextEl)
      fileCountTextEl.textContent = `${fileCount} archivos BIN detectados`;

    // Update last scan
    const lastScanEl = document.getElementById("project-last-scan");
    if (lastScanEl)
      lastScanEl.textContent = `Última actualización: ${lastScan}`;

    // Update summary cards
    const summaryFileCountEl = document.getElementById("summary-file-count");
    if (summaryFileCountEl) summaryFileCountEl.textContent = fileCount;

    const summaryEventCountEl = document.getElementById("summary-event-count");
    if (summaryEventCountEl) summaryEventCountEl.textContent = eventCount;
  }

  // ===================================================================
  // Data actions
  // ===================================================================

  async function refreshDataState() {
    const state = await Bridge.getDataState();
    const files = await Bridge.scanFiles();
    state.files = files;
    dataState = state;

    const container = document.getElementById("view-container");
    if (!container) return;

    if (currentView === "datos") {
      renderDataState(container, state);
    }
  }

  function renderDataState(container, state) {
    const files = state.files || [];
    const selectedFile = state.selected_file_name || "";
    const footerAnalyze = document.getElementById("btn-footer-analysis");
    if (footerAnalyze) {
      footerAnalyze.disabled = !selectedFile;
      footerAnalyze.dataset.action = "footer-analyze";
      footerAnalyze.dataset.file = selectedFile;
    }

    // Update file count
    const fileCountEl = document.getElementById("data-file-count");
    if (fileCountEl) fileCountEl.textContent = files.length;

    // Update selected count
    const selectedCountEl = document.getElementById("data-selected-count");
    if (selectedCountEl) {
      const count = selectedFile ? 1 : 0;
      selectedCountEl.textContent = `${count} archivo${count !== 1 ? "s" : ""} seleccionado${count !== 1 ? "s" : ""}`;
    }

    // Render table rows
    const tbody = document.getElementById("data-files-tbody");
    if (tbody) {
      if (files.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="text-center">
              <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <div class="empty-state-title">Sin archivos</div>
                <div class="empty-state-text">Selecciona una carpeta de datos en Proyecto</div>
              </div>
            </td>
          </tr>
        `;
      } else {
        tbody.innerHTML = files
          .map(
            (f) => `
          <tr class="${f.name === selectedFile ? "selected" : ""}" data-action="select-file" data-file="${f.name}" style="cursor: pointer;">
            <td><input type="checkbox" class="file-checkbox" data-file="${f.name}" ${f.name === selectedFile ? "checked" : ""} onclick="event.stopPropagation()"></td>
            <td>${f.name}</td>
            <td>${f.capture_date_text || "—"}</td>
            <td>${f.event_count_text || "—"}</td>
            <td>${f.duration_text || "—"}</td>
            <td>${f.size_text || "—"}</td>
            <td><span class="badge badge-${f.status_code}">${f.status_text}</span></td>
          </tr>
        `,
          )
          .join("");
      }
    }

    // Render detail panel if a file is selected
    if (selectedFile) {
      renderFileDetail(selectedFile, files);
    }
  }

  function renderFileDetail(fileName, files) {
    const file = files.find((f) => f.name === fileName);
    if (!file) return;

    const detailContent = document.getElementById("data-detail-content");
    if (!detailContent) return;

    detailContent.innerHTML = `
      <!-- Sección 1: Detalle del archivo -->
      <div class="detail-section">
        <div class="detail-section-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Detalle del archivo
        </div>
        <div class="mb-sm">
          <div class="d-flex justify-content-between align-items-center mb-sm">
            <h3 class="text-primary" style="font-size: var(--font-size-base);">${file.name}</h3>
            <span class="badge badge-${file.status_code}">${file.status_text}</span>
          </div>
          <p class="text-muted" style="font-size: var(--font-size-xs); word-break: break-all;">${file.path}</p>
        </div>
        <table class="table">
          <tbody>
            <tr><td class="text-muted">Versión del formato:</td><td>${file.format_version_text || "—"}</td></tr>
            <tr><td class="text-muted">Fecha de captura:</td><td>${file.capture_date_text || "—"}</td></tr>
            <tr><td class="text-muted">Tamaño de archivo:</td><td>${file.size_detail_text || file.size_text || "—"}</td></tr>
            <tr><td class="text-muted">Número de eventos:</td><td>${file.event_count_text || "—"}</td></tr>
            <tr><td class="text-muted">Duración total:</td><td>${file.duration_text || "—"}</td></tr>
            <tr><td class="text-muted">Frecuencia GEO:</td><td>${file.geophone_frequency_text || "—"}</td></tr>
            <tr><td class="text-muted">Frecuencia MPU:</td><td>${file.mpu_frequency_text || "—"}</td></tr>
            <tr><td class="text-muted">Hash (SHA256):</td><td style="font-size: var(--font-size-xs); word-break: break-all;">${file.sha256_text || "—"}</td></tr>
            <tr><td class="text-muted">Última modificación:</td><td>${file.modified_text || "—"}</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Sección 2: Eventos del archivo -->
      <div class="detail-events-section">
        <div class="detail-section-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6"/>
            <line x1="8" y1="12" x2="21" y2="12"/>
            <line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/>
            <line x1="3" y1="12" x2="3.01" y2="12"/>
            <line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
          Eventos del archivo (${file.event_count_text || 0})
        </div>
        <div class="table-container scrollable">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Inicio (s)</th>
                <th>Duración</th>
                <th>GEO (Hz)</th>
                <th>MPU (Hz)</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody id="detail-events-tbody">
              <tr><td colspan="6" class="text-center text-muted">Cargando eventos...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

    `;

    // Load events for this file
    loadFileEvents(fileName);
  }

  async function loadFileEvents(fileName) {
    const tbody = document.getElementById("detail-events-tbody");
    if (!tbody) return;

    const events = await Bridge.getFileEvents(fileName);
    if (events.length === 0 || events[0].error) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="text-center text-muted">No hay eventos</td></tr>';
      return;
    }

    tbody.innerHTML = events
      .map(
        (e) => `
      <tr>
        <td>${e.number}</td>
        <td>${e.start_text}</td>
        <td>${e.duration_text}</td>
        <td>${e.geophone_hz_text}</td>
        <td>${e.mpu_hz_text}</td>
        <td><span class="badge badge-${e.status_code}">${e.status_text}</span></td>
      </tr>
    `,
      )
      .join("");
  }

  async function selectFile(fileName) {
    console.log(`[App] Selecting file: ${fileName}`);
    const result = await Bridge.selectFile(fileName);
    if (result.error) {
      alert("Error: " + result.error);
      return;
    }
    await refreshDataState();
  }

  async function analyzeFile(fileName) {
    console.log(`[App] Analyzing file: ${fileName}`);
    await selectAnalysisFile(fileName);
    await navigateTo("analisis");
  }

  // ===================================================================
  // Analysis actions
  // ===================================================================

  async function refreshAnalysisState() {
    const state = await Bridge.getAnalysisState();
    const files = await Bridge.getAnalysisFiles();
    state.files = files;
    analysisState = state;

    const container = document.getElementById("view-container");
    if (!container) return;

    if (currentView === "analisis") {
      renderAnalysisState(container, state);
    }
  }

  function renderAnalysisState(container, state) {
    const files = state.files || [];
    const selectedFile = state.selected_file_name || "";
    const eventCounter = state.event_counter_text || "— / —";

    const isEmpty = state.state === "empty" || state.state === "unavailable";

    // Show/hide empty state vs content
    const emptyEl = document.getElementById("analysis-empty");
    const contentEl = document.getElementById("analysis-content");
    if (emptyEl) emptyEl.style.display = isEmpty ? "flex" : "none";
    if (contentEl) contentEl.style.display = isEmpty ? "none" : "grid";

    if (isEmpty) return;

    // Update file selector
    const fileSelect = document.getElementById("analysis-file-select");
    if (fileSelect) {
      const currentValue = fileSelect.value;
      fileSelect.innerHTML =
        '<option value="">-- Seleccionar --</option>' +
        files
          .map(
            (f) =>
              `<option value="${f.name}" ${f.name === selectedFile ? "selected" : ""}>${f.name}</option>`,
          )
          .join("");
      if (currentValue && files.some((f) => f.name === currentValue)) {
        fileSelect.value = currentValue;
      }
    }

    // Update event counter
    const eventCounterEl = document.getElementById("analysis-event-counter");
    if (eventCounterEl) eventCounterEl.textContent = eventCounter;

    // Update time info
    const startTimeEl = document.getElementById("analysis-start-time");
    const endTimeEl = document.getElementById("analysis-end-time");
    const durationEl = document.getElementById("analysis-duration");
    if (startTimeEl)
      startTimeEl.textContent = state.event_start_text || "0.000 s";
    if (endTimeEl) endTimeEl.textContent = state.event_end_text || "0.000 s";
    if (durationEl)
      durationEl.textContent = state.event_duration_text || "0.000 s";

    // Update sidebar info
    const infoFileName = document.getElementById("info-file-name");
    const infoEventCounter = document.getElementById("info-event-counter");
    const infoStartTime = document.getElementById("info-start-time");
    const infoEndTime = document.getElementById("info-end-time");
    const infoDuration = document.getElementById("info-duration");
    const infoSampleCount = document.getElementById("info-sample-count");
    const infoGeoFreq = document.getElementById("info-geo-freq");
    const infoMpuFreq = document.getElementById("info-mpu-freq");

    if (infoFileName)
      infoFileName.textContent = state.selected_file_name || "—";
    if (infoEventCounter) infoEventCounter.textContent = eventCounter;
    if (infoStartTime)
      infoStartTime.textContent = state.event_start_text || "—";
    if (infoEndTime) infoEndTime.textContent = state.event_end_text || "—";
    if (infoDuration)
      infoDuration.textContent = state.event_duration_text || "—";
    if (infoSampleCount)
      infoSampleCount.textContent = state.event_sample_count_text || "—";
    if (infoGeoFreq)
      infoGeoFreq.textContent = state.geophone_frequency_text || "—";
    if (infoMpuFreq) infoMpuFreq.textContent = state.mpu_frequency_text || "—";

    // Update chart frequencies
    const geoFreqEl = document.getElementById("geophone-freq");
    const mpuFreqEl = document.getElementById("mpu-freq");
    if (geoFreqEl) geoFreqEl.textContent = state.geophone_frequency_text || "—";
    if (mpuFreqEl) mpuFreqEl.textContent = state.mpu_frequency_text || "—";

    // Update metrics
    const metricDominantFreq = document.getElementById("metric-dominant-freq");
    const metricMaxAmp = document.getElementById("metric-max-amp");
    const metricRms = document.getElementById("metric-rms");
    const metricSnr = document.getElementById("metric-snr");
    const metricJitter = document.getElementById("metric-jitter");
    const metricSaturated = document.getElementById("metric-saturated");
    const metricFindings = document.getElementById("metric-findings");

    if (metricDominantFreq)
      metricDominantFreq.textContent = state.dominant_frequency_text || "—";
    if (metricMaxAmp)
      metricMaxAmp.textContent = state.maximum_amplitude_text || "—";
    if (metricRms) metricRms.textContent = state.rms_text || "—";
    if (metricSnr) metricSnr.textContent = state.snr_text || "—";
    if (metricJitter) metricJitter.textContent = state.jitter_text || "—";
    if (metricSaturated)
      metricSaturated.textContent = state.saturated_samples_text || "—";
    if (metricFindings)
      metricFindings.textContent = state.signal_findings_text || "—";

    // Update submenu visibility
    updateSubmenuVisibility(state.active_submenu);

    // Update metric sensor tabs
    updateMetricSensorTabs(state.selected_metric_sensor);

    // Render charts if in señales submenu
    if (state.active_submenu === "senales") {
      renderSignalCharts(state);
    } else if (state.active_submenu === "sta_lta") {
      renderStaltaCharts(state);
    } else if (state.active_submenu === "frecuencia") {
      renderSpectrumCharts(state);
    } else if (state.active_submenu === "espectrograma") {
      renderSpectrogramCharts(state);
    }
  }

  function updateSubmenuVisibility(activeSubmenu) {
    const submenus = [
      { key: "senales", id: "senales" },
      { key: "sta_lta", id: "stalta" },
      { key: "frecuencia", id: "frecuencia" },
      { key: "espectrograma", id: "espectrograma" },
    ];
    submenus.forEach(({ key, id }) => {
      const contentEl = document.getElementById("submenu-content-" + id);
      const tabEl = document.getElementById("submenu-" + id);
      if (contentEl)
        contentEl.style.display = key === activeSubmenu ? "grid" : "none";
      if (tabEl) tabEl.classList.toggle("active", key === activeSubmenu);
    });
    const staltaConfig = document.getElementById("stalta-config-card");
    if (staltaConfig)
      staltaConfig.style.display =
        activeSubmenu === "sta_lta" ? "block" : "none";
    const spectrumConfig = document.getElementById("spectrum-config-card");
    const spectrumMetrics = document.getElementById("spectrum-metrics-card");
    if (spectrumConfig)
      spectrumConfig.style.display =
        activeSubmenu === "frecuencia" ? "block" : "none";
    if (spectrumMetrics)
      spectrumMetrics.style.display =
        activeSubmenu === "frecuencia" ? "block" : "none";
    const spectrogramConfig = document.getElementById(
      "spectrogram-config-card",
    );
    const spectrogramQuick = document.getElementById("spectrogram-quick-card");
    const analysisMetrics = document.getElementById("analysis-metrics-card");
    if (spectrogramConfig)
      spectrogramConfig.style.display =
        activeSubmenu === "espectrograma" ? "block" : "none";
    if (spectrogramQuick)
      spectrogramQuick.style.display =
        activeSubmenu === "espectrograma" ? "block" : "none";
    if (analysisMetrics)
      analysisMetrics.style.display = ["espectrograma", "frecuencia"].includes(
        activeSubmenu,
      )
        ? "none"
        : "";
  }

  function updateMetricSensorTabs(selectedSensor) {
    const geoTab = document.getElementById("btn-sensor-geophone");
    const mpuTab = document.getElementById("btn-sensor-mpu");
    if (geoTab)
      geoTab.classList.toggle("active", selectedSensor === "geophone");
    if (mpuTab) mpuTab.classList.toggle("active", selectedSensor === "mpu");
  }

  function renderSignalCharts(state) {
    const geoCanvas = document.getElementById("chart-geophone");
    const mpuCanvas = document.getElementById("chart-mpu");
    const geoCursorText = document.getElementById("cursor-text-geophone");
    const mpuCursorText = document.getElementById("cursor-text-mpu");
    const eventStart = Number.parseFloat(state.event_start_text) || 0;
    const makeHover = (target, unit) => (point) => {
      if (!target) return;
      if (!point) {
        target.textContent =
          "Mueve el cursor sobre la señal para inspeccionar muestras.";
        return;
      }
      const relative = point.time - eventStart;
      target.textContent = `t = ${point.time.toFixed(3)} s · ${relative.toFixed(3)} s (evento)   Amplitud = ${point.value.toFixed(6)} ${unit}`;
    };

    if (geoCanvas && state.geophone_times && state.geophone_values) {
      Charts.plotTimeSeries(
        geoCanvas,
        state.geophone_times,
        state.geophone_values,
        {
          color: Charts.COLORS.geophone,
          yLabel: "Amplitud (mm/s)",
          xLabel: "Tiempo (s)",
          cursorTime: state.cursor_time >= 0 ? state.cursor_time : undefined,
          onHover: makeHover(geoCursorText, "mm/s"),
          syncGroup: "signal-pair",
        },
      );
    }

    if (mpuCanvas && state.mpu_times && state.mpu_values) {
      Charts.plotTimeSeries(mpuCanvas, state.mpu_times, state.mpu_values, {
        color: Charts.COLORS.mpu,
        yLabel: "Amplitud (m/s²)",
        xLabel: "Tiempo (s)",
        cursorTime: state.cursor_time >= 0 ? state.cursor_time : undefined,
        onHover: makeHover(mpuCursorText, "m/s²"),
        syncGroup: "signal-pair",
      });
    }

    if (geoCursorText && !state.geophone_times)
      geoCursorText.textContent =
        state.geophone_cursor_text || "Mueve el cursor sobre la señal";
    if (mpuCursorText && !state.mpu_times)
      mpuCursorText.textContent =
        state.mpu_cursor_text || "Mueve el cursor sobre la señal";
  }

  function renderStaltaCharts(state) {
    const geoCanvas = document.getElementById("chart-stalta-geophone");
    const mpuCanvas = document.getElementById("chart-stalta-mpu");
    const geoCursorText = document.getElementById(
      "cursor-text-stalta-geophone",
    );
    const mpuCursorText = document.getElementById("cursor-text-stalta-mpu");
    const eventStart = Number.parseFloat(state.event_start_text) || 0;
    const makeStaltaHover = (target, unit) => (point) => {
      if (!target) return;
      if (!point) {
        target.textContent =
          "Mueve el cursor sobre la señal para inspeccionar muestras.";
        return;
      }
      const relative = point.time - eventStart;
      const amplitude = Number.isFinite(point.value)
        ? point.value.toFixed(6)
        : "—";
      const sta = Number.isFinite(point.sta) ? point.sta.toFixed(6) : "—";
      const lta = Number.isFinite(point.lta) ? point.lta.toFixed(6) : "—";
      const ratio = Number.isFinite(point.ratio) ? point.ratio.toFixed(4) : "—";
      target.textContent = `t = ${point.time.toFixed(3)} s · ${relative.toFixed(3)} s (evento)   Amplitud = ${amplitude} ${unit}   STA = ${sta}   LTA = ${lta}   Ratio = ${ratio}`;
    };

    if (geoCanvas && state.geophone_sta_values) {
      Charts.plotStalta(
        geoCanvas,
        state.geophone_times || [],
        state.geophone_sta_values,
        state.geophone_lta_values,
        state.geophone_ratio_values,
        [],
        {
          signal: state.geophone_values || [],
          yLabel: "Amplitud (mm/s)",
          signalColor: Charts.COLORS.geophone,
          syncGroup: "stalta-pair",
          onHover: makeStaltaHover(geoCursorText, "mm/s"),
        },
      );
    }

    if (mpuCanvas && state.mpu_sta_values) {
      Charts.plotStalta(
        mpuCanvas,
        state.mpu_times || [],
        state.mpu_sta_values,
        state.mpu_lta_values,
        state.mpu_ratio_values,
        [],
        {
          signal: state.mpu_values || [],
          yLabel: "Amplitud (m/s²)",
          signalColor: Charts.COLORS.mpu,
          syncGroup: "stalta-pair",
          onHover: makeStaltaHover(mpuCursorText, "m/s²"),
        },
      );
    }
  }

  function renderSpectrumCharts(state) {
    const geoCanvas = document.getElementById("chart-spectrum-geophone");
    const mpuCanvas = document.getElementById("chart-spectrum-mpu");
    const geoReadout = document.getElementById("spectrum-readout-geophone");
    const mpuReadout = document.getElementById("spectrum-readout-mpu");
    const makeSpectrumHover = (target, unit) => (point) => {
      if (!target) return;
      if (!point) {
        target.textContent = `Espectro (${unit}) · Mueve el cursor para inspeccionar bins.`;
        return;
      }
      const frequency = Number.isFinite(point.frequency)
        ? point.frequency.toFixed(3)
        : "—";
      const amplitude = Number.isFinite(point.amplitude)
        ? point.amplitude.toFixed(6)
        : "—";
      target.textContent = `Bin ${point.index} · f = ${frequency} Hz · Amplitud = ${amplitude} ${unit}`;
    };

    if (
      geoCanvas &&
      state.geophone_spectrum_freqs &&
      state.geophone_spectrum_amps
    ) {
      Charts.plotSpectrum(
        geoCanvas,
        state.geophone_spectrum_freqs,
        state.geophone_spectrum_amps,
        {
          color: Charts.COLORS.geophone,
          onHover: makeSpectrumHover(geoReadout, "mm/s"),
        },
      );
    }

    if (mpuCanvas && state.mpu_spectrum_freqs && state.mpu_spectrum_amps) {
      Charts.plotSpectrum(
        mpuCanvas,
        state.mpu_spectrum_freqs,
        state.mpu_spectrum_amps,
        {
          color: Charts.COLORS.mpu,
          onHover: makeSpectrumHover(mpuReadout, "m/s²"),
        },
      );
    }

    const spectrumParamsNote = document.getElementById("spectrum-params-note");
    if (spectrumParamsNote)
      spectrumParamsNote.textContent =
        state.spectral_resolution_text ||
        "Resolución espectral según frecuencia de muestreo";
    const selectedSensor = state.metric_sensor || "geophone";
    const isMpu = selectedSensor === "mpu";
    const selectedIds = {
      dominant: document.getElementById("spectrum-selected-dominant"),
      amp: document.getElementById("spectrum-selected-amp"),
      centroid: document.getElementById("spectrum-selected-centroid"),
      bandwidth: document.getElementById("spectrum-selected-bandwidth"),
      resolution: document.getElementById("spectrum-selected-resolution"),
    };
    // Use the spectral fields already supplied by the analysis state; the
    // selected sensor is handled by Bridge.setMetricSensor().
    const spectrumValues = [
      state.spectral_dominant_frequency_text,
      state.spectral_dominant_amplitude_text,
      state.spectral_centroid_text,
      state.spectral_bandwidth_text,
      state.spectral_resolution_text || state.spectral_resolution,
    ];
    [
      selectedIds.dominant,
      selectedIds.amp,
      selectedIds.centroid,
      selectedIds.bandwidth,
      selectedIds.resolution,
    ].forEach((el, i) => {
      if (el) el.textContent = spectrumValues[i] || "—";
    });
    document
      .getElementById("spectrum-btn-geophone")
      ?.classList.toggle("active", !isMpu);
    document
      .getElementById("spectrum-btn-mpu")
      ?.classList.toggle("active", isMpu);

    // Update spectrum metrics
    const specDomGeo = document.getElementById("spectrum-dominant-geophone");
    const specAmpGeo = document.getElementById("spectrum-amp-geophone");
    const specCentroidGeo = document.getElementById(
      "spectrum-centroid-geophone",
    );
    const specDomMpu = document.getElementById("spectrum-dominant-mpu");
    const specAmpMpu = document.getElementById("spectrum-amp-mpu");
    const specBwMpu = document.getElementById("spectrum-bandwidth-mpu");

    if (specDomGeo)
      specDomGeo.textContent = state.spectral_dominant_frequency_text || "—";
    if (specAmpGeo)
      specAmpGeo.textContent = state.spectral_dominant_amplitude_text || "—";
    if (specCentroidGeo)
      specCentroidGeo.textContent = state.spectral_centroid_text || "—";
    if (specDomMpu)
      specDomMpu.textContent = state.spectral_dominant_frequency_text || "—";
    if (specAmpMpu)
      specAmpMpu.textContent = state.spectral_dominant_amplitude_text || "—";
    if (specBwMpu) specBwMpu.textContent = state.spectral_bandwidth_text || "—";
  }

  function renderSpectrogramCharts(state) {
    const geoCanvas = document.getElementById("chart-spectrogram-geophone");
    const mpuCanvas = document.getElementById("chart-spectrogram-mpu");

    if (
      geoCanvas &&
      state.geophone_spectrogram_times &&
      state.geophone_spectrogram_freqs &&
      state.geophone_spectrogram_amps
    ) {
      // Convert flat amps array to 2D for spectrogram
      const frameCount = state.geophone_spectrogram_frame_count || 0;
      const binCount = state.geophone_spectrogram_bin_count || 0;
      if (frameCount > 0 && binCount > 0) {
        const amps2D = [];
        for (let i = 0; i < frameCount; i++) {
          amps2D.push(
            state.geophone_spectrogram_amps.slice(
              i * binCount,
              (i + 1) * binCount,
            ),
          );
        }
        Charts.plotSpectrogram(
          geoCanvas,
          state.geophone_spectrogram_times,
          state.geophone_spectrogram_freqs,
          amps2D,
          {
            color: Charts.COLORS.geophone,
            onHover: (point) => {
              const readout = document.getElementById(
                "spectrogram-readout-geophone",
              );
              if (!readout) return;
              readout.textContent = point
                ? `t = ${point.time.toFixed(3)} s   f = ${point.frequency.toFixed(2)} Hz   Amplitud = ${point.amplitude === null ? "—" : point.amplitude.toPrecision(4)}`
                : "t = — s   f = — Hz   Amplitud = —";
            },
          },
        );
      }
    }

    if (
      mpuCanvas &&
      state.mpu_spectrogram_times &&
      state.mpu_spectrogram_freqs &&
      state.mpu_spectrogram_amps
    ) {
      const frameCount = state.mpu_spectrogram_frame_count || 0;
      const binCount = state.mpu_spectrogram_bin_count || 0;
      if (frameCount > 0 && binCount > 0) {
        const amps2D = [];
        for (let i = 0; i < frameCount; i++) {
          amps2D.push(
            state.mpu_spectrogram_amps.slice(i * binCount, (i + 1) * binCount),
          );
        }
        Charts.plotSpectrogram(
          mpuCanvas,
          state.mpu_spectrogram_times,
          state.mpu_spectrogram_freqs,
          amps2D,
          {
            color: Charts.COLORS.mpu,
            onHover: (point) => {
              const readout = document.getElementById(
                "spectrogram-readout-mpu",
              );
              if (!readout) return;
              readout.textContent = point
                ? `t = ${point.time.toFixed(3)} s   f = ${point.frequency.toFixed(2)} Hz   Amplitud = ${point.amplitude === null ? "—" : point.amplitude.toPrecision(4)}`
                : "t = — s   f = — Hz   Amplitud = —";
            },
          },
        );
      }
    }

    // Update spectrogram metrics and contextual readouts
    const geoFreq = document.getElementById("spectrogram-freq-geophone");
    const mpuFreq = document.getElementById("spectrogram-freq-mpu");
    if (geoFreq) geoFreq.textContent = state.geophone_frequency_text || "— Hz";
    if (mpuFreq) mpuFreq.textContent = state.mpu_frequency_text || "— Hz";
    const paramsNote = document.getElementById("spectrogram-params-note");
    if (paramsNote)
      paramsNote.textContent =
        [
          state.spectrogram_resolution_text,
          state.spectrogram_window_text,
          state.spectrogram_window_count_text,
        ]
          .filter(Boolean)
          .join(" · ") || "Resolución y parámetros de análisis";
    const energyReadout = document.getElementById("spectrogram-energy-readout");
    const dominantReadout = document.getElementById(
      "spectrogram-dominant-readout",
    );
    const changeReadout = document.getElementById("spectrogram-change-readout");
    const resolutionReadout = document.getElementById(
      "spectrogram-resolution-readout",
    );
    if (energyReadout)
      energyReadout.textContent = state.spectrogram_energy_interval_text || "—";
    if (dominantReadout)
      dominantReadout.textContent = state.spectrogram_dominant_band_text || "—";
    if (changeReadout)
      changeReadout.textContent = state.spectrogram_change_text || "—";
    if (resolutionReadout)
      resolutionReadout.textContent = state.spectrogram_resolution_text || "—";
    const specResGeo = document.getElementById(
      "spectrogram-resolution-geophone",
    );
    const specBandGeo = document.getElementById("spectrogram-band-geophone");
    const specResMpu = document.getElementById("spectrogram-resolution-mpu");
    const specBandMpu = document.getElementById("spectrogram-band-mpu");

    if (specResGeo)
      specResGeo.textContent = state.spectrogram_resolution_text || "—";
    if (specBandGeo)
      specBandGeo.textContent = state.spectrogram_dominant_band_text || "—";
    if (specResMpu)
      specResMpu.textContent = state.spectrogram_resolution_text || "—";
    if (specBandMpu)
      specBandMpu.textContent = state.spectrogram_dominant_band_text || "—";
  }

  function cleanupAnalysisCharts() {
    if (typeof Charts !== "undefined" && Charts.cleanupAllCanvases) {
      Charts.cleanupAllCanvases();
    }
  }

  async function selectAnalysisFile(fileName) {
    cleanupAnalysisCharts();
    console.log(`[App] Selecting analysis file: ${fileName}`);
    const result = await Bridge.selectAnalysisFile(fileName);
    if (result.error || result.success === false) {
      alert("Error: " + (result.error || "No se pudo seleccionar el archivo."));
      return;
    }

    // El backend carga el BIN de forma asíncrona. Esperar a que termine
    // evita dejar el contador y las gráficas en su estado provisional hasta
    // que el usuario pulse los controles de evento.
    const maxAttempts = 300;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const state = await Bridge.getAnalysisState();
      if (!state || !state.loading) break;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    await refreshAnalysisState();
  }

  async function previousEvent() {
    cleanupAnalysisCharts();
    const state = await Bridge.getAnalysisState();
    if (!state || !state.has_selection || state.loading) return;
    const currentIndex = Number(state.selected_event_index);
    if (!Number.isInteger(currentIndex) || currentIndex <= 0) return;

    const result = await Bridge.selectAnalysisEvent(currentIndex - 1);
    if (result && result.success) {
      await refreshAnalysisState();
    } else if (result && result.error) {
      console.error("[App] Could not select previous event:", result.error);
    }
  }

  async function nextEvent() {
    cleanupAnalysisCharts();
    const state = await Bridge.getAnalysisState();
    if (!state || !state.has_selection || state.loading) return;
    const currentIndex = Number(state.selected_event_index);
    const totalEvents = Number(state.total_events);
    if (
      !Number.isInteger(currentIndex) ||
      !Number.isInteger(totalEvents) ||
      currentIndex < 0 ||
      currentIndex >= totalEvents - 1
    )
      return;

    const result = await Bridge.selectAnalysisEvent(currentIndex + 1);
    if (result && result.success) {
      await refreshAnalysisState();
    } else if (result && result.error) {
      console.error("[App] Could not select next event:", result.error);
    }
  }

  async function selectSubmenu(submenu) {
    cleanupAnalysisCharts();
    console.log(`[App] Selecting submenu: ${submenu}`);
    await Bridge.selectSubmenu(submenu);
    await refreshAnalysisState();
  }

  async function setMetricSensor(sensor) {
    console.log(`[App] Setting metric sensor: ${sensor}`);
    await Bridge.setMetricSensor(sensor);
    await refreshAnalysisState();
  }

  async function setStaltaParameter(param, value) {
    console.log(`[App] Setting STA/LTA param: ${param} = ${value}`);
    await Bridge.setStaltaParameters({ [param]: value });
    await refreshAnalysisState();
  }

  async function setSpectrumWindow(window) {
    console.log(`[App] Setting spectrum window: ${window}`);
    await Bridge.setSpectrumParameters({ window });
    await refreshAnalysisState();
  }

  async function setSpectrumRange(range) {
    console.log(`[App] Setting spectrum range: ${range}`);
    await Bridge.setSpectrumParameters({ range_hz: range });
    await refreshAnalysisState();
  }

  async function setSpectrogramWindow(window) {
    console.log(`[App] Setting spectrogram window: ${window}`);
    await Bridge.setSpectrogramParameters({ window });
    await refreshAnalysisState();
  }

  async function setSpectrogramDuration(duration) {
    console.log(`[App] Setting spectrogram duration: ${duration}`);
    await Bridge.setSpectrogramParameters({ duration_seconds: duration });
    await refreshAnalysisState();
  }

  async function setSpectrogramOverlap(overlap) {
    console.log(`[App] Setting spectrogram overlap: ${overlap}`);
    await Bridge.setSpectrogramParameters({ overlap });
    await refreshAnalysisState();
  }

  async function setSpectrogramRange(range) {
    console.log(`[App] Setting spectrogram range: ${range}`);
    await Bridge.setSpectrogramParameters({ range_hz: range });
    await refreshAnalysisState();
  }

  async function setStaltaMethod(method) {
    console.log(`[App] Setting STA/LTA method: ${method}`);
    await Bridge.setStaltaParameters({ method });
    await refreshAnalysisState();
  }

  async function setCursorTime(time) {
    await Bridge.setCursorTime(time);
  }

  async function clearCursor() {
    await Bridge.clearCursor();
    await refreshAnalysisState();
  }

  async function resetViewport() {
    await Bridge.resetViewport();
    await refreshAnalysisState();
  }

  // ===================================================================
  // Public API
  // ===================================================================

  return {
    init,
    navigateTo,
    refreshProjectState,
    refreshDataState,
    refreshAnalysisState,
  };
})();

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
