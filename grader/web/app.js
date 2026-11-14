"use strict";
// Minimal demo client. Everything that comes back from the grader is untrusted (it contains student
// output), so the DOM is only ever built with textContent, never innerHTML.
const $ = (id) => document.getElementById(id);
const h = (tag, props = {}, ...kids) => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids.filter((k) => k != null));
  return e;
};
const store = {
  get: (k) => { try { return sessionStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* private mode */ } },
};
const KEYMAP = { " ": "spc", "\n": "ret", "-": "minus", "=": "equal", ",": "comma", ".": "dot", "/": "slash", ";": "semicolon" };

let lab = null;       // description of the selected lab
let files = {};       // name -> text (editable)
let current = "";     // open tab
let marks = {};       // file -> Set(line) with findings

async function api(path, body, method) {
  const res = await fetch(path, {
    method: method || (body ? "POST" : "GET"),
    headers: { "X-API-Key": store.get("key") || "", ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) { askKey(true); throw new Error("Cần API key."); }
  if (!res.ok) {
    const e = new Error(res.status === 503 ? "Hệ thống đang hết chỗ, thử lại sau ít giây." : `Lỗi ${res.status}`);
    e.status = res.status;
    throw e;
  }
  return res.json();
}

function askKey(wrong) {
  $("key-error").hidden = !wrong;
  if (!$("key-dialog").open) $("key-dialog").showModal();
}

// ---- editor -------------------------------------------------------------------------------
function drawGutter() {
  const n = $("code").value.split("\n").length;
  const set = marks[current] || new Set();
  $("gutter").replaceChildren(...Array.from({ length: n }, (_, i) =>
    h("span", { textContent: String(i + 1), className: set.has(i + 1) ? "mark" : "" })));
  $("gutter").scrollTop = $("code").scrollTop;
}

function openTab(name) {
  if (current in files) files[current] = $("code").value;
  current = name;
  const readonly = !(name in files);
  $("code").value = readonly ? lab.scaffold[name] : files[name];
  $("code").readOnly = readonly;
  for (const b of $("tabs").children) b.setAttribute("aria-selected", String(b.dataset.name === name));
  drawGutter();
}

function drawTabs() {
  const tab = (name, ro) => {
    const b = h("button", { type: "button", textContent: name, className: ro ? "readonly" : "", onclick: () => openTab(name) });
    b.dataset.name = name;
    b.setAttribute("role", "tab");
    return b;
  };
  $("tabs").replaceChildren(...Object.keys(files).map((n) => tab(n, false)), ...Object.keys(lab.scaffold).map((n) => tab(n, true)));
}

function goTo(file, line, col) {
  if (!(file in files)) return;
  openTab(file);
  const lines = $("code").value.split("\n");
  const start = lines.slice(0, line - 1).reduce((a, l) => a + l.length + 1, 0);
  $("code").focus();
  $("code").setSelectionRange(start + Math.max(0, (col || 1) - 1), start + (lines[line - 1] || "").length);
  const lh = parseFloat(getComputedStyle($("code")).lineHeight);
  $("code").scrollTop = Math.max(0, (line - 4) * lh);
  $("work").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function saveDraft() {
  if (current in files) files[current] = $("code").value;
  store.set(`draft:${lab.id}`, JSON.stringify(files));
}

async function loadLab(id, fresh) {
  lab = await api(`/labs/${id}`);
  const names = [...new Set([...lab.files, ...Object.keys(lab.starter)])];
  const starter = Object.fromEntries(names.map((n) => [n, lab.starter[n] || ""]));
  let draft = null;
  try { draft = fresh ? null : JSON.parse(store.get(`draft:${id}`)); } catch { draft = null; }
  files = { ...starter, ...(draft || {}) };
  marks = {};
  current = "";
  $("statement").textContent = lab.statement;
  $("stdin-box").hidden = lab.mode !== "user";
  $("keys-box").hidden = lab.mode !== "toy";
  $("live").hidden = lab.mode !== "toy";
  stopLive();
  drawTabs();
  openTab(Object.keys(files).find((n) => !n.endsWith(".S")) || Object.keys(files)[0]);
  $("result").replaceChildren(h("p", { className: "empty", textContent: "Chưa có kết quả cho bài này." }));
}

// ---- results ------------------------------------------------------------------------------
function screen(p) {
  if (!p.text) return h("p", { className: "empty", textContent: "Không lấy được màn hình (kernel dừng trước khi vẽ)." });
  const pre = h("pre", { className: "screen" });
  pre.setAttribute("aria-label", "Màn hình VGA 80x25");
  p.text.forEach((row, r) => {
    const text = row.padEnd(p.cols, " ");
    const attr = p.attr[r];
    for (let c = 0; c < p.cols;) {  // one <span> per run of equal colour
      const a = attr.slice(c * 2, c * 2 + 2);
      let end = c + 1;
      while (end < p.cols && attr.slice(end * 2, end * 2 + 2) === a) end++;
      const v = parseInt(a, 16);
      const s = h("span", { textContent: text.slice(c, end) });
      s.style.color = p.palette[v & 15];
      s.style.background = p.palette[(v >> 4) & 7];
      pre.append(s);
      c = end;
    }
    pre.append("\n");
  });
  return h("div", { className: "screen-wrap" }, pre);
}

function preview(p) {
  if (!p) return [];
  if (p.kind === "screen") {
    return [h("h3", { textContent: "Màn hình kernel của bạn" }), screen(p),
      h("h3", { textContent: "Cổng serial (COM1)" }), h("pre", { className: "out", textContent: p.serial || "(trống)" })];
  }
  if (p.kind === "console") {
    return [h("h3", { textContent: "Kernel log" }), h("pre", { className: "out", textContent: p.log || "(trống)" })];
  }
  const state = p.timed_out ? "quá thời gian" : p.killed ? "bị dừng do vượt giới hạn" : `mã thoát ${p.exit_code}`;
  return [h("h3", { textContent: `Output chương trình (${state})` }), h("pre", { className: "out", textContent: p.stdout || "(không in gì)" }),
    ...(p.stderr ? [h("h3", { textContent: "stderr" }), h("pre", { className: "out", textContent: p.stderr })] : [])];
}

function fixButton(a) {
  return h("button", { type: "button", textContent: `${a.label} → ${a.file}:${a.line}`, onclick: () => goTo(a.file, a.line, a.col) });
}

function item(i) {
  const line = (label, text, cls) => text && h("p", { className: cls || "" }, h("span", { className: "label", textContent: `${label}: ` }), text);
  return h("div", { className: `item ${i.severity}` },
    h("div", { className: "head" }, h("span", { className: "title", textContent: i.title }),
      h("span", { className: "loc", textContent: i.file ? `${i.file}:${i.line}` : "" })),
    i.code && h("code", { className: "src", textContent: i.code }),
    h("p", { textContent: i.explain }), line("Gợi ý", i.hint), line("Khái niệm", i.concept, "concept"),
    i.action && fixButton(i.action));
}

function test(t) {
  return h("li", {},
    h("span", { className: t.passed ? "pass" : "fail", textContent: t.passed ? "✓ " : "✗ " }),
    h("span", { className: "id", textContent: t.id }),
    h("span", { className: "pts", textContent: `${t.earned}/${t.points}` }),
    !t.passed && h("p", { textContent: t.message }),
    !t.passed && t.hint && h("p", { textContent: `Gợi ý: ${t.hint}` }),
    !t.passed && t.concept && h("p", { className: "concept", textContent: `Khái niệm: ${t.concept}` }));
}

function score(s) {
  const names = { compile: "Biên dịch", static: "Phân tích tĩnh", dynamic: "Chạy thử" };
  const bars = h("div", { className: "bars" });
  for (const [k, c] of Object.entries(s.components)) {
    const fill = h("i");
    fill.style.width = `${c.percent}%`;
    bars.append(h("span", { textContent: names[k] }), h("div", { className: "bar" }, fill), h("span", { textContent: `${c.earned}/${c.weight}` }));
  }
  return h("div", { className: "score" },
    h("div", { className: "total", textContent: String(s.score) }, h("small", { textContent: ` / ${s.max}` })), bars);
}

function show(r) {
  const fb = r.feedback;
  marks = {};
  for (const i of fb.items) if (i.file) (marks[i.file] ||= new Set()).add(i.line);
  drawGutter();
  const good = r.score ? r.score.score === 100 : r.status === "done" && !fb.items.length;
  const bad = ["rejected", "compile_error", "infra_error"].includes(r.status);
  $("result").replaceChildren(
    h("p", { className: `summary ${good ? "ok" : bad ? "bad" : ""}`, textContent: fb.summary }),
    ...(r.score ? [score(r.score)] : []),
    ...(fb.retry ? [fixButton(fb.retry)] : []),
    ...preview(r.preview),
    ...(fb.items.length ? [h("h3", { textContent: "Nhận xét" }), ...fb.items.map(item)] : []),
    ...(fb.more ? [h("p", { className: "empty", textContent: `… và ${fb.more} mục khác.` })] : []),
    ...(fb.tests.length ? [h("h3", { textContent: "Các test" }), h("ul", { className: "tests" }, ...fb.tests.map(test))] : []),
    ...(fb.next_steps.length ? [h("h3", { textContent: "Việc nên làm tiếp" }), h("ol", { className: "steps" }, ...fb.next_steps.map((s) => h("li", { textContent: s })))] : []));
}

// ---- live session (toy kernels) -----------------------------------------------------------
const NAMED = { Enter: "ret", Backspace: "backspace", Escape: "esc", " ": "spc", ArrowUp: "up", ArrowDown: "down",
  ArrowLeft: "left", ArrowRight: "right", "-": "minus", "=": "equal", ",": "comma", ".": "dot", "/": "slash",
  ";": "semicolon", "'": "apostrophe", "[": "bracket_left", "]": "bracket_right", "\\": "backslash", "`": "grave_accent" };
const SHIFTED = { _: "minus", "+": "equal", "<": "comma", ">": "dot", "?": "slash", ":": "semicolon", '"': "apostrophe",
  "{": "bracket_left", "}": "bracket_right", "|": "backslash", "~": "grave_accent", "!": "1", "@": "2", "#": "3",
  $: "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0" };
const ENDED = { timeout: "Hết thời gian của phiên.", idle: "Phiên tự dừng vì không còn ai theo dõi.", stopped: "Đã dừng.",
  reset: "Máy ảo đã dừng: kernel làm CPU reset (triple fault) hoặc tự tắt.", infra_error: "Hệ thống gặp sự cố, hãy thử lại.",
  unsupported: "Bài này không hỗ trợ chạy trực tiếp." };
let liveId = null;
let keyBuf = [];

function qcode(key) {  // one character or KeyboardEvent.key -> QEMU key name (with shift+ when needed)
  if (NAMED[key]) return NAMED[key];
  if (SHIFTED[key]) return `shift+${SHIFTED[key]}`;
  if (/^[a-z0-9]$/.test(key)) return key;
  if (/^[A-Z]$/.test(key)) return `shift+${key.toLowerCase()}`;
  return key === "\n" ? "ret" : null;
}

function typeKeys(keys) {
  if (!liveId || !keys.length) return;
  if (!keyBuf.length) {
    setTimeout(() => {  // batch a burst of typing into one request
      const batch = keyBuf.splice(0, 32);
      if (liveId && batch.length) api(`/live/${liveId}/keys`, { keys: batch }).catch(() => {});
    }, 80);
  }
  keyBuf.push(...keys);
}

function stopLive() {
  if (liveId) api(`/live/${liveId}`, null, "DELETE").catch(() => {});
}

async function startLive() {
  saveDraft();
  stopLive();
  const bar = h("div", { className: "livebar" }, h("span", { className: "dot" }));
  const state = h("span", { className: "state", textContent: "Đang biên dịch…" });
  const stop = h("button", { type: "button", textContent: "■ Dừng", onclick: stopLive });
  bar.append(state, stop);
  const view = h("div", {});
  const serialOut = h("pre", { className: "out", textContent: "(trống)" });
  const extra = h("div", {});
  $("result").replaceChildren(bar, view, h("p", { className: "hint", textContent: "Bấm vào màn hình rồi gõ phím để gửi vào kernel. Trên điện thoại: nhập vào ô “Phím gõ” rồi nhấn Enter." }),
    h("h3", { textContent: "Cổng serial (COM1)" }), serialOut, extra);
  let id;
  try {
    ({ id } = await api("/live", { lab: lab.id, files }));
  } catch (e) {
    state.textContent = e.message;
    stop.remove();
    return;
  }
  liveId = id;
  let after = -1;
  let wrap = null;
  let deadline = 0;  // frames only arrive when the screen changes, so the countdown ticks locally
  const clock = setInterval(() => {
    if (deadline) state.textContent = `Đang chạy trực tiếp · còn ${Math.max(0, Math.round((deadline - Date.now()) / 1000))} giây`;
  }, 1000);
  try {
    while (liveId === id) {
      const f = await api(`/live/${id}?after=${after}`);
      if (liveId !== id) break;  // a newer session took over this panel
      const stale = f.seq === after;  // the long-poll timed out and returned the frame we already have
      after = f.seq;
      if (f.text && !stale) {
        const fresh = screen(f);
        if (wrap) {
          wrap.replaceChildren(...fresh.childNodes);  // keep the focused element in place
        } else {
          wrap = fresh;
          wrap.tabIndex = 0;
          wrap.setAttribute("role", "application");
          wrap.setAttribute("aria-label", "Màn hình kernel đang chạy. Gõ phím để gửi vào kernel.");
          wrap.addEventListener("keydown", (e) => {
            if (e.ctrlKey || e.metaKey || e.altKey || e.key === "Tab") return;  // browser shortcuts and focus keep working
            const k = qcode(e.key);
            if (k) { e.preventDefault(); typeKeys([k]); }
          });
          view.replaceChildren(h("h3", { textContent: "Màn hình kernel (trực tiếp)" }), wrap);
          wrap.focus({ preventScroll: true });
        }
        serialOut.textContent = f.serial || "(trống)";
      }
      if (f.state === "running") {
        bar.classList.add("on");
        if (!stale) {
          deadline = Date.now() + f.left * 1000;
          state.textContent = `Đang chạy trực tiếp · còn ${f.left} giây`;
        }
      } else if (f.state === "queued") {
        state.textContent = "Đang chờ tới lượt…";
      } else if (f.state === "ended") {
        deadline = 0;
        bar.classList.remove("on");
        stop.remove();
        const fb = f.feedback;
        state.textContent = fb ? fb.summary : ENDED[f.reason] || "Phiên đã kết thúc.";
        if (fb) {
          marks = {};
          for (const i of fb.items) if (i.file) (marks[i.file] ||= new Set()).add(i.line);
          drawGutter();
          extra.replaceChildren(h("h3", { textContent: "Nhận xét" }), ...fb.items.map(item));
        }
        break;
      }
    }
  } catch (e) {
    bar.classList.remove("on");
    state.textContent = e.status === 404 ? "Phiên đã hết hạn." : e.message;
  } finally {
    clearInterval(clock);
    if (liveId === id) liveId = null;
  }
}

async function send(kind) {
  saveDraft();
  stopLive();
  const body = { lab: lab.id, files };
  if (kind === "run" && lab.mode === "user") body.stdin = $("stdin").value;
  if (kind === "run" && lab.mode === "toy") {
    body.keys = [...$("keys").value.toLowerCase()].map((c) => KEYMAP[c] || c).filter((k) => /^[a-z0-9_]{1,16}$/.test(k)).slice(0, 64);
  }
  for (const b of [$("run"), $("submit")]) b.disabled = true;
  const t0 = Date.now();
  try {
    const { id } = await api(kind === "run" ? "/runs" : "/submissions", body);
    for (;;) {
      const r = await api(`/submissions/${id}`);
      const secs = ((Date.now() - t0) / 1000).toFixed(0);
      if (r.status !== "queued" && r.status !== "running") { show(r); $("busy").textContent = `Xong sau ${secs} giây.`; break; }
      if (Date.now() - t0 > 180000) throw new Error("Chờ quá lâu, hãy thử lại.");
      $("busy").textContent = `${r.status === "queued" ? "Đang chờ tới lượt" : kind === "run" ? "Đang chạy" : "Đang chấm"}… ${secs}s`;
      await new Promise((ok) => setTimeout(ok, 400));
    }
  } catch (e) {
    $("busy").textContent = e.message;
  } finally {
    for (const b of [$("run"), $("submit")]) b.disabled = false;
  }
}

async function start() {
  const labs = await api("/labs");
  $("lab").replaceChildren(...labs.map((l) => h("option", { value: l.id, textContent: l.title })));
  const last = store.get("lab");
  if (labs.some((l) => l.id === last)) $("lab").value = last;
  await loadLab($("lab").value);
}

$("code").addEventListener("input", () => { drawGutter(); saveDraft(); });
$("code").addEventListener("scroll", () => { $("gutter").scrollTop = $("code").scrollTop; });
$("code").addEventListener("keydown", (e) => {
  if (e.key !== "Tab" || e.shiftKey || $("code").readOnly) return;  // Shift+Tab still leaves the editor
  e.preventDefault();
  $("code").setRangeText(current.endsWith(".c") || current.endsWith(".S") ? "\t" : "    ", $("code").selectionStart, $("code").selectionEnd, "end");
  drawGutter();
});
$("lab").addEventListener("change", () => { store.set("lab", $("lab").value); loadLab($("lab").value).catch((e) => { $("busy").textContent = e.message; }); });
$("run").addEventListener("click", () => send("run"));
$("live").addEventListener("click", startLive);
$("keys").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !liveId) return;
  e.preventDefault();
  typeKeys([...$("keys").value].map(qcode).filter(Boolean).concat("ret"));
  $("keys").value = "";
});
$("submit").addEventListener("click", () => send("grade"));
$("reset").addEventListener("click", () => { if (confirm("Bỏ mã hiện tại và quay về mã ban đầu của bài?")) loadLab(lab.id, true); });
$("key-btn").addEventListener("click", () => askKey(false));
$("key-dialog").addEventListener("close", () => { store.set("key", $("key").value); start().catch(() => {}); });
if (store.get("key")) start().catch((e) => { $("busy").textContent = e.message; }); else askKey(false);
