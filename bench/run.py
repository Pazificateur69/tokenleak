"""A/B benchmark: Claude Code with vs without the tokenleak rules, on identical tasks.

    python3 bench/run.py --runs 3 --model sonnet          # run + summarize
    python3 bench/run.py --summarize bench/results/<dir>   # re-print (and rewrite) its summary.md

Each run gets a fresh copy of the fixture repo and a clean Claude Code: no user/global settings,
CLAUDE.md, plugins, skills or MCP servers (--setting-sources project, --strict-mcp-config,
--disable-slash-commands). The only difference between variants is --append-system-prompt-file
with the rules, i.e. what the plugin's SessionStart hook injects.
"""
import argparse
import concurrent.futures as cf
import glob
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "skills", "tokenleak", "scripts")]
import fixture  # noqa: E402
import tokenleak as T  # noqa: E402

TASKS = {
    "fix-test": "The test suite (`python3 -m unittest`) is failing. Find the root cause and fix it in the "
                "application code. Do not modify the tests.",
    "find-answer": "How many products in this repo's catalog fall in the heavy shipping tariff and are currently out of "
                   "stock (stock 0)? Reply with just the number.",
    "fix-build": "`./build.sh` fails. Fix the cause so the build passes. Do not modify build.sh.",
    # held out: written before the v1.1 rule changes, never used to tune them
    "add-feature": "Add a `--category NAME` option to tools/report.py that keeps only the orders whose product is "
                   "in that category. `python3 -m tools.report data/orders.csv --category toys` must work and end "
                   "with its usual summary line.",
}
VARIANTS = ("baseline", "tokenleak", "guard")  # guard = rules + the plugin's PreToolUse Read guard
SCRIPT = os.environ.get("TOKENLEAK_BENCH_SCRIPT") or os.path.join(ROOT, "skills", "tokenleak", "scripts", "tokenleak.py")  # guard under test
# Same for both variants: the agent can work in its repo (+ temp dirs) and cannot read your personal folders.
HOME_DIRS = ["~/Desktop", "~/Documents", "~/Downloads", "~/Developer", "~/.claude", "~/.codex", "~/.ssh", "~/Library"]
SANDBOX = {
    "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False,
                "filesystem": {"denyRead": HOME_DIRS, "allowWrite": ["/tmp", "/private/tmp"]}},
    "permissions": {"deny": [f"Read({d}/**)" for d in HOME_DIRS]},
}


