"""Bootstrap confidence intervals for the benchmark's headline number.

    python3 bench/stats.py bench/results/<dir> baseline <variant> [--batch b1] [--from DIR] [--field context_tokens]
    python3 bench/stats.py --selftest

Metric, as in summary.md and the README: each arm's median per task, summed over the tasks, and the change.
The 95% interval resamples runs with replacement within each task and arm (10,000 times, fixed seed), so it is
reproducible. --from takes the variant's runs from another folder (e.g. a second guard arm run apart).
"""
import argparse
import glob
import json
import os
import random
import statistics
import sys

RESAMPLES = 10000
SEED = 2026
med = statistics.median


def load(folder, variant, batch=None):
    """-> {task: [records]} for one arm, in file-name order."""
    out = {}
    for p in sorted(glob.glob(os.path.join(folder, "*--*--*.json"))):
        with open(p) as f:
            r = json.load(f)
        if r.get("variant") == variant and (batch is None or r.get("batch") == batch):
            out.setdefault(r["task"], []).append(r)
    return out


def change(b, v):
    return 100.0 * (v - b) / b


def interval(xs):
    xs = sorted(xs)
    return xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]


def compare(base, var, resamples=RESAMPLES, seed=SEED):
    """base, var: {task: [values]} -> point estimates and 95% bootstrap intervals, total and per task.

    "rest" drops the task with the largest saving in absolute terms (it weighs most in a sum of medians)."""
    tasks = [t for t in base if base[t] and var.get(t)]
    point = {t: (med(base[t]), med(var[t])) for t in tasks}
    top = max(tasks, key=lambda t: point[t][0] - point[t][1]) if len(tasks) > 1 else None
    rng = random.Random(seed)
    boots, tot, rest = {t: [] for t in tasks}, [], []
    for _ in range(resamples):
        sb = sv = rb = rv = 0.0
        for t in tasks:
            b = med(rng.choices(base[t], k=len(base[t])))
            v = med(rng.choices(var[t], k=len(var[t])))
            boots[t].append(change(b, v))
            sb, sv = sb + b, sv + v
            if t != top:
                rb, rv = rb + b, rv + v
        tot.append(change(sb, sv))
        if top:
            rest.append(change(rb, rv))

    def row(name, b, v, bs):
        return {"name": name, "base": b, "var": v, "change": change(b, v), "ci": interval(bs)}

    out = {"tasks": [row(t, point[t][0], point[t][1], boots[t]) for t in tasks],
           "total": row("total", sum(p[0] for p in point.values()), sum(p[1] for p in point.values()), tot),
           "top": top, "rest": None}
    if top:
        others = [t for t in tasks if t != top]
        out["rest"] = row("without " + top, sum(point[t][0] for t in others), sum(point[t][1] for t in others), rest)
    return out


def selftest():
    # no spread: the interval collapses on the point estimate; "a" saves the most dollars, "b" the most percent
    r = compare({"a": [10.0] * 3, "b": [1.0] * 3}, {"a": [9.0] * 3, "b": [0.1] * 3}, resamples=200)
    assert abs(r["total"]["change"] - 100 * (9.1 - 11) / 11) < 1e-9, r["total"]
    assert r["total"]["ci"][0] == r["total"]["ci"][1] == r["total"]["change"]
    assert r["top"] == "a" and abs(r["rest"]["change"] + 90) < 1e-9, r["rest"]
    # with spread: reproducible, ordered, and wider than nothing
    base, var = {"t": [1.0, 1.2, 0.9, 1.5, 1.1]}, {"t": [0.7, 0.9, 0.8, 1.3, 0.6]}
    r1, r2 = compare(base, var, resamples=500), compare(base, var, resamples=500)
    assert r1 == r2 and r1["rest"] is None
    lo, hi = r1["total"]["ci"]
    assert lo < hi and lo <= r1["total"]["change"] <= hi, r1["total"]
    print("selftest ok")


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("base")
    ap.add_argument("variant")
    ap.add_argument("--batch", help="only runs tagged with this batch (b1, b2)")
    ap.add_argument("--from", dest="src", help="take the variant's runs from this folder instead")
    ap.add_argument("--field", default="cost_usd", help="cost_usd (default) or e.g. context_tokens")
    a = ap.parse_args()
    recs = {"base": load(a.folder, a.base, a.batch), "var": load(a.src or a.folder, a.variant, a.batch)}
    vals = {k: {t: [r[a.field] for r in rs if r.get(a.field) is not None] for t, rs in d.items()}
            for k, d in recs.items()}
    if not vals["base"] or not vals["var"]:
        sys.exit("no runs for one of the arms (check the folder, variant and --batch)")
    r = compare(vals["base"], vals["var"])
    fmt = (lambda x: "$%.3f" % x) if a.field == "cost_usd" else (lambda x: "{:,.0f}".format(x))
    label = a.variant + (" (%s)" % os.path.basename(os.path.normpath(a.src)) if a.src else "")

    def n(k, ts):
        return sum(len(vals[k].get(t, [])) for t in ts)

    def passed(k, ts):
        rs = [x for t in ts for x in recs[k].get(t, [])]
        return "%d/%d" % (sum(1 for x in rs if x.get("pass")), len(rs))

    print("%s%s · %s · %s vs %s · median per task, summed · 95%% bootstrap CI (%s resamples, seed %d)\n"
          % (a.folder, " · batch " + a.batch if a.batch else "", a.field, a.base, label, "{:,}".format(RESAMPLES), SEED))
    print("| task | runs | %s | %s | change | 95%% CI | passed |" % (a.base, label))
    print("|---|---|---|---|---|---|---|")
    names = [x["name"] for x in r["tasks"]]
    rows = [(x, [x["name"]]) for x in r["tasks"]] + ([(r["total"], names)] if len(names) > 1 else [])
    if r["rest"]:
        rows.append((r["rest"], [t for t in names if t != r["top"]]))
    for x, ts in rows:
        print("| %s | %d · %d | %s | %s | %+.0f%% | %+.0f%% to %+.0f%% | %s · %s |"
              % (x["name"], n("base", ts), n("var", ts), fmt(x["base"]), fmt(x["var"]), x["change"],
                 x["ci"][0], x["ci"][1], passed("base", ts), passed("var", ts)))
    if min(len(v) for d in vals.values() for v in d.values()) < 3:
        print("\nnote: an arm has fewer than 3 runs in a task; its interval says little.")


if __name__ == "__main__":
    main()
