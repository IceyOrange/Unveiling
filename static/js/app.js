const AGENTS = [
  { key: "abstracter", label: "Abstracter — 生成抽象透镜" },
  { key: "vertical_discovery", label: "Vertical Discovery — 穿越时间搜索" },
  { key: "horizontal_discovery", label: "Horizontal Discovery — 穿越领域搜索" },
  { key: "comparator", label: "Comparator — 逐个对比分析" },
  { key: "causal_reviewer", label: "Causal Reviewer — 因果审查" },
  { key: "synthesizer", label: "Synthesizer — 综合整合" },
];

let currentTaskId = null;
let lastBlackboardCount = 0;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("topic-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startAnalysis();
  });
});

function scrollToAnalysis() {
  document.getElementById("analysis").scrollIntoView({ behavior: "smooth" });
}

function setTopic(topic) {
  const input = document.getElementById("topic-input");
  input.value = topic;
  input.focus();
}

function startAnalysis() {
  const topic = document.getElementById("topic-input").value.trim();
  const style = document.getElementById("style-select").value;
  const language = document.getElementById("language-select").value;

  if (!topic) {
    alert("请输入分析主题");
    return;
  }

  document.getElementById("start-btn").disabled = true;
  document.getElementById("progress-section").style.display = "block";
  document.getElementById("result-section").style.display = "none";
  document.getElementById("error-section").style.display = "none";
  document.getElementById("progress-topic").textContent = topic;
  document.getElementById("progress-bar").style.width = "0%";
  document.getElementById("progress-pct").textContent = "0%";

  const thinkingContent = document.getElementById("thinking-content");
  thinkingContent.innerHTML = '<div class="thinking-placeholder">等待 Agent 开始思考...</div>';

  buildTimeline();
  scrollToAnalysis();

  fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, style_preset: style, language }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) throw new Error(data.error);
      currentTaskId = data.task_id;
      listenProgress(data.task_id);
    })
    .catch((err) => {
      showError(err.message);
    });
}

function buildTimeline() {
  const container = document.getElementById("agent-timeline");
  container.innerHTML = AGENTS.map(
    (a) =>
      `<div class="agent-step" id="step-${a.key}">` +
      `<span class="dot"></span>` +
      `<span class="agent-name">${a.label}</span>` +
      `</div>`
  ).join("");
}

function updateTimeline(agentKey) {
  const agents = AGENTS.map((a) => a.key);
  const idx = agents.indexOf(agentKey);
  if (idx < 0) return;

  AGENTS.forEach((a, i) => {
    const el = document.getElementById("step-" + a.key);
    el.classList.remove("running", "done");
    if (i < idx) el.classList.add("done");
    else if (i === idx) el.classList.add("running");
  });
}

function addThought(agentKey, label, text) {
  const container = document.getElementById("thinking-content");
  const placeholder = container.querySelector(".thinking-placeholder");
  if (placeholder) placeholder.remove();

  const item = document.createElement("div");
  item.className = "think-item";
  item.innerHTML = `<div class="think-agent">${label}</div><div class="think-text">${escapeHtml(text)}</div>`;
  container.appendChild(item);
  container.scrollTop = container.scrollHeight;
}

function updateBlackboard(messages) {
  if (!messages || messages.length === 0) return;

  const container = document.getElementById("blackboard-content");
  const placeholder = container.querySelector(".blackboard-placeholder");
  if (placeholder) placeholder.remove();

  // Only add new messages
  const newMessages = messages.slice(lastBlackboardCount);
  if (newMessages.length === 0) return;

  newMessages.forEach(msg => {
    const item = document.createElement("div");
    item.className = "blackboard-message";

    const time = msg.timestamp ? msg.timestamp.substring(11, 19) : "";
    const agent = msg.agent || "unknown";
    const content = msg.content || "";

    item.innerHTML = `
      <div class="msg-header">
        <span class="msg-agent">${agent}</span>
        <span class="msg-time">${time}</span>
      </div>
      <div class="msg-content">${escapeHtml(content)}</div>
    `;
    container.appendChild(item);
  });

  lastBlackboardCount = messages.length;
  document.getElementById("blackboard-count").textContent = `${messages.length} 条消息`;
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function listenProgress(taskId) {
  const source = new EventSource("/progress/" + taskId);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.status === "running") {
      document.getElementById("progress-bar").style.width = data.progress + "%";
      document.getElementById("progress-pct").textContent = data.progress + "%";
      document.getElementById("status-msg").textContent = data.label || "分析中...";
      if (data.agent) updateTimeline(data.agent);
      if (data.thought) {
        addThought(data.agent, data.label, data.thought);
      }
      if (data.blackboard_messages) {
        updateBlackboard(data.blackboard_messages);
      }
    }

    if (data.status === "completed") {
      source.close();
      showResult(taskId);
    }

    if (data.status === "error") {
      source.close();
      showError(data.error || "未知错误");
    }
  };

  source.onerror = () => {
    source.close();
  };
}

function showResult(taskId) {
  fetch("/result/" + taskId)
    .then((r) => r.json())
    .then((data) => {
      document.getElementById("progress-section").style.display = "none";
      document.getElementById("result-section").style.display = "block";

      const filename = data.filename;
      if (filename) {
        document.getElementById("slide-frame").src = "/slides/" + filename;
        document.getElementById("download-link").href = "/slides/" + filename;
      }
    })
    .catch((err) => showError(err.message));
}

function viewSlides() {
  const frame = document.getElementById("slide-frame");
  if (frame.src) window.open(frame.src, "_blank");
}

function showError(msg) {
  document.getElementById("progress-section").style.display = "none";
  document.getElementById("result-section").style.display = "none";
  document.getElementById("error-section").style.display = "block";
  document.getElementById("error-msg").textContent = msg;
}

function resetUI() {
  document.getElementById("error-section").style.display = "none";
  document.getElementById("result-section").style.display = "none";
  document.getElementById("progress-section").style.display = "none";
  document.getElementById("start-btn").disabled = false;
  document.getElementById("topic-input").value = "";
  currentTaskId = null;
  lastBlackboardCount = 0;
  window.scrollTo({ top: 0, behavior: "smooth" });
}
