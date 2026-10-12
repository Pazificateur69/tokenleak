"""Render ANSI terminal output as an SVG 'screenshot' for the README.

    FORCE_COLOR=1 python3 skills/tokenleak/scripts/tokenleak.py ... | python3 assets/render_svg.py > assets/demo.svg
"""
import html
import re
import sys

FG = {"31": "#ff6b6b", "32": "#5af78e", "33": "#f3f99d"}
LINE_H, CHAR_W, PAD, TOP = 19, 8.4, 20, 44

lines = sys.stdin.read().rstrip("\n").split("\n")
width = int(max(len(re.sub(r"\033\[[0-9;]*m", "", l)) for l in lines) * CHAR_W + 2 * PAD)
height = TOP + len(lines) * LINE_H + PAD
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
       f'<rect width="{width}" height="{height}" rx="10" fill="#0d1117"/>',
       '<circle cx="22" cy="20" r="6" fill="#ff5f56"/><circle cx="42" cy="20" r="6" fill="#ffbd2e"/>'
       '<circle cx="62" cy="20" r="6" fill="#27c93f"/>',
       '<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="14" fill="#c9d1d9" '
       'xml:space="preserve">']
for i, line in enumerate(lines):
    y = TOP + i * LINE_H
    spans, style = [], {}
    for part in re.split(r"(\033\[[0-9;]*m)", line):
        m = re.fullmatch(r"\033\[([0-9;]*)m", part)
        if m:
            codes = m.group(1).split(";")
            style = {} if codes in (["0"], [""]) else style
            for c in codes:
                if c == "1":
                    style["weight"] = "bold"
                elif c == "2":
                    style["dim"] = True
                elif c in FG:
                    style["fill"] = FG[c]
            continue
        if not part:
            continue
        attrs = ""
        if style.get("weight"):
            attrs += ' font-weight="bold"'
        if style.get("fill"):
            attrs += f' fill="{style["fill"]}"'
        elif style.get("dim"):
            attrs += ' fill="#8b949e"'
        spans.append(f"<tspan{attrs}>{html.escape(part)}</tspan>")
    out.append(f'<text x="{PAD}" y="{y}">{"".join(spans)}</text>')
out += ["</g>", "</svg>"]
print("\n".join(out))
