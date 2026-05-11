let currentTaskId = null;
let eventSource = null;

function setTopic(topic) {
  document.getElementById('question-input').value = topic;
}

function startAnalysis() {
  const question = document.getElementById('question-input').value.trim();
  const mode = document.getElementById('mode-select').value;
  if (!question) {
    alert('请输入分析问题');
    return;
  }

  document.getElementById('start-btn').disabled = true;
  document.getElementById('input-section').style.display = 'none';
  document.getElementById('progress-section').style.display = 'block';
  document.getElementById('result-section').style.display = 'none';
  document.getElementById('error-section').style.display = 'none';

  // Clear previous state
  document.getElementById('event-stream').innerHTML = '';
  document.getElementById('issue-tree-panel').innerHTML = '<div class="placeholder">等待启动期完成...</div>';
  updateStats({ rounds: 0, evidence: 0, debates: 0, tokens: 0 });
  setPhaseActive('inception');

  fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, mode }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      currentTaskId = data.task_id;
      connectSSE(data.task_id);
    })
    .catch(err => showError(err.message));
}

function connectSSE(taskId) {
  eventSource = new EventSource(`/progress/${taskId}`);

  eventSource.onmessage = (e) => {
    const event = JSON.parse(e.data);
    if (event.done) {
      eventSource.close();
      loadResult(taskId);
      return;
    }
    if (event.error) {
      eventSource.close();
      showError(event.error);
      return;
    }
    handleEvent(event);
  };

  eventSource.onerror = () => {
    eventSource.close();
  };
}

function handleEvent(event) {
  // Update phase
  if (event.phase) {
    if (event.phase === 'exploration') {
      setPhaseDone('inception');
      setPhaseActive('exploration');
    } else if (event.phase === 'convergence') {
      setPhaseDone('inception');
      setPhaseDone('exploration');
      setPhaseActive('convergence');
    }
  }

  // Update stats
  if (event.evidence_count) {
    const current = parseInt(document.getElementById('stat-evidence').textContent);
    document.getElementById('stat-evidence').textContent = current + event.evidence_count;
  }
  if (event.debate_count) {
    const current = parseInt(document.getElementById('stat-debates').textContent);
    document.getElementById('stat-debates').textContent = current + event.debate_count;
  }

  // Update issue tree
  if (event.issue_tree_update) {
    updateIssueTree(event.issue_tree_update);
  }

  // Add to event stream
  addEventToStream(event);

  // Increment rounds for scheduler events
  if (event.node === 'scheduler_node') {
    const rounds = parseInt(document.getElementById('stat-rounds').textContent);
    document.getElementById('stat-rounds').textContent = rounds + 1;
  }
}

function setPhaseActive(phase) {
  document.getElementById(`phase-${phase}`).classList.add('active');
}

function setPhaseDone(phase) {
  const el = document.getElementById(`phase-${phase}`);
  el.classList.remove('active');
  el.classList.add('done');
}

function updateIssueTree(updates) {
  const panel = document.getElementById('issue-tree-panel');
  if (panel.querySelector('.placeholder')) {
    panel.innerHTML = '';
  }

  updates.forEach(node => {
    const existing = document.getElementById(`node-${node.id}`);
    if (existing) {
      existing.querySelector('.status-badge').textContent = node.status;
      existing.querySelector('.status-badge').className = `status-badge status-${node.status}`;
      return;
    }

    const isDriving = node.parent_id === null;
    const div = document.createElement('div');
    div.id = `node-${node.id}`;
    div.className = `issue-node ${isDriving ? 'driving' : 'child'}`;
    div.innerHTML = `
      <span class="status-badge status-${node.status}">${node.status}</span>
      <span>${escapeHtml(node.content)}</span>
    `;
    panel.appendChild(div);
  });
}

function addEventToStream(event) {
  const stream = document.getElementById('event-stream');
  if (stream.querySelector('.placeholder')) {
    stream.innerHTML = '';
  }

  const item = document.createElement('div');
  item.className = `event-item ${getEventClass(event.node)}`;

  const nodeName = event.node ? event.node.replace('_node', '') : 'system';
  const decision = event.decision || '';

  item.innerHTML = `
    <span class="event-node">[${nodeName}]</span>
    <span class="event-decision">${escapeHtml(decision)}</span>
  `;
  stream.appendChild(item);
  stream.scrollTop = stream.scrollHeight;
}

function getEventClass(node) {
  if (!node) return '';
  if (node.includes('inception')) return 'inception';
  if (node.includes('search')) return 'search';
  if (node.includes('deepdig')) return 'deepdig';
  if (node.includes('debate')) return 'debate';
  if (node.includes('judge')) return 'judge';
  if (node.includes('convergence')) return 'convergence';
  return '';
}

function updateStats(stats) {
  document.getElementById('stat-rounds').textContent = stats.rounds;
  document.getElementById('stat-evidence').textContent = stats.evidence;
  document.getElementById('stat-debates').textContent = stats.debates;
  document.getElementById('stat-tokens').textContent = stats.tokens;
}

function loadResult(taskId) {
  fetch(`/result/${taskId}`)
    .then(r => r.json())
    .then(data => {
      if (data.status) {
        setTimeout(() => loadResult(taskId), 500);
        return;
      }
      if (data.error) {
        showError(data.error);
        return;
      }
      displayResult(data);
    })
    .catch(err => showError(err.message));
}

function displayResult(data) {
  document.getElementById('progress-section').style.display = 'none';
  document.getElementById('result-section').style.display = 'block';

  const c = data.conclusion || {};
  document.getElementById('res-convergent-finding').textContent = c.convergent_finding || '';
  document.getElementById('res-tension').textContent = c.tension || '';
  document.getElementById('res-boundary').textContent = c.boundary_condition || '';
  document.getElementById('res-unresolved').textContent = c.unresolved || '';
  document.getElementById('res-implication').textContent = c.implication || '';

  const lensesEl = document.getElementById('res-lenses');
  lensesEl.innerHTML = (data.lenses || []).map(l => `
    <div class="lens-item">
      <strong>${escapeHtml(l.name)}</strong>
      <p>${escapeHtml(l.rationale)}</p>
    </div>
  `).join('');

  const predsEl = document.getElementById('res-predictions');
  predsEl.innerHTML = (data.predictions || []).map(p => `
    <div class="prediction-item">
      <span>${escapeHtml(p.claim)}</span>
      <span class="pred-status ${p.status}">${p.status}</span>
    </div>
  `).join('');

  // Update final stats
  updateStats({
    rounds: data.round_count || 0,
    evidence: data.evidence_count || 0,
    debates: data.debate_count || 0,
    tokens: data.token_spent || 0,
  });
}

function showError(msg) {
  document.getElementById('progress-section').style.display = 'none';
  document.getElementById('error-section').style.display = 'block';
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('start-btn').disabled = false;
}

function resetUI() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  currentTaskId = null;
  document.getElementById('input-section').style.display = 'block';
  document.getElementById('progress-section').style.display = 'none';
  document.getElementById('result-section').style.display = 'none';
  document.getElementById('error-section').style.display = 'none';
  document.getElementById('start-btn').disabled = false;

  // Reset phase timeline
  ['inception', 'exploration', 'convergence'].forEach(p => {
    const el = document.getElementById(`phase-${p}`);
    el.classList.remove('active', 'done');
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