def digest(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with open(p, "rb") as f:
            h.update(p.encode() + f.read())
    return h.hexdigest()


def check(task, work, answer, expected, snap):
    def sh(cmd):
        return subprocess.run(cmd, cwd=work, shell=True, capture_output=True, text=True, timeout=300)

    if task == "fix-test":
        r = sh("python3 -m unittest")
        return r.returncode == 0 and digest(glob.glob(os.path.join(work, "tests", "*.py"))) == snap["tests"]
    if task == "find-answer":
        return re.findall(r"\d+", answer or "") == [str(expected["t2_count"])]
    if task == "fix-build":
        r = sh("./build.sh")
        return (r.returncode == 0 and "report: 2400 orders" in r.stdout
                and digest([os.path.join(work, "build.sh")]) == snap["build"])
    if task == "add-feature":  # two categories (so a hard-coded "toys" fails) and the default run unchanged
        for arg, n, sku in ((" --category toys", expected["t4_toys"], " sku=TY-"),
                            (" --category audio", expected["t4_by_cat"]["audio"], " sku=AU-"), ("", 2400, " sku=")):
            r = sh("python3 -m tools.report data/orders.csv" + arg)
            lines = r.stdout.strip().splitlines()
            orders = [l for l in lines if l.startswith("report: order ")]
            if not (r.returncode == 0 and lines and lines[-1].startswith(f"report: {n} orders")
                    and len(orders) == n and all(sku in l for l in orders)):
                return False
        return True
    raise ValueError(task)


def safe_check(*a):
    try:
        return check(*a)
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  checker failed: {e}", file=sys.stderr)
        return False


def output_share(r):
    """Share of a run's cost (in relative price units) spent on what the model wrote."""
    u = r.get("usage")
    if not u:
        return None
    units = u["fresh"] + 1.25 * u["cache_write_5m"] + 2 * u["cache_write_1h"] + 0.1 * u["cache_read"] + 5 * u["output"]
    return 100 * 5 * u["output"] / units if units else None


def transcript_metrics(session_id):
    files = glob.glob(os.path.join(T.roots()["claude"], "*", f"{session_id}.jsonl"))
    if not files:
        return {}
    calls, findings, units, model = [], [], 0.0, None
    for t in T.parse(files[0]):
        fs, u = T.analyze(t)
        calls += t.calls
        findings += fs
        units += u
    with open(files[0]) as f:
        for line in f:
            if '"model"' in line and '"assistant"' in line:
                model = (json.loads(line).get("message") or {}).get("model") or model
    by_kind = {}
    for f in findings:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
    return {
        "transcript": files[0],
        "model": model,
        "api_calls": len(calls),
        "context_tokens": sum(c.ctx_in for c in calls),
        "output_tokens": sum(c.out for c in calls),
        "max_context": max((c.ctx_in for c in calls), default=0),
        "usage": {"fresh": sum(c.fresh for c in calls), "cache_write_5m": sum(c.c5m for c in calls),
                  "cache_write_1h": sum(c.c1h for c in calls), "cache_read": sum(c.cread for c in calls),
                  "output": sum(c.out for c in calls)},
        "leak_pct": round(100 * sum(f.cost for f in findings) / units, 2) if units else 0,
        "leaks": by_kind,
    }


def escaped(transcript, work):
    """Did the agent reach for files outside its repo? (reported, and blocked by the sandbox)"""
    if not transcript:
        return False
    home = os.path.expanduser("~")
    with open(transcript) as f:
        for line in f:
            d = json.loads(line)
            for c in ((d.get("message") or {}).get("content") or []) if d.get("type") == "assistant" else []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    s = json.dumps(c.get("input")).replace(work, "")
                    if home in s or "~/" in s or re.search(r"find /[\s\"]", s):
                        return True
    return False


def run_one(task, variant, i, args, outdir, rules):
    work = tempfile.mkdtemp(prefix=f"{task}-{variant}-{i}-", dir=args.workdir)
    expected = fixture.write(work)
    snap = {"tests": digest(glob.glob(os.path.join(work, "tests", "*.py"))),
            "build": digest([os.path.join(work, "build.sh")])}
    settings = dict(SANDBOX)
    if variant == "guard":
        settings["hooks"] = {"PreToolUse": [{"matcher": "Read", "hooks": [
            {"type": "command", "command": f'python3 "{SCRIPT}" guard'}]}]}
    cmd = ["claude", "-p", TASKS[task], "--model", args.model, "--output-format", "json",
           "--setting-sources", "project", "--strict-mcp-config", "--disable-slash-commands",
           "--permission-mode", "bypassPermissions", "--max-turns", str(args.max_turns),
           "--settings", json.dumps(settings)]
    if variant in ("tokenleak", "guard"):
        cmd += ["--append-system-prompt-file", rules]
    t0 = time.time()
    try:
        # Apple's python3 caches bytecode under ~/Library/Caches, which the sandbox (rightly) denies
        env = dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(work, ".pycache"))
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=args.timeout, env=env)
        data = json.loads(p.stdout)
    except (subprocess.TimeoutExpired, ValueError) as e:
        data = {"is_error": True, "result": f"runner error: {e}"}
    rec = {
        "task": task, "variant": variant, "run": i, "workdir": work,
        "wall_s": round(time.time() - t0, 1),
        "pass": (not data.get("is_error")) and safe_check(task, work, data.get("result"), expected, snap),
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "session_id": data.get("session_id"),
        "answer": (data.get("result") or "")[:500],
    }
    if data.get("session_id"):
        rec.update(transcript_metrics(data["session_id"]))
        rec["escaped"] = escaped(rec.get("transcript"), work)
    with open(os.path.join(outdir, f"{task}--{variant}--{i}.json"), "w") as f:
        json.dump(rec, f, indent=2)
    print(f"  {task:<12} {variant:<10} #{i}  {'PASS' if rec['pass'] else 'FAIL'}  "
          f"${rec['cost_usd'] or 0:.3f}  ctx {T.fmt(rec.get('context_tokens', 0))}  "
          f"calls {rec.get('api_calls', '?')}  {rec['wall_s']}s{'  ESCAPED' if rec.get('escaped') else ''}",
          flush=True)
    return rec


