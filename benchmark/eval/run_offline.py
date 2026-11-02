#!/usr/bin/env python3
"""Offline (no-LLM) evaluation: tool correctness vs independent gold, and DB-side timing.

Modes timed per question (each call opens its own sqlite3 connection and fetches all rows):
  direct   - SemanticFastTools method call
  mcp      - MCPProtocolHandler.handle_request (JSON-RPC encode + dispatch + response encode/decode)
  noindex  - same tool SQL, no index hint, compound/project indexes dropped (copy of the DB)
  refsql   - hand-written textbook multi-join SQL (NOT LLM-generated); delayed_projects and
             department_summary only

Usage: python3 run_offline.py --sizes 1000,10000,100000,800000 --runs 20 --warmup 3 --sample 10
"""
import argparse
import json
import os
import platform
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import gen_db  # noqa: E402
import qgen  # noqa: E402
from fast_mcp.semantic_tools import SemanticFastTools  # noqa: E402
from fast_mcp.mcp_protocol import MCPProtocolHandler  # noqa: E402

WORK = "/home/suphachai/fastmcp_eval"


def close(a, b, tol=0.011):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def rows_equal(got, gold):
    if len(got) != len(gold):
        return False, f"len {len(got)} vs {len(gold)}"
    for i, (g, w) in enumerate(zip(got, gold)):
        if set(g) != set(w):
            return False, f"row {i} keys {sorted(g)} vs {sorted(w)}"
        for k in w:
            if not close(g[k], w[k]):
                return False, f"row {i} field {k}: {g[k]} vs {w[k]}"
    return True, ""


def call_tool(tools, name, args):
    return getattr(tools, name)(**args)["data"]


REF_DELAYED = """
SELECT p.project_code, p.project_name,
       SUM(CAST(s.net_budget AS REAL)), SUM(CAST(s.used_budget AS REAL)), SUM(CAST(s.remain_budget AS REAL)) AS remain
FROM projects p
JOIN activities a ON p.project_id = a.project_id
JOIN expense_items i ON a.activity_id = i.activity_id
JOIN transaction_statement s ON i.item_id = s.item_id
WHERE s.dept_code = ? AND s.fiscal_year = ? AND s.month = ?
GROUP BY p.project_id
HAVING remain > ?
ORDER BY remain DESC, p.project_code ASC LIMIT 10"""

REF_SUMMARY = """
SELECT d.dept_code, SUM(CAST(s.net_budget AS REAL)), SUM(CAST(s.used_budget AS REAL)), SUM(CAST(s.remain_budget AS REAL))
FROM departments d JOIN transaction_statement s ON s.dept_code = d.dept_code
WHERE d.dept_code IN ({ph}) AND s.fiscal_year = ? AND s.month = ?
GROUP BY d.dept_code ORDER BY d.dept_code"""


def ref_sql(db, name, args):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    if name == "get_delayed_projects":
        cur.execute(REF_DELAYED, (args["dept_code"], args["fiscal_year"], args["month"], args["min_remain"]))
        rows = cur.fetchall()
        out = [{"project_code": r[0], "project_name": r[1], "net_budget": round(r[2], 2), "used_budget": round(r[3], 2),
                "remain_budget": round(r[4], 2), "burn_rate": round(r[3] * 100.0 / r[2], 2) if r[2] > 0 else 0.0} for r in rows]
    else:
        ds = args["dept_codes"]
        cur.execute(REF_SUMMARY.format(ph=",".join("?" for _ in ds)), list(ds) + [args["fiscal_year"], args["month"]])
        rows = cur.fetchall()
        out = [{"dept_code": r[0], "net_budget": round(r[1], 2), "used_budget": round(r[2], 2),
                "remain_budget": round(r[3], 2), "burn_rate": round(r[2] * 100.0 / r[1], 2)} for r in rows]
    conn.close()
    return out


def timeit(fn, runs, warmup):
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000.0)
    return ts


def summarize(vals):
    q = statistics.quantiles(vals, n=4) if len(vals) >= 2 else [vals[0]] * 3
    return {"n": len(vals), "median": statistics.median(vals), "q1": q[0], "q3": q[2]}


def env_info():
    cpu = ""
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    commit = subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", HERE, "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "cpu": cpu, "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "git_commit": commit, "working_tree_dirty": dirty, "db_dir": WORK}


