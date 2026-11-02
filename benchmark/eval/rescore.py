#!/usr/bin/env python3
"""Re-time predicted and reference SQL sequentially (no concurrency) and recompute VES.

run_llm.py measured e_pred_ms while 8 threads were active and e_ref_ms with a different
function. Here both are timed with the same run_sql(), one at a time, median of N runs
after one warm-up, and VES = (1/n) * sum over correct answers of sqrt(E_ref / E_pred).

Usage: python3 rescore.py [--runs 10]
"""
import argparse
import json
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import run_llm as R  # noqa: E402
import run_offline as ro  # noqa: E402
from fast_mcp.semantic_tools import SemanticFastTools  # noqa: E402


def lit(v):
    return "'" + str(v).replace("'", "''") + "'" if isinstance(v, str) else repr(v)


def ref_text(tool, a):
    if tool == "get_delayed_projects":
        return ro.REF_DELAYED.replace("?", "{}").format(*[lit(a[k]) for k in ("dept_code", "fiscal_year", "month", "min_remain")])
    if tool == "reconcile_staff_advances":
        return R.REF_ADV.replace("?", lit(a["dept_code"]))
    ph = ",".join(lit(d) for d in a["dept_codes"])
    return ro.REF_SUMMARY.format(ph=ph).replace("?", "{}").format(a["fiscal_year"], a["month"])


def med(fn, n):
    fn()
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/home/suphachai/fastmcp_eval/db_800000.db")
    ap.add_argument("--questions", default="/home/suphachai/fastmcp_eval/q_800000.jsonl")
    ap.add_argument("--in", dest="inp", default=os.path.join(HERE, "results", "llm_results.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "results", "ves_sequential.json"))
    ap.add_argument("--runs", type=int, default=10)
    a = ap.parse_args()
    qs = {q["id"]: q for q in map(json.loads, open(a.questions))}
    last = {}
    for l in open(a.inp):
        r = json.loads(l)
        last[(r["system"], r["qid"])] = r
    tools = SemanticFastTools(a.db, ensure_indexes=False)
    ref_cache = {}
    per = {}
    for (s, qid), r in sorted(last.items()):
        if r["intent"] == "out_of_scope":
            continue
        d = per.setdefault(s, {"n": 0, "ratios": []})
        d["n"] += 1
        if not r.get("correct"):
            continue
        q = qs[qid]
        if qid not in ref_cache:
            sql = ref_text(q["gold_tool"], q["gold_args"])
            ref_cache[qid] = med(lambda: R.run_sql(a.db, sql), a.runs)
        if s == "fast_mcp":
            args = r["exec_args"]
            e_pred = med(lambda: getattr(tools, r["tool"])(**args), a.runs)
        else:
            e_pred = med(lambda: R.run_sql(a.db, r["sql"]), a.runs)
        d["ratios"].append(math.sqrt(ref_cache[qid] / max(e_pred, 1e-3)))
    out = {s: {"n": d["n"], "correct": len(d["ratios"]), "VES": sum(d["ratios"]) / d["n"],
               "mean_ratio_correct_only": statistics.mean(d["ratios"]) if d["ratios"] else None} for s, d in per.items()}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
