#!/usr/bin/env python3
"""tokenleak: find where your coding agent leaks context tokens.

Reads local Claude Code and Codex transcripts, prices every tool result by the
"context tax" it imposed (its size x every later call that re-sent it), and
names the rule that would have avoided it. Local, read-only, stdlib only.
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import os
import re
import shlex
import sys
import time
from datetime import datetime

__version__ = "1.0.0"
REPO = "https://github.com/Pazificateur69/tokenleak"

CHARS_PER_TOKEN = 4.0  # transcripts don't store per-result token counts; ~4 chars/token for code + English
IMAGE_TOKENS = 1500

# Relative price weights, fresh input = 1. Claude: published cache/output multipliers.
# Codex: GPT-5-family ratios (cached input 0.1x, output 8x).
WEIGHTS = {
    "claude": {"read": 0.1, "out": 5.0},
    "codex": {"read": 0.1, "out": 8.0, "enter": 1.0},
}

# kind: (flag when a result is bigger than N tokens, budget a bounded version would cost, fix)
KINDS = {
    "noisy-shell": (2000, 800, "Bound every command: quiet flags, `> log; tail -n 40 log`, grep the log"),
    "big-read": (4000, 2000, "Locate, then read: grep -n first, then read only that range"),
    "re-read": (0, 0, "Never re-read: the file is still in your context"),
    "wide-search": (2000, 600, "Narrow searches: scope path/type, cap results, -l for names only"),
    "big-fetch": (3000, 1500, "Fetch precisely: ask a question, select fields, cap pages"),
    "big-result": (5000, 2000, "Cap tool output: limits, filters, fields"),
    "rewrite": (1500, 0, "Edit, don't rewrite whole files"),
    "serial-call": (0, 0, "Batch independent reads/searches in one turn"),
    "wasted-call": (0, 0, "Don't repeat a call whose result you already have"),
    "verbose-reply": (2000, 600, "Answer lean: result first, no recap"),
}
SIZE_KIND = {"shell": "noisy-shell", "read": "big-read", "search": "wide-search",
             "fetch": "big-fetch", "subagent": "big-result", "other": "big-result"}

READ_CMDS = {"cat", "sed", "head", "tail", "nl", "less", "more", "bat", "batcat", "view"}
SEARCH_CMDS = {"rg", "grep", "egrep", "ag", "ack", "find", "fd", "ls", "tree", "locate"}
SHELL_TOOLS = {"bash", "bashoutput", "shell", "exec_command", "local_shell", "local_shell_call",
               "exec", "container.exec", "unified_exec", "run_terminal_cmd", "run_command"}
EDIT_TOOLS = {"edit", "multiedit", "write", "notebookedit", "apply_patch", "str_replace_based_edit_tool",
              "edit_file", "write_file", "create_file"}
MUTATES_ALL = re.compile(r"git\s+(checkout|switch|stash|reset|pull|merge|rebase|restore|apply)|--fix\b|"
                         r"prettier|black\b|ruff\s+format|gofmt|cargo\s+fmt|npm\s+run\s+format|codemod|sed\s+-i")


# ---------------------------------------------------------------- model

class Call:
    __slots__ = ("pos", "seg", "fresh", "cread", "c5m", "c1h", "out", "tools", "text_chars")

    def __init__(self, pos, seg):
        self.pos, self.seg = pos, seg
        self.fresh = self.cread = self.c5m = self.c1h = self.out = 0
        self.tools, self.text_chars = [], 0

    @property
    def ctx_in(self):
        return self.fresh + self.cread + self.c5m + self.c1h


class ToolUse:
    __slots__ = ("id", "name", "input", "pos", "call", "result")

    def __init__(self, id, name, inp, pos):
        self.id, self.name, self.input, self.pos = id, name or "", inp, pos
        self.call = self.result = None


class Result:
    __slots__ = ("tool", "pos", "seg", "tokens", "text", "extra")

    def __init__(self, tool, pos, seg, tokens, text, extra=None):
        self.tool, self.pos, self.seg, self.tokens, self.text, self.extra = tool, pos, seg, tokens, text, extra


class Thread:
    """One transcript file = one context window lineage (main session or a subagent)."""

    def __init__(self, path, agent):
        self.path, self.agent = path, agent
        self.session = self.cwd = None
        self.subagent = "/subagents/" in path.replace(os.sep, "/")
        self.calls, self.uses, self.results, self.human_pos = [], [], [], []
        self.notes = []  # (pos, text) of user prompts: what the agent knew before calling tools
        self.cost_usd = None
        self.mtime = os.path.getmtime(path)


def measure(content):
    """(text, est. tokens) of what a tool result put into context."""
    if content is None:
        return "", 0.0
    if isinstance(content, str):
        return content, len(content) / CHARS_PER_TOKEN
    if isinstance(content, dict):
        content = [content]
    parts, images = [], 0
    for c in content if isinstance(content, list) else []:
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, dict):
            if "image" in str(c.get("type", "")):
                images += 1
            elif isinstance(c.get("text"), str):
                parts.append(c["text"])
    text = "\n".join(parts)
    return text, len(text) / CHARS_PER_TOKEN + images * IMAGE_TOKENS


def _json_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for pos, line in enumerate(f, 1):
            try:
                yield pos, json.loads(line)
            except ValueError:
                continue


# ---------------------------------------------------------------- parsers

MAX_KEEP_CHARS = 200_000  # result text kept for dependency checks; sizes are measured on the full text


def parse_claude(path):
    """-> [main thread, sidechain thread]. Old versions logged subagent turns inline (isSidechain)."""
    main, side = Thread(path, "claude"), Thread(path, "claude")
    side.subagent = True
    state = {False: (main, {}, {}), True: (side, {}, {})}
    seg = 0
    for pos, d in _json_lines(path):
        if not isinstance(d, dict):
            continue
        typ = d.get("type")
        t, calls, pending = state[bool(d.get("isSidechain"))]
        for th in (main, side):
            th.cwd = th.cwd or d.get("cwd")
            th.session = th.session or d.get("sessionId")
        if typ == "system" and d.get("subtype") == "compact_boundary":
            seg += 1
        elif typ == "cost-state":
            main.cost_usd = d.get("totalCostUSD", main.cost_usd)
        elif typ == "assistant":
            m = d.get("message") or {}
            u = m.get("usage") or {}
            mid = m.get("id") or d.get("requestId") or d.get("uuid")
            call = calls.get(mid)
            if call is None:
                if not any(u.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                              "cache_creation_input_tokens")):
                    continue  # synthetic / errored message: no API call billed
                call = calls[mid] = Call(pos, seg)
                t.calls.append(call)
            cc = u.get("cache_creation") or {}
            c5m, c1h = cc.get("ephemeral_5m_input_tokens") or 0, cc.get("ephemeral_1h_input_tokens") or 0
            if not (c5m or c1h):
                c5m = u.get("cache_creation_input_tokens") or 0
            # streamed blocks of one response repeat the usage; keep the final (max) values
            call.fresh = max(call.fresh, u.get("input_tokens") or 0)
            call.cread = max(call.cread, u.get("cache_read_input_tokens") or 0)
            call.c5m, call.c1h = max(call.c5m, c5m), max(call.c1h, c1h)
            call.out = max(call.out, u.get("output_tokens") or 0)
            for c in m.get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    tu = ToolUse(c.get("id"), c.get("name"), c.get("input") or {}, pos)
                    tu.call = call
                    call.tools.append(tu)
                    t.uses.append(tu)
                    pending[tu.id] = tu
                elif c.get("type") == "text":
                    call.text_chars += len(c.get("text") or "")
        elif typ == "user":
            content = (d.get("message") or {}).get("content")
            if isinstance(content, str):
                if not d.get("isMeta") and not d.get("isCompactSummary"):
                    t.human_pos.append(pos)
                    t.notes.append((pos, content[:MAX_KEEP_CHARS]))
                continue
            for c in content if isinstance(content, list) else []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_result":
                    tu = pending.pop(c.get("tool_use_id"), None)
                    if tu is not None:
                        text, toks = measure(c.get("content"))
                        extra = d.get("toolUseResult") if tu.name == "Write" else None
                        tu.result = Result(tu, pos, seg, toks, text[:MAX_KEEP_CHARS], extra)
                        t.results.append(tu.result)
                elif c.get("type") == "text" and not d.get("isMeta"):
                    t.human_pos.append(pos)
                    t.notes.append((pos, str(c.get("text") or "")[:MAX_KEEP_CHARS]))
                    break
    return [main, side]


def parse_codex(path):
    t = Thread(path, "codex")
    pending, seg = {}, 0
    records, counts, last_total = [], [], None
    for pos, d in _json_lines(path):
        if not isinstance(d, dict):
            continue
        typ, p = d.get("type"), d.get("payload") or {}
        if not isinstance(p, dict):
            continue
        if typ == "session_meta":
            t.cwd = t.cwd or p.get("cwd")
            t.session = t.session or p.get("id") or p.get("session_id")
        elif typ == "turn_context":
            t.cwd = t.cwd or p.get("cwd")
        elif typ == "compacted":
            seg += 1
        elif typ == "token_usage_record" and isinstance(p.get("usage"), dict):
            records.append((pos, seg, p["usage"]))
        elif typ == "event_msg" and p.get("type") == "token_count" and isinstance(p.get("info"), dict):
            info = p["info"]
            total = json.dumps(info.get("total_token_usage"), sort_keys=True)
            if total != last_total and isinstance(info.get("last_token_usage"), dict):
                last_total = total
                counts.append((pos, seg, info["last_token_usage"]))
        elif typ == "event_msg" and p.get("type") == "user_message":
            t.human_pos.append(pos)
            t.notes.append((pos, str(p.get("message") or "")[:MAX_KEEP_CHARS]))
        elif typ == "response_item":
            pt = p.get("type")
            if pt in ("function_call", "custom_tool_call", "local_shell_call"):
                raw = p.get("arguments") if p.get("arguments") is not None else p.get("input", p.get("action"))
                inp = raw
                if isinstance(raw, str):
                    try:
                        inp = json.loads(raw)
                    except ValueError:
                        inp = raw
                name = p.get("name") or pt
                if p.get("namespace"):  # MCP tools: keep the server name ("mcp__server:tool")
                    name = f"{p['namespace']}:{name}"
                tu = ToolUse(p.get("call_id") or p.get("id"), name, inp, pos)
                t.uses.append(tu)
                pending[tu.id] = tu
            elif pt in ("function_call_output", "custom_tool_call_output", "local_shell_call_output"):
                tu = pending.pop(p.get("call_id"), None)
                if tu is not None:
                    text, toks = measure(p.get("output"))
                    tu.result = Result(tu, pos, seg, toks, text[:MAX_KEEP_CHARS])
                    t.results.append(tu.result)
            elif pt == "message" and p.get("role") == "assistant":
                t.uses.append(ToolUse(None, "__text__", sum(len(c.get("text") or "") for c in p.get("content") or []
                                                            if isinstance(c, dict)), pos))
    for pos, s, u in records or counts:  # newer rollouts log both; prefer the per-response records
        call = Call(pos, s)
        cached = u.get("cached_input_tokens") or 0
        call.cread = cached
        call.fresh = max(0, (u.get("input_tokens") or 0) - cached)
        call.out = u.get("output_tokens") or 0
        t.calls.append(call)
    # a response's tool calls are logged before its usage record: attach each to the next record
    starts = [c.pos for c in t.calls]
    for tu in list(t.uses):
        i = bisect.bisect_left(starts, tu.pos)
        call = t.calls[i] if i < len(t.calls) else None
        if tu.name == "__text__":
            t.uses.remove(tu)
            if call:
                call.text_chars += tu.input
            continue
        tu.call = call
        if call:
            call.tools.append(tu)
    return [t]


CODEX_TYPES = {"session_meta", "response_item", "event_msg", "turn_context", "compacted", "token_usage_record"}


def parse(path):
    """-> list of Threads in this transcript file."""
    for _, d in zip(range(5), (d for _, d in _json_lines(path))):
        if isinstance(d, dict) and "payload" in d and d.get("type") in CODEX_TYPES:
            return parse_codex(path)
    return parse_claude(path)


# ---------------------------------------------------------------- classification

def shell_command(inp):
    if isinstance(inp, str):
        return inp
    if not isinstance(inp, dict):
        return ""
    c = inp.get("command") or inp.get("cmd") or inp.get("code") or inp.get("input") or ""
    if isinstance(c, list):
        if len(c) >= 3 and str(c[0]).rsplit("/", 1)[-1] in ("bash", "sh", "zsh") and c[1] in ("-lc", "-c"):
            return str(c[2])
        return " ".join(map(str, c))
    return str(c)


def _main_segment(cmd):
    """First meaningful simple command: skips `cd x &&`, env assignments, `export`."""
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        seg = seg.split("|")[0].strip()
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in ("sudo", "time", "env")):
            words = words[1:]
        if words and words[0] not in ("cd", "export", "source", ".", "set", "echo", "pushd"):
            return words
    return []


def classify(tu):
    """-> (category, target, range) where category in read/search/shell/fetch/edit/subagent/other."""
    n, inp = tu.name.lower(), tu.input if isinstance(tu.input, dict) else {}
    if n in ("read", "read_file", "view_file"):
        path = inp.get("file_path") or inp.get("path") or inp.get("target_file") or ""
        return "read", path, (inp.get("offset") or inp.get("start_line"), inp.get("limit") or inp.get("end_line"))
    if n in ("grep", "glob", "ls", "search", "codebase_search", "grep_search", "file_search", "list_dir"):
        return "search", str(inp.get("pattern") or inp.get("query") or inp.get("path") or ""), None
    if n in EDIT_TOOLS:
        return "edit", inp.get("file_path") or inp.get("path") or shell_command(tu.input), None
    if n in ("webfetch", "websearch", "web_search", "fetch", "web_fetch") or "mcp" in n:
        return "fetch", str(inp.get("url") or inp.get("query") or tu.name), None
    if n in ("task", "agent", "spawn_agent"):
        return "subagent", str(inp.get("description") or ""), None
    if n in SHELL_TOOLS or "command" in inp or "cmd" in inp:
        cmd = shell_command(tu.input)
        words = _main_segment(cmd)
        head = words[0].rsplit("/", 1)[-1] if words else ""
        if head in READ_CMDS and len(words) > 1:
            files = [w for w in words[1:] if not w.startswith("-") and not re.match(r"^[0-9,]+p?$|^'?[0-9,]+p'?$", w)]
            return "read", files[-1] if files else "", cmd.strip()
        if head in SEARCH_CMDS or words[:2] == ["git", "grep"]:
            return "search", cmd, None
        return "shell", cmd, None
    return "other", tu.name, None


def _covers(prev, new):
    """Does an earlier read range include a later one? Ranges are (offset, limit) or a shell command."""
    if isinstance(prev, str) or isinstance(new, str):
        if isinstance(prev, str) and isinstance(new, str) and prev == new:
            return True
        return isinstance(prev, str) and _main_segment(prev)[:1] == ["cat"] and "|" not in prev
    po, pl = prev
    no, nl = new
    if pl is None and (po in (None, 0, 1)):
        return True
    if pl is None or nl is None:
        return False
    po, no = po or 1, no or 1
    return po <= no and po + pl >= no + nl


# ---------------------------------------------------------------- analysis

class Finding:
    __slots__ = ("kind", "thread", "tool", "label", "tokens", "avoidable", "later", "cost", "pos")

    def __init__(self, kind, thread, tool, label, tokens, avoidable, later, cost, pos):
        self.kind, self.thread, self.tool, self.label = kind, thread, tool, label
        self.tokens, self.avoidable, self.later, self.cost, self.pos = tokens, avoidable, later, cost, pos


def weights(t):
    w = dict(WEIGHTS[t.agent])
    if t.agent == "claude":
        c5, c1 = sum(c.c5m for c in t.calls), sum(c.c1h for c in t.calls)
        w["enter"] = (1.25 * c5 + 2.0 * c1) / (c5 + c1) if c5 + c1 else 1.25
    return w


def call_cost(t, c, w):
    if t.agent == "claude":
        return c.fresh + 1.25 * c.c5m + 2.0 * c.c1h + w["read"] * c.cread + w["out"] * c.out
    return c.fresh + w["read"] * c.cread + w["out"] * c.out


def analyze(t):
    """-> (findings, total cost units) for one thread."""
    w = weights(t)
    by_seg = {}
    for c in t.calls:
        by_seg.setdefault(c.seg, []).append(c.pos)

    def later(pos, seg):
        ps = by_seg.get(seg, [])
        return len(ps) - bisect.bisect_right(ps, pos)

    findings = []

    def add(kind, tu, label, tokens, avoidable, pos, seg, enter_w=None, cost=None):
        n = later(pos, seg)
        if cost is None:
            cost = avoidable * ((enter_w if enter_w is not None else w["enter"]) + n * w["read"])
        if cost > 0:
            findings.append(Finding(kind, t, tu.name if tu else "reply", label, tokens, avoidable, n, cost, pos))

    # events in transcript order: edits invalidate earlier reads
    reads, seen_calls = {}, {}
    for tu in sorted(t.uses, key=lambda u: u.pos):
        cat, target, rng = classify(tu)
        r = tu.result
        if cat == "edit":
            for p in re.findall(r"\*\*\* (?:Update|Add|Delete) File: (.+)", target) or [target]:
                reads.pop(_norm(p.strip(), t.cwd), None)
            if r and isinstance(r.extra, dict) and tu.name.lower() == "write" and r.extra.get("originalFile"):
                content = (tu.input or {}).get("content") or ""
                toks = len(content) / CHARS_PER_TOKEN
                changed = sum(len(line) for h in r.extra.get("structuredPatch") or [] if isinstance(h, dict)
                              for line in h.get("lines") or [] if line[:1] in "+-") / CHARS_PER_TOKEN
                if toks > KINDS["rewrite"][0] and changed < 0.5 * toks:
                    add("rewrite", tu, target, toks, toks - changed, tu.pos, r.seg, enter_w=w["out"])
            continue
        if cat == "shell":
            if MUTATES_ALL.search(target):
                reads.clear()
            else:
                for p in [p for p in reads if os.path.basename(p) and os.path.basename(p) in target]:
                    reads.pop(p)
        if r is None:
            continue
        if r.text.startswith("Wasted call") or "file unchanged since your last Read" in r.text[:200]:
            single = tu.call is not None and len(tu.call.tools) == 1
            nxt = _next_call(t, tu.call)
            cost = nxt.ctx_in * w["read"] if single and nxt else 0
            add("wasted-call", tu, target, r.tokens, r.tokens, r.pos, r.seg, cost=cost or None)
            continue
        if cat == "read" and target:
            key, body = _norm(target, t.cwd), _body(r.text)
            prev = reads.get(key)
            # a leak only if we got back what was already in context; different text = the file changed
            same = bool(prev) and prev[0] == r.seg and _covers(prev[1], rng) and bool(body) and body in prev[2]
            if same and r.tokens >= 50:
                add("re-read", tu, target, r.tokens, r.tokens, r.pos, r.seg)
                continue
            if not same:
                reads[key] = (r.seg, rng, body)
        elif cat in ("search", "fetch", "subagent", "other"):
            # identical call AND identical answer: pure repeat (stateful tools legitimately differ)
            sig = (tu.name, json.dumps(tu.input, sort_keys=True, default=str))
            prev = seen_calls.get(sig)
            digest = hash(_body(r.text))
            if prev == (r.seg, digest) and r.tokens >= 50:
                add("wasted-call", tu, target, r.tokens, r.tokens, r.pos, r.seg)
                continue
            seen_calls[sig] = (r.seg, digest)
        kind = SIZE_KIND.get(cat)
        if kind:
            flag, budget, _ = KINDS[kind]
            if r.tokens > flag:
                add(kind, tu, target, r.tokens, r.tokens - budget, r.pos, r.seg)

    # serial round-trips: call a then call b, one read/search each, where b's target was already
    # known before a was issued and nothing in a's result points to it -> could have been one turn
    human, known, ei = t.human_pos, set(), 0
    texts = sorted([(r.pos, r.text) for r in t.results] + t.notes, key=lambda x: x[0])
    for a, b in zip(t.calls, t.calls[1:]):
        while ei < len(texts) and texts[ei][0] < a.pos:
            known.update(WORD.findall(texts[ei][1]))
            ei += 1
        if a.seg != b.seg or len(a.tools) != 1 or len(b.tools) != 1:
            continue
        ta, tb = a.tools[0], b.tools[0]
        ca, tga, _ = classify(ta)
        cb, tgb, _ = classify(tb)
        if ca not in ("read", "search") or cb not in ("read", "search") or not ta.result:
            continue
        if bisect.bisect_left(human, a.pos) != bisect.bisect_left(human, b.pos):
            continue  # the user spoke in between
        key = _serial_key(cb, tgb)
        if not key or key not in known or (ca == cb == "read" and tga == tgb):
            continue
        if key.rsplit(".", 1)[0] in ta.result.text:
            continue  # b plausibly follows from what a returned
        if any(n in ta.result.text for n in re.findall(r"\d{2,}", json.dumps(tb.input, default=str))):
            continue  # e.g. `sed -n 153,160p` / offset taken from a's line numbers
        add("serial-call", tb, tgb, 0, 0, b.pos, b.seg, cost=b.cread * w["read"])

    flag, budget, _ = KINDS["verbose-reply"]
    for c in t.calls:
        toks = c.text_chars / CHARS_PER_TOKEN
        if toks > flag:
            add("verbose-reply", None, "", toks, toks - budget, c.pos, c.seg, enter_w=w["out"])

    return findings, sum(call_cost(t, c, w) for c in t.calls)


WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def _body(text):
    """Result text without harness-injected reminders, for content comparisons."""
    return REMINDER.sub("", text or "").strip()


def _serial_key(cat, target):
    if cat == "read":
        return os.path.basename(str(target).rstrip("/"))
    words = [w for w in re.findall(r"[A-Za-z0-9_]{4,}", str(target)) if w not in ("grep", "find", "head", "tail")]
    return max(words, key=len) if words else ""


def _next_call(t, call):
    if call is None:
        return None
    i = t.calls.index(call)
    return t.calls[i + 1] if i + 1 < len(t.calls) else None


def _norm(path, cwd):
    if not path:
        return ""
    path = os.path.expanduser(str(path))
    if cwd and not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return os.path.normpath(path)


# ---------------------------------------------------------------- discovery

def roots():
    claude = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")
    codex = os.path.join(os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex"), "sessions")
    return {"claude": claude, "codex": codex}


def find_files(paths, agent, since):
    out = []
    targets = paths or [r for a, r in roots().items() if agent in ("all", a)]
    for root in targets:
        if os.path.isfile(root):
            out.append(root)
            continue
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".jsonl"):
                    p = os.path.join(dirpath, f)
                    try:
                        if os.path.getmtime(p) >= since:
                            out.append(p)
                    except OSError:
                        pass
    return out


def parse_since(s):
    if not s or s == "all":
        return 0.0
    m = re.fullmatch(r"(\d+)([hdw])", s)
    if m:
        return time.time() - int(m.group(1)) * {"h": 3600, "d": 86400, "w": 604800}[m.group(2)]
    return datetime.fromisoformat(s).timestamp()  # naive dates = local time


# ---------------------------------------------------------------- report

def fmt(n):
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


def pct_str(p):
    return f"{p:.1f}%" if p >= 0.1 else f"{p:.2f}%" if p >= 0.01 else "<0.01%"


def grade(pct):
    for g, lim in (("A", 5), ("B", 10), ("C", 20), ("D", 30)):
        if pct < lim:
            return g
    return "F"


class Style:
    def __init__(self, on):
        self.on = on

    def __call__(self, code, s):
        return f"\033[{code}m{s}\033[0m" if self.on else str(s)


_INSTR_CACHE = {}


def always_loaded(agent, cwd):
    """Instruction files the agent loads into every call for this working dir: [(path, tokens)]."""
    key = (agent, cwd)
    if key in _INSTR_CACHE:
        return _INSTR_CACHE[key]
    home = os.path.expanduser("~")
    if agent == "claude":
        cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
        cands = [os.path.join(cfg, "CLAUDE.md")]
        names = ("CLAUDE.md", "CLAUDE.local.md", os.path.join(".claude", "CLAUDE.md"))
        if cwd:
            cands.append(os.path.join(roots()["claude"], re.sub(r"[^A-Za-z0-9]", "-", cwd), "memory", "MEMORY.md"))
    else:
        cands = [os.path.join(os.environ.get("CODEX_HOME") or os.path.join(home, ".codex"), "AGENTS.md")]
        names = ("AGENTS.md", "AGENTS.override.md")
    d = cwd
    while d:
        cands += [os.path.join(d, n) for n in names]
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    out, seen = [], set()
    for f in cands:
        real = os.path.realpath(f)
        if real in seen or not os.path.isfile(f):
            continue
        seen.add(real)
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                size = len(fh.read()) / CHARS_PER_TOKEN
            if size >= 1:
                out.append((f, size))
        except OSError:
            pass
    _INSTR_CACHE[key] = out
    return out


def project_name(t):
    return os.path.basename((t.cwd or "").rstrip("/")) or "?"


def run(args):
    since = 0.0 if args.paths and args.since is None else parse_since(args.since or "7d")
    files = find_files(args.paths, args.agent, since)
    here = os.path.realpath(os.getcwd())
    threads = []
    parsed = []
    for f in files:
        try:
            parsed += parse(f)
        except (OSError, UnicodeError) as e:
            print(f"tokenleak: skipping {f}: {e}", file=sys.stderr)
    for t in parsed:
        f = t.path
        if not t.calls:
            continue
        if args.here or args.current:
            cwd = os.path.realpath(t.cwd) if t.cwd else ""
            if not (cwd == here or cwd.startswith(here + os.sep)):
                continue
        if args.project and args.project.lower() not in (t.cwd or "").lower():
            continue
        if args.session and args.session not in (t.session or "") and args.session not in f:
            continue
        threads.append(t)
    if args.current and threads:
        latest = max((t for t in threads if not t.subagent), key=lambda t: t.mtime, default=None)
        threads = [t for t in threads if latest and t.session == latest.session]

    findings, units, sess, loaded, firsts, base_cost = [], 0.0, {}, {}, [], 0.0
    for t in threads:
        fs, u = analyze(t)
        if not t.subagent:
            w = weights(t)
            n, nseg = len(t.calls), len({c.seg for c in t.calls})
            firsts.append(t.calls[0].ctx_in)
            base_cost += t.calls[0].ctx_in * (nseg * w["enter"] + (n - nseg) * w["read"])
            for f, toks in always_loaded(t.agent, t.cwd):
                e = loaded.setdefault(f, {"tokens": toks, "cost": 0.0, "sessions": 0})
                e["cost"] += toks * (nseg * w["enter"] + (n - nseg) * w["read"])
                e["sessions"] += 1
        findings += fs
        units += u
        key = (t.agent, t.session or t.path)
        s = sess.setdefault(key, {"units": 0.0, "leak": 0.0, "usd": None})
        s["units"] += u
        s["leak"] += sum(f.cost for f in fs)
        if t.cost_usd is not None:
            s["usd"] = max(s["usd"] or 0, t.cost_usd)
        for c in t.calls:  # free memory early: transcripts can be huge
            c.tools = []
        for r in t.results:
            r.text = ""
    leak = sum(f.cost for f in findings)
    pct = 100 * leak / units if units else 0.0
    usd_total = sum(s["usd"] for s in sess.values() if s["usd"])
    usd_leak = sum(s["usd"] * s["leak"] / s["units"] for s in sess.values() if s["usd"] and s["units"])
    totals = {
        "threads": len(threads),
        "sessions": len(sess),
        "claude_sessions": sum(1 for a, _ in sess if a == "claude"),
        "codex_sessions": sum(1 for a, _ in sess if a == "codex"),
        "api_calls": sum(len(t.calls) for t in threads),
        "context_tokens": sum(c.ctx_in for t in threads for c in t.calls),
        "cache_read_tokens": sum(c.cread for t in threads for c in t.calls),
        "cache_write_tokens": sum(c.c5m + c.c1h for t in threads for c in t.calls),
        "fresh_tokens": sum(c.fresh for t in threads for c in t.calls),
        "output_tokens": sum(c.out for t in threads for c in t.calls),
        "cost_units": units,
        "leak_units": leak,
        "leak_pct": pct,
        "grade": grade(pct),
        "usd_total": usd_total or None,
        "usd_leak": usd_leak or None,
        "avg_first_call_context": sum(firsts) / len(firsts) if firsts else 0,
        "base_context_pct": 100 * base_cost / units if units else 0,
        "always_loaded": sorted(({"path": f, **e} for f, e in loaded.items()), key=lambda e: -e["cost"]),
    }
    by_kind = {}
    for f in findings:
        k = by_kind.setdefault(f.kind, {"count": 0, "avoidable_tokens": 0.0, "cost": 0.0})
        k["count"] += 1
        k["avoidable_tokens"] += f.avoidable
        k["cost"] += f.cost
    findings.sort(key=lambda f: -f.cost)
    return totals, by_kind, findings, since


def label_of(f, redact):
    if f.kind == "verbose-reply":
        return "assistant reply"
    if redact:
        return f.tool
    lab = re.sub(r"\s+", " ", str(f.label)).strip()
    home = os.path.expanduser("~")
    lab = lab.replace(home, "~")
    return f"{f.tool} {lab}" if lab and lab != f.tool else f.tool


def print_report(totals, by_kind, findings, since, args, out=None):
    out = out or sys.stdout
    st = Style((out.isatty() or bool(os.environ.get("FORCE_COLOR"))) and not args.no_color
               and not os.environ.get("NO_COLOR"))
    w = out.write
    if not totals["threads"]:
        w("tokenleak: no transcripts found for this filter. Try --since 30d, --agent all, or pass a path.\n")
        return
    src = ", ".join(x for x in (f"{totals['claude_sessions']} Claude Code" if totals["claude_sessions"] else "",
                                f"{totals['codex_sessions']} Codex" if totals["codex_sessions"] else "") if x)
    when = datetime.fromtimestamp(since).strftime("%Y-%m-%d") if since else "the beginning"
    w(f"\n{st('1', 'tokenleak')} {__version__}  {st('2', '·')}  {totals['sessions']} session{'s' * (totals['sessions'] != 1)} ({src})  "
      f"{st('2', '·')}  {fmt(totals['api_calls'])} API calls  {st('2', '·')}  since {when}\n\n")
    w(f"  context processed  {st('1', fmt(totals['context_tokens']))} tokens  "
      f"{st('2', '(cache reads ' + fmt(totals['cache_read_tokens']) + ' · writes ' + fmt(totals['cache_write_tokens']) + ' · fresh ' + fmt(totals['fresh_tokens']) + ')')}"
      f"   output {fmt(totals['output_tokens'])}\n")
    if totals["usd_total"]:
        w(f"  spend              ≈ ${totals['usd_total']:,.2f} API-equivalent {st('2', '(Claude Code sessions, its own pricing)')}\n")
    pct, g = totals["leak_pct"], totals["grade"]
    color = {"A": "32", "B": "32", "C": "33", "D": "31", "F": "31"}[g]
    money = f"   ≈ ${totals['usd_leak']:,.2f} avoidable" if totals["usd_leak"] else ""
    w(f"\n  {st('1', 'LEAK SCORE')}  {st('1;' + color, f'{pct:.1f}%')}  grade {st('1;' + color, g)}{money}"
      f"   {st('2', 'share of token cost spent on avoidable context (A <5 · B <10 · C <20 · D <30)')}\n\n")
    if not by_kind:
        w("  No leaks found. Your agent is lean.\n\n")
        return
    w(st("2", f"  {'leak':<14}{'count':>7}{'avoidable':>12}{'of cost':>9}   fix\n"))
    for kind, k in sorted(by_kind.items(), key=lambda kv: -kv[1]["cost"]):
        share = 100 * k["cost"] / totals["cost_units"] if totals["cost_units"] else 0
        avoid = fmt(k["avoidable_tokens"]) if k["avoidable_tokens"] else "—"
        w(f"  {kind:<14}{k['count']:>7}{avoid:>12}{share:>8.1f}%   {st('2', KINDS[kind][2])}\n")
    if totals["always_loaded"] or totals["avg_first_call_context"]:
        w(f"\n  {st('1', 'always loaded')}  ~{totals['base_context_pct']:.0f}% of cost  "
          f"{st('2', 'avg ' + fmt(totals['avg_first_call_context']) + ' tokens before the first tool call (system prompt, tools, MCP, files below), re-sent on every call; not counted as leaks')}\n")
        home = os.path.expanduser("~")
        for e in totals["always_loaded"][:5]:
            share = pct_str(100 * e["cost"] / totals["cost_units"] if totals["cost_units"] else 0)
            path = e["path"] if not args.redact else os.path.basename(e["path"])
            path = path.replace(home, "~")
            path = path if len(path) <= 60 else "…" + path[-59:]
            w(f"  {share:>7}  {path:<60} {st('2', fmt(e['tokens']) + ' tok (current size)')}\n")
    w(f"\n  {st('1', 'top leaks')}\n")
    width = 58
    for i, f in enumerate(findings[: args.top], 1):
        share = pct_str(100 * f.cost / totals["cost_units"] if totals["cost_units"] else 0)
        lab = label_of(f, args.redact)
        lab = lab if len(lab) <= width else lab[: width - 1] + "…"
        if f.kind == "serial-call":
            size = "extra round-trip"
        else:
            size = f"{fmt(f.tokens)} tok" + (f" × {f.later} later calls" if f.later else "")
        where = "" if args.redact else f"{project_name(f.thread)} · {(f.thread.session or '')[:8]}"
        w(f"  {i:>2}  {share:>6}  {st('33', f'{f.kind:<13}')} {lab:<{width}}  {st('2', size)}  {st('2', where)}\n")
    w(st("2", "\n  estimates: tokens ≈ chars/4 · avoidable = size above a sane budget, priced on every later call that"
              "\n  re-sent it (cache read 0.1x, write 1.25-2x, output 5x) · everything stays on this machine\n"))
    w(f"\n  Plug the leaks: {REPO}\n\n")


def print_share(totals, by_kind, out=None):
    out = out or sys.stdout
    top = [k for k, _ in sorted(by_kind.items(), key=lambda kv: -kv[1]["cost"])][:3]
    rows = [
        f"tokenleak · {totals['sessions']} sessions · {fmt(totals['context_tokens'])} context tokens",
        f"Leak score {totals['leak_pct']:.1f}% (grade {totals['grade']})"
        + (f" · ≈ ${totals['usd_leak']:,.0f} avoidable" if totals["usd_leak"] else ""),
        "Top leaks: " + (", ".join(top) if top else "none"),
        REPO.replace("https://", ""),
    ]
    width = max(len(r) for r in rows) + 2
    out.write("╭" + "─" * width + "╮\n")
    for r in rows:
        out.write("│ " + r.ljust(width - 1) + "│\n")
    out.write("╰" + "─" * width + "╯\n")


def to_json(totals, by_kind, findings, args):
    if args.redact:
        totals = dict(totals, always_loaded=[dict(e, path=os.path.basename(e["path"])) for e in totals["always_loaded"]])
    return {
        "version": __version__,
        "totals": totals,
        "by_kind": by_kind,
        "findings": [{
            "kind": f.kind, "tool": f.tool, "label": None if args.redact else label_of(f, False),
            "tokens": round(f.tokens), "avoidable_tokens": round(f.avoidable), "later_calls": f.later,
            "cost_units": round(f.cost, 1),
            "share_pct": round(100 * f.cost / totals["cost_units"], 3) if totals["cost_units"] else 0,
            "agent": f.thread.agent, "session": f.thread.session,
            "project": None if args.redact else f.thread.cwd, "line": f.pos,
        } for f in findings[: args.top if args.top else None]],
    }


def print_rules(out=None):
    out = out or sys.stdout
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = text.split("\n---\n", 1)
    out.write(parts[1].lstrip() if text.startswith("---") and len(parts) == 2 else text)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tokenleak",
        description="Find where your coding agent leaks context tokens (Claude Code + Codex transcripts). "
                    "Local and read-only.",
        epilog="`tokenleak rules` prints the rules to paste into AGENTS.md / CLAUDE.md / .cursorrules.")
    ap.add_argument("paths", nargs="*", help="transcript files or folders (default: ~/.claude/projects, ~/.codex/sessions)")
    ap.add_argument("--since", help="window: 24h, 7d (default), 4w, 2026-10-01, or all")
    ap.add_argument("--agent", choices=("all", "claude", "codex"), default="all")
    ap.add_argument("--here", action="store_true", help="only sessions started in this directory (or below)")
    ap.add_argument("--current", action="store_true", help="only the most recent session in this directory")
    ap.add_argument("--project", help="only sessions whose working dir contains this text")
    ap.add_argument("--session", help="only this session id (prefix ok)")
    ap.add_argument("--top", type=int, default=10, help="how many individual leaks to list (default 10)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--share", action="store_true", help="small anonymized card to share")
    ap.add_argument("--redact", action="store_true", help="hide commands, paths and project names")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=f"tokenleak {__version__}")
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["rules"]:
        print_rules()
        return 0
    if argv[:1] == ["hook"]:  # Claude Code / Codex lifecycle hook: inject the rules as context
        buf = io.StringIO()
        print_rules(buf)
        event = argv[1] if len(argv) > 1 else "SessionStart"
        json.dump({"hookSpecificOutput": {"hookEventName": event, "additionalContext": buf.getvalue()}}, sys.stdout)
        return 0
    if argv[:1] == ["audit"]:
        argv = argv[1:]
    args = ap.parse_args(argv)
    totals, by_kind, findings, since = run(args)
    if args.json:
        json.dump(to_json(totals, by_kind, findings, args), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    elif args.share:
        print_share(totals, by_kind)
    else:
        print_report(totals, by_kind, findings, since, args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
