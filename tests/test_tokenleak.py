"""Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "tokenleak", "scripts"))
import tokenleak as T  # noqa: E402

APP = "".join(f"{i:>6}\tline {i} of app.py " + "x" * 60 + "\n" for i in range(1, 300))  # ~20k chars
APP2 = APP.replace("line 7 ", "line 7 EDITED ")


def assistant(mid, usage, *blocks):
    return [{"type": "assistant", "sessionId": "s1", "cwd": "/proj",
             "message": {"id": mid, "usage": usage, "content": [b]}} for b in blocks]


def tool_use(tid, name, inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def result(tid, content, extra=None):
    d = {"type": "user", "sessionId": "s1", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": content}]}}
    if extra:
        d["toolUseResult"] = extra
    return d


def u(cread=0, c5m=0, out=50):
    return {"input_tokens": 10, "cache_read_input_tokens": cread, "cache_creation_input_tokens": c5m,
            "cache_creation": {"ephemeral_5m_input_tokens": c5m, "ephemeral_1h_input_tokens": 0},
            "output_tokens": out}


def claude_session():
    lines = [{"type": "user", "sessionId": "s1", "cwd": "/proj",
              "message": {"role": "user", "content": "Fix the bug in app.py. utils.py may matter too."}}]
    # m1 is streamed as two lines (thinking + tool_use) sharing one usage: must count once
    lines += assistant("m1", u(c5m=20000), {"type": "thinking", "thinking": "..."},
                       tool_use("t1", "Read", {"file_path": "/proj/app.py"}))
    lines.append(result("t1", APP))                                      # big read
    lines += assistant("m2", u(cread=25000), tool_use("t2", "Read", {"file_path": "/proj/utils.py"}))
    lines.append(result("t2", "def util():\n    pass\n"))                  # serial: utils.py known from prompt
    lines += assistant("m3", u(cread=26000), tool_use("t3", "Bash", {"command": "cd /proj && npm test"}))
    lines.append(result("t3", "PASS test\n" * 1200))                     # noisy shell, 12k chars
    lines += assistant("m4", u(cread=30000), tool_use("t4", "Read", {"file_path": "/proj/app.py"}))
    lines.append(result("t4", APP + "<system-reminder>be careful</system-reminder>"))  # true re-read
    lines += assistant("m5", u(cread=36000), tool_use("t5", "Edit", {"file_path": "/proj/app.py"}))
    lines.append(result("t5", "ok"))
    lines += assistant("m6", u(cread=36100), tool_use("t6", "Read", {"file_path": "/proj/app.py"}))
    lines.append(result("t6", APP2))                                     # changed file: not a re-read
    lines.append({"type": "system", "subtype": "compact_boundary"})
    lines += assistant("m7", u(c5m=8000), tool_use("t7", "Read", {"file_path": "/proj/app.py"}))
    lines.append(result("t7", APP2))                                     # after compaction: not a re-read
    lines += assistant("m8", u(cread=14000, out=3000), {"type": "text", "text": "y" * 10000})  # verbose
    lines.append({"type": "cost-state", "sessionId": "s1", "totalCostUSD": 2.0})
    return lines


def codex_session():
    meta = {"type": "session_meta", "payload": {"id": "c1", "cwd": "/proj"}}
    big = "row\n" * 6000  # 24k chars

    def call(cid, cmd):
        return {"type": "response_item", "payload": {"type": "function_call", "name": "shell", "call_id": cid,
                                                       "arguments": json.dumps({"command": ["bash", "-lc", cmd]})}}

    def out(cid, text):
        return {"type": "response_item", "payload": {"type": "function_call_output", "call_id": cid, "output": text}}

    def rec(inp, cached):
        return {"type": "token_usage_record", "payload": {"usage": {
            "input_tokens": inp, "cached_input_tokens": cached, "output_tokens": 40}}}

    def count(inp):  # older event: must be ignored when records exist
        return {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "total_token_usage": {"total_tokens": inp}, "last_token_usage": {"input_tokens": inp}}}}

    return [meta,
            {"type": "event_msg", "payload": {"type": "user_message", "message": "why is data.csv slow?"}},
            call("k1", "cat data.csv"), rec(9000, 0), count(9000), out("k1", big),
            call("k2", "cat data.csv"), rec(16000, 9000), count(16000), out("k2", big),
            call("k3", "wc -l data.csv"), rec(23000, 16000), out("k3", "6000 data.csv"),
            {"type": "compacted", "payload": {"message": ""}},
            call("k4", "cat data.csv"), rec(5000, 0), out("k4", big),
            rec(11000, 5000)]


def write_jsonl(path, lines):
    with open(path, "w") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")


class TokenleakTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.claude = os.path.join(self.dir, "claude.jsonl")
        self.codex = os.path.join(self.dir, "rollout-codex.jsonl")
        write_jsonl(self.claude, claude_session())
        write_jsonl(self.codex, codex_session())

    def kinds(self, path):
        (t, *_) = [t for t in T.parse(path) if t.calls]
        findings, units = T.analyze(t)
        return t, findings, units

    def test_claude_usage_is_counted_once_per_response(self):
        t, _, _ = self.kinds(self.claude)
        self.assertEqual(len(t.calls), 8)
        self.assertEqual(t.calls[0].c5m, 20000)
        self.assertEqual(t.cost_usd, 2.0)

    def test_claude_detectors(self):
        _, fs, _ = self.kinds(self.claude)
        kinds = sorted(f.kind for f in fs)
        self.assertEqual(kinds.count("re-read"), 1, kinds)          # t4 only: t6 changed, t7 after compaction
        self.assertEqual(kinds.count("big-read"), 2, kinds)         # t1, t7; t6 is never re-sent (compaction follows)
        self.assertEqual(kinds.count("serial-call"), 1, kinds)      # t2: utils.py known from the prompt
        self.assertEqual(kinds.count("noisy-shell"), 1, kinds)
        self.assertEqual(kinds.count("verbose-reply"), 1, kinds)
        self.assertNotIn("wasted-call", kinds)

    def test_context_tax_counts_later_calls_until_compaction(self):
        _, fs, _ = self.kinds(self.claude)
        first = next(f for f in fs if f.kind == "big-read")
        self.assertEqual(first.later, 5)                            # m2..m6, then compaction
        self.assertAlmostEqual(first.avoidable, len(APP) / 4 - 2000)
        # the first later call writes it to the cache (1.25x), the 4 after it read it (0.1x each)
        self.assertAlmostEqual(first.cost, first.avoidable * (1.25 + 4 * 0.1))
        serial = next(f for f in fs if f.kind == "serial-call")
        self.assertAlmostEqual(serial.cost, 25000 * 0.1)

    def test_codex(self):
        t, fs, _ = self.kinds(self.codex)
        self.assertEqual(len(t.calls), 5)                           # records only, token_count ignored
        kinds = sorted(f.kind for f in fs)
        self.assertEqual(kinds.count("re-read"), 1, kinds)          # k2; k4 is after compaction
        self.assertEqual(kinds.count("big-read"), 2, kinds)         # k1, k4
        self.assertEqual(t.calls[1].cread, 9000)
        self.assertEqual(t.calls[1].fresh, 7000)

    def test_classify_shell(self):
        tu = T.ToolUse("x", "Bash", {"command": "cd src && FOO=1 sed -n '10,40p' lib/a.py | head"}, 1)
        self.assertEqual(T.classify(tu)[:2], ("read", "lib/a.py"))
        tu = T.ToolUse("x", "Bash", {"command": "rg -n handler src/"}, 1)
        self.assertEqual(T.classify(tu)[0], "search")
        tu = T.ToolUse("x", "Bash", {"command": "npm run build"}, 1)
        self.assertEqual(T.classify(tu)[0], "shell")

    def test_covers(self):
        self.assertTrue(T._covers((None, None), (100, 20)))
        self.assertTrue(T._covers((1, 200), (50, 20)))
        self.assertFalse(T._covers((50, 20), (None, None)))
        self.assertFalse(T._covers((1, 40), (30, 20)))

    def test_cli_end_to_end(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([self.dir, "--json", "--since", "all"])
        data = json.loads(buf.getvalue())
        self.assertEqual(data["totals"]["sessions"], 2)
        self.assertGreater(data["totals"]["leak_pct"], 0)
        self.assertEqual(data["totals"]["usd_total"], 2.0)
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([self.dir, "--since", "all", "--no-color", "--redact"])
        out = buf.getvalue()
        self.assertIn("LEAK SCORE", out)
        self.assertNotIn("/proj", out)

    def test_compare_splits_sessions_by_start_date(self):
        old, new = claude_session(), claude_session()
        for d in old:
            d["timestamp"] = "2026-01-02T10:00:00.000Z"
        for d in new:
            d["timestamp"] = "2026-02-02T10:00:00.000Z"
            d["sessionId"] = "s2"
        d2 = tempfile.mkdtemp()
        write_jsonl(os.path.join(d2, "old.jsonl"), old)
        write_jsonl(os.path.join(d2, "new.jsonl"), new)
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([d2, "--compare", "2026-01-15", "--since", "all", "--json"])
        data = json.loads(buf.getvalue())
        self.assertEqual(data["before"]["sessions"], 1)
        self.assertEqual(data["after"]["sessions"], 1)
        self.assertAlmostEqual(data["before"]["leak_pct"], data["after"]["leak_pct"])

    def test_statusline(self):
        buf = io.StringIO()
        T.statusline(io.StringIO(json.dumps({"transcript_path": self.claude})), buf)
        line = buf.getvalue()
        self.assertIn("leak ", line)
        self.assertIn("ctx ", line)
        buf = io.StringIO()
        T.statusline(io.StringIO("{}"), buf)
        self.assertEqual(buf.getvalue(), "tokenleak\n")

    def test_command_family_and_advice(self):
        self.assertEqual(T.command_family('cd /p && FOO=1 npx vitest run src/a.test.ts'), "npx vitest run")
        self.assertEqual(T.command_family("npm run build -- --watch"), "npm run build")
        self.assertEqual(T.command_family("python3 -m pytest tests/ -x"), "python3 -m pytest")
        self.assertEqual(T.command_family("npx vitest src/a.test.ts"), "npx vitest")
        self.assertEqual(T.command_family("docker compose up -d"), "docker compose up")
        self.assertTrue(T.is_project_command("npm test", "npm test"))
        self.assertFalse(T.is_project_command("for f in *; do wc -l $f; done", "for"))
        self.assertFalse(T.is_project_command("python3 <<EOF", "python3 <<EOF"))
        self.assertIn("pytest -q -x", T.quiet_advice("pytest"))
        self.assertIn("git status -s", T.quiet_advice("git status"))
        self.assertIn('${TMPDIR:-/tmp}', T.quiet_advice("npm run build"))

    def test_suggest_project_rules(self):
        proj = tempfile.mkdtemp()
        big = os.path.join(proj, "catalog.py")
        with open(big, "w") as f:
            f.write(APP)
        lines = [{"type": "user", "sessionId": "p1", "cwd": proj, "message": {"role": "user", "content": "go"}}]
        for k in range(2):
            lines += assistant(f"t{k}", u(cread=20000), tool_use(f"b{k}", "Bash", {"command": f"cd {proj} && npm test"}))
            lines.append(result(f"b{k}", "PASS a test\n" * 1500))
            lines += assistant(f"r{k}", u(cread=30000), tool_use(f"r{k}", "Read", {"file_path": big}))
            lines.append(result(f"r{k}", APP))
            lines += assistant(f"x{k}", u(cread=31000), tool_use(f"x{k}", "Bash", {"command": "cat /tmp/elsewhere.txt"}))
            lines.append(result(f"x{k}", "z" * 30000))
        for d in lines:
            d["cwd"] = proj
        path = os.path.join(self.dir, "proj.jsonl")
        write_jsonl(path, lines)
        threads = [t for t in T.parse(path) if t.calls]
        buf = io.StringIO()
        T.suggest(threads, buf)
        out = buf.getvalue()
        self.assertIn("## Token hygiene for this repo", out)
        self.assertIn("`npm test`", out)
        self.assertIn("--silent", out)
        self.assertIn("`catalog.py`", out)
        self.assertNotIn("elsewhere", out)

    def test_html_report(self):
        out = os.path.join(self.dir, "r.html")
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([self.dir, "--since", "all", "--no-color", "--html", out, "--redact"])
        page = open(out, encoding="utf-8").read()
        self.assertIn("Leak score", page)
        self.assertIn("big-read", page)
        self.assertNotIn("/proj", page)  # --redact hides paths in the report too

    def test_malformed_tool_inputs_do_not_crash(self):
        lines = [{"type": "user", "sessionId": "m1", "cwd": "/p", "message": {"role": "user", "content": "go"}}]
        lines += assistant("a1", u(c5m=9000), tool_use("x1", "Read", {"file_path": "/p/a.py", "offset": [1, 2], "limit": "x"}))
        lines.append(result("x1", APP))
        lines += assistant("a2", u(cread=12000), tool_use("x2", "Edit", {"file_path": ["/p/a.py"]}))
        lines.append(result("x2", "ok"))
        lines += assistant("a3", u(cread=13000), tool_use("x3", "Read", {"file_path": "/p/a.py", "offset": [3]}))
        lines.append(result("x3", APP))
        path = os.path.join(self.dir, "bad.jsonl")
        write_jsonl(path, lines)
        totals, _, _ = T.summarize([t for t in T.parse(path) if t.calls])
        self.assertEqual(totals["api_calls"], 3)

    def test_codex_subagent_rollout_joins_its_parent(self):
        lines = [{"type": "session_meta", "payload": {"id": "child", "cwd": "/p",
                  "source": {"subagent": {"thread_spawn": {"parent_thread_id": "parent-1"}}}}},
                 {"type": "token_usage_record", "payload": {"usage": {"input_tokens": 100, "output_tokens": 5}}}]
        path = os.path.join(self.dir, "rollout-child.jsonl")
        write_jsonl(path, lines)
        (t,) = T.parse(path)
        self.assertTrue(t.subagent)
        self.assertEqual(t.session, "parent-1")

    def test_since_counts_only_calls_inside_the_window(self):
        lines = claude_session()
        stamps = iter(["2026-01-01T10:00:00.000Z"] * 8 + ["2026-03-01T10:00:00.000Z"] * 100)
        for d in lines:
            if d["type"] == "assistant":
                d["timestamp"] = next(stamps)
        # make the 4 last responses recent
        recent = [d for d in lines if d["type"] == "assistant"][-4:]
        for d in recent:
            d["timestamp"] = "2026-03-01T10:00:00.000Z"
        path = os.path.join(self.dir, "win", "s.jsonl")
        os.makedirs(os.path.dirname(path))
        write_jsonl(path, lines)
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([os.path.dirname(path), "--since", "2026-02-01", "--json"])
        self.assertEqual(json.loads(buf.getvalue())["totals"]["api_calls"], 4)

    def test_compare_respects_redact_and_rejects_html(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main([self.dir, "--since", "all", "--compare", "2026-01-15", "--json", "--redact"])
        self.assertNotIn("/proj", buf.getvalue())
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            T.main([self.dir, "--since", "all", "--compare", "2026-01-15", "--html", os.path.join(self.dir, "x.html")])

    def test_instruction_files_as_actually_loaded(self):
        lines = claude_session()
        lines.insert(1, {"type": "attachment", "sessionId": "s1", "cwd": "/proj", "attachment": {
            "type": "instructions", "files": [{"path": "/proj/CLAUDE.md", "type": "Project", "content": "r" * 4000}]}})
        path = os.path.join(self.dir, "att.jsonl")
        write_jsonl(path, lines)
        totals, _, _ = T.summarize([t for t in T.parse(path) if t.calls])
        loaded = {e["path"]: e for e in totals["always_loaded"]}
        self.assertEqual(list(loaded), ["/proj/CLAUDE.md"])
        self.assertTrue(loaded["/proj/CLAUDE.md"]["exact"])
        self.assertAlmostEqual(loaded["/proj/CLAUDE.md"]["tokens"], 1000)

    def test_image_only_repeats_are_not_wasted_calls(self):
        lines = [{"type": "user", "sessionId": "i1", "cwd": "/p", "message": {"role": "user", "content": "look"}}]
        for k in range(3):
            lines += assistant(f"s{k}", u(cread=10000 + k), tool_use(f"s{k}", "mcp__browser__screenshot", {}))
            lines.append(result(f"s{k}", [{"type": "image", "source": {"type": "base64", "data": "AAAA"}}]))
        path = os.path.join(self.dir, "img.jsonl")
        write_jsonl(path, lines)
        _, by_kind, _ = T.summarize([t for t in T.parse(path) if t.calls])
        self.assertNotIn("wasted-call", by_kind)

    def test_dates(self):
        self.assertAlmostEqual(T.epoch("2026-10-12T08:00:00.123456789Z"), T.epoch("2026-10-12T08:00:00.123456+00:00"))
        self.assertAlmostEqual(T.epoch(1791187125000), 1791187125.0)
        self.assertIsNone(T.epoch("yesterday"))
        with self.assertRaises(ValueError):
            T.parse_since("30m")
        self.assertGreater(T.parse_since("2026-10-01T00:00:00Z"), 0)

    def test_guard(self):
        big = os.path.join(self.dir, "big.py")
        with open(big, "w") as f:
            f.write("x = 1  # filler\n" * 3000)

        def run(event, env=None):
            old = dict(os.environ)
            os.environ.update(env or {})
            try:
                buf = io.StringIO()
                T.guard(io.StringIO(json.dumps(event)), buf)
                return buf.getvalue()
            finally:
                os.environ.clear()
                os.environ.update(old)

        denied = json.loads(run({"tool_name": "Read", "tool_input": {"file_path": big}}))
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("3000 lines", denied["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertEqual(run({"tool_name": "Read", "tool_input": {"file_path": big, "limit": 3001}}), "")
        self.assertEqual(run({"tool_name": "Bash", "tool_input": {"command": "cat " + big}}), "")
        self.assertEqual(run({"tool_name": "Read", "tool_input": {"file_path": big}}, {"TOKENLEAK_GUARD": "0"}), "")

    def test_rules_print_skill_body(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            T.main(["rules"])
        self.assertTrue(buf.getvalue().startswith("# tokenleak"))
        self.assertNotIn("description:", buf.getvalue())
        self.assertNotIn("## Audit", buf.getvalue())  # only needed with the script at hand


if __name__ == "__main__":
    unittest.main()
