document.documentElement.classList.add("js");

const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat("en-US");
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
const once = (el, fn, threshold = 0.25) => {
  const o = new IntersectionObserver((es) => { if (es[0].isIntersecting) { o.disconnect(); fn(); } }, { threshold });
  o.observe(el);
};
const tween = (from, to, ms, step) => {
  if (calm) return step(to);
  const t0 = performance.now();
  const tick = (t) => {
    const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
    step(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
};

// Scroll reveal (IntersectionObserver, no scroll listeners). CSS skips it under reduced motion.
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}, { threshold: 0.12 });
document.querySelectorAll(".reveal").forEach((el) => {
  const sib = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
  el.style.setProperty("--d", `${sib.indexOf(el) * 80}ms`);
  io.observe(el);
});

// Signature: one session as a stack of API calls. A test log read at call 3 is re-sent by every later call.
(function stack() {
  const svg = $("stack"), ns = "http://www.w3.org/2000/svg";
  const CALLS = 24, READ_AT = 3, BASE = 28000, STEP = 1500, LEAK = 12000, LEAN = 800;
  const X0 = 30, W = 520, top = 34, pitch = 12, h = 8;
  const sx = (t) => (t / (BASE + STEP * CALLS + LEAK)) * W;
  const el = (tag, a, text) => {
    const n = document.createElementNS(ns, tag);
    for (const k in a) n.setAttribute(k, a[k]);
    if (text != null) n.textContent = text;
    return n;
  };
  svg.setAttribute("viewBox", `0 0 560 ${top + CALLS * pitch + 4}`);
  const leakX = X0 + sx(BASE + STEP * READ_AT);
  const rows = [], leaks = [], afters = [];
  const noteLine = el("line", { class: "note-line", x1: leakX + 1, x2: leakX + 1, y1: 14, y2: top + READ_AT * pitch - 2 });
  const narrow = () => svg.getBoundingClientRect().width < 440;
  const noteText = (m) => m === "leak"
    ? (narrow() ? "12k-token test log" : "12k-token test log, read at call 3")
    : (narrow() ? "bounded to 800 tokens" : "same log, bounded to 800 tokens");
  const note = el("text", { class: "note", x: leakX + 8, y: 18 }, noteText("leak"));
  svg.append(noteLine, note);
  for (let i = 1; i <= CALLS; i++) {
    const y = top + (i - 1) * pitch;
    const g = el("g", { class: "row" });
    g.append(el("text", { class: "idx", x: X0 - 8, y: y + h - 1, "text-anchor": "end" }, String(i)));
    g.append(el("rect", { class: "sys", x: X0, y, width: sx(BASE), height: h, rx: 2 }));
    g.append(el("rect", { class: "conv", x: X0 + sx(BASE) + 1, y, width: Math.max(0, sx(STEP * Math.min(i, READ_AT)) - 1), height: h, rx: 2 }));
    if (i > READ_AT) {
      const lk = el("rect", { class: "leak", x: leakX + 1, y, width: sx(LEAK) - 1, height: h, rx: 2 });
      const af = el("rect", { class: "conv after", x: leakX + sx(LEAK) + 1, y, width: Math.max(0, sx(STEP * (i - READ_AT)) - 1), height: h, rx: 2 });
      g.append(lk, af);
      leaks.push(lk);
      afters.push(af);
    }
    svg.append(g);
    rows.push(g);
  }

  const meter = $("meter"), buttons = [...document.querySelectorAll(".toggle button")];
  let mode = "leak", shown = 0, value = 0, auto = !calm, timer = 0;
  const target = () => Math.max(0, shown - READ_AT) * (mode === "leak" ? LEAK : LEAN);
  const setMeter = () => {
    const from = value, to = target();
    value = to;
    tween(from, to, 700, (v) => { meter.textContent = nf.format(Math.round(v)); });
  };
  function setMode(m) {
    mode = m;
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === m)));
    const k = m === "leak" ? 1 : LEAN / LEAK, dx = m === "leak" ? 0 : -(sx(LEAK) - sx(LEAN));
    leaks.forEach((r) => { r.style.transform = `scaleX(${k})`; });
    afters.forEach((r) => { r.style.transform = `translateX(${dx}px)`; });
    note.textContent = noteText(m);
    setMeter();
  }
  buttons.forEach((b) => b.addEventListener("click", () => { auto = false; clearTimeout(timer); setMode(b.dataset.mode); }));

  function loop() {
    if (!auto) return;
    timer = setTimeout(() => {
      if (!auto) return;
      setMode(mode === "leak" ? "lean" : "leak");
      loop();
    }, mode === "leak" ? 2600 : 3600);
  }
  function play() {
    if (calm) {
      rows.forEach((r) => r.classList.add("on"));
      shown = CALLS;
      return setMeter();
    }
    rows.forEach((r, i) => setTimeout(() => {
      r.classList.add("on");
      shown = i + 1;
      if (shown > READ_AT) setMeter();
      if (shown === CALLS) loop();
    }, 120 + i * 105));
  }
  once(svg, play, 0.2);
})();

