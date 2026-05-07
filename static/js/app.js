const AGENTS = [
  { key: "abstracter", label: "Abstracter — 生成抽象透镜" },
  { key: "vertical_discovery", label: "Vertical Discovery — 穿越时间搜索" },
  { key: "horizontal_discovery", label: "Horizontal Discovery — 穿越领域搜索" },
  { key: "comparator", label: "Comparator — 逐个对比分析" },
  { key: "causal_reviewer", label: "Causal Reviewer — 因果审查" },
  { key: "synthesizer", label: "Synthesizer — 综合整合" },
  { key: "visualization_agent", label: "Visualization — 生成幻灯片" },
];

let currentTaskId = null;

function startAnalysis() {
  const topic = document.getElementById("topic-input").value.trim();
  const style = document.getElementById("style-select").value;

  if (!topic) {
    alert("Please enter a topic");
    return;
  }

  document.getElementById("start-btn").disabled = true;
  document.getElementById("input-section").style.display = "none";
  document.getElementById("progress-section").style.display = "block";
  document.getElementById("progress-topic").textContent = topic;
  document.getElementById("progress-bar").style.width = "0%";
  document.getElementById("progress-pct").textContent = "0%";

  buildTimeline();

  fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, style_preset: style }),
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

function listenProgress(taskId) {
  const source = new EventSource("/progress/" + taskId);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.status === "running") {
      document.getElementById("progress-bar").style.width = data.progress + "%";
      document.getElementById("progress-pct").textContent = data.progress + "%";
      document.getElementById("status-msg").textContent = data.label || "Running...";
      if (data.agent) updateTimeline(data.agent);
    }

    if (data.status === "completed") {
      source.close();
      showResult(taskId);
    }

    if (data.status === "error") {
      source.close();
      showError(data.error || "Unknown error");
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
  document.getElementById("input-section").style.display = "block";
  document.getElementById("start-btn").disabled = false;
  document.getElementById("topic-input").value = "";
  currentTaskId = null;
}

// Enter key to start
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("topic-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startAnalysis();
  });
});
