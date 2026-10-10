// API 서버 주소: 배포 시 config.js(Vercel 환경 변수 API_BASE_URL로 생성)에서, 로컬이면 기본값
const API = (window.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const $ = (sel) => document.querySelector(sel);
const state = { conversationId: null, data: [], sending: false };

// ---------- 공통 ----------
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = body.detail;
    if (Array.isArray(msg)) msg = msg.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(", "); // Pydantic 422
    throw new Error(msg || `요청 실패 (${res.status})`);
  }
  return body;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// AI 답변의 간단한 마크다운(굵게, 목록, 줄바꿈)만 표시
function renderMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/^[-*]\s+/gm, "• ")
    .replace(/\n/g, "<br>");
}

let toastTimer;
function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast" + (isError ? " err" : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3000);
}

const fmt = (n, d = 1) => (n === null || n === undefined ? "-" : Number(n).toFixed(d));
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "");

// ---------- 서버 깨우기 (Render 무료 티어 콜드스타트 대응) ----------
async function wakeServer() {
  const status = $("#server-status");
  const banner = $("#wake-banner");
  const slow = setTimeout(() => (banner.hidden = false), 2500); // 2.5초 넘으면 안내
  for (let i = 0; i < 6; i++) {
    try {
      const res = await fetch(API + "/", { cache: "no-store" });
      if (res.ok) {
        clearTimeout(slow);
        banner.hidden = true;
        status.textContent = "서버 연결됨";
        status.className = "pill ok";
        return true;
      }
    } catch (e) { /* 아직 깨어나는 중 */ }
    status.textContent = `서버 깨우는 중… (${i + 1}/6)`;
    await new Promise((r) => setTimeout(r, 10000));
  }
  clearTimeout(slow);
  status.textContent = "서버 연결 실패";
  status.className = "pill err";
  banner.textContent = "서버에 연결할 수 없어요. 잠시 후 새로고침해 주세요.";
  return false;
}

// ---------- 다크 모드 ----------
function currentTheme() {
  return document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function updateThemeButton() {
  $("#theme-toggle").textContent = currentTheme() === "dark" ? "☀️ 라이트" : "🌙 다크";
}
$("#theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
  updateThemeButton();
  drawChart(); // 색이 바뀌므로 다시 그림
});

// ---------- 모바일 탭 ----------
document.querySelectorAll(".tabs button").forEach((btn) =>
  btn.addEventListener("click", () => showTab(btn.dataset.tab))
);
function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === name));
  if (name === "data") drawChart();
}

// ---------- 채팅 ----------
function clearEmptyState() {
  const empty = $(".empty-chat");
  if (empty) empty.remove();
}

function addMessage(role, content) {
  clearEmptyState();
  const div = document.createElement("div");
  div.className = "msg " + role;
  if (role === "assistant") div.innerHTML = renderMarkdown(content);
  else div.textContent = content;
  $("#messages").appendChild(div);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return div;
}

function resetChat() {
  state.conversationId = null;
  $("#chat-title").textContent = "새 대화";
  $("#messages").innerHTML = `
    <div class="empty-chat">
      <p>저장된 반도체 생산 데이터를 바탕으로 답해요.</p>
      <div class="chips">
        <button type="button" class="chip">최근 반도체 생산 흐름이 어때?</button>
        <button type="button" class="chip">생산이 가장 많았던 달은 언제야?</button>
        <button type="button" class="chip">2022년 불황 때는 얼마나 떨어졌어?</button>
        <button type="button" class="chip">코로나 시기에는 어땠어?</button>
      </div>
    </div>`;
  highlightConversation();
}

async function sendMessage(text) {
  text = text.trim();
  if (!text || state.sending) return;
  state.sending = true;
  $("#send-btn").disabled = true;
  $("#chat-input").value = "";
  autoGrow();

  addMessage("user", text);
  const loading = addMessage("assistant", "");
  loading.classList.add("loading");
  loading.innerHTML = '데이터를 보고 답변을 만드는 중<span class="dots"><span>.</span><span>.</span><span>.</span></span>';

  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, conversation_id: state.conversationId }),
    });
    loading.remove();
    addMessage("assistant", res.reply);
    const isNew = !state.conversationId;
    state.conversationId = res.conversation_id;
    if (isNew) $("#chat-title").textContent = text.length > 30 ? text.slice(0, 30) + "…" : text;
    loadConversations();
  } catch (e) {
    loading.remove();
    addMessage("error", "답변을 받지 못했어요: " + e.message);
  } finally {
    state.sending = false;
    $("#send-btn").disabled = false;
    $("#chat-input").focus();
  }
}