// Animated stats (final values are already in the HTML for no-JS readers)
document.querySelectorAll("[data-count]").forEach((s) => {
  const to = +s.dataset.count, suffix = s.dataset.suffix || "";
  const show = (v) => { const r = Math.round(v); s.textContent = `${r < 0 ? "−" : ""}${Math.abs(r)}${suffix}`; };
  if (calm) return;
  show(0);
  once(s, () => tween(0, to, 1400, show), 0.6);
});

// Terminal: type the command, then print the real report line by line
(function terminal() {
  const term = $("term"), typed = $("typed");
  if (!term || !typed) return;
  if (calm) { term.classList.add("run"); return; }
  const text = typed.dataset.text;
  typed.textContent = "";
  once(term, () => {
    let i = 0;
    const tick = () => {
      typed.textContent = text.slice(0, ++i);
      if (i < text.length) setTimeout(tick, 34 + Math.random() * 40);
      else setTimeout(() => term.classList.add("run"), 280);
    };
    setTimeout(tick, 350);
  }, 0.35);
})();

// Spotlight cards: the glow follows the pointer
document.querySelectorAll(".spot").forEach((c) => {
  c.addEventListener("pointermove", (e) => {
    const r = c.getBoundingClientRect();
    c.style.setProperty("--mx", `${e.clientX - r.left}px`);
    c.style.setProperty("--my", `${e.clientY - r.top}px`);
  });
});

// Context tax calculator. Claude ratios: cache write 1.25x, cache read 0.1x of fresh input.
const calls = $("calls");
function renderTax() {
  const size = +$("size").value, len = +$("len").value;
  const at = Math.min(+$("at").value, len - 1);
  $("at").max = len - 1;
  $("at").value = at;
  const later = len - at;
  $("o-size").textContent = nf.format(size);
  $("o-at").textContent = at;
  $("o-len").textContent = len;
  $("r-times").textContent = later;
  $("r-equiv").textContent = (1.25 + 0.1 * later).toFixed(2);
  $("r-save").textContent = size > 800 ? `${Math.round(100 * (size - 800) / size)}%` : "0%";
  if (calls.children.length !== len) calls.replaceChildren(...Array.from({ length: len }, () => document.createElement("i")));
  [...calls.children].forEach((c, i) => { c.className = i + 1 === at ? "at" : i + 1 > at ? "re" : ""; });
}
["size", "at", "len"].forEach((id) => $(id).addEventListener("input", renderTax));
renderTax();

// Benchmark: cost per run (USD, as reported by Claude Code), 5 runs per arm. Source: bench/results/2026-10-12-final-rules-v1.1
const BENCH = [
  { task: "Fix a failing test", note: "chatty test logs", base: [0.126, 0.129, 0.14, 0.142, 0.143], lean: [0.131, 0.14, 0.14, 0.141, 0.15] },
  { task: "Answer a data question", note: "big data module", base: [0.201, 0.202, 0.206, 0.208, 0.211], lean: [0.148, 0.149, 0.16, 0.169, 0.183] },
  { task: "Fix a noisy build", note: "600 lines of output", base: [0.252, 0.266, 0.267, 0.416, 0.446], lean: [0.144, 0.153, 0.159, 0.218, 0.232] },
  { task: "Add a feature", note: "held out from tuning", base: [0.288, 0.421, 0.459, 0.466, 0.492], lean: [0.164, 0.172, 0.184, 0.195, 0.225] },
];
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
const usd = (v) => `$${v.toFixed(3)}`;
const pct = (b, l) => {
  const d = Math.round(100 * (l - b) / b);
  return d === 0 ? "0%" : `${d > 0 ? "+" : "−"}${Math.abs(d)}%`;
};

