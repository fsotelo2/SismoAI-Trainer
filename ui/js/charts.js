/**
 * Charts module: Canvas-based rendering for sismograms, spectra, and spectrograms.
 * No external dependencies — uses native Canvas 2D API.
 */

const Charts = (() => {
  'use strict';

  // Color palette
  const COLORS = {
    geophone: '#2563EB',
    mpu: '#7C3AED',
    grid: '#E2E8F0',
    text: '#64748B',
    cursor: '#DC2626',
    trigger: '#10B981',
  };

  /**
   * Clear canvas and set dimensions
   */
  function setupCanvas(canvas, width, height) {
    if (!canvas) return null;
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(width * dpr);
    const pixelHeight = Math.round(height * dpr);
    // Resizing a canvas clears and reallocates its backing store. Avoid doing
    // that on every pointermove/zoom redraw; only resize when dimensions change.
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    canvas.style.width = '100%';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    // setTransform replaces the previous DPR transform instead of stacking it.
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  /**
   * Draw grid lines
   */
  function drawGrid(ctx, xMin, xMax, yMin, yMax, width, height, padding, leftPadding = padding, rightPadding = padding, yOffset = 0) {
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;

    // Vertical grid lines (5 divisions)
    for (let i = 0; i <= 5; i++) {
      const x = leftPadding + (width - leftPadding - rightPadding) * (i / 5);
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, height - padding);
      ctx.stroke();
    }

    // Horizontal grid lines (5 divisions)
    for (let i = 0; i <= 5; i++) {
      const y = padding + (height - 2 * padding) * (i / 5) + yOffset;
      ctx.beginPath();
      ctx.moveTo(leftPadding, y);
      ctx.lineTo(width - rightPadding, y);
      ctx.stroke();
    }
  }

  /**
   * Draw axis labels
   */
  function drawAxes(ctx, xMin, xMax, yMin, yMax, width, height, padding, xLabel, yLabel, leftPadding = padding, rightPadding = padding, yOffset = 0) {
    ctx.fillStyle = COLORS.text;
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';

    // X axis labels
    for (let i = 0; i <= 5; i++) {
      const value = xMin + (xMax - xMin) * (i / 5);
      const x = leftPadding + (width - leftPadding - rightPadding) * (i / 5);
      ctx.fillText(value.toFixed(2), x, height - padding + 16);
    }

    // Y axis labels
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const value = yMax - (yMax - yMin) * (i / 5);
      const y = padding + (height - 2 * padding) * (i / 5) + yOffset;
      ctx.fillText(value.toExponential(1), leftPadding - 8, y + 4);
    }

    // Axis titles
    ctx.textAlign = 'center';
    ctx.fillText(xLabel, width / 2, height - 4);

    ctx.save();
    ctx.translate(18, height / 2 + yOffset);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();
  }

  const timeChartState = new WeakMap();
  const timeRangeCache = new WeakMap();
  const staltaChartState = new WeakMap();

  const timeChartGroups = new Map();

  function syncTimeViewport(source, xMin, xMax) {
    const groupName = source.options.syncGroup;
    if (!groupName) { source.xMin = xMin; source.xMax = xMax; plotTimeSeries(source.canvas, source.times, source.values, source.options); return; }
    const members = timeChartGroups.get(groupName);
    if (!members) return;
    const startRatio = (xMin - source.fullMin) / source.fullSpan;
    const endRatio = (xMax - source.fullMin) / source.fullSpan;
    for (const peer of [...members]) {
      if (!peer.canvas?.isConnected) { members.delete(peer); continue; }
      const span = peer.fullSpan;
      const min = peer.fullMin + startRatio * span;
      const max = peer.fullMin + endRatio * span;
      peer.xMin = Math.max(peer.fullMin, min);
      peer.xMax = Math.min(peer.fullMax, max);
      plotTimeSeries(peer.canvas, peer.times, peer.values, peer.options);
    }
  }

  function attachTimeInteractions(canvas) {
    if (canvas.dataset.timeInteractions === 'true') return;
    canvas.dataset.timeInteractions = 'true';
    const getState = () => timeChartState.get(canvas);
    const plotArea = (st) => ({ left: 92, right: Math.max(92, canvas.getBoundingClientRect().width - 24) });
    canvas.addEventListener('wheel', (event) => {
      const st = getState();
      if (!st) return;
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const area = plotArea(st);
      const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left - area.left) / Math.max(1, area.right - area.left)));
      const span = Math.max(1e-9, st.xMax - st.xMin);
      const factor = event.deltaY < 0 ? 0.8 : 1.25;
      const nextSpan = Math.max(st.fullSpan / 10000, Math.min(st.fullSpan, span * factor));
      const anchor = st.xMin + span * ratio;
      let nextMin = anchor - nextSpan * ratio;
      nextMin = Math.max(st.fullMin, Math.min(st.fullMax - nextSpan, nextMin));
      syncTimeViewport(st, nextMin, nextMin + nextSpan);
    }, { passive: false });
    canvas.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) return;
      const st = getState();
      if (!st) return;
      event.preventDefault();
      st.drag = { pointerId: event.pointerId, x: event.clientX, min: st.xMin, max: st.xMax };
      canvas.setPointerCapture?.(event.pointerId);
      canvas.style.cursor = 'grabbing';
    });
    canvas.addEventListener('pointermove', (event) => {
      const st = getState();
      if (!st || !st.drag || st.drag.pointerId !== event.pointerId) return;
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const span = st.drag.max - st.drag.min;
      const delta = -(event.clientX - st.drag.x) / Math.max(1, rect.width - 116) * span;
      const nextMin = Math.max(st.fullMin, Math.min(st.fullMax - span, st.drag.min + delta));
      syncTimeViewport(st, nextMin, nextMin + span);
    }, { passive: false });
    const stopDrag = (event) => {
      const st = getState();
      if (!st || !st.drag || (event && st.drag.pointerId !== event.pointerId)) return;
      st.drag = null;
      canvas.style.cursor = 'crosshair';
    };
    canvas.addEventListener('pointerup', stopDrag);
    canvas.addEventListener('pointercancel', stopDrag);
    canvas.addEventListener('lostpointercapture', stopDrag);
    canvas.addEventListener('dblclick', (event) => {
      event.preventDefault();
      const st = getState();
      if (!st) return;
      st.options.cursorTime = undefined;
      st.options.onHover && st.options.onHover(null);
      syncTimeViewport(st, st.fullMin, st.fullMax);
    });
    canvas.addEventListener('mousemove', (event) => {
      const st = getState();
      if (!st || st.drag) return;
      const rect = canvas.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const plotLeft = 92, plotRight = rect.width - 24;
      if (px < plotLeft || px > plotRight) {
        st.options.cursorTime = undefined;
        st.options.onHover && st.options.onHover(null);
        plotTimeSeries(canvas, st.times, st.values, st.options);
        return;
      }
      const ratio = (px - plotLeft) / Math.max(1, plotRight - plotLeft);
      const time = st.xMin + ratio * (st.xMax - st.xMin);
      let lo = 0, hi = st.times.length - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (st.times[mid] < time) lo = mid + 1; else hi = mid;
      }
      const idx = lo > 0 && Math.abs(st.times[lo - 1] - time) < Math.abs(st.times[lo] - time) ? lo - 1 : lo;
      st.options.cursorTime = st.times[idx];
      st.options.onHover && st.options.onHover({ time: st.times[idx], value: st.values[idx], index: idx });
      plotTimeSeries(canvas, st.times, st.values, st.options);
    });
    canvas.addEventListener('mouseleave', () => {
      const st = getState();
      if (!st || st.drag) return;
      st.options.cursorTime = undefined;
      st.options.onHover && st.options.onHover(null);
      plotTimeSeries(canvas, st.times, st.values, st.options);
    });
    canvas.style.touchAction = 'none';
    canvas.style.userSelect = 'none';
    canvas.style.cursor = 'crosshair';
  }

  /**
   * Plot a time series on canvas
   */
  function plotTimeSeries(canvas, times, values, options = {}) {
    if (!canvas || !times || !values || times.length === 0) return;

    const width = options.width || canvas.parentElement?.clientWidth || canvas.clientWidth || 800;
    const height = options.height || canvas.clientHeight || 300;
    const padding = Math.min(50, Math.max(24, height * 0.18));
    const leftPadding = 92;
    const rightPadding = 24;
    const plotWidth = Math.max(1, width - leftPadding - rightPadding);
    const color = options.color || COLORS.geophone;
    const xLabel = options.xLabel || 'Tiempo (s)';
    const yLabel = options.yLabel || 'Amplitud';
    const title = options.title || '';

    const ctx = setupCanvas(canvas, width, height);
    if (!ctx) return;

    // Calculate ranges
    let timeRange = timeRangeCache.get(times);
    if (!timeRange || timeRange.values !== values) {
      let min = Infinity, max = -Infinity, yMin = Infinity, yMax = -Infinity;
      for (let i = 0; i < times.length; i++) {
        const t = Number(times[i]), v = Number(values[i]);
        if (Number.isFinite(t)) { if (t < min) min = t; if (t > max) max = t; }
        if (Number.isFinite(v)) { if (v < yMin) yMin = v; if (v > yMax) yMax = v; }
      }
      timeRange = { values, fullMin: min, fullMax: max, yMin: yMin === Infinity ? -1 : yMin, yMax: yMax === -Infinity ? 1 : yMax };
      timeRangeCache.set(times, timeRange);
    }
    const fullMin = timeRange.fullMin;
    const fullMax = timeRange.fullMax;
    let st = timeChartState.get(canvas);
    if (!st || st.times !== times || st.values !== values) {
      st = { times, values, fullMin, fullMax, fullSpan: fullMax - fullMin || 1, xMin: fullMin, xMax: fullMax, options: { ...options }, drag: null };
      st.canvas = canvas;
      timeChartState.set(canvas, st);
    } else {
      st.fullMin = fullMin; st.fullMax = fullMax; st.fullSpan = fullMax - fullMin || 1;
      st.options = { ...options };
      st.canvas = canvas;
    }
    if (options.syncGroup) {
      if (!timeChartGroups.has(options.syncGroup)) timeChartGroups.set(options.syncGroup, new Set());
      timeChartGroups.get(options.syncGroup).add(st);
    }
    attachTimeInteractions(canvas);
    const xMin = Math.max(fullMin, options.viewXMin ?? st.xMin);
    const xMax = Math.min(fullMax, options.viewXMax ?? st.xMax);
    st.xMin = xMin; st.xMax = xMax;
    const yMin = timeRange.yMin;
    const yMax = timeRange.yMax;
    const yPadding = (yMax - yMin) * 0.1 || 1;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Title
    if (title) {
      ctx.fillStyle = COLORS.text;
      ctx.font = 'bold 14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, width / 2, 20);
    }

    // Grid
    const yOffset = -10; // 20 px hacia arriba respecto al desplazamiento anterior.
    drawGrid(ctx, xMin, xMax, yMin - yPadding, yMax + yPadding, width, height, padding, leftPadding, rightPadding, yOffset);

    // Axes
    drawAxes(ctx, xMin, xMax, yMin - yPadding, yMax + yPadding, width, height, padding, xLabel, yLabel, leftPadding, rightPadding, yOffset);

    // Plot line
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    let lo = 0, hi = times.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (times[mid] < xMin) lo = mid + 1; else hi = mid; }
    let end = lo;
    hi = times.length;
    while (end < hi) { const mid = (end + hi) >> 1; if (times[mid] <= xMax) end = mid + 1; else hi = mid; }
    const visibleCount = end - lo;
    const step = Math.max(1, Math.ceil(visibleCount / Math.max(1, plotWidth * 2)));
    let started = false;
    for (let i = lo; i < end; i += step) {
      const x = leftPadding + plotWidth * ((times[i] - xMin) / (xMax - xMin || 1));
      const y = padding + (height - 2 * padding) * (1 - (values[i] - (yMin - yPadding)) / ((yMax + yPadding) - (yMin - yPadding))) + yOffset;
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Cursor line
    if (options.cursorTime !== undefined && options.cursorTime >= xMin && options.cursorTime <= xMax) {
      const cx = leftPadding + plotWidth * ((options.cursorTime - xMin) / (xMax - xMin));
      ctx.strokeStyle = COLORS.cursor;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx, padding + yOffset);
      ctx.lineTo(cx, height - padding + yOffset);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  /**
   * Plot spectrum (frequency domain)
   */
  const spectrumInteractionState = new WeakMap();

  function attachSpectrumInteractions(canvas) {
    if (canvas.dataset.spectrumInteractions === 'true') return;
    canvas.dataset.spectrumInteractions = 'true';
    const clear = () => {
      const state = spectrumInteractionState.get(canvas);
      if (!state) return;
      state.options.cursorFrequency = undefined;
      if (state.onHover) state.onHover(null);
      plotSpectrum(canvas, state.freqs, state.mags, state.options);
    };
    canvas.addEventListener('pointermove', (event) => {
      const state = spectrumInteractionState.get(canvas);
      if (!state) return;
      const rect = canvas.getBoundingClientRect();
      const scaleX = rect.width ? state.width / rect.width : 1;
      const scaleY = rect.height ? state.height / rect.height : 1;
      const x = (event.clientX - rect.left) * scaleX;
      const y = (event.clientY - rect.top) * scaleY;
      if (x < state.left || x > state.left + state.plotWidth ||
          y < state.top || y > state.top + state.plotHeight) {
        if (state.options.cursorFrequency !== undefined) clear();
        else if (state.onHover) state.onHover(null);
        return;
      }
      const frequency = state.xMin + ((x - state.left) / state.plotWidth) * (state.xMax - state.xMin);
      let index = 0, bestDistance = Infinity;
      for (let i = 0; i < state.freqs.length; i++) {
        const distance = Math.abs(Number(state.freqs[i]) - frequency);
        if (distance < bestDistance) { bestDistance = distance; index = i; }
      }
      state.options.cursorFrequency = Number(state.freqs[index]);
      if (state.onHover) state.onHover({
        frequency: Number(state.freqs[index]),
        amplitude: Number(state.mags[index]),
        index,
      });
      plotSpectrum(canvas, state.freqs, state.mags, state.options);
    });
    canvas.addEventListener('pointerleave', clear);
  }

  function plotSpectrum(canvas, freqs, mags, options = {}) {
    if (!canvas || !freqs || !mags || freqs.length === 0) return;

    const width = options.width || canvas.parentElement?.clientWidth || canvas.clientWidth || 800;
    const height = options.height || canvas.clientHeight || 300;
    const padding = 50;
    // Keep the Y-axis title left of tick labels, as in the time-series charts.
    const plotLeft = 82;
    const plotRight = 50;
    const plotWidth = Math.max(1, width - plotLeft - plotRight);
    const plotHeight = Math.max(1, height - 2 * padding);
    const color = options.color || COLORS.geophone;
    const title = options.title || '';

    const ctx = setupCanvas(canvas, width, height);
    if (!ctx) return;

    const xMin = Math.min(...freqs);
    const xMax = Math.max(...freqs);
    const yMin = 0;
    const yMax = Math.max(...mags) * 1.1 || 1;

    spectrumInteractionState.set(canvas, {
      freqs, mags, xMin, xMax, width, height,
      left: plotLeft, top: padding, plotWidth, plotHeight,
      onHover: options.onHover, options,
    });
    attachSpectrumInteractions(canvas);

    ctx.clearRect(0, 0, width, height);

    if (title) {
      ctx.fillStyle = COLORS.text;
      ctx.font = 'bold 14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, width / 2, 20);
    }

    drawGrid(ctx, xMin, xMax, yMin, yMax, width, height, padding, plotLeft, plotRight);
    drawAxes(ctx, xMin, xMax, yMin, yMax, width, height, padding, 'Frecuencia (Hz)', 'Magnitud', plotLeft, plotRight);

    // Plot bars
    const barWidth = plotWidth / freqs.length * 0.8;
    ctx.fillStyle = color;

    for (let i = 0; i < freqs.length; i++) {
      const x = plotLeft + plotWidth * ((freqs[i] - xMin) / (xMax - xMin || 1)) - barWidth / 2;
      const barHeight = plotHeight * (mags[i] / yMax);
      const y = height - padding - barHeight;
      ctx.fillRect(x, y, barWidth, barHeight);
    }

    // Dashed vertical cursor, aligned with the inspected frequency bin.
    if (options.cursorFrequency !== undefined &&
        options.cursorFrequency >= xMin && options.cursorFrequency <= xMax) {
      const cx = plotLeft + plotWidth * ((options.cursorFrequency - xMin) / (xMax - xMin || 1));
      ctx.strokeStyle = COLORS.cursor;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx, padding);
      ctx.lineTo(cx, height - padding);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  /**
   * Plot spectrogram as heatmap
   */
  const spectrogramInteractionState = new WeakMap();

  function attachSpectrogramInteractions(canvas) {
    if (canvas.dataset.spectrogramInteractions === 'true') return;
    canvas.dataset.spectrogramInteractions = 'true';
    const clear = () => {
      const st = spectrogramInteractionState.get(canvas);
      if (st?.onHover) st.onHover(null);
    };
    canvas.addEventListener('pointermove', (event) => {
      const st = spectrogramInteractionState.get(canvas);
      if (!st) return;
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      if (x < st.left || x > st.left + st.plotW || y < st.top || y > st.top + st.plotH) {
        if (st.onHover) st.onHover(null);
        return;
      }
      const time = st.xMin + ((x - st.left) / st.plotW) * (st.xMax - st.xMin);
      const freq = st.yMax - ((y - st.top) / st.plotH) * (st.yMax - st.yMin);
      let ti = 0, bestT = Infinity;
      for (let i = 0; i < st.times.length; i++) {
        const d = Math.abs(Number(st.times[i]) - time);
        if (d < bestT) { bestT = d; ti = i; }
      }
      let fi = 0, bestF = Infinity;
      for (let j = 0; j < st.freqs.length; j++) {
        const d = Math.abs(Number(st.freqs[j]) - freq);
        if (d < bestF) { bestF = d; fi = j; }
      }
      const row = st.intensities[ti] || [];
      const amplitude = Number(row[fi]);
      if (st.onHover) st.onHover({
        time: Number(st.times[ti]),
        frequency: Number(st.freqs[fi]),
        amplitude: Number.isFinite(amplitude) ? amplitude : null,
        timeIndex: ti,
        frequencyIndex: fi,
      });
    });
    canvas.addEventListener('pointerleave', clear);
  }

  function plotSpectrogram(canvas, times, freqs, intensities, options = {}) {
    if (!canvas || !times || !freqs || !intensities || !times.length || !freqs.length) return;
    const width = options.width || canvas.parentElement?.clientWidth || canvas.clientWidth || 800;
    const height = options.height || canvas.clientHeight || 300;
    const ctx = setupCanvas(canvas, width, height);
    if (!ctx) return;

    // Spectrogram timestamps represent window centers, not the outer edges.
    // Extend the displayed domain by half a time step on both sides so each
    // raster column is centered on its timestamp and the axis shows bin edges.
    const left = 82, right = 76, top = 24, bottom = 42;
    const plotW = Math.max(1, width - left - right);
    const plotH = Math.max(1, height - top - bottom);
    const firstTime = Number(times[0]);
    const lastTime = Number(times[times.length - 1]);
    const timeStep = times.length > 1 ? (lastTime - firstTime) / (times.length - 1) : 1;
    const xMin = firstTime - timeStep / 2;
    const xMax = lastTime + timeStep / 2;
    const yMin = Number(freqs[0]), yMax = Number(freqs[freqs.length - 1]);
    let maxIntensity = 0;
    for (let i = 0; i < times.length; i++) {
      const row = intensities[i] || [];
      for (let j = 0; j < Math.min(freqs.length, row.length); j++) {
        const value = Number(row[j]);
        if (Number.isFinite(value) && value > maxIntensity) maxIntensity = value;
      }
    }
    if (!(maxIntensity > 0)) maxIntensity = 1;

    spectrogramInteractionState.set(canvas, {
      times, freqs, intensities, xMin, xMax, yMin, yMax,
      left, top, plotW, plotH, onHover: options.onHover,
    });
    attachSpectrogramInteractions(canvas);

    // Dark plotting field and rasterized time-frequency cells.
    ctx.fillStyle = '#050914';
    ctx.fillRect(left, top, plotW, plotH);
    const cellW = plotW / times.length + 0.15;
    const cellH = plotH / freqs.length + 0.6;
    for (let i = 0; i < times.length; i++) {
      const row = intensities[i] || [];
      const x = left + (Number(times[i]) - xMin) / (xMax - xMin || 1) * plotW - cellW / 2;
      for (let j = 0; j < Math.min(freqs.length, row.length); j++) {
        const value = Number(row[j]);
        if (!Number.isFinite(value) || value <= 0) continue;
        const intensity = Math.max(0, Math.min(1, value / maxIntensity));
        const hue = 240 * (1 - Math.pow(intensity, 0.72));
        const light = 13 + 48 * Math.pow(intensity, 0.8);
        ctx.fillStyle = `hsl(${hue.toFixed(1)} 100% ${light.toFixed(1)}%)`;
        const y = top + plotH - (j + 1) * cellH;
        ctx.fillRect(x, y, cellW, cellH);
      }
    }

    // Grid, axes, and frequency labels.
    ctx.font = '10px Inter, sans-serif';
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(203,213,225,.65)';
    ctx.fillStyle = '#64748B';
    ctx.textAlign = 'right';
    for (let k = 0; k <= 4; k++) {
      const y = top + plotH * k / 4;
      const f = yMax - (yMax - yMin) * k / 4;
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + plotW, y); ctx.stroke();
      ctx.fillText(Number(f).toFixed(1).replace(/\\.0$/, ''), left - 10, y + 3);
    }
    ctx.textAlign = 'center';
    for (let k = 0; k <= 4; k++) {
      const x = left + plotW * k / 4;
      const t = xMin + (xMax - xMin) * k / 4;
      ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotH); ctx.stroke();
      ctx.textAlign = k === 0 ? 'left' : (k === 4 ? 'right' : 'center');
      ctx.fillText(Number(t).toFixed(1), x, top + plotH + 17);
    }
    ctx.strokeStyle = '#94A3B8';
    ctx.strokeRect(left, top, plotW, plotH);
    ctx.fillStyle = '#475569';
    ctx.fillText('Tiempo (s)', left + plotW / 2, height - 3);
    ctx.save();
    ctx.translate(14, top + plotH / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText('Frecuencia (Hz)', 0, 0); ctx.restore();

    // Intensity color scale.
    const barX = left + plotW + 12, barW = 10;
    for (let y = 0; y < plotH; y++) {
      const intensity = 1 - y / plotH;
      const hue = 240 * (1 - Math.pow(intensity, 0.72));
      const light = 13 + 48 * Math.pow(intensity, 0.8);
      ctx.fillStyle = `hsl(${hue.toFixed(1)} 100% ${light.toFixed(1)}%)`;
      ctx.fillRect(barX, top + y, barW, 1.5);
    }
    ctx.fillStyle = '#475569'; ctx.textAlign = 'left';
    ctx.fillText('100', barX + 13, top + 4);
    ctx.fillText('50', barX + 13, top + plotH / 2 + 3);
    ctx.fillText('0', barX + 13, top + plotH);
    ctx.textAlign = 'center';
    ctx.fillText('Intensidad', barX + barW / 2, top - 9);
  }

  const staltaChartGroups = new Map();
  const staltaRangeCache = new WeakMap();

  function syncStaltaViewport(source, xMin, xMax) {
    const groupName = source.options.syncGroup;
    const members = groupName && staltaChartGroups.get(groupName);
    if (!members) {
      source.xMin = xMin; source.xMax = xMax;
      plotStalta(source.canvas, source.times, source.sta, source.lta, source.ratio, source.triggers, source.options);
      return;
    }
    const startRatio = (xMin - source.fullMin) / source.fullSpan;
    const endRatio = (xMax - source.fullMin) / source.fullSpan;
    for (const peer of [...members]) {
      if (!peer.canvas?.isConnected) { members.delete(peer); continue; }
      const span = Math.max(1e-9, peer.fullSpan);
      const width = Math.min(span, Math.max(span / 10000, (endRatio - startRatio) * span));
      let min = peer.fullMin + startRatio * span;
      min = Math.max(peer.fullMin, Math.min(peer.fullMax - width, min));
      peer.xMin = min; peer.xMax = min + width;
      plotStalta(peer.canvas, peer.times, peer.sta, peer.lta, peer.ratio, peer.triggers, peer.options);
    }
  }

  function attachStaltaInteractions(canvas) {
    if (canvas.dataset.staltaInteractions === 'true') return;
    canvas.dataset.staltaInteractions = 'true';
    const getState = () => staltaChartState.get(canvas);
    canvas.addEventListener('wheel', (event) => {
      const st = getState();
      if (!st) return;
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const left = 84, right = rect.width - 58;
      const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left - left) / Math.max(1, right - left)));
      const span = Math.max(1e-9, st.xMax - st.xMin);
      const nextSpan = Math.max(st.fullSpan / 10000, Math.min(st.fullSpan, span * (event.deltaY < 0 ? 0.8 : 1.25)));
      const anchor = st.xMin + span * ratio;
      let min = anchor - nextSpan * ratio;
      min = Math.max(st.fullMin, Math.min(st.fullMax - nextSpan, min));
      syncStaltaViewport(st, min, min + nextSpan);
    }, { passive: false });
    canvas.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) return;
      const st = getState();
      if (!st) return;
      event.preventDefault();
      st.drag = { pointerId: event.pointerId, x: event.clientX, min: st.xMin, max: st.xMax };
      canvas.setPointerCapture?.(event.pointerId);
      canvas.style.cursor = 'grabbing';
    });
    canvas.addEventListener('pointermove', (event) => {
      const st = getState();
      if (!st || !st.drag || st.drag.pointerId !== event.pointerId) return;
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const span = st.drag.max - st.drag.min;
      const delta = -(event.clientX - st.drag.x) / Math.max(1, rect.width - 142) * span;
      const min = Math.max(st.fullMin, Math.min(st.fullMax - span, st.drag.min + delta));
      syncStaltaViewport(st, min, min + span);
    }, { passive: false });
    const stopDrag = (event) => {
      const st = getState();
      if (!st || !st.drag || (event && st.drag.pointerId !== event.pointerId)) return;
      st.drag = null;
      canvas.style.cursor = 'crosshair';
    };
    canvas.addEventListener('pointerup', stopDrag);
    canvas.addEventListener('pointercancel', stopDrag);
    canvas.addEventListener('lostpointercapture', stopDrag);
    canvas.addEventListener('dblclick', (event) => {
      event.preventDefault();
      const st = getState();
      if (!st) return;
      st.options.cursorIndex = undefined;
      st.options.onHover && st.options.onHover(null);
      syncStaltaViewport(st, st.fullMin, st.fullMax);
    });
    canvas.style.touchAction = 'none';
    canvas.style.userSelect = 'none';
    canvas.style.cursor = 'crosshair';
  }

  function attachStaltaHover(canvas) {
    if (canvas.dataset.staltaHover === 'true') return;
    canvas.dataset.staltaHover = 'true';
    canvas.addEventListener('mousemove', (event) => {
      const st = staltaChartState.get(canvas);
      if (!st || !st.times.length) return;
      const rect = canvas.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const left = 84, right = 58;
      if (px < left || px > rect.width - right) {
        if (st.options.cursorIndex !== undefined) {
          st.options.cursorIndex = undefined;
          st.options.onHover && st.options.onHover(null);
          plotStalta(canvas, st.times, st.sta, st.lta, st.ratio, st.triggers, st.options);
        }
        return;
      }
      const fraction = (px - left) / Math.max(1, rect.width - left - right);
      const targetTime = st.xMin + fraction * (st.xMax - st.xMin);
      let lo = 0, hi = st.count - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (st.times[mid] < targetTime) lo = mid + 1; else hi = mid;
      }
      const idx = lo > 0 && Math.abs(st.times[lo - 1] - targetTime) < Math.abs(st.times[lo] - targetTime) ? lo - 1 : lo;
      if (st.options.cursorIndex === idx) return;
      st.options.cursorIndex = idx;
      st.options.onHover && st.options.onHover({
        time: Number(st.times[idx]), value: Number(st.signal[idx]),
        sta: Number(st.sta[idx]), lta: Number(st.lta[idx]), ratio: Number(st.ratio[idx]), index: idx,
      });
      plotStalta(canvas, st.times, st.sta, st.lta, st.ratio, st.triggers, st.options);
    });
    canvas.addEventListener('mouseleave', () => {
      const st = staltaChartState.get(canvas);
      if (!st) return;
      st.options.cursorIndex = undefined;
      st.options.onHover && st.options.onHover(null);
      plotStalta(canvas, st.times, st.sta, st.lta, st.ratio, st.triggers, st.options);
    });
    canvas.style.cursor = 'crosshair';
  }

  /**
   * Plot STA/LTA with triggers
   */
  function plotStalta(canvas, times, sta, lta, ratio, triggers, options = {}) {
    if (!canvas || !times || !times.length) return;
    const width = Math.max(320, options.width || canvas.parentElement?.clientWidth || canvas.clientWidth || 800);
    const height = Math.max(220, options.height || canvas.clientHeight || 300);
    const ctx = setupCanvas(canvas, width, height);
    if (!ctx) return;

    const count = Math.min(times.length, sta?.length || 0, lta?.length || 0, ratio?.length || 0);
    if (!count) return;
    const signal = options.signal || [];
    let xMin = Number.isFinite(options.xMin) ? options.xMin : Math.min(...times.slice(0, count));
    let xMax = Number.isFinite(options.xMax) ? options.xMax : Math.max(...times.slice(0, count));
    let rangeCache = staltaRangeCache.get(sta);
    if (!rangeCache || rangeCache.signal !== signal || rangeCache.lta !== lta || rangeCache.ratio !== ratio || rangeCache.count !== count) {
      let min = Infinity, max = -Infinity, maxRatio = 5;
      for (const arr of [signal, sta, lta]) {
        for (let i = 0; i < count && i < arr.length; i++) {
          const v = Number(arr[i]);
          if (arr[i] != null && Number.isFinite(v)) { if (v < min) min = v; if (v > max) max = v; }
        }
      }
      for (let i = 0; i < count; i++) {
        const v = Number(ratio[i]);
        if (ratio[i] != null && Number.isFinite(v) && v > maxRatio) maxRatio = v;
      }
      rangeCache = { signal, lta, ratio, count, min: min === Infinity ? -1 : min, max: max === -Infinity ? 1 : max, maxRatio };
      staltaRangeCache.set(sta, rangeCache);
    }
    let yMin = rangeCache.min, yMax = rangeCache.max;
    if (yMin === yMax) { yMin -= 1; yMax += 1; }
    const yPad = (yMax - yMin) * 0.08;
    yMin -= yPad; yMax += yPad;
    const ratioMax = rangeCache.maxRatio * 1.05;
    const left = 84, right = 58, top = 18, bottom = 38;
    const plotW = width - left - right, plotH = height - top - bottom;
    const px = t => left + ((t - xMin) / (xMax - xMin || 1)) * plotW;
    const py = v => top + (1 - (v - yMin) / (yMax - yMin)) * plotH;
    const pry = v => top + (1 - v / ratioMax) * plotH;

    let st = staltaChartState.get(canvas);
    const fullMin = Number(times[0]), fullMax = Number(times[count - 1]);
    if (!st || st.times !== times || st.sta !== sta) {
      st = { canvas, times, sta, lta, ratio, signal, triggers, options: { ...options }, count, fullMin, fullMax,
        fullSpan: fullMax - fullMin || 1, xMin: fullMin, xMax: fullMax, drag: null };
      staltaChartState.set(canvas, st);
    } else {
      Object.assign(st, { canvas, times, sta, lta, ratio, signal, triggers, options: { ...options }, count, fullMin, fullMax,
        fullSpan: fullMax - fullMin || 1 });
    }
    if (options.syncGroup) {
      if (!staltaChartGroups.has(options.syncGroup)) staltaChartGroups.set(options.syncGroup, new Set());
      staltaChartGroups.get(options.syncGroup).add(st);
    }
    st.xMin = Math.max(fullMin, options.viewXMin ?? st.xMin);
    st.xMax = Math.min(fullMax, options.viewXMax ?? st.xMax);
    xMin = st.xMin; xMax = st.xMax;
    attachStaltaInteractions(canvas);
    attachStaltaHover(canvas);

    ctx.clearRect(0, 0, width, height);
    ctx.font = '11px Inter, sans-serif';
    ctx.lineWidth = 1;
    // Grid and dual axes
    for (let k = 0; k <= 4; k++) {
      const y = top + plotH * k / 4;
      const amp = yMax - (yMax - yMin) * k / 4;
      const rat = ratioMax * (1 - k / 4);
      ctx.strokeStyle = COLORS.grid || '#DCE4EE';
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - right, y); ctx.stroke();
      ctx.fillStyle = COLORS.textMuted || '#64748B';
      ctx.textAlign = 'right'; ctx.fillText(amp.toPrecision(3), left - 8, y + 4);
      ctx.fillStyle = '#DC2626'; ctx.textAlign = 'left'; ctx.fillText(rat.toFixed(1), width - right + 8, y + 4);
    }
    const ticks = 5;
    for (let k = 0; k <= ticks; k++) {
      const t = xMin + (xMax - xMin) * k / ticks;
      const x = px(t);
      ctx.strokeStyle = COLORS.grid || '#DCE4EE';
      ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotH); ctx.stroke();
      ctx.fillStyle = COLORS.textMuted || '#64748B';
      ctx.textAlign = 'center'; ctx.fillText(t.toFixed(2), x, height - 18);
    }
    ctx.strokeStyle = '#94A3B8';
    ctx.strokeRect(left, top, plotW, plotH);
    ctx.fillStyle = COLORS.text || '#334155';
    ctx.textAlign = 'center'; ctx.fillText('Tiempo (s)', left + plotW / 2, height - 3);
    ctx.save(); ctx.translate(22, top + plotH / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.fillText(options.yLabel || 'Amplitud', 0, 0); ctx.restore();
    ctx.save(); ctx.translate(width - 10, top + plotH / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.fillStyle = '#DC2626'; ctx.fillText('Ratio STA/LTA', 0, 0); ctx.restore();

    const drawSeries = (values, color, mapY, lineWidth = 1.2) => {
      ctx.strokeStyle = color; ctx.lineWidth = lineWidth; ctx.beginPath();
      let lo = 0, hi = count;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (Number(times[mid]) < xMin) lo = mid + 1; else hi = mid; }
      let end = lo; hi = count;
      while (end < hi) { const mid = (end + hi) >> 1; if (Number(times[mid]) <= xMax) end = mid + 1; else hi = mid; }
      const step = Math.max(1, Math.ceil((end - lo) / Math.max(1, plotW * 2)));
      let active = false;
      for (let i = lo; i < end; i += step) {
        const t = Number(times[i]), v = values[i];
        if (!Number.isFinite(t) || v == null || !Number.isFinite(Number(v))) { active = false; continue; }
        const x = px(t), y = mapY(Number(v));
        if (!active) { ctx.moveTo(x, y); active = true; } else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };
    if (signal.length) drawSeries(signal, options.signalColor || '#2563EB', py, 1);
    drawSeries(sta, '#F59E0B', py, 1.5);
    drawSeries(lta, '#16A34A', py, 1.5);
    drawSeries(ratio, '#DC2626', pry, 1.5);

    if (Number.isInteger(options.cursorIndex) && options.cursorIndex >= 0 && options.cursorIndex < count) {
      const ci = options.cursorIndex;
      const cx = px(Number(times[ci]));
      ctx.save();
      ctx.strokeStyle = COLORS.cursor;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, top + plotH); ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    if (triggers?.length) {
      ctx.strokeStyle = '#DC2626'; ctx.setLineDash([4, 3]);
      for (const t of triggers) { if (Number.isFinite(Number(t))) { const x = px(Number(t)); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotH); ctx.stroke(); } }
      ctx.setLineDash([]);
    }
    // Compact legend
    const legend = [
      ...(signal.length ? [{ color: options.signalColor || '#2563EB', label: 'Señal' }] : []),
      { color: '#F59E0B', label: 'STA' }, { color: '#16A34A', label: 'LTA' }, { color: '#DC2626', label: 'Ratio STA/LTA' },
    ];
    ctx.font = '11px Inter, sans-serif'; ctx.textAlign = 'left';
    let lx = left + 4;
    for (const item of legend) {
      ctx.fillStyle = item.color; ctx.fillRect(lx, top + 8, 12, 3);
      ctx.fillStyle = COLORS.text || '#334155'; ctx.fillText(item.label, lx + 17, top + 12);
      lx += 28 + ctx.measureText(item.label).width;
    }
  }

  // Public API
  return {
    plotTimeSeries,
    plotSpectrum,
    plotSpectrogram,
    plotStalta,
    COLORS,
  };
})();
