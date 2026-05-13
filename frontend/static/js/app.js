'use strict';

// =====================================================================
// Unveiling frontend controller — two screens, unified analysis → result.
//
//   • home      — manifesto + question form
//   • analysis  — phase ribbon + lens reveal + dual progress rails +
//                 chronological case feed + machine-view drawer +
//                 conclusion chapters (revealed after analysis completes)
//
// Backed by:
//   POST /analyze                  → { task_id }
//   GET  /progress/<task_id>       → SSE stream of typed events
//   GET  /result/<task_id>         → final cached JSON payload
//
// SSE event kinds: meta · phase · lens · evidence_batch · schedule ·
//                  conclusion · tokens · progress · done · error
// =====================================================================

(function () {

  // ============================== State ==============================

  var TARGET_PER_DIRECTION = 10;
  var MAX_ROUNDS = 3;

  var PHASE_ORDER = ['inception', 'exploration', 'convergence'];
  var PHASE_LABEL = {
    inception: '抽象',
    exploration: '搜集',
    convergence: '收拢',
  };

  var DIRECTION_LABEL = { lateral: '跨领域', vertical: '跨时期' };
  var LAYER_LABEL = {
    phenomenon: '现象',
    mechanism: '机制',
    structure: '结构',
  };
  var CONFIDENCE_LABEL = {
    strong: '强',
    medium: '中',
    weak: '弱',
    unexpected: '意外',
  };
  var LAYER_MARKER = {
    structure: '■■■',
    mechanism: '■■□',
    phenomenon: '■□□',
  };

  var CHAPTERS = [
    { key: 'core_finding',        fallback: '核心结论',         bodyClass: 'body-takeaway' },
    { key: 'temporal_trajectory', fallback: '这件事的走向',     bodyClass: 'body-trajectory' },
    { key: 'tension',             fallback: '难处在哪',         bodyClass: 'body-tension' },
    { key: 'boundary_condition',  fallback: '这话在哪里不成立', bodyClass: 'body-boundary' },
    { key: 'unresolved',          fallback: '还没回答清楚的',   bodyClass: 'body-unresolved' },
    { key: 'implication',         fallback: '所以你应该',       bodyClass: 'body-implication' },
  ];

  var state = {
    screen: 'home',
    mode: 'balance',
    language: '中文',
    taskId: null,
    eventSource: null,
    phase: 'inception',
    lens: null,
    evidence: [],
    schedule: [],
    tokens: 0,
    lateral: { count: 0, rounds: 0, done: false },
    vertical: { count: 0, rounds: 0, done: false },
    degradationCount: 0,
    conclusion: null,
    result: null,
  };

  // ============================ DOM refs =============================

  var dom = {};

  function resolveDom() {
    dom = {
      screens: document.querySelectorAll('.screen'),

      // Home
      homeForm: document.getElementById('home-form'),
      homeQuestion: document.getElementById('home-question'),
      modeOptions: document.querySelectorAll('.home-form__mode-option'),
      langOptions: document.querySelectorAll('.home-form__lang-option'),
      promptCards: document.querySelectorAll('.prompt-card'),

      // Analysis
      analysisEdition: document.getElementById('analysis-edition'),
      analysisQuestion: document.getElementById('analysis-question'),
      phaseIndicator: document.getElementById('phase-indicator'),
      narrationText: document.getElementById('narration-text'),

      lensReveal: document.getElementById('lens-reveal'),
      lensName: document.getElementById('lens-name'),
      lensRationale: document.getElementById('lens-rationale'),
      lensEntities: document.getElementById('lens-entities'),
      lensRelations: document.getElementById('lens-relations'),

      rails: document.getElementById('rails'),
      lateralCount: document.getElementById('lateral-count'),
      lateralRounds: document.getElementById('lateral-rounds'),
      lateralFill: document.getElementById('lateral-fill'),
      lateralStatus: document.getElementById('lateral-status'),
      verticalCount: document.getElementById('vertical-count'),
      verticalRounds: document.getElementById('vertical-rounds'),
      verticalFill: document.getElementById('vertical-fill'),
      verticalStatus: document.getElementById('vertical-status'),

      casesSection: document.getElementById('cases'),
      casesList: document.getElementById('cases-list'),
      casesCounter: document.getElementById('cases-counter'),

      machineView: document.getElementById('machine-view'),
      machineToggle: document.getElementById('machine-view-toggle'),
      machineMeta: document.getElementById('machine-view-meta'),
      scheduleLogList: document.getElementById('schedule-log-list'),

      // Unified: conclusion zone
      analysisTransition: document.getElementById('analysis-transition'),
      integrity: document.getElementById('integrity'),
      integrityLateral: document.getElementById('integrity-lateral'),
      integrityVertical: document.getElementById('integrity-vertical'),
      integrityDegradation: document.getElementById('integrity-degradation'),
      integrityTokens: document.getElementById('integrity-tokens'),
      conclusions: document.getElementById('conclusions'),
      conclusionChapters: document.querySelectorAll('.conclusion'),

      recap: document.getElementById('recap'),
      recapToggle: document.getElementById('recap-toggle'),
      recapMeta: document.getElementById('recap-meta'),

      lensResultName: document.getElementById('lens-result-name'),
      lensResultRationale: document.getElementById('lens-result-rationale'),
      lensResultEntities: document.getElementById('lens-result-entities'),
      lensResultRelations: document.getElementById('lens-result-relations'),

      caseIndex: document.getElementById('case-index'),
      caseIndexMeta: document.getElementById('case-index-meta'),

      sectionDegradation: document.getElementById('section-degradation'),
      degradationList: document.getElementById('degradation-list'),

      analysisFoot: document.getElementById('analysis-foot'),
      resultBack: document.getElementById('result-back'),
      resultMeta: document.getElementById('result-meta'),
    };
  }

  // ============================ Helpers ==============================

  function $$(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'class') node.className = attrs[k];
        else if (k === 'dataset') {
          Object.keys(attrs[k]).forEach(function (dk) {
            if (attrs[k][dk] != null) node.dataset[dk] = attrs[k][dk];
          });
        } else if (k.startsWith('on') && typeof attrs[k] === 'function') {
          node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        } else if (k in node && k !== 'list') {
          node[k] = attrs[k];
        } else {
          node.setAttribute(k, attrs[k]);
        }
      });
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(function (c) {
        if (c == null) return;
        node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    }
    return node;
  }

  function setText(node, value) {
    if (!node) return;
    node.textContent = value == null ? '' : String(value);
  }

  function clear(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function show(node) { if (node) node.hidden = false; }
  function hide(node) { if (node) node.hidden = true; }

  function formatTokens(n) {
    if (n >= 10000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function pct(num, denom) {
    if (!denom) return 0;
    return Math.min(100, Math.round((num / denom) * 100));
  }

  // ====================== Screen switching ===========================

  function showScreen(name) {
    state.screen = name;
    dom.screens.forEach(function (s) {
      s.classList.toggle('is-active', s.dataset.screen === name);
    });
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  }

  // ============================== Init ===============================

  function init() {
    resolveDom();
    bindHome();
    bindAnalysisControls();
    bindConclusionControls();

    var params = new URLSearchParams(window.location.search);
    if (params.get('demo') === '1') {
      loadDemoResult();
    }
  }

  function bindHome() {
    dom.modeOptions.forEach(function (opt) {
      opt.addEventListener('click', function () {
        state.mode = opt.dataset.mode;
        dom.modeOptions.forEach(function (o) {
          var selected = o === opt;
          o.classList.toggle('is-selected', selected);
          o.setAttribute('aria-checked', selected ? 'true' : 'false');
        });
      });
    });

    dom.langOptions.forEach(function (opt) {
      opt.addEventListener('click', function () {
        state.language = opt.dataset.lang;
        dom.langOptions.forEach(function (o) {
          var selected = o === opt;
          o.classList.toggle('is-selected', selected);
          o.setAttribute('aria-checked', selected ? 'true' : 'false');
        });
      });
    });

    dom.promptCards.forEach(function (card) {
      card.addEventListener('click', function () {
        dom.homeQuestion.value = card.dataset.example || '';
        dom.homeQuestion.focus();
      });
    });

    dom.homeForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = (dom.homeQuestion.value || '').trim();
      if (!q) return;
      startAnalysis(q, state.mode, state.language);
    });
  }

  function bindAnalysisControls() {
    dom.machineToggle.addEventListener('click', function () {
      var expanded = dom.machineView.classList.toggle('is-expanded');
      dom.machineToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
  }

  function bindConclusionControls() {
    // Back to home
    dom.resultBack.addEventListener('click', function () {
      if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
      }
      resetAnalysisState();
      showScreen('home');
    });

    // Chapter toggle — delegated on each conclusion
    Array.prototype.forEach.call(dom.conclusionChapters, function (chapter) {
      var toggle = chapter.querySelector('.conclusion__toggle');
      if (!toggle) return;
      toggle.addEventListener('click', function () {
        var expanded = chapter.classList.toggle('is-expanded');
        toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        var body = chapter.querySelector('.conclusion__body');
        if (body) body.setAttribute('aria-hidden', expanded ? 'false' : 'true');
      });
    });

    // Recap drawer toggle
    if (dom.recapToggle && dom.recap) {
      dom.recapToggle.addEventListener('click', function () {
        var open = dom.recap.classList.toggle('is-open');
        dom.recapToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
  }

  // ======================== Reset between runs =======================

  function resetAnalysisState() {
    state.taskId = null;
    state.phase = 'inception';
    state.lens = null;
    state.evidence = [];
    state.schedule = [];
    state.tokens = 0;
    state.lateral = { count: 0, rounds: 0, done: false };
    state.vertical = { count: 0, rounds: 0, done: false };
    state.degradationCount = 0;
    state.conclusion = null;
    state.result = null;

    setText(dom.narrationText, '正在准备分析……');
    hide(dom.lensReveal);
    hide(dom.rails);
    hide(dom.casesSection);
    clear(dom.lensEntities);
    clear(dom.lensRelations);
    clear(dom.casesList);
    clear(dom.scheduleLogList);
    setText(dom.casesCounter, '0 条');
    setText(dom.machineMeta, '0 条调度 · 0 token');
    setPhase('inception');
    updateRailUI('lateral');
    updateRailUI('vertical');

    // Reset conclusion zone
    hide(dom.analysisTransition);
    hide(dom.integrity);
    hide(dom.conclusions);
    hide(dom.recap);
    hide(dom.analysisFoot);
    dom.casesSection.classList.remove('is-complete');
    dom.rails.classList.remove('is-complete');
    dom.lensReveal.classList.remove('is-complete');

    CHAPTERS.forEach(function (chap) {
      var el = document.getElementById('chapter-' + chap.key);
      if (el) {
        el.classList.remove('is-empty', 'is-revealed', 'is-expanded');
        el.style.animationDelay = '';
      }
      var body = document.getElementById('body-' + chap.key);
      if (body) clear(body);
      var tagline = document.getElementById('tagline-' + chap.key);
      if (tagline) setText(tagline, '');
    });
  }

  // ========================== Start a run ============================

  function startAnalysis(question, mode, language) {
    resetAnalysisState();
    setText(dom.analysisQuestion, question);
    showScreen('analysis');

    fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, mode: mode, language: language }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error('analyze failed: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.task_id) throw new Error('no task_id returned');
        state.taskId = data.task_id;
        openEventSource(data.task_id);
      })
      .catch(function (err) {
        setText(dom.narrationText, '启动分析失败：' + (err.message || err));
      });
  }

  function openEventSource(taskId) {
    var es = new EventSource('/progress/' + encodeURIComponent(taskId));
    state.eventSource = es;

    es.onmessage = function (e) {
      var payload;
      try { payload = JSON.parse(e.data); }
      catch (_) { return; }
      if (!payload || !payload.kind) return;
      handleEvent(payload);
    };

    es.addEventListener('end', function () {
      es.close();
      state.eventSource = null;
      if (state.result) {
        transitionToResult(state.result);
      }
    });

    es.onerror = function () {
      // Browser will reconnect on its own.
    };
  }

  // ====================== SSE event dispatch =========================

  function handleEvent(ev) {
    switch (ev.kind) {
      case 'meta':         return;
      case 'phase':        return onPhase(ev);
      case 'lens':         return onLens(ev);
      case 'evidence_batch': return onEvidenceBatch(ev);
      case 'schedule':     return onSchedule(ev);
      case 'conclusion':   return onConclusion(ev);
      case 'tokens':       return onTokens(ev);
      case 'progress':     return onProgress(ev);
      case 'done':         return onDone(ev);
      case 'error':        return onError(ev);
    }
  }

  function onPhase(ev) {
    setPhase(ev.phase);
    if (ev.phase === 'exploration') {
      show(dom.rails);
      show(dom.casesSection);
      setText(dom.narrationText, '跨领域与跨时期并行搜索 — 找结构相似的类比案例');
    } else if (ev.phase === 'convergence') {
      setText(dom.narrationText, '正在跨案例归纳共性 · 找矛盾 · 写结论');
    } else if (ev.phase === 'inception') {
      setText(dom.narrationText, '正在拆解问题 — 提炼核心结构');
    }
  }

  function onLens(ev) {
    state.lens = ev.lens;
    renderLens(ev.lens);
    show(dom.lensReveal);
    setText(dom.narrationText, '观察角度已就位：' + (ev.lens.name || '未命名'));
  }

  function onEvidenceBatch(ev) {
    var items = ev.evidence || [];
    items.forEach(function (e) { state.evidence.push(e); });

    state.lateral.count = ev.lateral_count != null ? ev.lateral_count : state.lateral.count;
    state.vertical.count = ev.vertical_count != null ? ev.vertical_count : state.vertical.count;
    state.lateral.rounds = ev.lateral_rounds != null ? ev.lateral_rounds : state.lateral.rounds;
    state.vertical.rounds = ev.vertical_rounds != null ? ev.vertical_rounds : state.vertical.rounds;

    updateRailUI('lateral');
    updateRailUI('vertical');
    appendCases(items);

    if (items.length) {
      var first = items[0];
      var dirLabel = DIRECTION_LABEL[first.search_direction] || first.search_direction;
      var moreNote = items.length > 1 ? '（共 ' + items.length + ' 条）' : '';
      setText(dom.narrationText, '刚刚找到 [' + dirLabel + '] ' + (first.case_name || '一条案例') + moreNote);
    }
  }

  function onSchedule(ev) {
    if (!ev.entry) return;
    state.schedule.push(ev.entry);
    if (ev.entry.is_degradation) state.degradationCount += 1;
    appendScheduleLog(ev.entry);
    updateMachineMeta();
  }

  function onConclusion(ev) {
    state.conclusion = ev.conclusion;
    setText(dom.narrationText, '结论已写入，准备呈现……');
  }

  function onTokens(ev) {
    state.tokens = ev.tokens || 0;
    updateMachineMeta();
  }

  function onProgress(ev) {
    state.lateral.count = ev.lateral_count != null ? ev.lateral_count : state.lateral.count;
    state.vertical.count = ev.vertical_count != null ? ev.vertical_count : state.vertical.count;
    state.lateral.rounds = ev.lateral_rounds != null ? ev.lateral_rounds : state.lateral.rounds;
    state.vertical.rounds = ev.vertical_rounds != null ? ev.vertical_rounds : state.vertical.rounds;
    updateRailUI('lateral');
    updateRailUI('vertical');
  }

  function onDone(ev) {
    state.result = ev.result;
  }

  function onError(ev) {
    setText(dom.narrationText, '出错了：' + (ev.error || '未知错误'));
  }

  // ============================ Renderers ============================

  function setPhase(phaseKey) {
    state.phase = phaseKey;
    var idx = PHASE_ORDER.indexOf(phaseKey);
    $$('.phases__step', dom.phaseIndicator).forEach(function (step, i) {
      step.classList.remove('is-active', 'is-complete', 'is-future');
      if (i < idx) step.classList.add('is-complete');
      else if (i === idx) step.classList.add('is-active');
      else step.classList.add('is-future');
    });
    setText(dom.analysisEdition, '一份正在进行的分析 · ' + (PHASE_LABEL[phaseKey] || phaseKey));
  }

  function setPhaseAllComplete() {
    $$('.phases__step', dom.phaseIndicator).forEach(function (step) {
      step.classList.remove('is-active', 'is-future');
      step.classList.add('is-complete');
    });
    setText(dom.analysisEdition, '分析完成');
  }

  function renderLens(lens) {
    setText(dom.lensName, lens.name || '未命名');
    setText(dom.lensRationale, lens.rationale || '');
    clear(dom.lensEntities);
    (lens.entities || []).forEach(function (e) {
      dom.lensEntities.appendChild(buildLensPair(e.surface, e.structural_role));
    });
    clear(dom.lensRelations);
    (lens.relationships || []).forEach(function (r) {
      dom.lensRelations.appendChild(buildLensPair(r.surface, r.structural));
    });
  }

  function buildLensPair(surface, structural) {
    return el('li', { class: 'lens-pair' }, [
      el('span', { class: 'lens-pair__surface' }, surface || ''),
      el('span', { class: 'lens-pair__arrow', 'aria-hidden': 'true' }, '→'),
      el('span', { class: 'lens-pair__structural' }, structural || ''),
    ]);
  }

  function updateRailUI(direction) {
    var rec = state[direction];
    var isLateral = direction === 'lateral';
    var countEl = isLateral ? dom.lateralCount : dom.verticalCount;
    var roundsEl = isLateral ? dom.lateralRounds : dom.verticalRounds;
    var fillEl = isLateral ? dom.lateralFill : dom.verticalFill;
    var statusEl = isLateral ? dom.lateralStatus : dom.verticalStatus;
    if (!countEl) return;

    setText(countEl, rec.count);
    setText(roundsEl, rec.rounds);
    var fillPct = pct(rec.count, TARGET_PER_DIRECTION);
    fillEl.style.width = fillPct + '%';

    var label = '进行中';
    if (rec.count >= TARGET_PER_DIRECTION) {
      label = '已完成 — 找到 ' + rec.count + ' 条';
      fillEl.classList.add('rail__fill--done');
    } else if (rec.rounds >= MAX_ROUNDS) {
      label = '轮次用完 — 带 ' + rec.count + ' 条结束';
      fillEl.classList.add('rail__fill--stuck');
    } else if (rec.rounds === 0 && rec.count === 0) {
      label = '尚未开始';
    }
    setText(statusEl, label);
  }

  function appendCases(items) {
    items.forEach(function (e) {
      dom.casesList.appendChild(buildCaseRow(e));
    });
    setText(dom.casesCounter, state.evidence.length + ' 条');
  }

  function buildCaseRow(e) {
    var direction = e.search_direction;
    var layer = e.layer;
    var conf = e.confidence;
    var isUnexpected = !!e.is_unexpected;
    var dirChip = el('span', {
      class: 'case__chip case__chip--dir case__chip--' + direction,
    }, DIRECTION_LABEL[direction] || direction);
    var layerMark = el('span', {
      class: 'case__layer',
      title: '层级：' + (LAYER_LABEL[layer] || layer),
    }, LAYER_MARKER[layer] || '■□□');
    var confChip = el('span', {
      class: 'case__chip case__chip--conf case__chip--conf-' + conf,
    }, CONFIDENCE_LABEL[conf] || conf);
    var meta = el('div', { class: 'case__meta' }, [dirChip, layerMark, confChip]);
    if (isUnexpected) {
      meta.appendChild(el('span', {
        class: 'case__chip case__chip--unexpected',
        title: '系统标注为意外发现',
      }, '意外'));
    }
    return el('li', { class: 'case' + (isUnexpected ? ' case--unexpected' : '') }, [
      meta,
      el('div', { class: 'case__name' }, e.case_name || '（未命名案例）'),
      el('div', { class: 'case__body' }, e.content || ''),
    ]);
  }

  function appendScheduleLog(entry) {
    var klass = 'log' + (entry.is_degradation ? ' log--degraded' : '');
    var author = el('span', { class: 'log__author' }, entry.author || 'system');
    var decision = el('span', { class: 'log__decision' }, entry.decision || '');
    var reason = el('span', { class: 'log__reason' }, entry.reason || '');
    dom.scheduleLogList.appendChild(
      el('li', { class: klass }, [author, decision, reason])
    );
  }

  function updateMachineMeta() {
    setText(
      dom.machineMeta,
      state.schedule.length + ' 条调度 · ' + formatTokens(state.tokens) + ' token'
    );
  }

  // =================== Transition to result (no screen switch) ==========

  function transitionToResult(result) {
    if (!result) return;

    // 1. All phases complete
    setPhaseAllComplete();

    // 2. Narration wraps up
    setText(dom.narrationText, '分析完成');

    // 3. Process elements get "completed" visual treatment
    dom.casesSection.classList.add('is-complete');
    dom.rails.classList.add('is-complete');
    dom.lensReveal.classList.add('is-complete');

    // 4. Show transition marker
    show(dom.analysisTransition);

    // 5. Integrity strip
    renderIntegrity(result);
    show(dom.integrity);

    // 6. Render and show conclusions
    renderConclusions(result);
    show(dom.conclusions);

    // 7. Recap drawer
    renderRecap(result);
    show(dom.recap);

    // 8. Footer
    renderResultMeta(result);
    show(dom.analysisFoot);

    // 9. Smooth scroll to conclusions (only if near bottom)
    var nearBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 400;
    if (nearBottom && dom.analysisTransition) {
      dom.analysisTransition.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // ======================== Result sub-renderers ========================

  function renderIntegrity(result) {
    setText(dom.integrityLateral, result.lateral_count || 0);
    setText(dom.integrityVertical, result.vertical_count || 0);
    var degCount = (result.schedule_log || []).filter(function (l) {
      return l.is_degradation;
    }).length;
    setText(dom.integrityDegradation, degCount);
    setText(dom.integrityTokens, formatTokens(result.token_spent || 0));
  }

  function renderConclusions(result) {
    var c = result.conclusion || {};
    var taglines = (c.taglines && typeof c.taglines === 'object') ? c.taglines : {};
    CHAPTERS.forEach(function (chap, index) {
      renderConclusion(chap, taglines[chap.key], c[chap.key], index);
    });
  }

  function renderConclusion(chap, tagline, body, index) {
    var chapterEl = document.getElementById('chapter-' + chap.key);
    var taglineEl = document.getElementById('tagline-' + chap.key);
    var bodyEl = document.getElementById('body-' + chap.key);

    var text = (body == null ? '' : String(body)).trim();
    var taglineText = (tagline == null ? '' : String(tagline)).trim() || chap.fallback;

    if (taglineEl) setText(taglineEl, taglineText);

    if (bodyEl) {
      clear(bodyEl);
      var bodyClass = chap.bodyClass + (text ? '' : ' is-empty');
      bodyEl.appendChild(
        el('p', { class: bodyClass }, text || '（系统未给出此项）')
      );
    }

    if (chapterEl) {
      chapterEl.classList.toggle('is-empty', !text);
      chapterEl.style.animationDelay = (index * 120) + 'ms';
      chapterEl.classList.add('is-revealed');
    }
  }

  function renderRecap(result) {
    // Lens snapshot
    var lenses = result.lenses || [];
    if (lenses.length) {
      var lens = lenses[lenses.length - 1];
      setText(dom.lensResultName, lens.name || '');
      setText(dom.lensResultRationale, lens.rationale || '');
      clear(dom.lensResultEntities);
      (lens.entities || []).forEach(function (e) {
        dom.lensResultEntities.appendChild(buildLensPair(e.surface, e.structural_role));
      });
      clear(dom.lensResultRelations);
      (lens.relationships || []).forEach(function (r) {
        dom.lensResultRelations.appendChild(buildLensPair(r.surface, r.structural));
      });
    }

    // Case index
    renderCaseIndex(result.evidence || []);

    // Degradation list
    var degraded = (result.schedule_log || []).filter(function (l) {
      return l.is_degradation;
    });
    if (degraded.length) {
      clear(dom.degradationList);
      degraded.forEach(function (l) {
        dom.degradationList.appendChild(
          el('li', { class: 'degradation' }, [
            el('span', { class: 'degradation__author' }, l.author || ''),
            el('span', { class: 'degradation__decision' }, l.decision || ''),
            el('span', { class: 'degradation__reason' }, l.reason || ''),
          ])
        );
      });
      show(dom.sectionDegradation);
    } else {
      hide(dom.sectionDegradation);
    }

    // Recap drawer meta
    if (dom.recapMeta) {
      var bits = [];
      if (lenses.length) bits.push('观察角度');
      var evCount = (result.evidence || []).length;
      if (evCount) bits.push(evCount + ' 个案例');
      var degCount = degraded.length;
      if (degCount) bits.push(degCount + ' 处降级');
      setText(dom.recapMeta, bits.length ? bits.join(' · ') : '本次没有可回顾的过程材料');
    }
  }

  function renderResultMeta(result) {
    var degCount = (result.schedule_log || []).filter(function (l) {
      return l.is_degradation;
    }).length;
    setText(dom.resultMeta,
      '跨领域 ' + (result.lateral_count || 0) +
      ' · 跨时期 ' + (result.vertical_count || 0) +
      ' · ' + formatTokens(result.token_spent || 0) + ' token' +
      (degCount ? ' · ' + degCount + ' 处降级' : '')
    );
  }

  // ========================== Case index ==============================

  function renderCaseIndex(evidence) {
    clear(dom.caseIndex);
    setText(dom.caseIndexMeta, evidence.length + ' 条案例');
    if (!evidence.length) {
      dom.caseIndex.appendChild(
        el('div', { class: 'case-index__empty' }, '本次没有收集到案例。')
      );
      return;
    }

    var directions = ['lateral', 'vertical'];
    var layers = ['structure', 'mechanism', 'phenomenon'];
    directions.forEach(function (dir) {
      var row = el('div', { class: 'case-index__row' });
      row.appendChild(
        el('div', { class: 'case-index__rowhead' }, [
          el('span', { class: 'case-index__rowname' }, DIRECTION_LABEL[dir] || dir),
          el('span', { class: 'case-index__rowdesc' },
            dir === 'lateral' ? '当代其他行业' : '历史上的先例'),
        ])
      );
      var cells = el('div', { class: 'case-index__cells' });
      layers.forEach(function (layer) {
        var matches = evidence.filter(function (e) {
          return e.search_direction === dir && e.layer === layer;
        });
        var cell = el('div', { class: 'case-index__cell' }, [
          el('div', { class: 'case-index__layer' }, [
            el('span', { class: 'case-index__layer-marker' }, LAYER_MARKER[layer]),
            el('span', { class: 'case-index__layer-name' }, LAYER_LABEL[layer]),
          ]),
          buildCaseIndexList(matches),
        ]);
        cells.appendChild(cell);
      });
      row.appendChild(cells);
      dom.caseIndex.appendChild(row);
    });
  }

  function buildCaseIndexList(items) {
    if (!items.length) {
      return el('div', { class: 'case-index__none' }, '（无）');
    }
    var list = el('ul', { class: 'case-index__list' });
    items.forEach(function (e) {
      list.appendChild(
        el('li', { class: 'case-index__item' + (e.is_unexpected ? ' is-unexpected' : '') }, [
          el('span', { class: 'case-index__item-name' }, e.case_name || '（未命名）'),
          el('span', { class: 'case-index__item-conf' }, CONFIDENCE_LABEL[e.confidence] || e.confidence),
        ])
      );
    });
    return list;
  }

  // ============================== Demo ===============================

  function loadDemoResult() {
    var demo = {
      question: 'AI 时代人们的 AI 焦虑',
      mode: 'balance',
      language: '中文',
      lateral_count: 7,
      vertical_count: 5,
      lateral_rounds: 2,
      vertical_rounds: 2,
      token_spent: 9420,
      lenses: [{
        name: '新生产力对主体意义领地的渗透',
        rationale: '当一种新生产力把某类认知劳动的边际成本压向零，承载这类劳动的主体的功能与意义就会被重新分配。焦虑不是对工具的反应，而是对意义领地被重新划界的反应。',
        entities: [
          { surface: 'AI', structural_role: '崛起中的、能力可外溢的新型生产力' },
          { surface: '人们', structural_role: '其价值与身份正被新生产力冲击的主流主体' },
          { surface: '焦虑', structural_role: '主体面对外部不可控变化时的存在论反应' },
        ],
        relationships: [
          { surface: 'AI → 让 → 人们 → 产生焦虑', structural: '新生产力 → 渗透主体的功能与意义领地 → 触发存在论焦虑' },
        ],
      }],
      evidence: [
        { id: '1', case_name: '卢德运动 1810s', content: '英国织布工人破坏机器，并非反对技术本身，而是抵制技术对其手工技艺所承载的社会身份的剥夺。', search_direction: 'vertical', layer: 'mechanism', confidence: 'strong', is_unexpected: false },
        { id: '2', case_name: '印刷术革命 1450s', content: '抄写员行业终结。但更深的震动在于：知识的权威从教会与抄写员的"持有"，转向了印刷术使得知识"可复制、可传播"。', search_direction: 'vertical', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '3', case_name: '基因编辑伦理争议', content: '社会对 CRISPR 的恐慌不只是关于安全性，而是对"什么是自然人"的界定权被技术重新拿走的存在论不安。', search_direction: 'lateral', layer: 'structure', confidence: 'medium', is_unexpected: false },
        { id: '4', case_name: '社交媒体焦虑', content: '注意力被算法定价，自我表达被指标量化。焦虑来自于"我是谁"的判定权从内部转移到了平台。', search_direction: 'lateral', layer: 'mechanism', confidence: 'strong', is_unexpected: false },
        { id: '5', case_name: '电报革命 1840s', content: '空间被压平，远距离通讯不再是特权。但与今天 AI 的差异在于：电报扩张了人的能力，未取代人的判断。', search_direction: 'vertical', layer: 'mechanism', confidence: 'medium', is_unexpected: true },
        { id: '6', case_name: '电脑普及 1980s', content: '"会用电脑"成为新的识字能力。许多原本以人脑为唯一载体的认知任务被外包。', search_direction: 'vertical', layer: 'phenomenon', confidence: 'medium', is_unexpected: false },
        { id: '7', case_name: '石油行业抵制电动车', content: '既有生产力的承载者抵制新生产力，不只是经济利益问题，更是"我们决定能源未来"的权力领地被剥夺。', search_direction: 'lateral', layer: 'mechanism', confidence: 'medium', is_unexpected: false },
        { id: '8', case_name: '工业革命的女工抗议', content: '机器并未完全取代女工，而是把劳动重组到工厂体制下。抗议焦点是工作节奏与身体节奏被剥离了协商权。', search_direction: 'vertical', layer: 'mechanism', confidence: 'medium', is_unexpected: false },
        { id: '9', case_name: '医生面对 AI 诊断', content: '医生焦虑的不是"AI 比我准"，而是临床判断权从个人专业被重新分配到"AI + 医保 + 监管"的三方系统。', search_direction: 'lateral', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '10', case_name: '艺术家面对生成式 AI', content: '焦虑来自"风格作为劳动结果"被消解 — 风格的独占性被算法的可复用性瓦解。', search_direction: 'lateral', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '11', case_name: '律师面对法律检索 AI', content: '一部分初级案件的"思考"被外包，但责任仍归律师承担。义务领地未变，能力领地被压缩。', search_direction: 'lateral', layer: 'phenomenon', confidence: 'medium', is_unexpected: false },
        { id: '12', case_name: '汽车取代马车 1900s', content: '马车夫并未消失，转岗到出租车司机。但今天 AI 的差异在于：替代不是水平迁移，而是垂直挤压判断密度。', search_direction: 'vertical', layer: 'mechanism', confidence: 'weak', is_unexpected: true },
      ],
      conclusion: {
        core_finding: 'AI 焦虑的结构性根源不是"AI 会取代我做什么"，而是"AI 让我对「我是谁」的判定权被重新分配"。这种重分配把意义、专业身份、责任归属拆解到了一个由人、模型、机构共同构成的混合系统里。',
        temporal_trajectory: '在最初的几年，AI 焦虑表现为对失业的直接恐惧；随着应用深入，焦虑转向身份与意义的重组——"我做的事还算专业吗"取代了"我会不会被裁"。再往后，焦虑可能稳态化为一种"与系统协商的日常张力"，就像电报和电脑的焦虑最终被吸收进新的工作样态。但 AI 与前者不同：它压缩的是"判断"，而非"执行"。这意味着稳态化所需的时间会更长，且新的协商对象不再仅是雇主，而是包含模型、平台、监管的混合系统。',
        tension: '新生产力的扩展性与主体意义领地的稳定性互斥又共存：扩展性意味着能力可被复制、可外溢，这恰恰削弱了"专业身份"赖以成立的稀缺与边界；但主体又必须有稳定的意义边界才能产生焦虑——所以张力不是 AI vs 人，而是"能力可复制" vs "身份必须不可复制"。',
        boundary_condition: '在那些"能力的稀缺即身份"的领域（艺术家、医生、律师），焦虑最强。在"能力本就被工具中介"的领域（如会计、翻译），焦虑反而较弱——因为意义领地早已与具体技能解耦。',
        unresolved: '当 AI 同时降低了"产出"和"判断"的边际成本，是否仍有不可被复制的领域？我们没有找到结构上对应"判断本身被外包"的成熟历史案例——这是一个真正的新情境。',
        implication: '与其问"AI 会不会取代我"，更值得问的是"我的意义领地是建立在能力的稀缺上，还是建立在判断的承担上"。前者会被持续侵蚀，后者反而可能在 AI 时代被放大。',
        taglines: {
          core_finding: 'AI 焦虑的根源是判定权被重新分配',
          temporal_trajectory: '从失业恐惧 → 身份重组 → 与系统的日常协商',
          tension: '能力可复制 vs 身份必须不可复制',
          boundary_condition: '能力即身份的领域，焦虑最强',
          unresolved: '没有"判断本身被外包"的历史对应',
          implication: '问"判断的承担"，不是"能力的稀缺"',
        },
      },
      schedule_log: [
        { author: 'inception', decision: 'inception_complete', reason: "abstracted to pattern '新生产力对主体意义领地的渗透', 3 entities, 1 relationships", is_degradation: false },
        { author: 'search_lateral', decision: 'search_complete', reason: 'found 4 cases (lateral) via lens', is_degradation: false },
        { author: 'search_vertical', decision: 'search_complete', reason: 'found 3 cases (vertical) via lens', is_degradation: false },
      ],
    };

    // Render process elements as if SSE had streamed them
    setText(dom.analysisQuestion, demo.question);

    // Lens
    if (demo.lenses && demo.lenses.length) {
      state.lens = demo.lenses[demo.lenses.length - 1];
      renderLens(state.lens);
      show(dom.lensReveal);
    }

    // Rails
    state.lateral = { count: demo.lateral_count || 0, rounds: demo.lateral_rounds || 0, done: true };
    state.vertical = { count: demo.vertical_count || 0, rounds: demo.vertical_rounds || 0, done: true };
    updateRailUI('lateral');
    updateRailUI('vertical');
    show(dom.rails);

    // Cases
    state.evidence = demo.evidence || [];
    appendCases(demo.evidence);
    show(dom.casesSection);

    // Schedule log
    state.schedule = demo.schedule_log || [];
    state.tokens = demo.token_spent || 0;
    demo.schedule_log.forEach(function (entry) {
      appendScheduleLog(entry);
    });
    updateMachineMeta();

    // Phase to last known
    setPhase('convergence');

    // Now transition to result
    state.result = demo;
    transitionToResult(demo);
    showScreen('analysis');
  }

  // ============================== Boot ===============================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