function renderChart() {
  const host = $("chart");
  // Drawn at the container's real width so text stays at true size; narrow screens put labels above rows.
  const W = Math.max(300, Math.round(host.clientWidth || 900));
  const narrow = W < 640;
  const rowH = narrow ? 96 : 74, top = narrow ? 34 : 12, left = narrow ? 6 : 210, right = narrow ? 50 : 70;
  const H = top + BENCH.length * rowH + 34 - (narrow ? 24 : 0);
  const x0 = 0.1, x1 = 0.5;
  const sx = (v) => left + (v - x0) / (x1 - x0) * (W - left - right);
  const ns = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, text) => {
    const n = document.createElementNS(ns, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    return n;
  };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Dot plot of cost per run for four tasks, without and with tokenleak. Medians: " +
      BENCH.map((r) => `${r.task} ${usd(median(r.base))} to ${usd(median(r.lean))}`).join("; ") + "." });
  const grid = el("g", { class: "grid" }), axis = el("g", { class: "axis" });
  for (let v = 0.1; v <= 0.5001; v += narrow ? 0.2 : 0.1) {
    grid.append(el("line", { x1: sx(v), x2: sx(v), y1: top, y2: H - 30 }));
    axis.append(el("text", { x: sx(v), y: H - 10, "text-anchor": "middle" }, `$${v.toFixed(2)}`));
  }
  svg.append(grid, axis);
  BENCH.forEach((r, i) => {
    const y = top + i * rowH + rowH / 2 - (narrow ? 12 : 0);
    const mb = median(r.base), ml = median(r.lean);
    svg.append(el("text", { class: "task", x: 0, y: narrow ? y - 26 : y - 4 }, r.task + (narrow ? `, ${r.note}` : "")));
    if (!narrow) svg.append(el("text", { class: "val", x: 0, y: y + 15 }, r.note));
    const link = el("line", { class: "link draw", x1: sx(mb), x2: sx(ml), y1: y, y2: y });
    link.style.setProperty("--len", Math.abs(sx(mb) - sx(ml)));
    link.style.setProperty("--d", `${i * 120}ms`);
    svg.append(link);
    for (const [key, runs] of [["base", r.base], ["lean", r.lean]]) {
      const label = key === "base" ? "without the rules" : "with tokenleak";
      runs.forEach((v, j) => {
        svg.append(el("circle", { class: `run ${key}`, cx: sx(v), cy: y + (key === "base" ? -9 : 9), r: 4 }));
        const hit = el("circle", { class: "hit", cx: sx(v), cy: y + (key === "base" ? -9 : 9), r: 9 });
        hit.dataset.tip = `${r.task}, ${label}, run ${j + 1}: ${usd(v)}`;
        svg.append(hit);
      });
      const m = key === "base" ? mb : ml;
      svg.append(el("circle", { class: `med ${key}`, cx: sx(m), cy: y, r: 7 }));
      const hit = el("circle", { class: "hit", cx: sx(m), cy: y, r: 12 });
      hit.dataset.tip = `${r.task}, ${label}, median: ${usd(m)}`;
      svg.append(hit);
    }
    svg.append(el("text", { class: "delta", x: W - right + 14, y: y + 4 }, pct(mb, ml)));
  });
  host.replaceChildren(svg);

  const tip = $("tip");
  svg.addEventListener("pointermove", (e) => {
    const t = e.target.dataset && e.target.dataset.tip;
    if (!t) { tip.hidden = true; return; }
    tip.textContent = t;
    tip.style.left = `${e.clientX}px`;
    tip.style.top = `${e.clientY}px`;
    tip.hidden = false;
  });
  svg.addEventListener("pointerleave", () => { tip.hidden = true; });

  if ($("table").children.length) return;
  $("table").replaceChildren(...BENCH.map((r) => {
    const tr = document.createElement("tr");
    for (const v of [r.task, usd(median(r.base)), usd(median(r.lean)), pct(median(r.base), median(r.lean)), "5/5, 5/5"]) {
      const td = document.createElement("td");
      td.textContent = v;
      tr.append(td);
    }
    return tr;
  }));
}
renderChart();
once($("chart"), () => $("chart").classList.add("in"), 0.3);
let lastW = 0;
new ResizeObserver(() => {
  const w = Math.round($("chart").clientWidth);
  if (Math.abs(w - lastW) > 8) { lastW = w; requestAnimationFrame(renderChart); }
}).observe($("chart"));

// Tabs (WAI-ARIA pattern: arrows move between tabs)
const tabs = [...document.querySelectorAll('[role="tab"]')];
function select(tab) {
  tabs.forEach((t) => {
    const on = t === tab;
    t.setAttribute("aria-selected", on);
    t.tabIndex = on ? 0 : -1;
    $(t.getAttribute("aria-controls")).hidden = !on;
  });
}
tabs.forEach((t, i) => {
  t.addEventListener("click", () => select(t));
  t.addEventListener("keydown", (e) => {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = tabs[(i + step + tabs.length) % tabs.length];
    select(next);
    next.focus();
  });
});

// Copy buttons
document.querySelectorAll(".copy").forEach((b) => {
  b.addEventListener("click", async () => {
    const text = b.parentElement.querySelector("code").textContent;
    try {
      await navigator.clipboard.writeText(text);
      b.classList.add("done");
      b.querySelector(".i").className = "i i-check";
      b.setAttribute("aria-label", "Copied");
      setTimeout(() => {
        b.classList.remove("done");
        b.querySelector(".i").className = "i i-copy";
        b.setAttribute("aria-label", "Copy command");
      }, 1600);
    } catch {
      b.setAttribute("aria-label", "Copy failed, select the text instead");
    }
  });
});

// Live star count (unauthenticated GitHub API; hidden if it fails or is zero)
fetch("https://api.github.com/repos/Pazificateur69/tokenleak")
  .then((r) => (r.ok ? r.json() : Promise.reject()))
  .then((d) => {
    if (!d.stargazers_count) return;
    const s = document.querySelector("[data-stars]");
    s.textContent = nf.format(d.stargazers_count);
    s.hidden = false;
  })
  .catch(() => {});