function autoGrow() {
  const ta = $("#chat-input");
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage($("#chat-input").value);
});
$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    sendMessage($("#chat-input").value);
  }
});
$("#chat-input").addEventListener("input", autoGrow);
$("#messages").addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) sendMessage(e.target.textContent);
});
$("#new-chat").addEventListener("click", () => {
  resetChat();
  showTab("chat");
});

// ---------- 대화 기록 ----------
async function loadConversations() {
  const list = $("#conv-list");
  try {
    const convs = await api("/api/conversations");
    if (!convs.length) {
      list.innerHTML = '<li class="conv-empty">아직 저장된 대화가 없어요.</li>';
      return;
    }
    list.innerHTML = convs.map((c) => `
      <li data-id="${c.id}">
        <button type="button" class="conv-open" title="${escapeHtml(c.title)}">
          <span class="t">${escapeHtml(c.title)}</span>
          <span class="m">${fmtTime(c.updated_at)} · 메시지 ${c.message_count}개</span>
        </button>
        <button type="button" class="conv-del" aria-label="대화 삭제" title="삭제">✕</button>
      </li>`).join("");
    highlightConversation();
  } catch (e) {
    list.innerHTML = `<li class="conv-empty">목록을 불러오지 못했어요: ${escapeHtml(e.message)}</li>`;
  }
}

function highlightConversation() {
  document.querySelectorAll("#conv-list li").forEach((li) =>
    li.classList.toggle("active", li.dataset.id === state.conversationId)
  );
}

async function openConversation(id) {
  try {
    const conv = await api(`/api/conversations/${id}`);
    state.conversationId = conv.id;
    $("#chat-title").textContent = conv.title;
    $("#messages").innerHTML = "";
    conv.messages.forEach((m) => addMessage(m.role, m.content));
    highlightConversation();
    showTab("chat");
  } catch (e) {
    toast("대화를 불러오지 못했어요: " + e.message, true);
  }
}

$("#conv-list").addEventListener("click", async (e) => {
  const li = e.target.closest("li[data-id]");
  if (!li) return;
  if (e.target.closest(".conv-del")) {
    if (!confirm("이 대화를 삭제할까요?")) return;
    try {
      await api(`/api/conversations/${li.dataset.id}`, { method: "DELETE" });
      if (state.conversationId === li.dataset.id) resetChat();
      toast("대화를 삭제했어요");
      loadConversations();
    } catch (err) {
      toast("삭제 실패: " + err.message, true);
    }
  } else {
    openConversation(li.dataset.id);
  }
});

// ---------- 데이터 요약 ----------
async function loadSummary() {
  const box = $("#summary");
  try {
    const s = await api("/api/data/summary");
    if (!s.count) {
      box.innerHTML = '<div class="stat wide"><div class="k">데이터 없음</div></div>';
      return;
    }
    const m = s.metrics;
    const dir = s.trend_detail?.direction;
    const cls = dir === "상승" ? "trend-up" : dir === "하락" ? "trend-down" : "";
    const arrow = dir === "상승" ? "▲" : dir === "하락" ? "▼" : "■";
    const yoy = m.latest_yoy_pct;
    box.innerHTML = `
      <div class="stat wide"><div class="k">기간 · 개수</div><div class="v">${s.period}</div><div class="d">${s.count}개월</div></div>
      <div class="stat wide"><div class="k">최근 추세 (최근 12개월 vs 직전 12개월)</div>
        <div class="v ${cls}">${arrow} ${dir ?? "-"} ${s.trend_detail?.change_pct !== undefined ? `(${s.trend_detail.change_pct > 0 ? "+" : ""}${fmt(s.trend_detail.change_pct)}%)` : ""}</div>
        <div class="d">${escapeHtml(s.trend)}</div></div>
      <div class="stat"><div class="k">최근값</div><div class="v">${fmt(m.latest.value)}</div><div class="d">${m.latest.date}</div></div>
      <div class="stat"><div class="k">전년 동월 대비</div><div class="v ${yoy > 0 ? "trend-up" : yoy < 0 ? "trend-down" : ""}">${yoy === null ? "-" : (yoy > 0 ? "+" : "") + fmt(yoy) + "%"}</div><div class="d">${m.latest.date} 기준</div></div>
      <div class="stat"><div class="k">평균</div><div class="v">${fmt(m.average)}</div><div class="d">표준편차 ${fmt(m.std)}</div></div>
      <div class="stat"><div class="k">최대 / 최소</div><div class="v">${fmt(m.max.value)} / ${fmt(m.min.value)}</div><div class="d">${m.max.date} / ${m.min.date}</div></div>`;
  } catch (e) {
    box.innerHTML = `<div class="stat wide"><div class="k">요약을 불러오지 못했어요</div><div class="d">${escapeHtml(e.message)}</div></div>`;
  }
}

