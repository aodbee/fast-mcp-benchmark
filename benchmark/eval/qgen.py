#!/usr/bin/env python3
"""Seeded question-set generator. Writes JSONL: id, intent, question, gold_tool, gold_args.

gold_tool is null for out-of-scope questions (no semantic tool applies).
Thresholds for get_delayed_projects scale with the ledger size so that the
HAVING filter is selective at every scale.

Usage: python3 qgen.py <ledger_rows> <out.jsonl> [seed]
"""
import json
import random
import sys

DEPTS = [f"10{i:02d}0000" for i in range(1, 21)]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

OOS = [
    "How many ledger rows exist for department {d} in fiscal year 2026?",
    "Which staff member in department {d} has submitted the most approval forms?",
    "List all activities of department {d} that are not completed.",
    "What is the average approved budget of projects in department {d}?",
    "Show the total allocated budget of all departments.",
    "Which expense item has the largest allocated amount in department {d}?",
    "How many projects does department {d} have?",
    "What was the net budget of department {d} in month 1 compared with month 2?",
    "Name the division of department {d}.",
    "List the five staff members with the longest names in department {d}.",
]


def expected_project_remain(ledger_rows):
    # mean net 145,000 x mean (1 - burn) 0.45; 200 projects x 12 months
    return ledger_rows / (200 * 12) * 145000 * 0.45


def build(ledger_rows, seed=42):
    rng = random.Random(seed)
    exp = expected_project_remain(ledger_rows)
    qs = []

    def add(intent, question, tool, args):
        qs.append({"id": f"q{len(qs)+1:03d}", "intent": intent, "question": question,
                   "gold_tool": tool, "gold_args": args})

    for d in DEPTS:
        for f in (0.9, 1.0, 1.1):
            m = rng.randint(1, 12)
            thr = round(exp * f, -3)
            add("delayed_projects",
                f"List the delayed projects of department {d} in fiscal year 2026, month {m}, "
                f"whose remaining unspent budget exceeds {thr:,.0f} THB. Show the top 10 by remaining budget "
                f"with project code, project name, net budget, used budget, remaining budget and burn rate (used/net in %).",
                "get_delayed_projects",
                {"dept_code": d, "fiscal_year": 2026, "month": m, "min_remain": float(thr)})
    for d in DEPTS:
        add("staff_advances",
            f"Reconcile the approval forms of staff in department {d}: show the top 10 forms by amount with "
            f"staff name, department code, document number and amount.",
            "reconcile_staff_advances", {"dept_code": d})
    for _ in range(40):
        k = rng.choice([2, 3])
        ds = sorted(rng.sample(DEPTS, k))
        m = rng.randint(1, 12)
        add("department_summary",
            f"Compare net budget, disbursed amount, remaining balance and burn rate between departments "
            f"{', '.join(ds)} for fiscal year 2026, {MONTH_NAMES[m-1]} (month {m}). Show one row per department "
            f"with department code, net budget, used budget, remaining budget and burn rate (used/net in %).",
            "get_department_summary", {"dept_codes": ds, "fiscal_year": 2026, "month": m})
    for i in range(20):
        add("out_of_scope", OOS[i % len(OOS)].format(d=rng.choice(DEPTS)), None, None)
    rng.shuffle(qs)
    for i, q in enumerate(qs):
        q["id"] = f"q{i+1:03d}"
    return qs


if __name__ == "__main__":
    rows, out = int(sys.argv[1]), sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    with open(out, "w") as fh:
        for q in build(rows, seed):
            fh.write(json.dumps(q) + "\n")
    print(f"{out}: {len(build(rows, seed))} questions")