def summarize(outdir):
    recs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(outdir, "*--*--*.json")))]
    if not recs:
        sys.exit(f"no results in {outdir}")
    med = statistics.median
    present = [v for v in VARIANTS if any(r["variant"] == v for r in recs)]
    rows, tot = [], {v: {"cost": 0.0, "ctx": 0.0, "out": 0.0} for v in present}
    lines = ["| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) "
             "| API calls (median) | leak score (median) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for task in TASKS:
        for v in present:
            rs = [r for r in recs if r["task"] == task and r["variant"] == v]
            if not rs:
                continue
            costs = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
            c = med(costs) if costs else 0.0
            x = med([r.get("context_tokens", 0) for r in rs])
            o = med([r.get("output_tokens", 0) for r in rs])
            tot[v]["cost"] += c
            tot[v]["ctx"] += x
            tot[v]["out"] += o
            missing = f", {len(rs) - len(costs)} without a cost" if len(costs) < len(rs) else ""
            lines.append(f"| {task} | {v} | {len(rs)} | {sum(r['pass'] for r in rs)}/{len(rs)} | "
                         f"${c:.3f} (${min(costs or [0]):.3f}-{max(costs or [0]):.3f}{missing}) | {T.fmt(x)} | "
                         f"{T.fmt(o)} | {med([r.get('api_calls', 0) for r in rs]):.0f} | "
                         f"{med([r.get('leak_pct', 0) for r in rs]):.1f}% |")
    passes = {v: f"{sum(r['pass'] for r in recs if r['variant'] == v)}/{sum(1 for r in recs if r['variant'] == v)}"
              for v in present}
    models = sorted({r.get("model") for r in recs if r.get("model")})
    lines.append("")
    b = tot.get("baseline")
    for v in present:
        if v == "baseline" or not b:
            continue
        k = tot[v]

        def delta(key):
            return f"{100 * (k[key] - b[key]) / b[key]:+.0f}%" if b[key] else "n/a"

        lines.append(f"**Sum of medians, {v} vs baseline**: cost ${b['cost']:.3f} → ${k['cost']:.3f} ({delta('cost')}), "
                     f"context tokens {T.fmt(b['ctx'])} → {T.fmt(k['ctx'])} ({delta('ctx')}), "
                     f"output tokens {T.fmt(b['out'])} → {T.fmt(k['out'])} ({delta('out')}).")
    walls = {v: med([r["wall_s"] for r in recs if r["variant"] == v]) for v in present}
    shares = {v: [x for x in (output_share(r) for r in recs if r["variant"] == v) if x is not None] for v in present}
    lines.append("Median wall time per run: " + ", ".join(f"{v} {walls[v]:.0f}s" for v in present) + ".")
    if all(shares.values()):
        lines.append("Output share of cost (median per run, relative price units): "
                     + ", ".join(f"{v} {med(shares[v]):.1f}%" for v in present) + ".")
    lines.append(f"Passed: {', '.join(f'{v} {passes[v]}' for v in present)}. Model: {', '.join(models) or '?'}. "
                 f"Runs that tried to leave the repo: {sum(1 for r in recs if r.get('escaped'))}.")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(outdir, "summary.md"), "w") as f:
        f.write(text)
    print("\n" + text)


def export(src, dest):
    os.makedirs(dest, exist_ok=True)
    for p in glob.glob(os.path.join(src, "*--*--*.json")):
        rec = json.load(open(p))
        work = rec.pop("workdir", "")
        rec.pop("transcript", None)
        rec["answer"] = rec.get("answer", "").replace(work, "<repo>")
        with open(os.path.join(dest, os.path.basename(p)), "w") as f:
            json.dump(rec, f, indent=2)
    if os.path.exists(os.path.join(src, "rules.md")):
        shutil.copy(os.path.join(src, "rules.md"), os.path.join(dest, "rules.md"))
    summarize(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--variants", default="baseline,tokenleak", help="any of: baseline, tokenleak, guard")
    ap.add_argument("--workdir", default=tempfile.gettempdir())
    ap.add_argument("--out")
    ap.add_argument("--summarize")
    ap.add_argument("--export", nargs=2, metavar=("RUN_DIR", "DEST"), help="copy results without local paths")
    args = ap.parse_args()
    if args.summarize:
        return summarize(args.summarize)
    if args.export:
        return export(*args.export)
    outdir = args.out or os.path.join(HERE, "results", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(outdir, exist_ok=True)
    rules = os.path.join(outdir, "rules.md")
    with open(rules, "w") as f:
        T.print_rules(f)
    jobs = [(t, v, i) for i in range(1, args.runs + 1) for t in args.tasks.split(",") for v in args.variants.split(",")]
    print(f"{len(jobs)} runs -> {outdir}", flush=True)
    with cf.ThreadPoolExecutor(args.parallel) as ex:
        list(ex.map(lambda j: run_one(*j, args, outdir, rules), jobs))
    summarize(outdir)


if __name__ == "__main__":
    main()