// ---------- 그래프 (SVG 직접 그리기) ----------
let stats = [];
async function loadStatistics() {
  try {
    stats = await api("/api/data/statistics");
  } catch (e) {
    stats = [];
  }
  drawChart();
}

function drawChart() {
  const box = $("#chart");
  const tip = $("#chart-tip");
  box.querySelector("svg")?.remove();
  const W = box.clientWidth, H = box.clientHeight;
  if (!stats.length || !W) return;

  const pad = { l: 34, r: 10, t: 10, b: 22 };
  const vals = stats.flatMap((d) => [d.value, d.ma12]).filter((v) => v !== null);
  const lo = Math.floor(Math.min(...vals) / 20) * 20;
  const hi = Math.ceil(Math.max(...vals) / 20) * 20;
  const x = (i) => pad.l + (i / (stats.length - 1 || 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - lo) / (hi - lo || 1)) * (H - pad.t - pad.b);
  const path = (key) => {
    let d = "", pen = false;
    stats.forEach((p, i) => {
      if (p[key] === null) { pen = false; return; }
      d += (pen ? "L" : "M") + x(i).toFixed(1) + "," + y(p[key]).toFixed(1);
      pen = true;
    });
    return d;
  };

  let grid = "";
  for (let v = lo; v <= hi; v += 20) {
    grid += `<line class="grid-line" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/>`;
    grid += `<text class="axis-text" x="${pad.l - 6}" y="${y(v) + 3}" text-anchor="end">${v}</text>`;
  }
  let years = "";
  stats.forEach((p, i) => {
    const [yr, mo] = p.date.split("-");
    if (mo === "01" && (+yr % 2 === 1 || W > 500)) {
      years += `<text class="axis-text" x="${x(i)}" y="${H - 6}" text-anchor="middle">${yr.slice(2)}년</text>`;
    }
  });

  box.insertAdjacentHTML("afterbegin", `
    <svg viewBox="0 0 ${W} ${H}" aria-hidden="true">
      ${grid}${years}
      <path class="line-1" d="${path("value")}"/>
      <path class="line-2" d="${path("ma12")}"/>
      <g class="hover" visibility="hidden">
        <line class="cross" y1="${pad.t}" y2="${H - pad.b}"/>
        <circle class="dot-1" r="4"/><circle class="dot-2" r="4"/>
      </g>
      <rect x="${pad.l}" y="0" width="${W - pad.l - pad.r}" height="${H}" fill="transparent"/>
    </svg>`);

  const svg = box.querySelector("svg");
  const g = svg.querySelector(".hover");
  const move = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const px = clientX - rect.left;
    const i = Math.max(0, Math.min(stats.length - 1, Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (stats.length - 1))));
    const p = stats[i];
    g.setAttribute("visibility", "visible");
    g.querySelector(".cross").setAttribute("x1", x(i));
    g.querySelector(".cross").setAttribute("x2", x(i));
    g.querySelector(".dot-1").setAttribute("cx", x(i));
    g.querySelector(".dot-1").setAttribute("cy", y(p.value));
    const d2 = g.querySelector(".dot-2");
    if (p.ma12 !== null) { d2.setAttribute("cx", x(i)); d2.setAttribute("cy", y(p.ma12)); d2.style.display = ""; }
    else d2.style.display = "none";
    tip.innerHTML = `<b>${p.date}</b>생산지수 ${fmt(p.value)}<br>12개월 평균 ${fmt(p.ma12)}<br>전년 동월 대비 ${p.yoy_pct === null ? "-" : (p.yoy_pct > 0 ? "+" : "") + fmt(p.yoy_pct) + "%"}`;
    tip.hidden = false;
    const tw = tip.offsetWidth;
    tip.style.left = (x(i) + 10 + tw > W ? x(i) - tw - 10 : x(i) + 10) + "px"; // 오른쪽 끝에선 왼쪽에 표시
    tip.style.top = "4px";
  };
  svg.addEventListener("mousemove", (e) => move(e.clientX));
  svg.addEventListener("touchmove", (e) => move(e.touches[0].clientX), { passive: true });
  svg.addEventListener("mouseleave", () => { g.setAttribute("visibility", "hidden"); tip.hidden = true; });
}
let resizeTimer;
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawChart, 150); });

