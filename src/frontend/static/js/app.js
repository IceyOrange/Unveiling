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

  // ============================== i18n ===============================

  var I18N = {
    '中文': {
      pageTitle: 'Unveiling · 万事曾在别处发生，本质总在深处相通',
      manifesto: '万事曾在<em class="manifesto__em">别处</em>发生，本质总在<em class="manifesto__em">深处</em>相通',
      lead: '写一个问题。我们去别的行业、别的时代里，看看它曾经怎么发生过。',
      formLabel: '你想搞清楚什么',
      placeholder: '把它完整地写下来。越具体，类比越准。',
      submit: '开始分析',
      demoLink: '看一份示例',
      promptsHeading: '也可以从这些问题开始',
      prompt1q: '大学生实习难找',
      prompt1l: '也许会聊：医师执照 · 师徒制 · 城市的入场券',
      prompt2q: '街上看到越来越多低头族',
      prompt2l: '也许会聊：街边咖啡馆 · 火车上的报纸 · 早年的电视',
      prompt3q: '社交平台的劣化趋势',
      prompt3l: '也许会聊：购物中心 · 公共绿地 · 殖民地小镇',
      prompt4q: '养小猫还是养小狗',
      prompt4l: '也许会聊：合伙人 · 房客 · 一段长期友谊',
      footLine1: '不是给答案。',
      footLine2: '是给一个看法的支点。',
      editionPrefix: '一份正在进行的分析',
      editionComplete: '分析完成',
      phaseInception: '抽象',
      phaseInceptionDesc: '提炼问题的骨架',
      phaseExploration: '搜集',
      phaseExplorationDesc: '跨领域、跨时期 找类比',
      phaseConvergence: '收拢',
      phaseConvergenceDesc: '归纳 · 找矛盾',
      nowLabel: '现在',
      narrationInit: '正在准备分析……',
      narrationInception: '正在拆解问题 — 提炼核心结构',
      narrationExploration: '跨领域与跨时期并行搜索 — 找结构相似的类比案例',
      narrationConvergence: '正在跨案例归纳共性 · 找矛盾 · 写结论',
      narrationFoundCase: '刚刚找到 [{dir}] {name}{more}',
      narrationConclusionReady: '结论已写入，准备呈现……',
      narrationComplete: '分析完成',
      narrationStartFailed: '启动分析失败：',
      lensTag: '观察角度',
      lensUnnamed: '未命名',
      lensEntities: '参与的角色',
      lensRelations: '角色之间的关系',
      railsTitle: '搜索进度',
      railsSubtitle: '两个方向 · 各找 10 个 · 最多 3 轮',
      railLateral: '跨领域',
      railLateralDesc: '找当代其他行业',
      railVertical: '跨时期',
      railVerticalDesc: '找历史上的先例',
      railRounds: '第 {round} / {max} 轮',
      statusNotStarted: '尚未开始',
      statusInProgress: '进行中',
      statusComplete: '已完成 — 找到 {count} 条',
      statusRoundsExhausted: '轮次用完 — 带 {count} 条结束',
      casesTitle: '找到的类比',
      casesEmpty: '等系统找到第一个案例……',
      caseUnnamed: '（未命名案例）',
      caseUnexpected: '意外',
      caseUnexpectedTitle: '系统标注为意外发现',
      directionLateral: '跨领域',
      directionVertical: '跨时期',
      layerPhenomenon: '现象',
      layerMechanism: '机制',
      layerStructure: '结构',
      confStrong: '强',
      confMedium: '中',
      confWeak: '弱',
      confUnexpected: '意外',
      machineView: '机器视角',
      transitionLabel: '结论',
      integrityLateralLabel: '跨领域',
      integrityVerticalLabel: '跨时期',
      integrityDegradationLabel: '降级处理',
      integrityDegradationTitle: 'LLM 调用失败时启用的备用方案次数',
      integrityTokensLabel: 'token',
      unitCases: '个案例',
      unitIssues: '处',
      conclusionsTitle: '结论',
      conclusionsSubtitle: '标题为主，展开看完整推理',
      chapterCoreFinding: '核心结论',
      chapterTrajectory: '这件事的走向',
      chapterTension: '难处在哪',
      chapterBoundary: '这话在哪里不成立',
      chapterUnresolved: '还没回答清楚的',
      chapterImplication: '所以你应该',
      expandReasoning: '↓ 展开看推理',
      collapse: '↑ 收起',
      recapTitle: '分析过程速览',
      recapLensTitle: '我们用什么角度看',
      recapCaseIndex: '案例索引',
      recapDegradation: '降级与跳过',
      recapDegradationSubtitle: '系统在分析中遇到的失败点',
      recapMetaLens: '观察角度',
      recapMetaCases: '{count} 个案例',
      recapMetaDegradations: '{count} 处降级',
      recapMetaEmpty: '本次没有可回顾的过程材料',
      backBtn: '重新开始',
      resultMeta: '跨领域 {lateral} · 跨时期 {vertical} · {tokens} token{degradations}',
      logEntries: '条调度',
      tokensUnit: 'token',
      casesCounter: '{count} 条',
      layerTip: '层级：{layer}',
      outlineTitle: '这次分析',
      outlineLens: '观察角度',
      outlineRails: '搜索进度',
      outlineCases: '找到的类比',
      outlineSection: '§ {num}',
      outlineAriaLabel: '这次分析的目录',
      phaseAriaLabel: '分析阶段',
      emptyBody: '（系统未给出此项）',
      caseIndexEmpty: '本次没有收集到案例。',
      caseIndexNone: '（无）',
    },
    'English': {
      pageTitle: 'Unveiling · Everything happened elsewhere; essences always connect in the depths',
      manifesto: 'Everything happened <em class="manifesto__em">elsewhere</em>; essences always connect in the <em class="manifesto__em">depths</em>',
      lead: 'Write a question. We\'ll look across other industries and other eras to see how it happened before.',
      formLabel: 'What do you want to figure out',
      placeholder: 'Write it out in full. The more specific, the sharper the analogy.',
      submit: 'Start Analysis',
      demoLink: 'See an example',
      promptsHeading: 'Or start with one of these',
      prompt1q: 'College internships are hard to find',
      prompt1l: 'Might explore: medical licenses · apprenticeship · urban entry passes',
      prompt2q: 'More people staring at phones',
      prompt2l: 'Might explore: sidewalk cafés · newspapers on trains · early television',
      prompt3q: 'Social platforms degrading',
      prompt3l: 'Might explore: shopping malls · public greens · colonial towns',
      prompt4q: 'Get a cat or a dog',
      prompt4l: 'Might explore: partners · tenants · a long friendship',
      footLine1: 'Not answers.',
      footLine2: 'A pivot for perspective.',
      editionPrefix: 'An analysis in progress',
      editionComplete: 'Analysis complete',
      phaseInception: 'Abstraction',
      phaseInceptionDesc: 'Distill the question\'s skeleton',
      phaseExploration: 'Exploration',
      phaseExplorationDesc: 'Find analogies across domains & eras',
      phaseConvergence: 'Convergence',
      phaseConvergenceDesc: 'Synthesize · Find tension',
      nowLabel: 'Now',
      narrationInit: 'Preparing analysis…',
      narrationInception: 'Deconstructing the question — distilling core structure',
      narrationExploration: 'Parallel search across domains & eras — finding structurally similar cases',
      narrationConvergence: 'Synthesizing across cases · finding tension · writing conclusions',
      narrationFoundCase: 'Just found [{dir}] {name}{more}',
      narrationConclusionReady: 'Conclusions written, preparing to present…',
      narrationComplete: 'Analysis complete',
      narrationStartFailed: 'Failed to start analysis: ',
      lensTag: 'Lens',
      lensUnnamed: 'Unnamed',
      lensEntities: 'Entities',
      lensRelations: 'Relations',
      railsTitle: 'Search Progress',
      railsSubtitle: 'Two directions · 10 each · max 3 rounds',
      railLateral: 'Cross-domain',
      railLateralDesc: 'Find contemporary industries',
      railVertical: 'Cross-era',
      railVerticalDesc: 'Find historical precedents',
      railRounds: 'Round {round} / {max}',
      statusNotStarted: 'Not started',
      statusInProgress: 'In progress',
      statusComplete: 'Complete — {count} found',
      statusRoundsExhausted: 'Rounds exhausted — ended with {count}',
      casesTitle: 'Analogies Found',
      casesEmpty: 'Waiting for the first case…',
      caseUnnamed: '(Unnamed case)',
      caseUnexpected: 'Unexpected',
      caseUnexpectedTitle: 'System flagged as unexpected discovery',
      directionLateral: 'Cross-domain',
      directionVertical: 'Cross-era',
      layerPhenomenon: 'Phenomenon',
      layerMechanism: 'Mechanism',
      layerStructure: 'Structure',
      confStrong: 'Strong',
      confMedium: 'Medium',
      confWeak: 'Weak',
      confUnexpected: 'Unexpected',
      machineView: 'Machine View',
      transitionLabel: 'Conclusions',
      integrityLateralLabel: 'Cross-domain',
      integrityVerticalLabel: 'Cross-era',
      integrityDegradationLabel: 'Degradations',
      integrityDegradationTitle: 'Fallback activations when LLM calls failed',
      integrityTokensLabel: 'tokens',
      unitCases: ' cases',
      unitIssues: ' issues',
      conclusionsTitle: 'Conclusions',
      conclusionsSubtitle: 'Titles first; expand for full reasoning',
      chapterCoreFinding: 'Core Finding',
      chapterTrajectory: 'Trajectory',
      chapterTension: 'Tension',
      chapterBoundary: 'Boundary Conditions',
      chapterUnresolved: 'Unresolved',
      chapterImplication: 'Implication',
      expandReasoning: '↓ Expand reasoning',
      collapse: '↑ Collapse',
      recapTitle: 'Analysis Trail',
      recapLensTitle: 'Lens We Used',
      recapCaseIndex: 'Case Index',
      recapDegradation: 'Degradations & Skips',
      recapDegradationSubtitle: 'Failure points encountered during analysis',
      recapMetaLens: 'Lens',
      recapMetaCases: '{count} cases',
      recapMetaDegradations: '{count} degradations',
      recapMetaEmpty: 'No process material to review this time',
      backBtn: 'Start Over',
      resultMeta: 'Cross-domain {lateral} · Cross-era {vertical} · {tokens} tokens{degradations}',
      logEntries: 'log entries',
      tokensUnit: 'tokens',
      casesCounter: '{count} cases',
      layerTip: 'Layer: {layer}',
      outlineTitle: 'This Analysis',
      outlineLens: 'Lens',
      outlineRails: 'Progress',
      outlineCases: 'Cases Found',
      outlineSection: '§ {num}',
      outlineAriaLabel: 'Analysis outline',
      phaseAriaLabel: 'Analysis phase',
      emptyBody: '(System did not provide this item)',
      caseIndexEmpty: 'No cases collected this time.',
      caseIndexNone: '(None)',
    }
  };

  function t(key, params) {
    var dict = I18N[state.language] || I18N['中文'];
    var text = dict[key];
    if (text == null) text = I18N['中文'][key] || key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        text = text.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
      });
    }
    return text;
  }

  function detectLanguage() {
    var saved = null;
    try {
      saved = localStorage.getItem('unveiling-lang');
    } catch (e) {
      saved = null;
    }
    if (saved === '中文' || saved === 'English') return saved;
    var lang = (navigator.language || (navigator.languages && navigator.languages[0]) || 'zh-CN').toLowerCase();
    if (lang.indexOf('zh') === 0) return '中文';
    if (lang.indexOf('en') === 0) return 'English';
    return '中文';
  }

  function applyLanguage() {
    var lang = state.language === 'English' ? 'en' : 'zh-CN';
    document.documentElement.lang = lang;
    document.title = t('pageTitle');

    // --- Home screen ---
    var manifestoLine = document.querySelector('.manifesto__line');
    if (manifestoLine) manifestoLine.innerHTML = t('manifesto');

    var lead = document.querySelector('.home__lead');
    if (lead) lead.textContent = t('lead');

    var formLabel = document.querySelector('.home-form__label[for="home-question"]');
    if (formLabel) formLabel.textContent = t('formLabel');

    var questionInput = document.getElementById('home-question');
    if (questionInput) questionInput.placeholder = t('placeholder');

    var submitBtn = document.querySelector('.home-form__submit');
    if (submitBtn) {
      var submitText = submitBtn.querySelector('span:not(.home-form__submit-arrow)');
      if (submitText) submitText.textContent = t('submit');
    }

    var demoLink = document.querySelector('.home__demo-link');
    if (demoLink) {
      var arrow = demoLink.querySelector('span');
      demoLink.innerHTML = t('demoLink') + ' <span aria-hidden="true">→</span>';
    }

    var promptsHeading = document.querySelector('.prompts__heading-text');
    if (promptsHeading) promptsHeading.textContent = t('promptsHeading');

    var promptCards = document.querySelectorAll('.prompt-card');
    promptCards.forEach(function (card, i) {
      var qEl = card.querySelector('.prompt-card__question');
      var lEl = card.querySelector('.prompt-card__lenses');
      if (qEl) qEl.textContent = t('prompt' + (i + 1) + 'q');
      if (lEl) lEl.textContent = t('prompt' + (i + 1) + 'l');
    });

    var footLines = document.querySelectorAll('.home__foot-line');
    if (footLines.length >= 2) {
      footLines[0].textContent = t('footLine1');
      footLines[1].textContent = t('footLine2');
    }

    // --- Analysis screen ---
    // Phase names & descs
    var phaseSteps = document.querySelectorAll('.phases__step');
    var phaseKeys = ['inception', 'exploration', 'convergence'];
    phaseSteps.forEach(function (step, i) {
      var nameEl = step.querySelector('.phases__step-name');
      var descEl = step.querySelector('.phases__step-desc');
      if (nameEl) nameEl.textContent = t('phase' + phaseKeys[i].charAt(0).toUpperCase() + phaseKeys[i].slice(1));
      if (descEl) descEl.textContent = t('phase' + phaseKeys[i].charAt(0).toUpperCase() + phaseKeys[i].slice(1) + 'Desc');
    });

    var nowLabel = document.querySelector('.now__label');
    if (nowLabel) nowLabel.textContent = t('nowLabel');

    var lensTag = document.querySelector('.lens-reveal__tag');
    if (lensTag) lensTag.textContent = t('lensTag');

    var lensColHeads = document.querySelectorAll('.lens-reveal__col-head, .lens-map__col-head');
    if (lensColHeads.length >= 2) {
      lensColHeads[0].textContent = t('lensEntities');
      lensColHeads[1].textContent = t('lensRelations');
    }

    var railsTitle = document.querySelector('.rails__title');
    if (railsTitle) railsTitle.textContent = t('railsTitle');
    var railsSubtitle = document.querySelector('.rails__subtitle');
    if (railsSubtitle) railsSubtitle.textContent = t('railsSubtitle');

    var railNames = document.querySelectorAll('.rail__name');
    if (railNames.length >= 2) {
      railNames[0].textContent = t('railLateral');
      railNames[1].textContent = t('railVertical');
    }
    var railDescs = document.querySelectorAll('.rail__desc');
    if (railDescs.length >= 2) {
      railDescs[0].textContent = t('railLateralDesc');
      railDescs[1].textContent = t('railVerticalDesc');
    }

    var casesTitle = document.querySelector('.cases__title');
    if (casesTitle) casesTitle.textContent = t('casesTitle');

    var machineToggleLabel = document.querySelector('.drawer__toggle-label');
    if (machineToggleLabel) machineToggleLabel.textContent = t('machineView');

    var integrityLabels = document.querySelectorAll('.integrity__label');
    if (integrityLabels.length >= 4) {
      integrityLabels[0].textContent = t('integrityLateralLabel');
      integrityLabels[1].textContent = t('integrityVerticalLabel');
      integrityLabels[2].textContent = t('integrityDegradationLabel');
      integrityLabels[2].parentElement.title = t('integrityDegradationTitle');
      integrityLabels[3].textContent = t('integrityTokensLabel');
    }
    var integrityUnits = document.querySelectorAll('.integrity__unit');
    if (integrityUnits.length >= 3) {
      integrityUnits[0].textContent = t('unitCases');
      integrityUnits[1].textContent = t('unitCases');
      integrityUnits[2].textContent = t('unitIssues');
    }

    var conclusionsTitle = document.querySelector('.conclusions__title');
    if (conclusionsTitle) conclusionsTitle.textContent = t('conclusionsTitle');
    var conclusionsSubtitle = document.querySelector('.conclusions__subtitle');
    if (conclusionsSubtitle) conclusionsSubtitle.textContent = t('conclusionsSubtitle');

    // Chapter markers
    var chapterKeys = ['CoreFinding', 'Trajectory', 'Tension', 'Boundary', 'Unresolved', 'Implication'];
    var chapterEls = document.querySelectorAll('.conclusion');
    chapterEls.forEach(function (el, i) {
      var nameEl = el.querySelector('.conclusion__marker-name');
      if (nameEl) nameEl.textContent = t('chapter' + chapterKeys[i]);
      var toggleOpen = el.querySelector('.conclusion__toggle-open');
      var toggleClose = el.querySelector('.conclusion__toggle-close');
      if (toggleOpen) toggleOpen.textContent = t('expandReasoning');
      if (toggleClose) toggleClose.textContent = t('collapse');
    });

    var recapToggleLabel = document.querySelector('.recap__toggle-label');
    if (recapToggleLabel) recapToggleLabel.textContent = t('recapTitle');

    var recapSectionTitles = document.querySelectorAll('.recap__section-title');
    if (recapSectionTitles.length >= 3) {
      recapSectionTitles[0].textContent = t('recapLensTitle');
      recapSectionTitles[1].textContent = t('recapCaseIndex');
      recapSectionTitles[2].textContent = t('recapDegradation');
    }
    var recapSectionSubs = document.querySelectorAll('.recap__section-sub');
    if (recapSectionSubs.length >= 3) {
      recapSectionSubs[2].textContent = t('recapDegradationSubtitle');
    }

    var backBtn = document.querySelector('.analysis__back');
    if (backBtn) {
      var backText = backBtn.querySelector('span:not([aria-hidden])');
      if (backText) backText.textContent = t('backBtn');
    }

    var outlineTitle = document.querySelector('.outline__title');
    if (outlineTitle) outlineTitle.textContent = t('outlineTitle');
    var outlineItems = document.querySelectorAll('.outline__item[data-target]');
    var outlineKeys = ['outlineLens', 'outlineRails', 'outlineCases'];
    var chapterKeys = ['CoreFinding', 'Trajectory', 'Tension', 'Boundary', 'Unresolved', 'Implication'];
    outlineItems.forEach(function (item, i) {
      var label = item.querySelector('.outline__label');
      if (!label) return;
      var target = item.dataset.target;
      if (target && target.indexOf('chapter-') === 0) {
        var chapIdx = CHAPTERS.findIndex(function (ch) { return 'chapter-' + ch.key === target; });
        if (chapIdx >= 0) label.textContent = t('chapter' + chapterKeys[chapIdx]);
      } else if (i < 3) {
        label.textContent = t(outlineKeys[i]);
      }
    });

    // Update dynamic constants
    PHASE_LABEL.inception = t('phaseInception');
    PHASE_LABEL.exploration = t('phaseExploration');
    PHASE_LABEL.convergence = t('phaseConvergence');
    DIRECTION_LABEL.lateral = t('directionLateral');
    DIRECTION_LABEL.vertical = t('directionVertical');
    LAYER_LABEL.phenomenon = t('layerPhenomenon');
    LAYER_LABEL.mechanism = t('layerMechanism');
    LAYER_LABEL.structure = t('layerStructure');
    CONFIDENCE_LABEL.strong = t('confStrong');
    CONFIDENCE_LABEL.medium = t('confMedium');
    CONFIDENCE_LABEL.weak = t('confWeak');
    CONFIDENCE_LABEL.unexpected = t('confUnexpected');
    CHAPTERS[0].fallback = t('chapterCoreFinding');
    CHAPTERS[1].fallback = t('chapterTrajectory');
    CHAPTERS[2].fallback = t('chapterTension');
    CHAPTERS[3].fallback = t('chapterBoundary');
    CHAPTERS[4].fallback = t('chapterUnresolved');
    CHAPTERS[5].fallback = t('chapterImplication');

    // Update CSS pseudo-element labels via custom properties
    var casesList = document.querySelector('.cases__list');
    if (casesList) {
      casesList.style.setProperty('--cases-empty', '"' + t('casesEmpty') + '"');
    }
    var transitionEl = document.querySelector('.analysis__transition');
    if (transitionEl) {
      transitionEl.style.setProperty('--transition-label', '"' + t('transitionLabel') + '"');
    }

    // Update current edition label if analysis is visible
    if (state.screen === 'analysis') {
      if (state.result) {
        setText(dom.analysisEdition, t('editionComplete'));
      } else {
        setText(dom.analysisEdition, t('editionPrefix') + ' · ' + (PHASE_LABEL[state.phase] || state.phase));
      }
    }

    // Update dynamic counters / meta text that may have been rendered in another language
    if (dom.casesCounter) {
      setText(dom.casesCounter, t('casesCounter', {count: state.evidence.length}));
    }
    if (dom.machineMeta) {
      updateMachineMeta();
    }
    if (dom.caseIndexMeta) {
      setText(dom.caseIndexMeta, t('casesCounter', {count: state.evidence.length}));
    }
    if (state.result) {
      if (dom.resultMeta) renderResultMeta(state.result);
      if (dom.recapMeta) renderRecap(state.result);
    }
    if (dom.narrationText && state.screen === 'home') {
      setText(dom.narrationText, t('narrationInit'));
    }

    // Accessibility labels and document language
    var outlineEl = document.getElementById('outline');
    if (outlineEl) outlineEl.setAttribute('aria-label', t('outlineAriaLabel'));
    if (dom.phaseIndicator) dom.phaseIndicator.setAttribute('aria-label', t('phaseAriaLabel'));
    document.documentElement.lang = state.language === '中文' ? 'zh-CN' : 'en';
  }

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
    language: detectLanguage(),
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
      langOptions: document.querySelectorAll('.lang-toggle__btn'),
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

  function setNarration(text) {
    var wrap = dom.narrationText && dom.narrationText.closest('.now');
    if (!wrap) {
      setText(dom.narrationText, text);
      return;
    }
    wrap.classList.add('is-updating');
    setTimeout(function () {
      setText(dom.narrationText, text);
      wrap.classList.remove('is-updating');
    }, 160);
  }

  function animateNumber(el, target, duration) {
    if (!el) return;
    duration = duration || 700;
    var start = parseInt(el.textContent.replace(/\D/g, ''), 10) || 0;
    if (start === target) { setText(el, target); return; }
    var startTime = null;
    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.round(start + (target - start) * eased);
      setText(el, current);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
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
    syncLanguageToggle();
    bindHome();
    bindAnalysisControls();
    bindConclusionControls();
    outline.init();
    applyLanguage();

    var params = new URLSearchParams(window.location.search);
    if (params.get('demo') === '1') {
      loadDemoResult();
    }
  }

  function syncLanguageToggle() {
    dom.langOptions.forEach(function (opt) {
      var selected = opt.dataset.lang === state.language;
      opt.classList.toggle('is-selected', selected);
      opt.setAttribute('aria-checked', selected ? 'true' : 'false');
    });
  }

  function bindHome() {
    dom.langOptions.forEach(function (opt) {
      opt.addEventListener('click', function () {
        state.language = opt.dataset.lang;
        try {
          localStorage.setItem('unveiling-lang', opt.dataset.lang);
        } catch (e) {
          // ignore storage errors
        }
        dom.langOptions.forEach(function (o) {
          var selected = o === opt;
          o.classList.toggle('is-selected', selected);
          o.setAttribute('aria-checked', selected ? 'true' : 'false');
        });
        applyLanguage();
      });
    });

    dom.promptCards.forEach(function (card) {
      card.addEventListener('click', function () {
        var qEl = card.querySelector('.prompt-card__question');
        dom.homeQuestion.value = qEl ? qEl.textContent.trim() : '';
        dom.homeQuestion.focus();
      });
    });

    dom.homeForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = (dom.homeQuestion.value || '').trim();
      if (!q) return;
      startAnalysis(q, state.language);
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

    setNarration(t('narrationInit'));
    hide(dom.lensReveal);
    hide(dom.rails);
    hide(dom.casesSection);
    clear(dom.lensEntities);
    clear(dom.lensRelations);
    clear(dom.casesList);
    clear(dom.scheduleLogList);
    setText(dom.casesCounter, t('casesCounter', {count: 0}));
    setText(dom.machineMeta, '0 ' + t('logEntries') + ' · 0 ' + t('tokensUnit'));
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

    // Outline back to all-pending — sections will re-announce themselves
    // through MutationObserver as they come out of `hidden`.
    if (outline && outline.reset) outline.reset();
  }

  // ========================== Start a run ============================

  function startAnalysis(question, language) {
    resetAnalysisState();
    setText(dom.analysisQuestion, question);
    showScreen('analysis');

    fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, language: language }),
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
        setNarration(t('narrationStartFailed') + (err.message || err));
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
      setNarration(t('narrationExploration'));
    } else if (ev.phase === 'convergence') {
      setNarration(t('narrationConvergence'));
    } else if (ev.phase === 'inception') {
      setNarration(t('narrationInception'));
    }
  }

  function onLens(ev) {
    state.lens = ev.lens;
    renderLens(ev.lens);
    show(dom.lensReveal);
    setNarration(t('lensTag') + ' — ' + (ev.lens.name || t('lensUnnamed')));
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
      var moreNote = items.length > 1 ? ' (' + items.length + ')' : '';
      setNarration(t('narrationFoundCase', {
        dir: dirLabel,
        name: first.case_name || t('caseUnnamed'),
        more: moreNote
      }));
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
    setNarration(t('narrationConclusionReady'));
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
    setNarration('Error: ' + (ev.error || 'Unknown error'));
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
    setText(dom.analysisEdition, t('editionPrefix') + ' · ' + (PHASE_LABEL[phaseKey] || phaseKey));
  }

  function setPhaseAllComplete() {
    $$('.phases__step', dom.phaseIndicator).forEach(function (step) {
      step.classList.remove('is-active', 'is-future');
      step.classList.add('is-complete');
    });
    setText(dom.analysisEdition, t('editionComplete'));
  }

  function renderLens(lens) {
    setText(dom.lensName, lens.name || t('lensUnnamed'));
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
    setText(roundsEl, t('railRounds', {round: rec.rounds, max: MAX_ROUNDS}));
    var fillPct = pct(rec.count, TARGET_PER_DIRECTION);
    fillEl.style.width = fillPct + '%';

    var label = t('statusInProgress');
    if (rec.count >= TARGET_PER_DIRECTION) {
      label = t('statusComplete', {count: rec.count});
      fillEl.classList.add('rail__fill--done');
    } else if (rec.rounds >= MAX_ROUNDS) {
      label = t('statusRoundsExhausted', {count: rec.count});
      fillEl.classList.add('rail__fill--stuck');
    } else if (rec.rounds === 0 && rec.count === 0) {
      label = t('statusNotStarted');
    }
    setText(statusEl, label);
  }

  function appendCases(items) {
    items.forEach(function (e, i) {
      var card = buildCaseRow(e);
      card.style.animationDelay = (i * 70) + 'ms';
      dom.casesList.appendChild(card);
    });
    setText(dom.casesCounter, t('casesCounter', {count: state.evidence.length}));
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
      title: t('layerTip', {layer: LAYER_LABEL[layer] || layer}),
    }, LAYER_MARKER[layer] || '■□□');
    var confChip = el('span', {
      class: 'case__chip case__chip--conf case__chip--conf-' + conf,
    }, CONFIDENCE_LABEL[conf] || conf);
    var meta = el('div', { class: 'case__meta' }, [dirChip, layerMark, confChip]);
    if (isUnexpected) {
      meta.appendChild(el('span', {
        class: 'case__chip case__chip--unexpected',
        title: t('caseUnexpectedTitle'),
      }, t('caseUnexpected')));
    }
    return el('li', { class: 'case' + (isUnexpected ? ' case--unexpected' : '') }, [
      meta,
      el('div', { class: 'case__name' }, e.case_name || t('caseUnnamed')),
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
      state.schedule.length + ' ' + t('logEntries') + ' · ' + formatTokens(state.tokens) + ' ' + t('tokensUnit')
    );
  }

  // =================== Transition to result (no screen switch) ==========

  function transitionToResult(result) {
    if (!result) return;

    // 1. All phases complete
    setPhaseAllComplete();

    // 2. Narration wraps up
    setNarration(t('narrationComplete'));

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
    animateNumber(dom.integrityLateral, result.lateral_count || 0);
    animateNumber(dom.integrityVertical, result.vertical_count || 0);
    var degCount = (result.schedule_log || []).filter(function (l) {
      return l.is_degradation;
    }).length;
    animateNumber(dom.integrityDegradation, degCount);
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
        el('p', { class: bodyClass }, text || t('emptyBody'))
      );
    }

    if (chapterEl) {
      chapterEl.classList.toggle('is-empty', !text);
      chapterEl.style.animationDelay = (index * 160) + 'ms';
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
      if (lenses.length) bits.push(t('recapMetaLens'));
      var evCount = (result.evidence || []).length;
      if (evCount) bits.push(t('recapMetaCases', {count: evCount}));
      var degCount = degraded.length;
      if (degCount) bits.push(t('recapMetaDegradations', {count: degCount}));
      setText(dom.recapMeta, bits.length ? bits.join(' · ') : t('recapMetaEmpty'));
    }
  }

  function renderResultMeta(result) {
    var degCount = (result.schedule_log || []).filter(function (l) {
      return l.is_degradation;
    }).length;
    var degText = degCount ? ' · ' + t('recapMetaDegradations', {count: degCount}) : '';
    setText(dom.resultMeta,
      t('resultMeta', {
        lateral: result.lateral_count || 0,
        vertical: result.vertical_count || 0,
        tokens: formatTokens(result.token_spent || 0),
        degradations: degText
      })
    );
  }

  // ========================== Case index ==============================

  function renderCaseIndex(evidence) {
    clear(dom.caseIndex);
    setText(dom.caseIndexMeta, t('casesCounter', {count: evidence.length}));
    if (!evidence.length) {
      dom.caseIndex.appendChild(
        el('div', { class: 'case-index__empty' }, t('caseIndexEmpty'))
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
            dir === 'lateral' ? t('railLateralDesc') : t('railVerticalDesc')),
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
      return el('div', { class: 'case-index__none' }, t('caseIndexNone'));
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

  var DEMO_DATA = {
    '中文': {
      question: 'AI 时代人们的 AI 焦虑',
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
    },
    'English': {
      question: 'AI anxiety in the age of AI',
      language: 'English',
      lateral_count: 7,
      vertical_count: 5,
      lateral_rounds: 2,
      vertical_rounds: 2,
      token_spent: 9420,
      lenses: [{
        name: 'Penetration of new productive forces into the subject\'s territory of meaning',
        rationale: 'When a new productive force drives the marginal cost of a class of cognitive labor toward zero, the function and meaning carried by the subjects of that labor are redistributed. Anxiety is not a reaction to the tool itself, but a reaction to the redrawing of the territory of meaning.',
        entities: [
          { surface: 'AI', structural_role: 'A rising new productive force whose capabilities can spill over' },
          { surface: 'People', structural_role: 'Mainstream subjects whose value and identity are being disrupted by the new productive force' },
          { surface: 'Anxiety', structural_role: 'An ontological response when subjects face external uncontrollable change' },
        ],
        relationships: [
          { surface: 'AI → makes → people → anxious', structural: 'New productive force → penetrates subject\'s function and meaning territory → triggers ontological anxiety' },
        ],
      }],
      evidence: [
        { id: '1', case_name: 'Luddite movement 1810s', content: 'British textile workers destroyed machines not because they opposed technology itself, but because they resisted technology\'s stripping of the social identity embedded in their craft skills.', search_direction: 'vertical', layer: 'mechanism', confidence: 'strong', is_unexpected: false },
        { id: '2', case_name: 'Printing press revolution 1450s', content: 'The scribe profession ended. But the deeper shock was that the authority of knowledge shifted from the Church and scribes\' "possession" to the press\'s making knowledge "copyable and transmittable."', search_direction: 'vertical', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '3', case_name: 'Gene-editing ethics controversy', content: 'Society\'s panic over CRISPR is not just about safety, but about the ontological unease of having the power to define "what is a natural human" taken away by technology.', search_direction: 'lateral', layer: 'structure', confidence: 'medium', is_unexpected: false },
        { id: '4', case_name: 'Social-media anxiety', content: 'Attention is priced by algorithms; self-expression is quantified by metrics. Anxiety comes from the authority over "who I am" moving from inside oneself to the platform.', search_direction: 'lateral', layer: 'mechanism', confidence: 'strong', is_unexpected: false },
        { id: '5', case_name: 'Telegraph revolution 1840s', content: 'Space was flattened and long-distance communication was no longer a privilege. But unlike AI today, the telegraph expanded human ability without replacing human judgment.', search_direction: 'vertical', layer: 'mechanism', confidence: 'medium', is_unexpected: true },
        { id: '6', case_name: 'PC adoption 1980s', content: '"Knowing how to use a computer" became a new kind of literacy. Many cognitive tasks previously carried only by the human brain were outsourced.', search_direction: 'vertical', layer: 'phenomenon', confidence: 'medium', is_unexpected: false },
        { id: '7', case_name: 'Oil industry resisting electric vehicles', content: 'Incumbent carriers of productive forces resist new ones not only for economic reasons, but because their power territory over "we decide the energy future" is being stripped away.', search_direction: 'lateral', layer: 'mechanism', confidence: 'medium', is_unexpected: false },
        { id: '8', case_name: 'Female workers\' protests in the Industrial Revolution', content: 'Machines did not fully replace female workers; they reorganized labor under the factory system. The focus of protest was the loss of negotiating power over work rhythm and bodily rhythm.', search_direction: 'vertical', layer: 'mechanism', confidence: 'medium', is_unexpected: false },
        { id: '9', case_name: 'Doctors facing AI diagnosis', content: 'Doctors are not anxious that "AI is more accurate than me," but that clinical judgment is being redistributed from individual expertise to a tripartite system of "AI + insurance + regulation."', search_direction: 'lateral', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '10', case_name: 'Artists facing generative AI', content: 'Anxiety comes from "style as labor outcome" being dissolved — the exclusivity of style is undermined by the algorithm\'s reproducibility.', search_direction: 'lateral', layer: 'structure', confidence: 'strong', is_unexpected: false },
        { id: '11', case_name: 'Lawyers facing legal-research AI', content: 'Part of the "thinking" in routine cases is outsourced, but responsibility still rests with the lawyer. The obligation territory remains unchanged while the capability territory is compressed.', search_direction: 'lateral', layer: 'phenomenon', confidence: 'medium', is_unexpected: false },
        { id: '12', case_name: 'Cars replacing horse-drawn carriages 1900s', content: 'Coach drivers did not disappear; they became taxi drivers. But the difference with AI today is that substitution is not horizontal migration but vertical compression of judgment density.', search_direction: 'vertical', layer: 'mechanism', confidence: 'weak', is_unexpected: true },
      ],
      conclusion: {
        core_finding: 'The structural root of AI anxiety is not "what will AI replace me in doing," but "AI is redistributing my authority to decide who I am." This redistribution dismantles meaning, professional identity, and accountability into a hybrid system of humans, models, and institutions.',
        temporal_trajectory: 'In the first few years, AI anxiety appears as direct fear of unemployment; as adoption deepens, anxiety shifts to the reorganization of identity and meaning — "Is what I do still professional?" replaces "Will I be laid off?" Further on, anxiety may stabilize into a "daily tension of negotiating with the system," much as the anxieties around the telegraph and computer were eventually absorbed into new work forms. But AI differs from its predecessors: it compresses judgment, not execution. This means stabilization will take longer, and the new negotiation counterpart is no longer just the employer, but a hybrid system including models, platforms, and regulators.',
        tension: 'The scalability of new productive forces and the stability of the subject\'s meaning territory are both mutually exclusive and coexistent: scalability means capabilities can be copied and spill over, which precisely weakens the scarcity and boundaries on which "professional identity" depends; yet the subject must have stable meaning boundaries to feel anxiety at all — so the tension is not AI vs. humans, but "copyable capabilities" vs. "identity must be uncopyable."',
        boundary_condition: 'Anxiety is strongest in domains where "scarcity of capability is identity" (artists, doctors, lawyers). It is weaker in domains where capability is already mediated by tools (accounting, translation), because the territory of meaning has long been decoupled from specific skills.',
        unresolved: 'When AI simultaneously lowers the marginal cost of both "output" and "judgment," is there still any domain that cannot be copied? We have not found a mature historical counterpart to "judgment itself being outsourced" — this is a genuinely new situation.',
        implication: 'Rather than asking "Will AI replace me," it is more valuable to ask "Is my territory of meaning built on scarcity of capability, or on bearing judgment." The former will be continuously eroded; the latter may actually be amplified in the AI age.',
        taglines: {
          core_finding: 'The root of AI anxiety is the redistribution of judgment authority',
          temporal_trajectory: 'From fear of unemployment → identity reorganization → daily negotiation with the system',
          tension: 'Copyable capabilities vs. identity must be uncopyable',
          boundary_condition: 'Anxiety is strongest where capability is identity',
          unresolved: 'No historical counterpart for "judgment itself being outsourced"',
          implication: 'Ask about bearing judgment, not scarcity of capability',
        },
      },
      schedule_log: [
        { author: 'inception', decision: 'inception_complete', reason: "abstracted to pattern 'Penetration of new productive forces into the subject\'s territory of meaning', 3 entities, 1 relationships", is_degradation: false },
        { author: 'search_lateral', decision: 'search_complete', reason: 'found 4 cases (lateral) via lens', is_degradation: false },
        { author: 'search_vertical', decision: 'search_complete', reason: 'found 3 cases (vertical) via lens', is_degradation: false },
      ],
    }
  };

  function loadDemoResult() {
    var demo = DEMO_DATA[state.language] || DEMO_DATA['中文'];

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

  // ============================== Outline ============================
  //
  // A persistent left-side TOC. Each item has three states:
  //   pending   — target section is still hidden in the DOM
  //   available — section has been revealed; jumpable
  //   current   — section is the one currently in the user's viewport
  //
  // We listen for `hidden` attribute changes on the tracked elements to
  // flip pending → available, and use IntersectionObserver to pick one
  // available item as current. No coupling into the existing render flow.

  var outline = (function () {
    var rail = null;
    var items = [];
    var ioObserver = null;
    var targetsCache = [];

    // Each tracked DOM element enables one or more outline items.
    // #conclusions becoming visible reveals all six chapters at once.
    var ENABLE_MAP = {
      'lens-reveal': ['lens-reveal'],
      'rails': ['rails'],
      'cases': ['cases'],
      'conclusions': [
        'chapter-core_finding',
        'chapter-temporal_trajectory',
        'chapter-tension',
        'chapter-boundary_condition',
        'chapter-unresolved',
        'chapter-implication',
      ],
    };

    function findItem(targetId) {
      if (!rail) return null;
      for (var i = 0; i < items.length; i++) {
        if (items[i].dataset.target === targetId) return items[i];
      }
      return null;
    }

    function setItemState(item, state) {
      if (!item) return;
      item.classList.remove(
        'outline__item--pending',
        'outline__item--available',
        'outline__item--current'
      );
      item.classList.add('outline__item--' + state);
    }

    function handleVisibilityChange(sourceId, isVisible) {
      var targetIds = ENABLE_MAP[sourceId] || [];
      targetIds.forEach(function (tid) {
        var item = findItem(tid);
        if (!item) return;
        if (isVisible) {
          if (!item.classList.contains('outline__item--current')) {
            setItemState(item, 'available');
          }
        } else {
          setItemState(item, 'pending');
        }
      });
      // Refresh the IO target cache when visibility changes.
      refreshTargetsCache();
    }

    function refreshTargetsCache() {
      targetsCache = items
        .map(function (item) {
          return { item: item, el: document.getElementById(item.dataset.target) };
        })
        .filter(function (x) { return x.el && !x.el.hidden; });
    }

    function updateCurrent() {
      if (!targetsCache.length) return;
      var focusLine = Math.max(window.innerHeight * 0.28, 120);
      var current = null;

      for (var i = 0; i < targetsCache.length; i++) {
        var t = targetsCache[i];
        var rect = t.el.getBoundingClientRect();
        if (rect.top <= focusLine && rect.bottom > 80) {
          if (!current) current = t;
          else if (rect.top > current.el.getBoundingClientRect().top) current = t;
        }
      }

      // Fallback: if nothing crosses the focus line, the topmost
      // visible-on-screen section is current.
      if (!current) {
        for (var j = 0; j < targetsCache.length; j++) {
          var t2 = targetsCache[j];
          var r2 = t2.el.getBoundingClientRect();
          if (r2.bottom > 0 && r2.top < window.innerHeight) {
            if (!current) current = t2;
            else if (r2.top < current.el.getBoundingClientRect().top) current = t2;
          }
        }
      }

      items.forEach(function (item) {
        if (item.classList.contains('outline__item--pending')) return;
        if (current && item === current.item) {
          setItemState(item, 'current');
        } else if (item.classList.contains('outline__item--current')) {
          setItemState(item, 'available');
        }
      });
    }

    function init() {
      rail = document.getElementById('outline');
      if (!rail) return;
      items = Array.prototype.slice.call(
        rail.querySelectorAll('.outline__item[data-target]')
      );

      // 1. Click → smooth scroll
      items.forEach(function (item) {
        var link = item.querySelector('.outline__link');
        if (!link) return;
        link.addEventListener('click', function (e) {
          e.preventDefault();
          if (item.classList.contains('outline__item--pending')) return;
          var target = document.getElementById(item.dataset.target);
          if (!target) return;
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });

      // 2. MutationObserver on hidden attribute of each tracked element
      Object.keys(ENABLE_MAP).forEach(function (sourceId) {
        var source = document.getElementById(sourceId);
        if (!source) return;
        var mo = new MutationObserver(function () {
          handleVisibilityChange(sourceId, !source.hidden);
        });
        mo.observe(source, { attributes: true, attributeFilter: ['hidden'] });
        // Initial sync
        handleVisibilityChange(sourceId, !source.hidden);
      });

      // 3. IntersectionObserver for scroll position
      if ('IntersectionObserver' in window) {
        ioObserver = new IntersectionObserver(function () {
          updateCurrent();
        }, {
          rootMargin: '-25% 0px -65% 0px',
          threshold: [0, 0.1, 0.5, 1],
        });
        // Observe every potential target — observers are no-ops on hidden.
        var allTargets = [];
        items.forEach(function (item) {
          var el = document.getElementById(item.dataset.target);
          if (el) allTargets.push(el);
        });
        allTargets.forEach(function (el) { ioObserver.observe(el); });
      }

      // 4. Throttled scroll fallback (and for chapter expand/collapse)
      var scrollTick = null;
      window.addEventListener('scroll', function () {
        if (scrollTick) return;
        scrollTick = requestAnimationFrame(function () {
          scrollTick = null;
          updateCurrent();
        });
      }, { passive: true });
    }

    function reset() {
      items.forEach(function (item) {
        setItemState(item, 'pending');
      });
      refreshTargetsCache();
    }

    return { init: init, reset: reset };
  })();

  // ============================== Boot ===============================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
