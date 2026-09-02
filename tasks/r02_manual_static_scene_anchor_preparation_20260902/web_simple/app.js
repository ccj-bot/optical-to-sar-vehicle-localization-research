let boundaryOrder = [
  "OPT_BOUNDARY_NEAR",
  "OPT_BOUNDARY_FAR",
  "SAR_BOUNDARY_NEAR",
  "SAR_BOUNDARY_FAR",
];

const colors = {
  OPT_BOUNDARY_NEAR: "#00c7d8",
  OPT_BOUNDARY_FAR: "#ff9d2e",
  SAR_BOUNDARY_NEAR: "#00c7d8",
  SAR_BOUNDARY_FAR: "#ff9d2e",
  OPT_STATIC_TREE_A: "#31d17c",
  OPT_STATIC_TREE_B: "#45a8ff",
  OPT_STATIC_TREE_C: "#ed66dc",
  SAR_STATIC_POINT_TREE_A: "#31d17c",
  SAR_STATIC_POINT_TREE_B: "#45a8ff",
  SAR_STATIC_POINT_TREE_C: "#ed66dc",
};

let state = null;
let currentIndex = 0;
let activeObjectType = "OPT_BOUNDARY_NEAR";
let confidenceState = "CONFIDENT";
let hintsEnabled = false;
let workflowMode = "FULL_STATIC_SCENE";
let spaceDown = false;
let toastTimer = null;

const saveState = document.getElementById("saveState");
const toast = document.getElementById("toast");
const workspace = document.getElementById("workspace");
const opticalCard = document.getElementById("opticalCard");
const sarCard = document.getElementById("sarCard");

function workflowViewers() {
  return workflowMode === "SAR_BOUNDARY_ONLY" ? [sarViewer] : viewers;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 1800);
}

