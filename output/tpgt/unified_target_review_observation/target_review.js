(function () {
  'use strict';

  const DATA = window.TPGT_REVIEW_DATA;
  const query = new URLSearchParams(location.search);
  const sceneId = query.get('scene') || 'GM_RM017';
  const scene = DATA.scenes[sceneId];
  const $ = id => document.getElementById(id);
  const storageKey = 'TPGT_OPTICAL_HUMAN_TARGET_SET_' + sceneId;
  const conditionIds = {
    IMAGE_EDGE_TRUNCATED: 'edgeTruncated',
    NEAR_FIELD_TRUNCATED: 'nearTruncated',
    OCCLUDED: 'occluded'
  };
  const zh = {
    car: '车辆', truck: '卡车', person: '人员', motorcycle: '摩托车', bus: '公交车', unknown: '未知',
    UNKNOWN: '不确定', COMPLETE_VISIBLE: '完整可见', PARTIAL_VISIBLE: '部分可见',
    VISIBLE_UNBOXED: '可见但无可靠框', NOT_VISIBLE: '不可见',
    IMAGE_EDGE_TRUNCATED: '边缘截断', NEAR_FIELD_TRUNCATED: '近场截断', OCCLUDED: '遮挡'
  };

  let frame = 0;
  let timer = null;
  let mode = 'select';
  let manualDrag = null;
  let pendingNewTarget = false;
  let pendingChoices = [];
  let previewChoiceIndex = null;
  let currentPreviewIndex = null;

  function blankReview() {
    return {
      schema_version: 'TPGT_OPTICAL_HUMAN_TARGET_SET_v0.1',
      scene_id: sceneId,
      targets: {},
      active_target_id: null,
      updated_at: new Date().toISOString()
    };
  }

  function loadReview() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey));
      return parsed && parsed.scene_id === sceneId ? parsed : blankReview();
    } catch (_) {
      return blankReview();
    }
  }

  let review = loadReview();

  function normalize() {
    review.schema_version = 'TPGT_OPTICAL_HUMAN_TARGET_SET_v0.1';
    review.scene_id = sceneId;
    review.targets = review.targets || {};
    review.edit_history = review.edit_history || [];
    review.deleted_targets = review.deleted_targets || [];
    for (const target of Object.values(review.targets)) {
      target.anchors = target.anchors || [];
      target.frame_observations = target.frame_observations || {};
      target.identity_segments = target.identity_segments || [];
      target.visible_segments = target.visible_segments || [];
      target.formal_annotations = target.formal_annotations || [];
      target.primary_annotation_frame_index = target.primary_annotation_frame_index ?? null;
      target.primary_core_interval = target.primary_core_interval || [null, null];
      target.research_status = target.research_status || 'DEFER_COMPLEX';
      target.identity_relation = target.identity_relation || 'AMBIGUOUS';
      target.frozen_revisions = target.frozen_revisions || [];
      for (const observation of Object.values(target.frame_observations)) {
        observation.condition_flags = observation.condition_flags || [];
        if (observation.visibility_state === 'OCCLUDED') {
          observation.visibility_state = 'PARTIAL_VISIBLE';
          if (!observation.condition_flags.includes('OCCLUDED')) observation.condition_flags.push('OCCLUDED');
        }
      }
    }
  }

  normalize();

  function save() {
    review.updated_at = new Date().toISOString();
    localStorage.setItem(storageKey, JSON.stringify(review));
  }

  function active() {
    return review.targets[review.active_target_id] || null;
  }

  function detections(f) {
    return ['yolo11', 'yolo26'].flatMap(model => (scene.detections?.[model] || []).filter(d => d.frame === f));
  }

  function detectionVisible(detection) {
    const hiddenModel = (detection.model === 'YOLO11' && !$('yolo11Toggle').checked) || (detection.model === 'YOLO26' && !$('yolo26Toggle').checked);
    const hiddenClass = (detection.class_name === 'person' && !$('personToggle').checked) || (detection.class_name !== 'person' && !$('carToggle').checked);
    return !hiddenModel && !hiddenClass;
  }

  function sameTargetDomain(targetClass, detectionClass) {
    return (targetClass === 'person') === (detectionClass === 'person');
  }

  function boxCopy(box) {
    return box ? {x1: box.x1, y1: box.y1, x2: box.x2, y2: box.y2} : null;
  }

  function area(box) {
    return Math.max(0, box.x2 - box.x1) * Math.max(0, box.y2 - box.y1);
  }

  function center(box) {
    return {x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2};
  }

  function iou(a, b) {
    const w = Math.max(0, Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1));
    const h = Math.max(0, Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1));
    const intersection = w * h;
    const union = area(a) + area(b) - intersection;
    return union ? intersection / union : 0;
  }

  function proposal(target, f) {
    const observations = target.frame_observations || {};
    const nearbyFrames = Object.keys(observations).map(Number).filter(k => observations[k].bbox).sort((a, b) => Math.abs(a - f) - Math.abs(b - f));
    const previous = observations[nearbyFrames[0]]?.bbox || target.anchors.at(-1)?.bbox;
    if (!previous) return null;
    const previousCenter = center(previous);
    const diagonal = Math.hypot(scene.width, scene.height) || 1;
    const candidates = detections(f).filter(d => d.class_name === target.class);
    return candidates.map(d => {
      const c = center(d);
      const distance = Math.hypot(c.x - previousCenter.x, c.y - previousCenter.y) / diagonal;
      const scale = Math.min(area(d), area(previous)) / Math.max(area(d), area(previous), 1);
      return {detection: d, score: 2 * iou(d, previous) + 0.5 * scale - distance};
    }).sort((a, b) => b.score - a.score)[0]?.detection || null;
  }

  function mergeSegments(segments) {
    const sorted = segments.filter(s => Number.isInteger(s[0]) && Number.isInteger(s[1])).map(s => [Math.min(s[0], s[1]), Math.max(s[0], s[1])]).sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const segment of sorted) {
      const last = merged.at(-1);
      if (!last || segment[0] > last[1] + 1) merged.push(segment);
      else last[1] = Math.max(last[1], segment[1]);
    }
    return merged;
  }

  function removeFrameFromSegments(segments, removedFrame) {
    return removeRangeFromSegments(segments, removedFrame, removedFrame);
  }

  function removeRangeFromSegments(segments, removedStart, removedEnd) {
    const result = [];
    for (const [start, end] of segments || []) {
      if (removedEnd < start || removedStart > end) result.push([start, end]);
      else {
        if (start < removedStart) result.push([start, removedStart - 1]);
        if (removedEnd < end) result.push([removedEnd + 1, end]);
      }
    }
    return result;
  }

  function updatePrimaryAnnotation(target) {
    target.formal_annotations.sort((a, b) => a.frame_index - b.frame_index);
    if (!target.formal_annotations.some(item => item.frame_index === target.primary_annotation_frame_index)) {
      target.primary_annotation_frame_index = target.formal_annotations.at(-1)?.frame_index ?? null;
    }
    target.primary_core_interval = target.primary_annotation_frame_index == null
      ? [null, null]
      : [target.primary_annotation_frame_index, target.primary_annotation_frame_index];
  }

  function clearProposalChooser() {
    pendingChoices = [];
    previewChoiceIndex = null;
    $('proposalChooser').classList.add('hidden');
    $('proposalChoices').innerHTML = '';
  }

  function renderCurrentFrameCandidates(target) {
    const list = $('currentFrameCandidateList');
    const choices = detections(frame).filter(detectionVisible);
    currentPreviewIndex = null;
    if (!choices.length) {
      list.className = 'candidate-list muted';
      list.textContent = '当前帧没有 detector 候选；可以使用“手动画框”。';
      return;
    }
    list.className = 'candidate-list';
    list.innerHTML = choices.map((detection, index) => {
      const incompatible = target && !pendingNewTarget && !sameTargetDomain(target.class, detection.class_name);
      const width = Math.round(detection.x2 - detection.x1);
      const height = Math.round(detection.y2 - detection.y1);
      return `<button class="candidate-choice ${incompatible ? 'incompatible' : ''}" data-candidate="${index}" ${incompatible ? 'disabled title="当前目标类别不匹配"' : ''}>${index + 1}. ${detection.model} · ${zh[detection.class_name] || detection.class_name} · 置信度 ${detection.confidence.toFixed(2)} · ${width}×${height}</button>`;
    }).join('');
    document.querySelectorAll('.candidate-choice').forEach(button => {
      button.onmouseenter = () => {currentPreviewIndex = Number(button.dataset.candidate); draw();};
      button.onmouseleave = () => {currentPreviewIndex = null; draw();};
      button.onclick = () => useBox(choices[Number(button.dataset.candidate)], choices[Number(button.dataset.candidate)].model, choices[Number(button.dataset.candidate)].class_name);
    });
  }

  function showProposalChooser(choices) {
    pendingChoices = choices;
    previewChoiceIndex = 0;
    $('proposalChooser').classList.remove('hidden');
    $('proposalChoices').innerHTML = choices.map((detection, index) => {
      const width = Math.round(detection.x2 - detection.x1);
      const height = Math.round(detection.y2 - detection.y1);
      return `<button class="proposal-choice" data-choice="${index}">${index + 1}. ${detection.model} · ${zh[detection.class_name] || detection.class_name} · 置信度 ${detection.confidence.toFixed(2)} · ${width}×${height}</button>`;
    }).join('');
    document.querySelectorAll('.proposal-choice').forEach(button => {
      button.onmouseenter = () => {previewChoiceIndex = Number(button.dataset.choice); draw();};
      button.onclick = () => {
        const selected = pendingChoices[Number(button.dataset.choice)];
        clearProposalChooser();
        useBox(selected, selected.model, selected.class_name);
      };
    });
    setStatus(`此处命中 ${choices.length} 个候选框，请在右侧选择；鼠标移到候选项可预览。`);
    draw();
  }

  function visibleSegments(target) {
    const visibleFrames = Object.keys(target.frame_observations).map(Number).filter(f => {
      const state = target.frame_observations[f].visibility_state;
      return ['COMPLETE_VISIBLE', 'PARTIAL_VISIBLE', 'VISIBLE_UNBOXED'].includes(state);
    }).sort((a, b) => a - b);
    return mergeSegments(visibleFrames.map(f => [f, f]));
  }

  function selectedConditions() {
    return Object.entries(conditionIds).filter(([, id]) => $(id).checked).map(([flag]) => flag);
  }

  function bboxRole(visibility, conditions, box) {
    if (!box) return 'UNKNOWN';
    if (visibility === 'COMPLETE_VISIBLE' && conditions.length === 0) return 'FULL_VISIBLE_TARGET';
    return 'VISIBLE_SUPPORT_ONLY';
  }

  function ensureObservation(target, f) {
    if (!target.frame_observations[f]) {
      target.frame_observations[f] = {
        frame_index: f,
        visibility_state: 'UNKNOWN',
        condition_flags: [],
        bbox: null,
        bbox_role: 'UNKNOWN',
        bbox_source: 'NONE',
        identity_relation: 'UNKNOWN',
        human_confirmed: false,
        note: ''
      };
    }
    return target.frame_observations[f];
  }

  function recordBox(target, f, box, source) {
    const observation = ensureObservation(target, f);
    observation.bbox = boxCopy(box);
    observation.bbox_source = source;
    observation.human_confirmed = true;
    observation.identity_relation = 'SAME_TARGET_HUMAN_CONFIRMED';
    observation.bbox_role = bboxRole(observation.visibility_state, observation.condition_flags || [], observation.bbox);
    target.anchors.push({
      frame_index: f,
      bbox: boxCopy(box),
      bbox_role: observation.bbox_role,
      bbox_source: source,
      created_at: new Date().toISOString()
    });
    target.identity_segments = mergeSegments([...(target.identity_segments || []), [f, f]]);
    target.visible_segments = visibleSegments(target);
  }

  function nextTargetId(className) {
    const stem = className === 'person' ? 'PERSON' : 'CAR';
    const numbers = Object.keys(review.targets).filter(id => id.includes(`HUMAN_${stem}_`)).map(id => Number(id.split('_').at(-1))).filter(Number.isFinite);
    return `${sceneId}:HUMAN_${stem}_${String((numbers.length ? Math.max(...numbers) : 0) + 1).padStart(3, '0')}`;
  }

  function createTarget(className, box, source) {
    const id = nextTargetId(className);
    review.targets[id] = {
      id,
      class: className,
      anchors: [],
      frame_observations: {},
      identity_segments: [],
      visible_segments: [],
      formal_annotations: [],
      primary_annotation_frame_index: null,
      primary_core_interval: [null, null],
      research_status: 'DEFER_COMPLEX',
      identity_relation: 'AMBIGUOUS',
      frozen_revisions: [],
      created_at: new Date().toISOString()
    };
    review.active_target_id = id;
    pendingNewTarget = false;
    if (box) recordBox(review.targets[id], frame, box, source);
    save();
    setStatus(`${zh[className] || className}目标已建立。请确认当前帧状态，并继续确认同一目标连续帧段。`);
  }

  function setStatus(message, error) {
    $('status').textContent = message;
    $('status').classList.toggle('danger', Boolean(error));
  }

  function renderTargetList() {
    const targets = Object.values(review.targets);
    $('targetList').innerHTML = targets.map(target => {
      const selected = target.id === review.active_target_id ? 'active' : '';
      const shortId = target.id.split(':').at(-1).replace('HUMAN_CAR_', '车辆').replace('HUMAN_PERSON_', '人员');
      return `<button class="target-item ${selected}" data-id="${target.id}">${shortId}</button>`;
    }).join('') || '<span class="muted">还没有人工目标</span>';
    document.querySelectorAll('.target-item').forEach(button => {
      button.onclick = () => {
        review.active_target_id = button.dataset.id;
        pendingNewTarget = false;
        mode = 'select';
        save();
        draw();
      };
    });
  }

  function drawBand(container, segments, className) {
    const denominator = Math.max(1, scene.frame_count - 1);
    container.innerHTML = (segments || []).map(([start, end]) => {
      const left = start / denominator * 100;
      const width = Math.max(0.3, (end - start + 1) / scene.frame_count * 100);
      return `<span class="band ${className}" style="left:${left}%;width:${width}%"></span>`;
    }).join('');
  }

  function renderTimeline(target) {
    drawBand($('identityBands'), target?.identity_segments || [], 'identity');
    drawBand($('visibleBands'), target?.visible_segments || [], 'human');
    const denominator = Math.max(1, scene.frame_count - 1);
    $('annotationMarks').innerHTML = (target?.formal_annotations || []).map(annotation => `<i class="annotation-mark" title="正式标注帧 ${annotation.frame_index}" style="left:${annotation.frame_index / denominator * 100}%"></i>`).join('');
    $('playhead').style.left = `${frame / denominator * 100}%`;
  }

  function draw() {
    const image = $('optical');
    const canvas = $('overlay');
    image.src = scene.optical[frame].path;
    canvas.width = scene.width;
    canvas.height = scene.height;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);

    for (const detection of detections(frame)) {
      if (!detectionVisible(detection)) continue;
      context.strokeStyle = detection.model === 'YOLO11' ? '#43c8ff' : '#ff9f5b';
      context.lineWidth = 2;
      context.strokeRect(detection.x1, detection.y1, detection.x2 - detection.x1, detection.y2 - detection.y1);
      if ($('confidenceToggle').checked) {
        context.fillStyle = context.strokeStyle;
        context.font = `${Math.max(14, Math.round(scene.width / 120))}px sans-serif`;
        context.fillText(`${detection.model} ${zh[detection.class_name] || detection.class_name} ${detection.confidence.toFixed(2)}`, detection.x1, Math.max(20, detection.y1 - 4));
      }
    }

    for (const target of Object.values(review.targets)) {
      const observation = target.frame_observations[frame];
      if (!observation?.bbox) continue;
      context.strokeStyle = target.id === review.active_target_id ? '#ffe36b' : '#8be3a1';
      context.lineWidth = target.id === review.active_target_id ? 5 : 3;
      context.strokeRect(observation.bbox.x1, observation.bbox.y1, observation.bbox.x2 - observation.bbox.x1, observation.bbox.y2 - observation.bbox.y1);
    }

    const target = active();
    const machineProposal = target && $('machineToggle').checked ? proposal(target, frame) : null;
    if (machineProposal) {
      context.save();
      context.strokeStyle = '#d29cff';
      context.lineWidth = 4;
      context.setLineDash([10, 7]);
      context.strokeRect(machineProposal.x1, machineProposal.y1, machineProposal.x2 - machineProposal.x1, machineProposal.y2 - machineProposal.y1);
      context.restore();
    }

    if (pendingChoices.length && previewChoiceIndex != null) {
      const preview = pendingChoices[previewChoiceIndex];
      if (preview && preview.frame === frame) {
        context.save();
        context.strokeStyle = '#fff36b';
        context.lineWidth = 7;
        context.setLineDash([16, 8]);
        context.strokeRect(preview.x1, preview.y1, preview.x2 - preview.x1, preview.y2 - preview.y1);
        context.restore();
      }
    }
    if (currentPreviewIndex != null) {
      const currentCandidates = detections(frame).filter(detectionVisible);
      const preview = currentCandidates[currentPreviewIndex];
      if (preview) {
        context.save();
        context.strokeStyle = '#fff36b';
        context.lineWidth = 8;
        context.setLineDash([18, 8]);
        context.strokeRect(preview.x1, preview.y1, preview.x2 - preview.x1, preview.y2 - preview.y1);
        context.restore();
      }
    }

    $('sceneTitle').textContent = sceneId;
    $('frameInfo').textContent = `第 ${frame} 帧 / ${scene.frame_count - 1}`;
    $('frameInput').max = scene.frame_count - 1;
    $('frameInput').value = frame;
    $('identityStart').max = scene.frame_count - 1;
    $('identityEnd').max = scene.frame_count - 1;
    renderTargetList();
    renderCurrentFrameCandidates(target);

    if (target) {
      const observation = target.frame_observations[frame] || {};
      const flags = observation.condition_flags || [];
      const segments = (target.identity_segments || []).map(x => x.join('–')).join(', ') || '—';
      $('targetMeta').innerHTML = `<b>${target.id}</b><br>${zh[target.class] || target.class} · ${target.frozen_revisions.length ? '已冻结' : '未冻结'}<br>本帧：${zh[observation.visibility_state] || '未记录'}${observation.bbox ? ' · 有框' : ' · 无框'}<br>条件：${flags.map(x => zh[x]).join('＋') || '无'}<br>同一目标连续段：${segments}`;
      $('frameState').value = observation.visibility_state || 'UNKNOWN';
      for (const [flag, id] of Object.entries(conditionIds)) $(id).checked = flags.includes(flag);
      $('identityStatus').value = target.identity_relation;
      $('admission').value = target.research_status;
      $('provenance').textContent = `anchors=${target.anchors.length} · frame_observations=${Object.keys(target.frame_observations).length} · detector_is_proposal_only=true`;
      const annotations = target.formal_annotations || [];
      $('annotationMeta').textContent = annotations.length ? `正式标注帧：${annotations.map(a => a.frame_index).join(', ')}；主标注帧：${target.primary_annotation_frame_index}` : '尚未选择正式标注帧';
      $('sarLink').classList.toggle('hidden', !target.frozen_revisions.length);
      if (target.frozen_revisions.length) $('sarLink').href = 'SAR_OBSERVATION_VIEW.html?target=' + encodeURIComponent(target.id);
    } else {
      $('targetMeta').textContent = pendingNewTarget ? '等待选择新目标框' : '未选择人工目标';
      $('annotationMeta').textContent = '';
      $('frameState').value = 'UNKNOWN';
      Object.values(conditionIds).forEach(id => $(id).checked = false);
      $('sarLink').classList.add('hidden');
    }
    renderTimeline(target);
  }

  function canvasPoint(event) {
    const rect = $('overlay').getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(scene.width, (event.clientX - rect.left) * scene.width / rect.width)),
      y: Math.max(0, Math.min(scene.height, (event.clientY - rect.top) * scene.height / rect.height))
    };
  }

  function useBox(box, source, className) {
    clearProposalChooser();
    if (pendingNewTarget || !active()) createTarget(className || $('newTargetClass').value, box, source);
    else {
      recordBox(active(), frame, box, source);
      save();
      setStatus('当前帧框已关联到选中的人工目标；请继续确认可见性和截断/遮挡状态。');
    }
    mode = 'select';
    draw();
  }

  $('overlay').onpointerdown = event => {
    if (mode !== 'manual') return;
    event.preventDefault();
    manualDrag = {start: canvasPoint(event)};
    $('overlay').setPointerCapture?.(event.pointerId);
  };

  $('overlay').onpointerup = event => {
    if (mode !== 'manual' || !manualDrag) return;
    const end = canvasPoint(event);
    const start = manualDrag.start;
    manualDrag = null;
    const box = {x1: Math.min(start.x, end.x), y1: Math.min(start.y, end.y), x2: Math.max(start.x, end.x), y2: Math.max(start.y, end.y)};
    if (area(box) < 16) {
      setStatus('手动画框过小，请重新拖动。', true);
      return;
    }
    useBox(box, 'HUMAN_MANUAL', active()?.class || $('newTargetClass').value);
  };

  $('overlay').onclick = event => {
    if (mode === 'manual') return;
    const point = canvasPoint(event);
    const currentTarget = active();
    const hits = detections(frame).filter(d => detectionVisible(d))
      .filter(d => !currentTarget || pendingNewTarget || sameTargetDomain(currentTarget.class, d.class_name))
      .filter(d => point.x >= d.x1 && point.x <= d.x2 && point.y >= d.y1 && point.y <= d.y2)
      .sort((a, b) => area(a) - area(b));
    if (!hits.length) {
      setStatus('这里没有可选 detector 框；可以使用“手动画框”。', true);
      return;
    }
    if (hits.length === 1) useBox(hits[0], hits[0].model, hits[0].class_name);
    else showProposalChooser(hits);
  };

  $('manualBox').onclick = () => {
    mode = 'manual';
    setStatus('请在图像上按住鼠标并拖出真实可见区域。截断目标不要补画不可见部分。');
  };

  $('newTarget').onclick = () => {
    clearProposalChooser();
    review.active_target_id = null;
    pendingNewTarget = true;
    mode = 'select';
    save();
    setStatus(`正在新建${zh[$('newTargetClass').value]}目标：请点击检测框或手动画框。`);
    draw();
  };

  $('reselect').onclick = () => {
    if (!active()) return setStatus('请先从目标列表选择已有目标。', true);
    mode = 'select';
    setStatus('请点击当前帧中的另一个 detector 框，或点击“手动画框”；它会关联到当前已有目标。');
  };

  $('cancelProposalChoice').onclick = () => {
    clearProposalChooser();
    setStatus('已取消候选框选择。');
    draw();
  };

  $('clearFrameBox').onclick = () => {
    const target = active();
    const observation = target?.frame_observations?.[frame];
    if (!target || !observation?.bbox) return setStatus('当前目标在本帧没有可清除的框。', true);
    review.edit_history.push({
      operation: 'CLEAR_FRAME_BBOX',
      target_id: target.id,
      frame_index: frame,
      previous_observation: structuredClone(observation),
      edited_at: new Date().toISOString()
    });
    target.anchors = target.anchors.filter(anchor => anchor.frame_index !== frame);
    target.formal_annotations = target.formal_annotations.filter(annotation => annotation.frame_index !== frame);
    observation.bbox = null;
    observation.bbox_source = 'NONE';
    observation.bbox_role = 'UNKNOWN';
    if (['COMPLETE_VISIBLE', 'PARTIAL_VISIBLE'].includes(observation.visibility_state)) observation.visibility_state = 'VISIBLE_UNBOXED';
    updatePrimaryAnnotation(target);
    target.visible_segments = visibleSegments(target);
    save();
    setStatus(`已清除 ${target.id} 第 ${frame} 帧的框；identity 归属仍保留。`);
    draw();
  };

  $('removeFrameFromTarget').onclick = () => {
    const target = active();
    const observation = target?.frame_observations?.[frame];
    const isInSegment = target?.identity_segments?.some(([start, end]) => frame >= start && frame <= end);
    if (!target || (!observation && !isInSegment)) return setStatus('当前帧没有该目标的 observation 或 identity 归属。', true);
    if (!confirm(`确认把第 ${frame} 帧从 ${target.id} 中移除？连续段会在这里截断或拆分。`)) return;
    review.edit_history.push({
      operation: 'REMOVE_FRAME_FROM_TARGET',
      target_id: target.id,
      frame_index: frame,
      previous_observation: observation ? structuredClone(observation) : null,
      edited_at: new Date().toISOString()
    });
    delete target.frame_observations[frame];
    target.anchors = target.anchors.filter(anchor => anchor.frame_index !== frame);
    target.identity_segments = removeFrameFromSegments(target.identity_segments, frame);
    target.formal_annotations = target.formal_annotations.filter(annotation => annotation.frame_index !== frame);
    updatePrimaryAnnotation(target);
    target.visible_segments = visibleSegments(target);
    save();
    setStatus(`第 ${frame} 帧已从 ${target.id} 移除。`);
    draw();
  };

  $('deleteTarget').onclick = () => {
    const target = active();
    if (!target) return setStatus('当前没有选中目标。', true);
    if (target.frozen_revisions.length) return setStatus('该目标已有冻结 revision，不能直接删除；请保留并在后续 revision 中标记排除。', true);
    if (!confirm(`确认删除整个目标 ${target.id}？此操作与“移除本帧”不同。`)) return;
    review.deleted_targets.push({target_id: target.id, target_snapshot: structuredClone(target), deleted_at: new Date().toISOString()});
    delete review.targets[target.id];
    review.active_target_id = Object.keys(review.targets)[0] || null;
    save();
    setStatus(`${target.id} 已删除；原记录保存在导出 JSON 的 deleted_targets 中。`);
    draw();
  };

  $('accept').onclick = () => {
    const target = active();
    const machineProposal = target && proposal(target, frame);
    if (!machineProposal) return setStatus('当前帧没有同类机器建议；可手动画框或保存为可见但无框。', true);
    recordBox(target, frame, machineProposal, 'HUMAN_ACCEPTED_MACHINE_PROPOSAL');
    save();
    setStatus('机器框已由人工接受并关联到当前目标；它不自动证明 physical identity。');
    draw();
  };

  $('saveFrameState').onclick = () => {
    const target = active();
    if (!target) return setStatus('请先建立或选择人工目标。', true);
    const observation = ensureObservation(target, frame);
    observation.visibility_state = $('frameState').value;
    observation.condition_flags = selectedConditions();
    if (['VISIBLE_UNBOXED', 'NOT_VISIBLE'].includes(observation.visibility_state)) {
      observation.bbox = null;
      observation.bbox_source = 'NONE';
      observation.bbox_role = 'UNKNOWN';
    } else {
      observation.bbox_role = bboxRole(observation.visibility_state, observation.condition_flags, observation.bbox);
    }
    observation.human_confirmed = true;
    target.visible_segments = visibleSegments(target);
    save();
    setStatus('当前帧可见性和成像条件已保存。');
    draw();
  };

  $('startHere').onclick = () => {$('identityStart').value = frame;};
  $('endHere').onclick = () => {$('identityEnd').value = frame;};
  $('confirmIdentitySegment').onclick = () => {
    const target = active();
    if (!target) return setStatus('请先建立或选择人工目标。', true);
    let start = Number($('identityStart').value);
    let end = Number($('identityEnd').value);
    if (!Number.isInteger(start) || !Number.isInteger(end)) return setStatus('请填写连续段起始帧和结束帧。', true);
    [start, end] = [Math.min(start, end), Math.max(start, end)];
    if (start < 0 || end >= scene.frame_count) return setStatus('连续段超出场景帧范围。', true);
    const confirmedAt = new Date().toISOString();
    for (let f = start; f <= end; f++) {
      const observation = ensureObservation(target, f);
      observation.identity_relation = 'SAME_TARGET_HUMAN_CONFIRMED';
      observation.identity_human_confirmed_at = confirmedAt;
      observation.human_confirmed = true;
    }
    target.identity_segments = mergeSegments([...(target.identity_segments || []), [start, end]]);
    save();
    setStatus(`已确认第 ${start}–${end} 帧属于同一人工目标；没有 bbox 的帧仍保持 bbox=null。`);
    draw();
  };

  $('removeIdentityRange').onclick = () => {
    const target = active();
    if (!target) return setStatus('请先建立或选择人工目标。', true);
    let start = Number($('identityStart').value);
    let end = Number($('identityEnd').value);
    if (!Number.isInteger(start) || !Number.isInteger(end)) return setStatus('请填写要移除的起始帧和结束帧。', true);
    [start, end] = [Math.min(start, end), Math.max(start, end)];
    if (start < 0 || end >= scene.frame_count) return setStatus('移除帧段超出场景范围。', true);
    if (!confirm(`确认从 ${target.id} 移除第 ${start}–${end} 帧？范围内的 observation、anchor 和正式标注也会移除。`)) return;
    const removedObservations = {};
    for (let f = start; f <= end; f++) {
      if (target.frame_observations[f]) removedObservations[f] = structuredClone(target.frame_observations[f]);
      delete target.frame_observations[f];
    }
    review.edit_history.push({
      operation: 'REMOVE_FRAME_RANGE_FROM_TARGET',
      target_id: target.id,
      frame_range: [start, end],
      previous_observations: removedObservations,
      edited_at: new Date().toISOString()
    });
    target.anchors = target.anchors.filter(anchor => anchor.frame_index < start || anchor.frame_index > end);
    target.identity_segments = removeRangeFromSegments(target.identity_segments, start, end);
    target.formal_annotations = target.formal_annotations.filter(annotation => annotation.frame_index < start || annotation.frame_index > end);
    updatePrimaryAnnotation(target);
    target.visible_segments = visibleSegments(target);
    save();
    setStatus(`已从 ${target.id} 移除第 ${start}–${end} 帧。`);
    draw();
  };

  $('markAnnotation').onclick = () => {
    const target = active();
    if (!target) return setStatus('请先建立或选择人工目标。', true);
    const observation = target.frame_observations[frame];
    if (!observation?.bbox) return setStatus('正式标注帧必须有人工确认的目标框。', true);
    if (observation.visibility_state !== 'COMPLETE_VISIBLE') return setStatus('请先把当前帧可见性保存为“完整可见”。', true);
    if ((observation.condition_flags || []).length) return setStatus('当前帧仍有截断或遮挡标记，不能作为完整目标正式标注帧。', true);
    const annotation = {
      annotation_id: `${target.id}:OPTICAL_FRAME_${String(frame).padStart(6, '0')}`,
      frame_index: frame,
      bbox: boxCopy(observation.bbox),
      bbox_role: 'FULL_VISIBLE_TARGET',
      bbox_source: observation.bbox_source,
      identity_relation: observation.identity_relation,
      human_confirmed: true,
      marked_at: new Date().toISOString()
    };
    const existing = target.formal_annotations.findIndex(item => item.frame_index === frame);
    if (existing >= 0) target.formal_annotations[existing] = annotation;
    else target.formal_annotations.push(annotation);
    target.formal_annotations.sort((a, b) => a.frame_index - b.frame_index);
    target.primary_annotation_frame_index = frame;
    target.primary_core_interval = [frame, frame];
    save();
    setStatus(`第 ${frame} 帧已设为当前目标的正式光学标注帧。`);
    draw();
  };

  $('identityStatus').onchange = event => {if (active()) {active().identity_relation = event.target.value; save();}};
  $('admission').onchange = event => {if (active()) {active().research_status = event.target.value; save();}};

  $('freeze').onclick = () => {
    const target = active();
    if (!target) return setStatus('请先建立或选择人工目标。', true);
    if (target.primary_annotation_frame_index == null) return setStatus('请先选择至少一个完整可见的正式标注帧。', true);
    const revision = {
      schema_version: 'HUMAN_FROZEN_OPTICAL_TARGET_v0.2',
      freeze_id: `${target.id}:FREEZE_${Date.now()}`,
      revision: target.frozen_revisions.length + 1,
      target_id: target.id,
      identity_segments: structuredClone(target.identity_segments),
      visible_segments: structuredClone(target.visible_segments),
      formal_annotations: structuredClone(target.formal_annotations),
      primary_annotation_frame_index: target.primary_annotation_frame_index,
      frozen_at: new Date().toISOString()
    };
    target.frozen_revisions.push(revision);
    save();
    setStatus(`目标标注已冻结为 revision ${revision.revision}。`);
    draw();
  };

  function moveFrame(delta) {
    clearProposalChooser();
    frame = Math.max(0, Math.min(scene.frame_count - 1, frame + delta));
    draw();
  }

  $('prev').onclick = () => moveFrame(-1);
  $('next').onclick = () => moveFrame(1);
  $('jump').onclick = () => {clearProposalChooser(); frame = Math.max(0, Math.min(scene.frame_count - 1, Number($('frameInput').value) || 0)); draw();};
  $('play').onclick = () => {
    clearInterval(timer);
    timer = setInterval(() => {
      if (frame >= scene.frame_count - 1) {clearInterval(timer); timer = null; return;}
      moveFrame(1);
    }, 1000 / (18 * Number($('speed').value)));
  };
  $('pause').onclick = () => {clearInterval(timer); timer = null;};

  ['yolo11Toggle', 'yolo26Toggle', 'carToggle', 'personToggle', 'confidenceToggle', 'machineToggle'].forEach(id => $(id).onchange = draw);

  $('timeline').onclick = event => {
    clearProposalChooser();
    const rect = $('timeline').getBoundingClientRect();
    frame = Math.max(0, Math.min(scene.frame_count - 1, Math.round((event.clientX - rect.left) / rect.width * (scene.frame_count - 1))));
    draw();
  };

  $('exportTargets').onclick = () => {
    save();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2)], {type: 'application/json'}));
    link.download = `TPGT_OPTICAL_HUMAN_TARGET_SET_${sceneId}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  $('importTargets').onclick = () => $('importFile').click();
  $('importFile').onchange = async event => {
    try {
      const imported = JSON.parse(await event.target.files[0].text());
      if (imported.scene_id !== sceneId || !imported.targets) throw new Error('scene mismatch or targets missing');
      review = imported;
      normalize();
      save();
      setStatus('目标集 JSON 已载入。');
      draw();
    } catch (error) {
      setStatus(`载入失败：${error.message}`, true);
    } finally {
      event.target.value = '';
    }
  };

  window.onkeydown = event => {
    if (event.target.matches('input,select,textarea')) return;
    if (event.code === 'Space') {
      event.preventDefault();
      timer ? $('pause').click() : $('play').click();
    } else if (event.key === 'ArrowLeft') moveFrame(event.shiftKey ? -10 : -1);
    else if (event.key === 'ArrowRight') moveFrame(event.shiftKey ? 10 : 1);
    else if (event.key.toUpperCase() === 'A') $('accept').click();
    else if (event.key.toUpperCase() === 'R') $('reselect').click();
    else if (event.key.toUpperCase() === 'V') {$('frameState').value = 'COMPLETE_VISIBLE'; $('saveFrameState').click();}
    else if (event.key.toUpperCase() === 'P') {$('frameState').value = 'PARTIAL_VISIBLE'; $('saveFrameState').click();}
    else if (event.key.toUpperCase() === 'X') {$('frameState').value = 'NOT_VISIBLE'; $('saveFrameState').click();}
  };

  $('sceneTitle').textContent = sceneId;
  draw();
})();
