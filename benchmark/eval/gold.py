#!/usr/bin/env python3
"""Independent gold implementation. Usage: gold.py <db> <questions.jsonl> <out.json>"""
import sys, json, sqlite3, time
from collections import defaultdict


def main(db, qpath, out):
    t0 = time.time()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    projects = {r[0]: r for r in con.execute("SELECT project_id, project_code, project_name, dept_code FROM projects")}
    act_proj = {r[0]: r[1] for r in con.execute("SELECT activity_id, project_id FROM activities")}
    item_act = {r[0]: r[1] for r in con.execute("SELECT item_id, activity_id FROM expense_items")}
    staff = list(con.execute("SELECT staff_id, full_name, dept_code FROM staff_users"))
    forms_by_staff = defaultdict(list)
    for doc_no, sid, amt in con.execute("SELECT doc_no, staff_id, amount FROM approval_forms"):
        forms_by_staff[sid].append((doc_no, amt))

    # ledger: index by (dept, fy, month) -> list of (chain_pid, net, used, remain)
    idx = defaultdict(list)
    st = dict(rows=0, orphan_chain=0, chain_ne_ownpid=0, chain_dept_ne_ledger_dept=0, nulls=0)
    seen = set(); st["dup_statement_id"] = 0
    for sid, item, pid, dept, fy, mo, net, used, rem in con.execute(
            "SELECT statement_id,item_id,project_id,dept_code,fiscal_year,month,net_budget,used_budget,remain_budget FROM transaction_statement"):
        st["rows"] += 1
        if sid in seen: st["dup_statement_id"] += 1
        seen.add(sid)
        if None in (item, pid, dept, fy, mo, net, used, rem): st["nulls"] += 1; continue
        a = item_act.get(item)
        cp = act_proj.get(a) if a is not None else None
        if cp is None or cp not in projects:
            st["orphan_chain"] += 1; cp = None
        else:
            if cp != pid: st["chain_ne_ownpid"] += 1
            if projects[cp][3] != dept: st["chain_dept_ne_ledger_dept"] += 1
        idx[(dept, fy, mo)].append((cp, float(net), float(used), float(rem)))
    del seen

    res = {}
    for line in open(qpath):
        line = line.strip()
        if not line: continue
        q = json.loads(line)
        tool, a = q.get("gold_tool"), q.get("gold_args")
        if not tool: continue
        if tool == "get_delayed_projects":
            agg = {}
            for cp, n, u, r in idx.get((a["dept_code"], a["fiscal_year"], a["month"]), []):
                if cp is None: continue
                s = agg.setdefault(cp, [0.0, 0.0, 0.0]); s[0] += n; s[1] += u; s[2] += r
            cand = [(cp, s) for cp, s in agg.items() if s[2] > a["min_remain"]]
            cand.sort(key=lambda x: (-x[1][2], projects[x[0]][1]))
            data = []
            for cp, (n, u, r) in cand[:10]:
                data.append({"project_code": projects[cp][1], "project_name": projects[cp][2],
                             "net_budget": round(n, 2), "used_budget": round(u, 2), "remain_budget": round(r, 2),
                             "burn_rate": round(u * 100 / n, 2) if n > 0 else 0.0})
        elif tool == "reconcile_staff_advances":
            rows = []
            for sid, name, d in staff:
                if d != a["dept_code"]: continue
                for doc, amt in forms_by_staff.get(sid, []):
                    rows.append((amt, doc, name, d))
            rows.sort(key=lambda x: (-x[0], x[1]))
            data = [{"staff_name": n, "dept_code": d, "doc_no": doc, "amount": amt} for amt, doc, n, d in rows[:10]]
        elif tool == "get_department_summary":
            data = []
            for d in sorted(set(a["dept_codes"])):
                rows = idx.get((d, a["fiscal_year"], a["month"]))
                if not rows: continue
                n = sum(r[1] for r in rows); u = sum(r[2] for r in rows); r_ = sum(r[3] for r in rows)
                data.append({"dept_code": d, "net_budget": round(n, 2), "used_budget": round(u, 2),
                             "remain_budget": round(r_, 2), "burn_rate": round(u * 100 / n, 2) if n > 0 else 0.0})
        else:
            continue
        res[q["id"]] = {"data": data}
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    st["questions_in_scope"] = len(res); st["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(st), file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:4])
