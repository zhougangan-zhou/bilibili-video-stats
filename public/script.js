const form = document.querySelector("#form");
const input = document.querySelector("#input");
const chat = document.querySelector("#chat");
const submit = document.querySelector("#submit");
const example = document.querySelector("#example");

const sampleUrl = "https://www.bilibili.com/video/BV1U6gF63EYE/";

example.addEventListener("click", () => {
  input.value = sampleUrl;
  input.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addMessage("user", text);
  input.value = "";
  submit.disabled = true;
  submit.textContent = "抓取中";

  const loading = addMessage("assistant", "正在抓取数据...");
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch("/api/stats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
    const data = await response.json();
    loading.remove();
    if (!response.ok || !data.ok) {
      addMessage("assistant", data.error || "抓取失败");
      return;
    }
    addResult(data);
  } catch (error) {
    loading.remove();
    const message =
      error.name === "AbortError"
        ? "请求超过 30 秒还没有返回。请确认终端里的 python3 app.py 还在运行，并稍后重试。"
        : `请求失败：${error.message}。请确认你打开的是 http://127.0.0.1:8765，不是直接双击 index.html。`;
    addMessage("assistant", message);
  } finally {
    window.clearTimeout(timer);
    submit.disabled = false;
    submit.textContent = "抓取数据";
  }
});

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "我" : "B";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  article.append(avatar, bubble);
  chat.append(article);
  chat.scrollTop = chat.scrollHeight;
  return article;
}

function addResult(data) {
  const article = document.createElement("article");
  article.className = "message assistant";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "B";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "result-summary";
  summary.innerHTML = `<strong>抓取完成</strong><span>识别 ${data.count} 条，成功 ${data.success} 条，失败 ${data.failed} 条</span>`;
  bubble.append(summary);

  const tableWrap = document.createElement("div");
  tableWrap.className = "table-wrap";
  tableWrap.append(buildTable(data.rows));
  bubble.append(tableWrap);

  const download = document.createElement("a");
  download.className = "download";
  download.href = URL.createObjectURL(new Blob([data.csv], { type: "text/csv;charset=utf-8" }));
  download.download = "bilibili_stats.csv";
  download.textContent = "下载 CSV";
  bubble.append(download);

  article.append(avatar, bubble);
  chat.append(article);
  chat.scrollTop = chat.scrollHeight;
}

function buildTable(rows) {
  const table = document.createElement("table");
  const headers = [
    ["title", "标题"],
    ["owner", "UP主"],
    ["like", "点赞"],
    ["favorite", "收藏"],
    ["reply", "评论"],
    ["share", "转发"],
    ["interaction_total", "总和"],
    ["status", "状态"],
  ];

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const [, label] of headers) {
    const th = document.createElement("th");
    th.textContent = label;
    headRow.append(th);
  }
  thead.append(headRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const [key] of headers) {
      const td = document.createElement("td");
      const value = key === "status" && row.status === "error" ? row.error || "error" : row[key];
      td.textContent = value ?? "";
      if (["like", "favorite", "reply", "share", "interaction_total"].includes(key)) {
        td.className = "num";
      }
      if (key === "status") {
        td.className = row.status === "ok" ? "ok" : "error";
        td.textContent = row.status === "ok" ? "ok" : value;
      }
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}
