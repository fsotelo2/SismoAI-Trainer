/**
 * Bridge module: JavaScript interface to Python ApiBridge via pywebview.
 * 
 * All methods return Promises. Errors are caught and returned as { error: string }.
 */

const Bridge = (() => {
  'use strict';

  // Check if running inside pywebview
  const isNative = () => {
    return typeof window.pywebview !== 'undefined' && window.pywebview.api;
  };

  // Safe API call wrapper
  async function call(methodName, ...args) {
    if (!isNative()) {
      console.warn(`[Bridge] pywebview not available, ${methodName} skipped`);
      return { error: 'pywebview no disponible' };
    }
    try {
      const result = await window.pywebview.api[methodName](...args);
      return result;
    } catch (err) {
      console.error(`[Bridge] Error in ${methodName}:`, err);
      return { error: err.message || String(err) };
    }
  }

  // Public API
  return {
    // Project
    selectDataFolder: () => call('select_data_folder'),
    getProjectState: () => call('get_project_state'),
    rescanProject: () => call('rescan_project'),

    // Data
    scanFiles: () => call('scan_files'),
    getQualitySummary: (fileName) => call('get_quality_summary', fileName),
    getFileEvents: (fileName) => call('get_file_events', fileName),
    selectFile: (fileName) => call('select_file', fileName),
    getDataState: () => call('get_data_state'),

    // Analysis
    getChannelSeries: (fileName, eventIndex, channel) => call('get_channel_series', fileName, eventIndex, channel),
    runStalta: (params) => call('run_stalta', params),
    runSpectrum: (params) => call('run_spectrum', params),
    runSpectrogram: (params) => call('run_spectrogram', params),

    // Analysis state
    getAnalysisState: () => call('get_analysis_state'),
    getAnalysisFiles: () => call('get_analysis_files'),
    selectAnalysisFile: (fileName) => call('select_analysis_file', fileName),
    selectAnalysisEvent: (eventIndex) => call('select_analysis_event', eventIndex),
    getAnalysisEventData: () => call('get_analysis_event_data'),

    // Phase 6 — Windows
    getWindowContext: () => call('get_window_context'),
    generateWindows: (params) => call('generate_windows', params),
    addManualWindow: (params) => call('add_manual_window', params),
    getWindows: () => call('get_windows'),
    beginWindowSession: () => call('begin_window_session'),
    getLabelingWorkspace: () => call('get_labeling_workspace'),
    createWindowSelection: (name) => call('create_window_selection', name),
    getWindowSelections: () => call('get_window_selections'),
    selectWindowSelection: (filename) => call('select_window_selection', filename),
    createLabelBatch: (name) => call('create_label_batch', name),
    getLabelBatches: () => call('get_label_batches'),
    selectLabelBatch: (filename) => call('select_label_batch', filename),
    getDatasetWorkspace: () => call('get_dataset_workspace'),
    getDatasetCatalog: () => call('get_dataset_catalog'),
    deleteDataset: (filename) => call('delete_dataset', filename),
    selectDataset: (filename) => call('select_dataset', filename),
    getModelExperiments: () => call('get_model_experiments'),
    deleteModelExperiment: (experimentId) => call('delete_model_experiment', experimentId),
    saveModelExperiment: (config, datasetId, datasetName) => call('save_model_experiment', config, datasetId, datasetName),
    startModelTraining: (config, datasetId) => call('start_model_training', config, datasetId),
    getModelTrainingState: () => call('get_model_training_state'),
    generateDataset: (ratios, seed, name) => call('generate_dataset', ratios, seed, name),
    getWindowSignal: (windowId, windowRef) => call('get_window_signal', windowId, windowRef),
    saveWindowLabel: (windowId, payload, windowRef) => call('save_window_label', windowId, payload, windowRef),
    clearWindows: () => call('clear_windows'),
    setWindowSelection: (windowId, status) => call('set_window_selection', windowId, status),
    getAnalysisMetrics: () => call('get_analysis_metrics'),
    getStaltaResults: () => call('get_stalta_results'),
    getSpectrumResults: () => call('get_spectrum_results'),
    getSpectrogramResults: () => call('get_spectrogram_results'),

    // Parameters
    setStaltaParameters: (params) => call('set_stalta_parameters', params),
    setSpectrumParameters: (params) => call('set_spectrum_parameters', params),
    setSpectrogramParameters: (params) => call('set_spectrogram_parameters', params),
    setMetricSensor: (sensor) => call('set_metric_sensor', sensor),
    selectSubmenu: (submenu) => call('select_submenu', submenu),

    // Interaction
    setCursorTime: (timeSeconds) => call('set_cursor_time', timeSeconds),
    clearCursor: () => call('clear_cursor'),
    getCursorTexts: () => call('get_cursor_texts'),
    zoomTime: (factor, anchorRatio) => call('zoom_time', factor, anchorRatio),
    panViewport: (sensor, hFrac, vFrac) => call('pan_viewport', sensor, hFrac, vFrac),
    resetViewport: () => call('reset_viewport'),

    // Utility
    isNative: isNative,
  };
})();