function setSaveStatus(kind, text) {
  saveState.className = `save-state ${kind}`;
  saveState.textContent = text;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function currentPair() {
  return state.batch[currentIndex];
}

function labelFor(objectType) {
  return state.labels.find((item) => item.object_type === objectType);
}

function annotationFor(objectType) {
  const batchIndex = currentPair().batch_index;
  return state.annotations.find((item) => item.batch_index === batchIndex && item.object_type === objectType) || null;
}

function annotationsFor(modality) {
  const batchIndex = currentPair().batch_index;
  return state.annotations.filter((item) => item.batch_index === batchIndex && item.modality === modality);
}

function updateStateFromResponse(payload) {
  if (payload.state) {
    state.annotations = payload.state.annotations;
    state.session = payload.state.session;
  }
}

async function saveAnnotation(objectType, points, geometryStatus, visibilityState = "VISIBLE_OR_GEOMETRY_PROVIDED", confidence = confidenceState) {
  setSaveStatus("saving", "正在保存…");
  try {
    const payload = await api("/api/save", {
      method: "POST",
      body: JSON.stringify({
        batch_index: currentPair().batch_index,
        object_type: objectType,
        points,
        confidence_state: confidence,
        geometry_status: geometryStatus,
        visibility_state: visibilityState,
      }),
    });
    updateStateFromResponse(payload);
    setSaveStatus("saved", "已自动保存");
    updateUI();
    workflowViewers().forEach((viewer) => viewer.draw());
    return payload.record;
  } catch (error) {
    setSaveStatus("error", "保存失败");
    showToast(`保存失败：${error.message}`);
    throw error;
  }
}

async function deleteAnnotation(objectType) {
  setSaveStatus("saving", "正在保存…");
  try {
    const payload = await api("/api/delete", {
      method: "POST",
      body: JSON.stringify({ batch_index: currentPair().batch_index, object_type: objectType }),
    });
    updateStateFromResponse(payload);
    setSaveStatus("saved", "已自动保存");
    updateUI();
    workflowViewers().forEach((viewer) => viewer.draw());
  } catch (error) {
    setSaveStatus("error", "保存失败");
    showToast(`删除失败：${error.message}`);
  }
}

async function updateSession(extra = {}) {
  const payload = await api("/api/session", {
    method: "POST",
    body: JSON.stringify({
      current_index: currentIndex,
      confidence_state: confidenceState,
      hints_enabled: hintsEnabled,
      ...extra,
    }),
  });
  state.session = payload.session;
}

class ImageViewer {
  constructor(canvasId, modality, coordId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.modality = modality;
    this.coord = document.getElementById(coordId);
    this.image = new Image();
    this.imageLoaded = false;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.cssWidth = 1;
    this.cssHeight = 1;
    this.panning = false;
    this.panStart = null;
    this.dragVertex = null;
    this.pointerImage = null;
    this.image.onload = () => {
      this.imageLoaded = true;
      this.fit();
    };
    this.canvas.addEventListener("contextmenu", (event) => event.preventDefault());
    this.canvas.addEventListener("wheel", (event) => this.onWheel(event), { passive: false });
    this.canvas.addEventListener("pointerdown", (event) => this.onPointerDown(event));
    this.canvas.addEventListener("pointermove", (event) => this.onPointerMove(event));
    this.canvas.addEventListener("pointerup", (event) => this.onPointerUp(event));
    this.canvas.addEventListener("pointercancel", (event) => this.onPointerUp(event));
    new ResizeObserver(() => this.resize()).observe(this.canvas);
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    if (width === this.cssWidth && height === this.cssHeight) return;
    this.cssWidth = width;
    this.cssHeight = height;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (this.imageLoaded) this.fit();
  }

  load() {
    this.imageLoaded = false;
    this.image.src = `/api/image?batch_index=${currentPair().batch_index}&modality=${this.modality}&v=${currentPair().batch_index}`;
  }

  fit() {
    if (!this.imageLoaded) return;
    this.scale = Math.min(this.cssWidth / this.image.naturalWidth, this.cssHeight / this.image.naturalHeight);
    this.offsetX = (this.cssWidth - this.image.naturalWidth * this.scale) / 2;
    this.offsetY = (this.cssHeight - this.image.naturalHeight * this.scale) / 2;
    this.draw();
  }

  screenPoint(event) {
    const rect = this.canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  toImage(screen) {
    return [(screen.x - this.offsetX) / this.scale, (screen.y - this.offsetY) / this.scale];
  }

  toScreen(point) {
    return { x: this.offsetX + point[0] * this.scale, y: this.offsetY + point[1] * this.scale };
  }

  inside(point) {
    return point[0] >= 0 && point[1] >= 0 && point[0] < this.image.naturalWidth && point[1] < this.image.naturalHeight;
  }

  onWheel(event) {
    if (!this.imageLoaded) return;
    event.preventDefault();
    const screen = this.screenPoint(event);
    const imagePoint = this.toImage(screen);
    const fitScale = Math.min(this.cssWidth / this.image.naturalWidth, this.cssHeight / this.image.naturalHeight);
    const factor = event.deltaY < 0 ? 1.18 : 1 / 1.18;
    const newScale = Math.min(Math.max(this.scale * factor, fitScale), fitScale * 14);
    this.offsetX = screen.x - imagePoint[0] * newScale;
    this.offsetY = screen.y - imagePoint[1] * newScale;
    this.scale = newScale;
    this.draw();
  }

  hitVertex(screen) {
    const annotation = annotationFor(activeObjectType);
    if (!annotation || annotation.modality !== this.modality || !annotation.points) return null;
    for (let index = 0; index < annotation.points.length; index += 1) {
      const target = this.toScreen(annotation.points[index]);
      if (Math.hypot(target.x - screen.x, target.y - screen.y) <= 13) return { annotation, index };
    }
    return null;
  }

  async onPointerDown(event) {
    if (!this.imageLoaded) return;
    const screen = this.screenPoint(event);
    if (spaceDown || event.button === 1 || event.button === 2) {
      this.panning = true;
      this.panStart = { x: screen.x, y: screen.y, offsetX: this.offsetX, offsetY: this.offsetY };
      this.canvas.setPointerCapture(event.pointerId);
      return;
    }
    if (event.button !== 0) return;
    const label = labelFor(activeObjectType);
    if (label.modality !== this.modality) {
      showToast(`当前步骤要在 ${label.modality === "OPTICAL" ? "左侧光学图" : "右侧 SAR 图"}上操作`);
      return;
    }
    const vertex = this.hitVertex(screen);
    if (vertex) {
      this.dragVertex = vertex;
      this.canvas.setPointerCapture(event.pointerId);
      return;
    }
    const point = this.toImage(screen);
    if (!this.inside(point)) return;
    const existing = annotationFor(activeObjectType);
    if (label.geometry_type === "point") {
      await saveAnnotation(activeObjectType, [point], "COMPLETE");
      showToast("点已精确保存，可直接拖动修正");
      return;
    }
    if (existing && existing.geometry_status === "COMPLETE" && existing.points.length) {
      showToast("这条线已完成：拖动节点微调，或点“清空重画”");
      return;
    }
    const points = existing && existing.geometry_status === "DRAFT" ? [...existing.points, point] : [point];
    await saveAnnotation(activeObjectType, points, "DRAFT");
  }

  onPointerMove(event) {
    if (!this.imageLoaded) return;
    const screen = this.screenPoint(event);
    const imagePoint = this.toImage(screen);
    this.pointerImage = this.inside(imagePoint) ? imagePoint : null;
    this.coord.textContent = this.pointerImage ? `x ${imagePoint[0].toFixed(1)}, y ${imagePoint[1].toFixed(1)}` : "x —, y —";
    if (this.panning && this.panStart) {
      this.offsetX = this.panStart.offsetX + screen.x - this.panStart.x;
      this.offsetY = this.panStart.offsetY + screen.y - this.panStart.y;
    }
    if (this.dragVertex) {
      const annotation = this.dragVertex.annotation;
      if (this.inside(imagePoint)) annotation.points[this.dragVertex.index] = imagePoint;
    }
    this.draw();
  }

  async onPointerUp(event) {
    if (this.panning) {
      this.panning = false;
      this.panStart = null;
      try { this.canvas.releasePointerCapture(event.pointerId); } catch (_) {}
      return;
    }
    if (this.dragVertex) {
      const annotation = this.dragVertex.annotation;
      this.dragVertex = null;
      try { this.canvas.releasePointerCapture(event.pointerId); } catch (_) {}
      await saveAnnotation(
        annotation.object_type,
        annotation.points,
        annotation.geometry_status,
        annotation.visibility_state,
        annotation.confidence_state,
      );
      showToast("节点位置已自动保存");
    }
  }

  drawHints(ctx) {
    if (!hintsEnabled || workflowMode === "SAR_BOUNDARY_ONLY") return;
    ctx.save();
    ctx.translate(this.offsetX, this.offsetY);
    ctx.scale(this.scale, this.scale);
    ctx.lineWidth = 1.5 / this.scale;
    ctx.font = `${12 / this.scale}px "Segoe UI"`;
    if (this.modality === "OPTICAL") {
      const slope = 0.02666536443690682;
      const intercept = -45.502258572693094;
      [-30, 0, 30].forEach((theta) => {
        const x = (theta - intercept) / slope;
        ctx.strokeStyle = "rgba(255,255,255,.55)";
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.image.naturalHeight); ctx.stroke();
        ctx.fillStyle = "rgba(255,255,255,.85)";
        ctx.fillText(`AUTOMATIC_HINT θ=${theta}°`, x + 8 / this.scale, 24 / this.scale);
      });
    } else {
      const cx = 511.745326, cy = 590.776351, ppm = 591.340317 / 20;
      [[4.9, "#00c7d8"], [7.1, "#ff9d2e"], [12.4, "#ed66dc"]].forEach(([distance, color]) => {
        const y = cy - distance * ppm;
        const x0 = cx + distance * ppm * Math.tan(-48 * Math.PI / 180);
        const x1 = cx + distance * ppm * Math.tan(48 * Math.PI / 180);
        ctx.strokeStyle = color; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
        ctx.fillStyle = color; ctx.fillText(`AUTOMATIC_HINT ${distance}m`, Math.max(3, x0), y - 5 / this.scale);
      });
    }
    ctx.restore();
  }

  drawAnnotations(ctx) {
    ctx.save();
    ctx.translate(this.offsetX, this.offsetY);
    ctx.scale(this.scale, this.scale);
    annotationsFor(this.modality).forEach((annotation) => {
      const color = colors[annotation.object_type] || "#ffffff";
      const isActive = annotation.object_type === activeObjectType;
      const points = annotation.points || [];
      if (!points.length) return;
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = (isActive ? 4 : 2.5) / this.scale;
      ctx.beginPath();
      points.forEach((point, index) => index ? ctx.lineTo(point[0], point[1]) : ctx.moveTo(point[0], point[1]));
      if (annotation.geometry_type === "polyline") ctx.stroke();
      points.forEach((point) => {
        ctx.beginPath();
        ctx.arc(point[0], point[1], (isActive ? 7 : 4.5) / this.scale, 0, Math.PI * 2);
        ctx.fill();
        if (isActive) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1.4 / this.scale;
          ctx.stroke();
          ctx.strokeStyle = color;
        }
      });
      ctx.font = `${13 / this.scale}px "Microsoft YaHei UI"`;
      ctx.fillText(`${annotation.object_type} · ${annotation.confidence_state}`, points[0][0] + 10 / this.scale, points[0][1] - 10 / this.scale);
    });
    ctx.restore();
  }

  draw() {
    const ctx = this.ctx;
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    ctx.clearRect(0, 0, this.cssWidth, this.cssHeight);
    ctx.fillStyle = "#0a1016";
    ctx.fillRect(0, 0, this.cssWidth, this.cssHeight);
    if (!this.imageLoaded) return;
    ctx.drawImage(this.image, this.offsetX, this.offsetY, this.image.naturalWidth * this.scale, this.image.naturalHeight * this.scale);
    this.drawHints(ctx);
    this.drawAnnotations(ctx);
    if (this.pointerImage) {
      const point = this.toScreen(this.pointerImage);
      ctx.strokeStyle = "rgba(255,255,255,.8)";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(point.x - 10, point.y); ctx.lineTo(point.x + 10, point.y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(point.x, point.y - 10); ctx.lineTo(point.x, point.y + 10); ctx.stroke();
    }
  }
}

const opticalViewer = new ImageViewer("opticalCanvas", "OPTICAL", "opticalCoord");
const sarViewer = new ImageViewer("sarCanvas", "SAR", "sarCoord");
const viewers = [opticalViewer, sarViewer];

function setActiveObject(objectType) {
  activeObjectType = objectType;
  const label = labelFor(objectType);
  const existing = annotationFor(objectType);
  if (existing && ["CONFIDENT", "LIKELY"].includes(existing.confidence_state)) confidenceState = existing.confidence_state;
  workspace.className = `workspace ${label.modality === "OPTICAL" ? "active-optical" : "active-sar"}`;
  opticalCard.classList.toggle("active", label.modality === "OPTICAL");
  sarCard.classList.toggle("active", label.modality === "SAR");
  updateUI();
  setTimeout(() => workflowViewers().forEach((viewer) => viewer.fit()), 210);
}

function objectComplete(objectType) {
  const annotation = annotationFor(objectType);
  return annotation && annotation.geometry_status === "COMPLETE";
}

function updateUI() {
  if (!state) return;
  const pair = currentPair();
  document.getElementById("pairProgress").textContent = workflowMode === "SAR_BOUNDARY_ONLY"
    ? `第 ${currentIndex + 1} / ${state.batch.length} 张 keyframe`
    : `第 ${currentIndex + 1} / ${state.batch.length} 对`;
  document.getElementById("timestampInfo").textContent = workflowMode === "SAR_BOUNDARY_ONLY"
    ? `${pair.bracket_id} · ${pair.seed_role} ｜ SAR F${String(pair.sar_frame_index).padStart(3, "0")} · ${pair.sar_timestamp_ms} ms`
    : `OPT F${String(pair.optical_frame_index).padStart(3, "0")} · ${pair.optical_timestamp_ms} ms  ↔  SAR F${String(pair.sar_frame_index).padStart(3, "0")} · ${pair.sar_timestamp_ms} ms  ｜残差 ${pair.nominal_timestamp_residual_ms >= 0 ? "+" : ""}${pair.nominal_timestamp_residual_ms} ms`;
  document.getElementById("opticalFrame").textContent = `F${pair.optical_frame_index} · ${pair.optical_timestamp_ms} ms`;
  document.getElementById("sarFrame").textContent = `F${pair.sar_frame_index} · ${pair.sar_timestamp_ms} ms`;
  document.querySelectorAll("[data-object]").forEach((button) => {
    const objectType = button.dataset.object;
    const annotation = annotationFor(objectType);
    button.classList.toggle("active", objectType === activeObjectType);
    button.classList.toggle("complete", Boolean(annotation && annotation.geometry_status === "COMPLETE" && annotation.visibility_state === "VISIBLE_OR_GEOMETRY_PROVIDED"));
    button.classList.toggle("unresolved", Boolean(annotation && annotation.geometry_status === "COMPLETE" && annotation.visibility_state !== "VISIBLE_OR_GEOMETRY_PROVIDED"));
  });
  document.querySelectorAll("[data-confidence]").forEach((button) => button.classList.toggle("selected", button.dataset.confidence === confidenceState));
  document.getElementById("hintToggle").checked = hintsEnabled;
  document.getElementById("previousPair").disabled = currentIndex === 0;
  document.getElementById("nextPair").disabled = currentIndex === state.batch.length - 1;
}

async function changePair(delta, resetStep = false) {
  const next = Math.min(Math.max(currentIndex + delta, 0), state.batch.length - 1);
  if (next === currentIndex) return;
  currentIndex = next;
  if (resetStep) activeObjectType = boundaryOrder[0];
  await updateSession();
  updateUI();
  workflowViewers().forEach((viewer) => viewer.load());
  setActiveObject(activeObjectType);
}

async function advanceGuidedStep() {
  const index = boundaryOrder.indexOf(activeObjectType);
  if (index >= 0 && index < boundaryOrder.length - 1) {
    setActiveObject(boundaryOrder[index + 1]);
  } else if (index === boundaryOrder.length - 1) {
    if (currentIndex < state.batch.length - 1) await changePair(1, true);
    else showToast(`${state.batch.length} 张 keyframe 已经浏览完成，可以保存退出`);
  }
}

async function finishCurrent() {
  const label = labelFor(activeObjectType);
  const annotation = annotationFor(activeObjectType);
  if (label.geometry_type === "point") {
    if (!annotation || !annotation.points.length) return showToast("请先在图中点一下目标中心");
    await saveAnnotation(activeObjectType, annotation.points, "COMPLETE");
    return;
  }
  if (!annotation || annotation.points.length < 2) return showToast("折线至少需要两个点，通常 3–8 点即可");
  await saveAnnotation(activeObjectType, annotation.points, "COMPLETE");
  showToast("这一条已完成，自动进入下一项");
  await advanceGuidedStep();
}

async function undoPoint() {
  const annotation = annotationFor(activeObjectType);
  if (!annotation || !annotation.points.length) return showToast("当前没有可撤销的点");
  const points = annotation.points.slice(0, -1);
  if (!points.length) await deleteAnnotation(activeObjectType);
  else await saveAnnotation(activeObjectType, points, "DRAFT", "VISIBLE_OR_GEOMETRY_PROVIDED", annotation.confidence_state);
}

async function markUnresolved(confidence, visibility) {
  await saveAnnotation(activeObjectType, [], "COMPLETE", visibility, confidence);
  showToast(confidence === "NOT_VISIBLE" ? "已记录为不可见" : "已记录为无法判断");
  if (boundaryOrder.includes(activeObjectType)) await advanceGuidedStep();
}

document.querySelectorAll("[data-object]").forEach((button) => button.addEventListener("click", () => setActiveObject(button.dataset.object)));
document.querySelectorAll("[data-confidence]").forEach((button) => button.addEventListener("click", async () => {
  confidenceState = button.dataset.confidence;
  await updateSession();
  const annotation = annotationFor(activeObjectType);
  if (annotation && annotation.points.length) await saveAnnotation(activeObjectType, annotation.points, annotation.geometry_status, annotation.visibility_state, confidenceState);
  updateUI();
}));
document.querySelectorAll("[data-fit]").forEach((button) => button.addEventListener("click", () => (button.dataset.fit === "OPTICAL" ? opticalViewer : sarViewer).fit()));

document.getElementById("previousPair").addEventListener("click", () => changePair(-1));
document.getElementById("nextPair").addEventListener("click", () => changePair(1));
document.getElementById("skipPair").addEventListener("click", async () => {
  await updateSession({ skip_batch_index: currentPair().batch_index });
  showToast("已跳过这一对，可以随时返回");
  if (currentIndex < state.batch.length - 1) await changePair(1, true);
});
document.getElementById("finishObject").addEventListener("click", finishCurrent);
document.getElementById("undoPoint").addEventListener("click", undoPoint);
document.getElementById("clearObject").addEventListener("click", () => deleteAnnotation(activeObjectType));
document.getElementById("uncertainObject").addEventListener("click", () => markUnresolved("UNCERTAIN", "UNRESOLVED_BY_USER"));
document.getElementById("notVisibleObject").addEventListener("click", () => markUnresolved("NOT_VISIBLE", "NOT_VISIBLE"));
document.getElementById("treeUnknown").addEventListener("click", async () => {
  const label = labelFor(activeObjectType);
  if (label.modality !== "SAR" || !label.object_type.includes("TREE")) return showToast("请先选择一个 SAR Tree A/B/C");
  await markUnresolved("UNCERTAIN", "TREE_UNKNOWN");
});
document.getElementById("hintToggle").addEventListener("change", async (event) => {
  if (workflowMode === "SAR_BOUNDARY_ONLY") {
    hintsEnabled = false;
    event.target.checked = false;
    return showToast("本批次不显示自动提示");
  }
  hintsEnabled = event.target.checked;
  await updateSession();
  workflowViewers().forEach((viewer) => viewer.draw());
  showToast(hintsEnabled ? "自动提示已打开：它不是答案" : "自动提示已关闭");
});
document.getElementById("saveAndExit").addEventListener("click", async () => {
  setSaveStatus("saving", "正在退出…");
  try {
    await api("/api/shutdown", { method: "POST", body: "{}" });
    document.body.innerHTML = '<main style="max-width:620px;margin:15vh auto;padding:30px;background:white;border-radius:14px;font-family:Microsoft YaHei UI"><h2>已保存并退出</h2><p>可以关闭这个浏览器标签页。人工 JSONL、summary、progress 和 coverage report 都已写入。</p></main>';
  } catch (error) {
    showToast(`退出失败：${error.message}`);
  }
});

document.addEventListener("keydown", async (event) => {
  if (event.code === "Space") { spaceDown = true; event.preventDefault(); return; }
  if (event.key === "Enter") { event.preventDefault(); await finishCurrent(); }
  else if (event.key === "Backspace") { event.preventDefault(); await undoPoint(); }
  else if (event.key === "Delete") { event.preventDefault(); await deleteAnnotation(activeObjectType); }
  else if (event.key === "ArrowRight") { event.preventDefault(); await changePair(1); }
  else if (event.key === "ArrowLeft") { event.preventDefault(); await changePair(-1); }
  else if (event.key.toLowerCase() === "s") { event.preventDefault(); document.getElementById("skipPair").click(); }
  else if (event.key.toLowerCase() === "h") { event.preventDefault(); document.getElementById("hintToggle").click(); }
});
document.addEventListener("keyup", (event) => { if (event.code === "Space") spaceDown = false; });
window.addEventListener("blur", () => { spaceDown = false; });

async function initialize() {
  try {
    state = await api("/api/state");
    workflowMode = state.workflow_mode || "FULL_STATIC_SCENE";
    boundaryOrder = state.guided_boundary_order || boundaryOrder;
    document.body.classList.toggle("sar-only", workflowMode === "SAR_BOUNDARY_ONLY");
    if (workflowMode === "SAR_BOUNDARY_ONLY") {
      document.getElementById("pageTitle").textContent = "SAR 端点边界标注";
      document.getElementById("workflowTitle").textContent = "每张只做两步 SAR 边界";
      document.getElementById("previousPair").textContent = "← 上一张";
      document.getElementById("nextPair").textContent = "下一张 →";
      document.getElementById("skipPair").textContent = "跳过这张";
      document.querySelector('[data-object="SAR_BOUNDARY_NEAR"] b').textContent = "1";
      document.querySelector('[data-object="SAR_BOUNDARY_FAR"] b').textContent = "2";
    }
    currentIndex = Math.min(Math.max(Number(state.session.current_index || 0), 0), state.batch.length - 1);
    confidenceState = ["CONFIDENT", "LIKELY"].includes(state.session.confidence_state) ? state.session.confidence_state : "CONFIDENT";
    hintsEnabled = workflowMode === "SAR_BOUNDARY_ONLY" ? false : Boolean(state.session.hints_enabled);
    const existingDraft = state.annotations.find((item) => item.batch_index === currentPair().batch_index && item.geometry_status === "DRAFT" && boundaryOrder.includes(item.object_type));
    activeObjectType = existingDraft ? existingDraft.object_type : boundaryOrder[0];
    updateUI();
    workflowViewers().forEach((viewer) => viewer.load());
    setActiveObject(activeObjectType);
    setSaveStatus("saved", "已自动保存");
    showToast(existingDraft ? "已恢复你上次未完成的草稿" : `从${workflowMode === "SAR_BOUNDARY_ONLY" ? "SAR 近边" : "光学近边"}开始，画完按 Enter`);
  } catch (error) {
    setSaveStatus("error", "载入失败");
    showToast(`载入失败：${error.message}`);
  }
}

initialize();