// ---------- 데이터 관리 (CRUD) ----------
async function loadData(flashId) {
  try {
    state.data = await api("/api/data");
    renderTable(flashId);
  } catch (e) {
    $("#data-body").innerHTML = `<tr><td colspan="4" class="muted">데이터를 불러오지 못했어요: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function renderTable(flashId) {
  $("#data-count").textContent = `총 ${state.data.length}개`;
  // 최신 데이터가 위로 오게
  $("#data-body").innerHTML = [...state.data].reverse().map((d) => `
    <tr data-id="${d.id}" class="${d.id === flashId ? "flash" : ""}">
      <td>${d.date}</td>
      <td class="num">${fmt(d.value)}</td>
      <td class="memo" title="${escapeHtml(d.memo)}">${escapeHtml(d.memo)}</td>
      <td class="act"><button type="button" class="edit">수정</button><button type="button" class="del">삭제</button></td>
    </tr>`).join("");
  if (flashId) $(`tr[data-id="${flashId}"]`)?.scrollIntoView({ block: "nearest" });
}

async function refreshAll(flashId) {
  await Promise.all([loadData(flashId), loadSummary(), loadStatistics()]);
}

$("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    date: $("#add-date").value,
    value: parseFloat($("#add-value").value),
    memo: $("#add-memo").value,
  };
  try {
    const created = await api("/api/data", { method: "POST", body: JSON.stringify(body) });
    e.target.reset();
    toast(`${created.date} 데이터를 추가했어요`);
    refreshAll(created.id);
  } catch (err) {
    toast("추가 실패: " + err.message, true);
  }
});

$("#data-body").addEventListener("click", async (e) => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  const item = state.data.find((d) => d.id === tr.dataset.id);

  if (e.target.classList.contains("del")) {
    if (!confirm(`${item.date} 데이터를 삭제할까요?`)) return;
    try {
      await api(`/api/data/${item.id}`, { method: "DELETE" });
      toast(`${item.date} 데이터를 삭제했어요`);
      refreshAll();
    } catch (err) {
      toast("삭제 실패: " + err.message, true);
    }
  } else if (e.target.classList.contains("edit")) {
    tr.innerHTML = `
      <td><input type="month" value="${item.date}" class="e-date"></td>
      <td><input type="number" step="0.1" min="0" max="1000" value="${item.value}" class="e-value"></td>
      <td><input type="text" maxlength="200" value="${escapeHtml(item.memo)}" class="e-memo"></td>
      <td class="act"><button type="button" class="save">저장</button><button type="button" class="cancel">취소</button></td>`;
    tr.querySelector(".e-value").focus();
  } else if (e.target.classList.contains("cancel")) {
    renderTable();
  } else if (e.target.classList.contains("save")) {
    const changes = {
      date: tr.querySelector(".e-date").value,
      value: parseFloat(tr.querySelector(".e-value").value),
      memo: tr.querySelector(".e-memo").value,
    };
    try {
      await api(`/api/data/${item.id}`, { method: "PUT", body: JSON.stringify(changes) });
      toast(`${changes.date} 데이터를 수정했어요`);
      refreshAll(item.id);
    } catch (err) {
      toast("수정 실패: " + err.message, true);
    }
  }
});

$("#refresh-data").addEventListener("click", () => refreshAll());

// ---------- 내보내기 ----------
function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
$("#export-csv").addEventListener("click", () => {
  const esc = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const rows = ["date,value,memo", ...state.data.map((d) => [d.date, d.value, esc(d.memo)].join(","))];
  download("semiconductor_production.csv", "﻿" + rows.join("\n"), "text/csv;charset=utf-8"); // BOM: 엑셀 한글 깨짐 방지
});
$("#export-json").addEventListener("click", () => {
  const rows = state.data.map(({ date, value, memo }) => ({ date, value, memo }));
  download("semiconductor_production.json", JSON.stringify(rows, null, 2), "application/json");
});

// ---------- 시작 ----------
(async function init() {
  updateThemeButton();
  const ok = await wakeServer();
  if (!ok) return;
  loadConversations();
  refreshAll();
})();
