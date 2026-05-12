'use strict';

// =====================================================================
// Unveiling frontend controller.
//
// Three screens, one column each:
//   • home      — single-screen manifesto + form
//   • analysis  — phase timeline + sub-question rows + persistent journey log
//   • result    — inline long-scroll paper (no iframe), 8 cognitive sections
//
// The journey log is PERSISTENT — entries never disappear. Users complained
// that bubbles vanished too quickly; this rebuild treats every finding as
// something the reader can scroll back to.
// =====================================================================

(function () {

  // ============================== State ==============================

  const state = {
    screen: 'home',
    mode: 'balance',
    language: '中文',
    taskId: null,
    eventSource: null,
    treeSignature: '',
    activeSubQuestionId: null,
    phase: 'inception',
    schedule: [],
    journeyCount: 0,
  };

  // ============================ DOM refs =============================

  let dom = {};

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
      nowLine: document.getElementById('now-line'),
      narrationText: document.getElementById('narration-text'),
      subsProgress: document.getElementById('subs-progress'),
      treeList: document.getElementById('tree-node-list'),
      journeyList: document.getElementById('journey-list'),
      journeyCount: document.getElementById('journey-count'),
      machineView: document.getElementById('machine-view'),
      machineToggle: document.getElementById('machine-view-toggle'),
      machineMeta: document.getElementById('machine-view-meta'),
      machineContent: document.getElementById('machine-view-content'),

      // Result — paper sections
      paperEdition: document.getElementById('paper-edition'),
      paperQuestion: document.getElementById('paper-question'),
      paperDeckLink: document.getElementById('paper-deck-link'),
      paperTakeaway: document.getElementById('paper-takeaway'),
      paperTension: document.getElementById('paper-tension'),
      paperBoundary: document.getElementById('paper-boundary'),
      paperFindings: document.getElementById('paper-findings'),
      paperUnexpected: document.getElementById('paper-unexpected'),
      paperPredictions: document.getElementById('paper-predictions'),
      paperUnresolved: document.getElementById('paper-unresolved'),
      paperImplication: document.getElementById('paper-implication'),

      // Result — section wrappers (for is-empty toggling)
      sectionTakeaway: document.getElementById('section-takeaway'),
      sectionTension: document.getElementById('section-tension'),
      sectionBoundary: document.getElementById('section-boundary'),
      sectionFindings: document.getElementById('section-findings'),
      sectionUnexpected: document.getElementById('section-unexpected'),
      sectionPredictions: document.getElementById('section-predictions'),
      sectionUnresolved: document.getElementById('section-unresolved'),
      sectionImplication: document.getElementById('section-implication'),

      // Result — journey block
      lensChains: document.getElementById('lens-timeline-chains'),
      subList: document.getElementById('thinking-sub-questions-list'),
      thinkingToggle: document.getElementById('thinking-toggle'),
      resultBack: document.getElementById('result-back'),
      resultMeta: document.getElementById('result-meta'),
    };
  }

  // ============================ Helpers ==============================

  function $$(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'class') node.className = attrs[k];
        else if (k === 'dataset') {
          Object.keys(attrs[k]).forEach(function (dk) {
            if (attrs[k][dk] != null) node.dataset[dk] = attrs[k][dk];
          });
        } else if (k.startsWith('on') && typeof attrs[k] === 'function') {
          node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        } else if (k in node) {
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

  function toggleEmpty(section, isEmpty) {
    if (!section) return;
    section.classList.toggle('is-empty', !!isEmpty);
  }

  function formatTokens(n) {
    if (n >= 10000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
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
    bindResultControls();

    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === '1') {
      loadDemoResult();
    }
  }

  function bindHome() {
    dom.modeOptions.forEach(function (opt) {
      opt.addEventListener('click', function () {
        state.mode = opt.dataset.mode;
        dom.modeOptions.forEach(function (o) {
          const selected = o === opt;
          o.classList.toggle('is-selected', selected);
          o.setAttribute('aria-checked', selected ? 'true' : 'false');
        });
      });
    });

    dom.langOptions.forEach(function (opt) {
      opt.addEventListener('click', function () {
        state.language = opt.dataset.lang;
        dom.langOptions.forEach(function (o) {
          const selected = o === opt;
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
      const q = (dom.homeQuestion.value || '').trim();
      if (!q) return;
      startAnalysis(q, state.mode);
    });
  }

  function bindAnalysisControls() {
    dom.machineToggle.addEventListener('click', function () {
      const expanded = dom.machineView.classList.toggle('is-expanded');
      dom.machineToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
  }

  function bindResultControls() {
    dom.resultBack.addEventListener('click', function () {
      if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
      }
      resetAnalysisState();
      showScreen('home');
    });

    dom.thinkingToggle.addEventListener('click', function () {
      const expanded = dom.thinkingToggle.dataset.expanded === 'true';
      const next = !expanded;
      dom.thinkingToggle.dataset.expanded = next ? 'true' : 'false';
      dom.thinkingToggle.textContent = next ? '收起详情' : '展开详情';
      $$('.sub-card', dom.subList).forEach(function (card) {
        card.classList.toggle('is-expanded', next);
      });
    });
  }

  // ======================== Reset between runs =======================

  function resetAnalysisState() {
    state.taskId = null;
    state.activeSubQuestionId = null;
    state.treeSignature = '';
    state.phase = 'inception';
    state.schedule = [];
    state.journeyCount = 0;

    setText(dom.analysisEdition, 'issue · 思考进行中');
    setText(dom.analysisQuestion, '');
    setText(dom.narrationText, '系统正在准备……');
    if (dom.nowLine) dom.nowLine.classList.remove('is-degradation');
    setText(dom.subsProgress, '');
    clear(dom.treeList);
    dom.treeList.appendChild(el('li', { class: 'empty-line', textContent: '问题树正在生成……' }));
    clear(dom.journeyList);
    setText(dom.journeyCount, '还没找到第一条');
    clear(dom.machineContent);
    setText(dom.machineMeta, '回合 0 · 0 token');
    dom.machineView.classList.remove('is-expanded');
    dom.machineToggle.setAttribute('aria-expanded', 'false');
    updatePhaseIndicator('inception');

    // Result-screen cleanup so a new run starts blank.
    setText(dom.paperQuestion, '');
    setText(dom.paperTakeaway, '');
    setText(dom.paperTension, '');
    setText(dom.paperBoundary, '');
    clear(dom.paperFindings);
    clear(dom.paperUnexpected);
    clear(dom.paperPredictions);
    setText(dom.paperUnresolved, '');
    setText(dom.paperImplication, '');
    clear(dom.lensChains);
    clear(dom.subList);
    if (dom.thinkingToggle) {
      dom.thinkingToggle.dataset.expanded = 'false';
      dom.thinkingToggle.textContent = '展开详情';
    }
  }

  // ======================== Analysis start ===========================

  function startAnalysis(question, mode) {
    resetAnalysisState();
    setText(dom.analysisQuestion, question);

    fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, mode: mode, language: state.language }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data || !data.task_id) {
          throw new Error(data && data.error ? data.error : '启动分析失败');
        }
        state.taskId = data.task_id;
        showScreen('analysis');
        openStream(data.task_id);
      })
      .catch(function (err) {
        alert('启动失败:' + (err && err.message ? err.message : err));
      });
  }

  function openStream(taskId) {
    const es = new EventSource('/progress/' + encodeURIComponent(taskId));
    state.eventSource = es;
    es.onmessage = function (ev) {
      try {
        handleEvent(JSON.parse(ev.data));
      } catch (e) {
        console.warn('Bad SSE payload', e, ev.data);
      }
    };
    es.onerror = function () {
      // Stream usually closes cleanly after `done`.
      es.close();
      state.eventSource = null;
    };
  }

  // ============================ Events ===============================

  function handleEvent(ev) {
    switch (ev.type) {
      case 'started':
        setText(dom.analysisQuestion, ev.question || '');
        break;
      case 'phase':
        updatePhaseIndicator(ev.phase);
        state.phase = ev.phase;
        break;
      case 'issue_tree':
        renderIssueTree(ev.tree || [], ev.active_sub_question_id);
        if (ev.phase) {
          updatePhaseIndicator(ev.phase);
          state.phase = ev.phase;
        }
        if (typeof ev.round_count === 'number') {
          setText(dom.machineMeta, '回合 ' + ev.round_count + ' · 实时');
        }
        break;
      case 'narration':
        renderNarration(ev.text || '', ev.author || '', !!ev.degradation);
        appendMachineEntry(ev);
        break;
      case 'bubble':
        appendJourneyEntry(ev);
        break;
      case 'done':
        finishAnalysis();
        break;
      case 'error':
        alert('分析出错:' + (ev.error || '未知错误'));
        if (state.eventSource) { state.eventSource.close(); state.eventSource = null; }
        showScreen('home');
        break;
      default:
        // unknown event, ignore
    }
  }

  function finishAnalysis() {
    if (!state.taskId) return;
    fetch('/result/' + encodeURIComponent(state.taskId))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data && data.status === 'error') {
          alert('分析出错:' + (data.error || '未知错误'));
          showScreen('home');
          return;
        }
        renderResult(data);
        showScreen('result');
      })
      .catch(function (err) {
        alert('获取结果失败:' + (err && err.message ? err.message : err));
      });
  }

  // ======================== Phase indicator ==========================

  const PHASE_ORDER = ['inception', 'exploration', 'convergence'];

  function updatePhaseIndicator(current) {
    if (!PHASE_ORDER.includes(current)) return;
    const idx = PHASE_ORDER.indexOf(current);
    $$('.phases__step', dom.phaseIndicator).forEach(function (step, i) {
      step.classList.toggle('is-active', i === idx);
      step.classList.toggle('is-complete', i < idx);
    });
  }

  // ====================== Issue tree (sub-rows) =======================

  function renderIssueTree(tree, activeId) {
    state.activeSubQuestionId = activeId || null;

    const root = tree.find(function (n) { return !n.parent_id; });
    const subs = tree.filter(function (n) { return !!n.parent_id; });

    if (root && !dom.analysisQuestion.textContent) {
      setText(dom.analysisQuestion, root.content);
    }

    const signature = subs
      .map(function (n) { return n.id + ':' + n.status; })
      .join('|') + '||active=' + (activeId || '');

    if (signature === state.treeSignature) return;
    state.treeSignature = signature;

    clear(dom.treeList);
    if (subs.length === 0) {
      dom.treeList.appendChild(el('li', {
        class: 'empty-line', textContent: '问题树正在生成……',
      }));
      setText(dom.subsProgress, '');
      return;
    }

    const closedCount = subs.filter(function (n) { return n.status === 'closed'; }).length;
    setText(dom.subsProgress, closedCount + '/' + subs.length + ' 想清楚');

    subs.forEach(function (node, i) {
      const row = el('li', {
        class: 'sub-row' + (node.id === activeId ? ' is-active' : ''),
        dataset: { status: node.status || 'untouched', id: node.id },
      }, [
        el('span', { class: 'sub-row__index', textContent: String(i + 1).padStart(2, '0') }),
        el('span', { class: 'sub-row__content', textContent: node.content || '' }),
        el('span', {
          class: 'sub-row__pill',
        }, [
          el('span', { class: 'pill', textContent: statusLabel(node.status) }),
        ]),
      ]);
      dom.treeList.appendChild(row);
    });
  }

  function statusLabel(status) {
    switch (status) {
      case 'closed': return '想清楚了';
      case 'exploring': return '还在看';
      case 'untouched': return '还没看';
      case 'stuck': return '卡住了';
      default: return status || '—';
    }
  }

  // =========================== Narration =============================

  function renderNarration(text, author, degradation) {
    setText(dom.narrationText, text);
    if (dom.nowLine) {
      dom.nowLine.classList.toggle('is-degradation', !!degradation);
      if (author) dom.nowLine.dataset.author = author;
    }
  }

  // ====================== Journey log (persistent) ====================

  // Maps SSE bubble kinds to {glyph, label}. These never disappear; the
  // reader can scroll the log at any moment to revisit what was found.
  const JOURNEY_GLYPH = {
    lens_initial:           { glyph: '⊙', label: '新透镜' },
    lens_evolved:           { glyph: '◐', label: '透镜演化' },
    prediction_new:         { glyph: '⊕', label: '新预判' },
    prediction_supported:   { glyph: '✓', label: '预判被支持' },
    prediction_refuted:     { glyph: '✗', label: '预判被驳' },
    prediction_modified:    { glyph: '↻', label: '预判修正' },
    evidence_structure:     { glyph: '▲', label: '结构层' },
    evidence_mechanism:     { glyph: '◆', label: '机制层' },
    evidence_unexpected:    { glyph: '★', label: '意外发现' },
    debate:                 { glyph: '✶', label: '辩论' },
    sub_question_closed:    { glyph: '✓', label: '子问题闭合' },
    sub_question_stuck:     { glyph: '⊘', label: '子问题卡住' },
    degradation:            { glyph: '⚠', label: '降级' },
  };

  function appendJourneyEntry(payload) {
    const kind = payload.kind || 'generic';
    const meta = JOURNEY_GLYPH[kind] || { glyph: '·', label: payload.title || kind };
    const detail = payload.detail || '';

    const entry = el('li', {
      class: 'journey-entry is-entering',
      dataset: { kind: kind },
    }, [
      el('span', { class: 'journey-entry__glyph', textContent: meta.glyph }),
      el('span', { class: 'journey-entry__kind', textContent: meta.label }),
      el('span', { class: 'journey-entry__detail', textContent: detail }),
    ]);
    dom.journeyList.appendChild(entry);

    state.journeyCount += 1;
    setText(dom.journeyCount, state.journeyCount + ' 件事');

    // Drop the entrance class once animation settles.
    setTimeout(function () { entry.classList.remove('is-entering'); }, 400);
  }

  // ======================= Machine-view drawer =======================

  function appendMachineEntry(ev) {
    const line = el('div', { class: 'drawer__entry' });
    line.appendChild(el('span', {
      class: 'drawer__entry-author',
      textContent: (ev.author || '') + ' · ',
    }));
    line.appendChild(el('span', {
      class: 'drawer__entry-text',
      textContent: ev.text || '',
    }));
    if (ev.degradation) line.classList.add('is-degradation');
    dom.machineContent.appendChild(line);
    state.schedule.push(ev);
    if (state.schedule.length > 200) {
      const first = dom.machineContent.firstChild;
      if (first) dom.machineContent.removeChild(first);
      state.schedule.shift();
    }
    dom.machineContent.scrollTop = dom.machineContent.scrollHeight;
  }

  // ============================================================
  // ============     RESULT SCREEN RENDERING     ===============
  // ============================================================

  function loadDemoResult() {
    fetch('/demo-result')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        state.taskId = 'demo';
        renderResult(data);
        showScreen('result');
      })
      .catch(function (err) {
        alert('加载示例失败:' + (err && err.message ? err.message : err));
      });
  }

  function renderResult(data) {
    if (!data) return;

    const deckTarget = state.taskId || 'demo';
    if (dom.paperDeckLink) {
      dom.paperDeckLink.href = '/deck/' + encodeURIComponent(deckTarget);
    }
    setText(dom.paperEdition, 'a closing reading');
    setText(dom.paperQuestion, data.driving_question || '');

    renderPaperSections(data);
    renderLensTimeline(data.lens_chains || []);
    renderSubList(data.sub_questions || []);

    if (data.integrity) {
      setText(dom.resultMeta,
        '回合 ' + (data.integrity.round_count || 0) +
        ' · ' + formatTokens(data.integrity.token_spent || 0) + ' token'
      );
    }

    // Always reset the journey toggle to collapsed on each render.
    if (dom.thinkingToggle) {
      dom.thinkingToggle.dataset.expanded = 'false';
      dom.thinkingToggle.textContent = '展开详情';
    }
  }

  // -------- The 8 cognitive-rhythm paper sections --------

  function renderPaperSections(data) {
    const conclusion = data.conclusion || {};
    const subs = data.sub_questions || [];
    const evidence = data.evidence || [];
    const predictions = data.predictions || [];

    // §1 一句话回答
    const takeaway = conclusion.convergent_finding || '';
    setText(dom.paperTakeaway, takeaway);
    toggleEmpty(dom.sectionTakeaway, !takeaway);

    // §2 张力
    setText(dom.paperTension, conclusion.tension || '');
    toggleEmpty(dom.sectionTension, !conclusion.tension);

    // §3 在哪里不成立
    setText(dom.paperBoundary, conclusion.boundary_condition || '');
    toggleEmpty(dom.sectionBoundary, !conclusion.boundary_condition);

    // §4 收敛的几条 — bullet list of minimum_viable_answer from closed subs
    const findings = subs
      .filter(function (sq) { return sq.status === 'closed' && sq.minimum_viable_answer; })
      .map(function (sq) { return sq.minimum_viable_answer; });
    clear(dom.paperFindings);
    findings.forEach(function (text) {
      dom.paperFindings.appendChild(el('li', { textContent: text }));
    });
    toggleEmpty(dom.sectionFindings, findings.length === 0);

    // §5 意外发现 — unexpected evidence, deduplicated
    const seen = new Set();
    const unexpected = [];
    subs.forEach(function (sq) {
      (sq.top_evidence || []).forEach(function (e) {
        if (e.is_unexpected && !seen.has(e.content)) {
          seen.add(e.content);
          unexpected.push(e);
        }
      });
    });
    evidence.forEach(function (e) {
      if (e.is_unexpected && !seen.has(e.content)) {
        seen.add(e.content);
        unexpected.push(e);
      }
    });
    clear(dom.paperUnexpected);
    unexpected.forEach(function (e) {
      dom.paperUnexpected.appendChild(el('li', { textContent: e.content }));
    });
    toggleEmpty(dom.sectionUnexpected, unexpected.length === 0);

    // §6 可证伪预判
    clear(dom.paperPredictions);
    predictions.forEach(function (p) {
      dom.paperPredictions.appendChild(buildPredictionCard(p));
    });
    toggleEmpty(dom.sectionPredictions, predictions.length === 0);

    // §7 还没回答清楚的
    setText(dom.paperUnresolved, conclusion.unresolved || '');
    toggleEmpty(dom.sectionUnresolved, !conclusion.unresolved);

    // §8 所以你应该
    setText(dom.paperImplication, conclusion.implication || '');
    toggleEmpty(dom.sectionImplication, !conclusion.implication);
  }

  function buildPredictionCard(p) {
    const card = el('div', { class: 'prediction-card' });

    const head = el('div', { class: 'prediction-card__head' }, [
      el('div', { class: 'prediction-card__claim', textContent: p.claim || '' }),
      el('span', {
        class: 'prediction-card__status',
        dataset: { status: p.status || 'pending' },
        textContent: predictionStatusLabel(p.status),
      }),
    ]);
    card.appendChild(head);

    const detail = el('div', { class: 'prediction-card__detail' });
    let hasDetail = false;
    function addRow(label, value) {
      if (!value) return;
      hasDetail = true;
      detail.appendChild(el('div', { class: 'prediction-card__detail-row' }, [
        el('span', { class: 'prediction-card__detail-label', textContent: label }),
        el('span', { textContent: value }),
      ]));
    }
    addRow('Killer 证据', p.killer_evidence);
    addRow('如果成立', p.if_true_we_should_see);
    addRow('如果不成立', p.if_false_we_should_see);

    if (hasDetail) card.appendChild(detail);
    return card;
  }

  function predictionStatusLabel(status) {
    switch (status) {
      case 'supported': return '被支持';
      case 'refuted': return '被驳斥';
      case 'modified': return '已修正';
      case 'pending': return '待验';
      default: return status || '待验';
    }
  }

  // ---------- Journey block: lens chains ----------

  function renderLensTimeline(chains) {
    clear(dom.lensChains);
    if (!chains.length) {
      dom.lensChains.appendChild(el('div', {
        class: 'empty-line', textContent: '这次没换过角度，或者换得太少没看出来。',
      }));
      return;
    }
    chains.forEach(function (entry) {
      const chain = entry.chain || [];
      if (!chain.length) return;
      const block = el('div', { class: 'lens-chain' });
      chain.forEach(function (lens, i) {
        const version = el('div', {
          class: 'lens-version' + (i === 0 ? ' is-initial' : ' is-evolved'),
        });
        version.appendChild(el('div', {
          class: 'lens-version__tag',
          textContent: 'v' + (i + 1) + (i === 0 ? ' · 起点' : ' · 改一稿'),
        }));
        version.appendChild(el('div', { class: 'lens-version__name', textContent: lens.name || '' }));
        if (lens.rationale) {
          version.appendChild(el('div', {
            class: 'lens-version__rationale', textContent: lens.rationale,
          }));
        }
        block.appendChild(version);
      });
      dom.lensChains.appendChild(block);
    });
  }

  // ---------- Journey block: sub-question cards ----------

  function renderSubList(subs) {
    clear(dom.subList);
    if (!subs.length) {
      dom.subList.appendChild(el('div', {
        class: 'empty-line', textContent: '这次还没拆出小问题。',
      }));
      return;
    }
    subs.forEach(function (sq) {
      dom.subList.appendChild(buildSubCard(sq));
    });
  }

  function buildSubCard(sq) {
    const card = el('article', {
      class: 'sub-card',
      dataset: { status: sq.status || 'untouched', id: sq.id || '' },
    });

    const header = el('button', { class: 'sub-card__header', type: 'button' }, [
      el('span', { class: 'sub-card__status-dot' }),
      el('span', { class: 'sub-card__question', textContent: sq.content || '' }),
      el('span', { class: 'pill', textContent: statusLabel(sq.status) }),
      el('span', { class: 'sub-card__chevron', textContent: '▾' }),
    ]);
    header.addEventListener('click', function () {
      card.classList.toggle('is-expanded');
    });
    card.appendChild(header);

    const body = el('div', { class: 'sub-card__body' });

    if (sq.minimum_viable_answer) {
      body.appendChild(el('div', { class: 'sub-card__answer' }, [
        el('span', { class: 'sub-card__answer-label', textContent: '最少够用的答案' }),
        el('span', { textContent: sq.minimum_viable_answer }),
      ]));
    }

    const stats = el('div', { class: 'sub-card__stats' });
    stats.appendChild(buildStat(sq.structure_layer_count, '底层规律'));
    stats.appendChild(buildStat(sq.mechanism_layer_count, '怎么运作'));
    stats.appendChild(buildStat(sq.unexpected_count, '意外发现', 'unexpected'));
    stats.appendChild(buildStat(sq.evidence_count, '找到的证据'));
    body.appendChild(stats);

    if (sq.conclusion) {
      body.appendChild(buildSubConclusion(sq.conclusion));
    }

    if (sq.top_evidence && sq.top_evidence.length) {
      body.appendChild(el('div', {
        class: 'sub-card__evidence-heading', textContent: '最有分量的几条',
      }));
      const list = el('div', { class: 'sub-card__evidence-list' });
      sq.top_evidence.forEach(function (ev) {
        list.appendChild(buildEvidenceItem(ev));
      });
      body.appendChild(list);
    }

    if (sq.status === 'stuck') {
      body.appendChild(el('div', {
        class: 'sub-card__stuck-note',
        textContent: '这个小问题试了几次没能想清楚。一般是材料没找够、看的角度还不对路，或者问题本身要换个问法。',
      }));
    }

    card.appendChild(body);
    return card;
  }

  function buildStat(count, label, emphasis) {
    const stat = el('div', { class: 'sub-card__stat' });
    if (emphasis) stat.dataset.emphasis = emphasis;
    stat.appendChild(el('strong', { textContent: String(count || 0) }));
    stat.appendChild(el('span', { textContent: label }));
    return stat;
  }

  function buildSubConclusion(c) {
    const block = el('div', { class: 'sub-card__conclusion' });
    if (c.convergent_finding) {
      block.appendChild(el('div', { class: 'sub-card__conclusion-row is-finding' }, [
        el('span', { class: 'sub-card__conclusion-label', textContent: '小结' }),
        el('span', { textContent: c.convergent_finding }),
      ]));
    }
    if (c.tension) {
      block.appendChild(el('div', { class: 'sub-card__conclusion-row is-tension' }, [
        el('span', { class: 'sub-card__conclusion-label', textContent: '张力' }),
        el('span', { textContent: c.tension }),
      ]));
    }
    if (c.boundary_condition) {
      block.appendChild(el('div', { class: 'sub-card__conclusion-row' }, [
        el('span', { class: 'sub-card__conclusion-label', textContent: '不成立' }),
        el('span', { textContent: c.boundary_condition }),
      ]));
    }
    if (c.unresolved) {
      block.appendChild(el('div', { class: 'sub-card__conclusion-row' }, [
        el('span', { class: 'sub-card__conclusion-label', textContent: '未尽' }),
        el('span', { textContent: c.unresolved }),
      ]));
    }
    return block;
  }

  function buildEvidenceItem(ev) {
    const item = el('div', {
      class: 'evidence-item',
      dataset: {
        confidence: ev.is_unexpected ? 'unexpected' : (ev.confidence || 'medium'),
        layer: ev.layer || 'phenomenon',
      },
    });
    item.appendChild(el('span', {
      class: 'evidence-item__layer', textContent: layerLabel(ev.layer),
    }));
    item.appendChild(el('span', {
      class: 'evidence-item__text', textContent: ev.content || '',
    }));
    return item;
  }

  function layerLabel(layer) {
    return ({
      structure: '底层规律',
      mechanism: '怎么运作',
      phenomenon: '表面',
    }[layer]) || (layer || '—');
  }

  // ============================== Boot ===============================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
