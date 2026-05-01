const API = "http://localhost:8000";

async function loadModels() {
  try {
    const res = await fetch(`${API}/models`);
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const { models } = await res.json();
    ["agent1_model", "agent2_model", "judge_model"].forEach((id, i) => {
      const sel = document.getElementById(id);
      models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        sel.appendChild(opt);
      });
      const defaults = ["llama-3.3-70b-versatile", "qwen/qwen3-32b", "meta-llama/llama-4-scout-17b-16e-instruct"];
      const match = models.find(m => m === defaults[i]);
      if (match) sel.value = match;
    });
  } catch (err) {
    showError(`Failed to load models: ${err.message}. Is the backend running?`);
  }
}

function stripMarkdown(text) {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/^[-*+]\s+/gm, "• ")
    .replace(/^\d+\.\s+/gm, "")
    .replace(/`{1,3}([^`]*)`{1,3}/g, "$1")
    .replace(/\[(.+?)\]\(.+?\)/g, "$1")
    .trim();
}

function showError(msg) {
  document.getElementById("debate-output").classList.remove("hidden");
  const messages = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = "message error";
  const span = document.createElement("div");
  span.className = "speaker";
  span.textContent = "Error";
  const content = document.createElement("div");
  content.className = "content";
  content.textContent = msg;
  div.appendChild(span);
  div.appendChild(content);
  messages.appendChild(div);
  div.scrollIntoView({ behavior: "smooth" });
}

function addMessage(type, speaker, content) {
  const messages = document.getElementById("messages");

  if (type === "turn_start") {
    const div = document.createElement("div");
    div.className = "turn-divider";
    div.textContent = `— Turn ${content} —`;
    messages.appendChild(div);
    return;
  }

  if (type === "error") {
    showError(content);
    return;
  }

  const cssClass = { agent1: "for", agent2: "against", opening: "judge", verdict: "verdict", saved: "saved" }[type] || "";
  const label = type === "saved" ? "Saved" : speaker;
  const clean = type === "saved" ? content : stripMarkdown(content);

  const div = document.createElement("div");
  div.className = `message ${cssClass}`;

  const speakerEl = document.createElement("div");
  speakerEl.className = "speaker";
  speakerEl.textContent = label;

  const contentEl = document.createElement("div");
  contentEl.className = "content";
  contentEl.textContent = clean;

  div.appendChild(speakerEl);
  div.appendChild(contentEl);
  messages.appendChild(div);
  div.scrollIntoView({ behavior: "smooth" });
}

document.getElementById("debate-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const btn = document.getElementById("start-btn");
  btn.disabled = true;
  btn.textContent = "Debate in progress...";

  document.getElementById("messages").innerHTML = "";
  document.getElementById("debate-output").classList.remove("hidden");

  const body = {
    topic: document.getElementById("topic").value.trim(),
    turns: parseInt(document.getElementById("turns").value),
    max_lines: parseInt(document.getElementById("max_lines").value),
    agent1_model: document.getElementById("agent1_model").value,
    agent2_model: document.getElementById("agent2_model").value,
    judge_model: document.getElementById("judge_model").value,
    agent1_name: document.getElementById("agent1_name").value.trim(),
    agent2_name: document.getElementById("agent2_name").value.trim(),
    judge_name: document.getElementById("judge_name").value.trim(),
  };

  try {
    const res = await fetch(`${API}/debate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(`Server returned ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const { type, speaker, content } = JSON.parse(part.slice(6));
        addMessage(type, speaker, content);
      }
    }
  } catch (err) {
    showError(`Debate failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Start Debate";
  }
});

loadModels();
