"""Animated SVG of the context stack for the README (pure CSS animation: GitHub renders it in <img>, no JS).

    python3 assets/make_stack_svg.py > assets/stack.svg

Same model as the website: 24 API calls, a 12k-token test log read at call 3 is re-sent by every later
call; then the same session with the log bounded to 800 tokens.
"""
CALLS, READ_AT, BASE, STEP, LEAK, LEAN = 24, 3, 28000, 1500, 12000, 800
W, H = 900, 490
X0, BAR_W, TOP, PITCH, BH = 64, 540, 118, 12.5, 8.5
CYCLE = 9.0  # seconds for one without/with loop, after the rows have appeared
scale = BAR_W / (BASE + STEP * CALLS + LEAK)
sx = lambda t: t * scale
leak_x = X0 + sx(BASE + STEP * READ_AT)
k = LEAN / LEAK
shift = sx(LEAK) - sx(LEAN)
start = 1.5  # bars are static (CSS entrance animations don't run reliably inside <img>); the loop starts here

css = f"""
  .bg {{ fill: #09090b; }} .card {{ fill: #111114; stroke: rgba(255,255,255,.09); }}
  text {{ font-family: ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  .t1 {{ fill: #f4f4f5; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }}
  .t2 {{ fill: #8b8b95; font-size: 13px; }}
  .idx {{ fill: #55555f; font-size: 9px; }}
  .sys {{ fill: #26262d; }} .conv {{ fill: #3a3a45; }} .leak {{ fill: #f5a524; }}
  .leak {{ transform-box: fill-box; transform-origin: left; animation: shrink {CYCLE}s cubic-bezier(.16,1,.3,1) {start}s infinite; }}
  .after {{ animation: slide {CYCLE}s cubic-bezier(.16,1,.3,1) {start}s infinite; }}
  .on-leak {{ animation: showA {CYCLE}s linear {start}s infinite; }}
  .on-lean {{ opacity: 0; animation: showB {CYCLE}s linear {start}s infinite; }}
  .pill {{ fill: rgba(255,255,255,.06); stroke: rgba(255,255,255,.14); }}
  .lbl {{ fill: #f4f4f5; font-size: 13px; font-weight: 600; }}
  .lbl.amber {{ fill: #ffc46b; }}
  .meter {{ fill: #ffc46b; font-size: 26px; font-weight: 600; }}
  .note {{ fill: #ffc46b; font-size: 11px; font-weight: 600; }}
  .cap {{ fill: #6d6d77; font-size: 11px; }}
  .glow {{ filter: url(#glow); }}
  @keyframes shrink {{ 0%, 38% {{ transform: scaleX(1); }} 46%, 86% {{ transform: scaleX({k:.4f}); }} 94%, 100% {{ transform: scaleX(1); }} }}
  @keyframes slide {{ 0%, 38% {{ transform: translateX(0); }} 46%, 86% {{ transform: translateX(-{shift:.1f}px); }} 94%, 100% {{ transform: translateX(0); }} }}
  @keyframes showA {{ 0%, 39% {{ opacity: 1; }} 41%, 89% {{ opacity: 0; }} 91%, 100% {{ opacity: 1; }} }}
  @keyframes showB {{ 0%, 41% {{ opacity: 0; }} 43%, 87% {{ opacity: 1; }} 89%, 100% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .leak, .after, .on-leak, .on-lean {{ animation: none; }} }}
"""

rows = []
for i in range(1, CALLS + 1):
    y = TOP + (i - 1) * PITCH
    parts = [f'<text class="idx mono" x="{X0 - 8}" y="{y + BH - 1:.1f}" text-anchor="end">{i}</text>',
             f'<rect class="sys" x="{X0}" y="{y:.1f}" width="{sx(BASE):.1f}" height="{BH}" rx="2"/>',
             f'<rect class="conv" x="{X0 + sx(BASE) + 1:.1f}" y="{y:.1f}" width="{sx(STEP * min(i, READ_AT)) - 1:.1f}" height="{BH}" rx="2"/>']
    if i > READ_AT:
        parts.append(f'<rect class="leak glow" x="{leak_x + 1:.1f}" y="{y:.1f}" width="{sx(LEAK) - 1:.1f}" height="{BH}" rx="2"/>')
        parts.append(f'<rect class="conv after" x="{leak_x + sx(LEAK) + 1:.1f}" y="{y:.1f}" width="{sx(STEP * (i - READ_AT)) - 1:.1f}" height="{BH}" rx="2"/>')
    rows.append(f'<g class="row">{"".join(parts)}</g>')

panel_x = X0 + BAR_W + 40
re_sent = CALLS - READ_AT
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Animation: 24 API calls of one agent session. A 12,000-token test log read at call 3 is re-sent by the 21 later calls (252,000 tokens). With tokenleak the same log is bounded to 800 tokens (16,800 tokens).">
<defs><filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<radialGradient id="aura" cx="78%" cy="20%" r="60%"><stop offset="0" stop-color="#f5a524" stop-opacity=".16"/><stop offset="1" stop-color="#f5a524" stop-opacity="0"/></radialGradient></defs>
<style>{css}</style>
<rect class="bg" width="{W}" height="{H}" rx="16"/>
<rect width="{W}" height="{H}" rx="16" fill="url(#aura)"/>
<rect class="card" x="16" y="16" width="{W - 32}" height="{H - 32}" rx="14"/>
<text class="t1" x="40" y="58">Every later call re-sends what the agent read</text>
<text class="t2" x="40" y="82">One agent session. Each bar is one API call; its length is the context it sends.</text>
<line x1="{leak_x + 1:.1f}" x2="{leak_x + 1:.1f}" y1="{TOP - 16}" y2="{TOP + READ_AT * PITCH - 3:.1f}" stroke="rgba(255,196,107,.6)"/>
<text class="note mono on-leak" x="{leak_x + 8:.1f}" y="{TOP - 8}">12k-token test log, read at call 3</text>
<text class="note mono on-lean" x="{leak_x + 8:.1f}" y="{TOP - 8}">same log, bounded to 800 tokens</text>
{"".join(rows)}
<g transform="translate({panel_x},{TOP})">
  <rect class="pill" width="{W - panel_x - 40}" height="34" rx="17"/>
  <text class="lbl on-leak" x="18" y="22">Without rules</text>
  <text class="lbl amber on-lean" x="18" y="22">With tokenleak</text>
  <text class="t2" x="0" y="84">Log re-sent by {re_sent} later calls</text>
  <text class="meter mono on-leak" x="0" y="118">252,000</text>
  <text class="meter mono on-lean" x="0" y="118">16,800</text>
  <text class="t2" x="0" y="140">tokens</text>
  <text class="cap" x="0" y="196">Illustration. Measured on 80 runs (Sonnet 5):</text>
  <text class="t1" x="0" y="230" style="fill:#ffc46b">&#8722;32% cost</text>
  <text class="cap" x="0" y="252">same 40/40 pass rate</text>
</g>
<text class="cap" x="40" y="{H - 34}">system prompt + tools</text><rect class="sys" x="28" y="{H - 43}" width="8" height="8" rx="2"/>
<text class="cap" x="200" y="{H - 34}">conversation</text><rect class="conv" x="188" y="{H - 43}" width="8" height="8" rx="2"/>
<text class="cap" x="308" y="{H - 34}">test log</text><rect class="leak" x="296" y="{H - 43}" width="8" height="8" rx="2" style="animation:none"/>
</svg>
"""
print(svg)