def run_size(rows, args):
    db = f"{WORK}/db_{rows}.db"
    qf = f"{WORK}/q_{rows}.jsonl"
    gold_f = f"{WORK}/gold_{rows}.json"
    if not os.path.exists(db):
        gen_db.generate(db, rows, args.seed)
    with open(qf, "w") as fh:
        for q in qgen.build(rows, args.seed):
            fh.write(json.dumps(q) + "\n")
    subprocess.run([sys.executable, os.path.join(HERE, "gold.py"), db, qf, gold_f], check=True)
    questions = [json.loads(l) for l in open(qf)]
    gold = json.load(open(gold_f))

    noidx = f"{WORK}/db_{rows}.noidx.db"
    shutil.copyfile(db, noidx)
    c = sqlite3.connect(noidx)
    gen_db.drop_indexes(c, ["idx_statement_dept_year_month", "idx_statement_project_year"])
    c.close()

    tools = SemanticFastTools(db, ensure_indexes=False)
    tools_noidx = SemanticFastTools(noidx, ensure_indexes=False, use_index_hint=False)
    handler = MCPProtocolHandler(db)
    handler.fast_tools = tools

    correctness = {"direct": [], "refsql": [], "noindex": []}
    per_intent_corr = {}
    mismatches = []
    in_scope = [q for q in questions if q["gold_tool"]]
    for q in in_scope:
        name, a = q["gold_tool"], q["gold_args"]
        w = gold[q["id"]]["data"]
        ok, why = rows_equal(call_tool(tools, name, a), w)
        correctness["direct"].append(ok)
        per_intent_corr.setdefault(q["intent"], []).append(ok)
        if not ok:
            mismatches.append({"id": q["id"], "mode": "direct", "why": why})
        ok2, why2 = rows_equal(call_tool(tools_noidx, name, a), w)
        correctness["noindex"].append(ok2)
        if not ok2:
            mismatches.append({"id": q["id"], "mode": "noindex", "why": why2})
        if name != "reconcile_staff_advances":
            ok3, why3 = rows_equal(ref_sql(db, name, a), w)
            correctness["refsql"].append(ok3)
            if not ok3:
                mismatches.append({"id": q["id"], "mode": "refsql", "why": why3})

    nonempty = {k: sum(1 for q in in_scope if q["intent"] == k and gold[q["id"]]["data"]) for k in {q["intent"] for q in in_scope}}
    counts = {k: sum(1 for q in in_scope if q["intent"] == k) for k in nonempty}

    sample = []
    for intent in ["delayed_projects", "staff_advances", "department_summary"]:
        pool = [q for q in in_scope if q["intent"] == intent and gold[q["id"]]["data"]]
        sample += pool[: args.sample]

    timing = []
    for q in sample:
        name, a = q["gold_tool"], q["gold_args"]
        rec = {"id": q["id"], "intent": q["intent"], "modes": {}}
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": a}})
        rec["modes"]["direct"] = timeit(lambda: tools.__getattribute__(name)(**a), args.runs, args.warmup)
        rec["modes"]["mcp"] = timeit(lambda: json.loads(handler.handle_request(req)), args.runs, args.warmup)
        slow_runs = max(5, args.runs // 2)
        rec["modes"]["noindex"] = timeit(lambda: tools_noidx.__getattribute__(name)(**a), slow_runs, 1)
        if name != "reconcile_staff_advances":
            rec["modes"]["refsql"] = timeit(lambda: ref_sql(db, name, a), slow_runs, 1)
        timing.append(rec)

    agg = {}
    for intent in ["delayed_projects", "staff_advances", "department_summary"]:
        agg[intent] = {}
        for mode in ["direct", "mcp", "noindex", "refsql"]:
            meds = [statistics.median(r["modes"][mode]) for r in timing if r["intent"] == intent and mode in r["modes"]]
            if meds:
                agg[intent][mode] = summarize(meds)

    return {
        "ledger_rows": rows, "seed": args.seed, "n_questions": len(questions), "n_in_scope": len(in_scope),
        "n_out_of_scope": len(questions) - len(in_scope), "questions_per_intent": counts, "nonempty_gold_per_intent": nonempty,
        "correct_direct": f"{sum(correctness['direct'])}/{len(correctness['direct'])}",
        "correct_noindex": f"{sum(correctness['noindex'])}/{len(correctness['noindex'])}",
        "correct_refsql": f"{sum(correctness['refsql'])}/{len(correctness['refsql'])}",
        "correct_direct_per_intent": {k: f"{sum(v)}/{len(v)}" for k, v in per_intent_corr.items()},
        "mismatches": mismatches, "timing_summary_ms": agg, "timing_raw_ms": timing,
        "runs": args.runs, "warmup": args.warmup, "sample_per_intent": args.sample,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1000,10000,100000,800000")
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "offline_results.json"))
    args = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    out = {"env": env_info(), "args": vars(args), "sizes": {}}
    for s in [int(x) for x in args.sizes.split(",")]:
        print(f"== {s} rows", flush=True)
        out["sizes"][str(s)] = run_size(s, args)
        r = out["sizes"][str(s)]
        print(f"   correct direct {r['correct_direct']} noindex {r['correct_noindex']} refsql {r['correct_refsql']}", flush=True)
        json.dump(out, open(args.out, "w"), indent=1)
    print("saved", args.out)


if __name__ == "__main__":
    main()
