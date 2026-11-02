#!/usr/bin/env python3
"""Gold results for the hard question set, in pure Python (no SQL aggregates).

Tiers A and D (gold_tool set) are delegated to gold.py (same semantics as the main set);
tiers B and C are computed here from raw table rows.

Usage: python3 gold_hard.py <db> <questions.jsonl> <out.json>
"""
import collections
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def rows(conn, sql):
    return conn.execute(sql).fetchall()


def main(db, qfile, out):
    questions = [json.loads(l) for l in open(qfile)]
    gold = {}

    tool_qs = [q for q in questions if q["gold_tool"]]
    with tempfile.TemporaryDirectory() as d:
        sub_q, sub_out = os.path.join(d, "q.jsonl"), os.path.join(d, "g.json")
        with open(sub_q, "w") as fh:
            for q in tool_qs:
                fh.write(json.dumps(q) + "\n")
        subprocess.run([sys.executable, os.path.join(HERE, "gold.py"), db, sub_q, sub_out], check=True, capture_output=True)
        gold.update(json.load(open(sub_out)))

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    proj = {r[0]: (r[1], r[2], r[3]) for r in rows(conn, "SELECT project_id, project_code, project_name, dept_code FROM projects")}
    ledger = rows(conn, "SELECT project_id, dept_code, month, net_budget, used_budget, remain_budget FROM transaction_statement")
    staff = {r[0]: (r[1], r[2]) for r in rows(conn, "SELECT staff_id, full_name, dept_code FROM staff_users")}
    forms = rows(conn, "SELECT doc_no, staff_id, amount FROM approval_forms")

    def r2(x):
        return round(x, 2)

    for q in questions:
        k = q.get("gold_kind")
        if not k:
            continue
        p = q["gold_params"]
        if k == "delayed_variant":
            agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
            for pid, dc, m, n, u, rm in ledger:
                if dc == p["dept_code"] and m in p["months"]:
                    a = agg[pid]
                    a[0] += float(n)
                    a[1] += float(u)
                    a[2] += float(rm)
            items = [(proj[pid][0], proj[pid][1], a) for pid, a in agg.items() if a[2] > p["min_remain"]]
            items.sort(key=lambda t: (t[2][2], t[0]) if p["order"] == "asc" else (-t[2][2], t[0]))
            data = [{"project_code": c, "project_name": nm, "net_budget": r2(a[0]), "used_budget": r2(a[1]), "remain_budget": r2(a[2]),
                     "burn_rate": r2(a[1] * 100.0 / a[0]) if a[0] > 0 else 0.0} for c, nm, a in items[: p["top_n"]]]
        elif k == "advances_variant":
            lst = []
            for doc, sid, amt in forms:
                if sid in staff and staff[sid][1] == p["dept_code"]:
                    lst.append((amt, doc, staff[sid][0]))
            lst.sort(key=lambda t: (t[0], t[1]) if p["order"] == "asc" else (-t[0], t[1]))
            data = [{"staff_name": nm, "dept_code": p["dept_code"], "doc_no": doc, "amount": amt} for amt, doc, nm in lst[: p["top_n"]]]
        elif k == "dept_burn_rank":
            tot = collections.defaultdict(lambda: [0.0, 0.0])
            for pid, dc, m, n, u, rm in ledger:
                if m == p["month"]:
                    tot[dc][0] += float(n)
                    tot[dc][1] += float(u)
            best = max(tot.items(), key=lambda kv: kv[1][1] / kv[1][0])
            data = [{"dept_code": best[0], "burn_rate": r2(best[1][1] * 100.0 / best[1][0])}]
        elif k == "monthly_used":
            tot = collections.defaultdict(float)
            for pid, dc, m, n, u, rm in ledger:
                if dc == p["dept_code"]:
                    tot[m] += float(u)
            data = [{"month": m, "used": r2(tot[m])} for m in sorted(tot)]
        elif k == "count_projects":
            tot = collections.defaultdict(float)
            for pid, dc, m, n, u, rm in ledger:
                if dc == p["dept_code"]:
                    tot[pid] += float(rm)
            data = [{"count": sum(1 for v in tot.values() if v > p["min_remain"])}]
        elif k == "top_staff_total":
            tot = collections.defaultdict(float)
            for doc, sid, amt in forms:
                if sid in staff and staff[sid][1] == p["dept_code"]:
                    tot[sid] += amt
            top = sorted(tot.items(), key=lambda kv: (-kv[1], kv[0]))[: p["top_n"]]
            data = [{"full_name": staff[sid][0], "total": r2(v)} for sid, v in top]
        elif k == "forms_count":
            data = [{"count": sum(1 for doc, sid, amt in forms if sid in staff and staff[sid][1] == p["dept_code"])}]
        else:
            raise ValueError(k)
        gold[q["id"]] = {"data": data}
    json.dump(gold, open(out, "w"))
    print(out, len(gold), "gold entries;", sum(1 for v in gold.values() if not v["data"]), "empty")


if __name__ == "__main__":
    main(*sys.argv[1:4])
