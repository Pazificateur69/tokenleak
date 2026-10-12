document.documentElement.classList.add("js");

// Scroll reveal (IntersectionObserver, no scroll listeners). CSS skips it under reduced motion.
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}, { threshold: 0.15 });
document.querySelectorAll(".reveal").forEach((el) => {
  const siblings = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
  el.style.setProperty("--d", `${siblings.indexOf(el) * 80}ms`);
  io.observe(el);
});

// Context tax calculator. Claude ratios: cache write 1.25x, cache read 0.1x of fresh input.
const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat("en-US");
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
  const equiv = 1.25 + 0.1 * later;
  $("r-equiv").textContent = equiv.toFixed(2);
  $("r-save").textContent = size > 800 ? `${Math.round(100 * (size - 800) / size)}%` : "0%";
  if (calls.children.length !== len) calls.replaceChildren(...Array.from({ length: len }, () => document.createElement("i")));
  [...calls.children].forEach((c, i) => {
    c.className = i + 1 === at ? "at" : i + 1 > at ? "re" : "";
  });
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
  const W = 900, rowH = 74, top = 12, left = 210, right = 70, H = top + BENCH.length * rowH + 34;
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
  for (let v = 0.1; v <= 0.5001; v += 0.1) {
    grid.append(el("line", { x1: sx(v), x2: sx(v), y1: top, y2: H - 30 }));
    axis.append(el("text", { x: sx(v), y: H - 10, "text-anchor": "middle" }, `$${v.toFixed(2)}`));
  }
  svg.append(grid, axis);
  BENCH.forEach((r, i) => {
    const y = top + i * rowH + rowH / 2;
    const mb = median(r.base), ml = median(r.lean);
    svg.append(el("text", { class: "task", x: 0, y: y - 4 }, r.task));
    svg.append(el("text", { class: "val", x: 0, y: y + 15 }, r.note));
    const len = Math.abs(sx(mb) - sx(ml));
    const link = el("line", { class: "link draw", x1: sx(mb), x2: sx(ml), y1: y, y2: y });
    link.style.setProperty("--len", len);
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
  new IntersectionObserver((es, o) => { if (es[0].isIntersecting) { host.classList.add("in"); o.disconnect(); } }, { threshold: 0.3 }).observe(host);

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

// Live star count (unauthenticated GitHub API; hidden if it fails)
fetch("https://api.github.com/repos/Pazificateur69/tokenleak")
  .then((r) => (r.ok ? r.json() : Promise.reject()))
  .then((d) => {
    if (!d.stargazers_count) return;
    const s = document.querySelector("[data-stars]");
    s.textContent = nf.format(d.stargazers_count);
    s.hidden = false;
  })
  .catch(() => {});
