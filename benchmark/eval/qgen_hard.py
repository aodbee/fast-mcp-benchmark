#!/usr/bin/env python3
"""Harder question set (40 questions, 4 tiers) for separating Fast-MCP from few-shot SQL baselines.

Tiers
  A_paraphrase : same intents as the main set, free wording that does not follow the demo templates.
  B_variant    : tool-like intents with parameters the tools do not expose (top 5, ascending, months 1-3 combined).
  C_analytic   : analytics outside the three tools (needs free SQL).
  D_trap       : department given by name instead of code, relative month references.

gold_tool is set only where one of the three tools is the intended answer (tiers A and D).
Tiers B and C carry gold_kind/gold_params for gold_hard.py.

Usage: python3 qgen_hard.py <ledger_rows> <out.jsonl> [seed]
"""
import json
import random
import sys

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def code(i):
    return f"10{i:02d}0000"


def name(i):
    return f"Faculty / Division {i}"


def build(ledger_rows, seed=42):
    rng = random.Random(seed)
    exp = ledger_rows / (200 * 12) * 145000 * 0.45
    qs = []

    def add(tier, intent, question, tool=None, args=None, kind=None, params=None):
        qs.append({"id": f"h{len(qs)+1:03d}", "tier": tier, "intent": tier, "question": question,
                   "gold_tool": tool, "gold_args": args, "gold_kind": kind, "gold_params": params})

    depts = list(range(1, 21))
    rng.shuffle(depts)
    it = iter(depts * 3)

    # Tier A: paraphrases of the three tool intents
    for _ in range(4):
        d, m, f = next(it), rng.randint(1, 12), rng.choice((0.9, 1.0, 1.1))
        thr = round(exp * f, -3)
        add("A_paraphrase", "delayed",
            f"Which projects under department {code(d)} are running behind in month {m} of fiscal 2026? "
            f"I only care about the ones still holding more than {thr:,.0f} THB of unspent budget. Give me the ten with the most left, "
            f"with their budget figures and burn rate (used as a percentage of net).",
            "get_delayed_projects", {"dept_code": code(d), "fiscal_year": 2026, "month": m, "min_remain": float(thr)})
    for _ in range(4):
        d = next(it)
        add("A_paraphrase", "advances",
            f"Who in department {code(d)} has the biggest approval forms? List the ten largest with the staff member's name, "
            f"the department code, the document number and the amount.",
            "reconcile_staff_advances", {"dept_code": code(d)})
    for _ in range(4):
        ds = sorted(rng.sample(range(1, 21), rng.choice((2, 3))))
        m = rng.randint(1, 12)
        add("A_paraphrase", "summary",
            f"How do departments {', '.join(code(x) for x in ds)} compare in {MONTH_NAMES[m-1]} 2026 on budget, spend, what is left "
            f"and burn rate (spend as a percentage of budget)? One line per department.",
            "get_department_summary", {"dept_codes": [code(x) for x in ds], "fiscal_year": 2026, "month": m})

    # Tier B: variants outside the tools' parameters
    for _ in range(2):
        d, m = next(it), rng.randint(1, 12)
        thr = round(exp * 1.0, -3)
        add("B_variant", "delayed_top5",
            f"For department {code(d)}, month {m} of fiscal 2026, show only the top 5 projects by remaining budget among those above "
            f"{thr:,.0f} THB, with project code, name, net, used, remaining and burn rate (used/net in %).",
            kind="delayed_variant", params={"dept_code": code(d), "month": m, "months": [m], "min_remain": float(thr), "top_n": 5, "order": "desc"})
    for _ in range(2):
        d = next(it)
        thr = round(exp * 3 * 1.0, -3)
        add("B_variant", "delayed_q1",
            f"For department {code(d)}, combine months 1 to 3 of fiscal 2026 and list the projects whose combined remaining budget exceeds "
            f"{thr:,.0f} THB: the top 10 by remaining, with project code, name, net, used, remaining and burn rate (used/net in %).",
            kind="delayed_variant", params={"dept_code": code(d), "months": [1, 2, 3], "min_remain": float(thr), "top_n": 10, "order": "desc"})
    for _ in range(2):
        d, m = next(it), rng.randint(1, 12)
        thr = round(exp * 0.9, -3)
        add("B_variant", "delayed_least3",
            f"In department {code(d)}, month {m} of fiscal 2026, which 3 projects have the LEAST remaining budget while still exceeding "
            f"{thr:,.0f} THB? Show project code, name, net, used, remaining and burn rate (used/net in %).",
            kind="delayed_variant", params={"dept_code": code(d), "months": [m], "min_remain": float(thr), "top_n": 3, "order": "asc"})
    for _ in range(2):
        d = next(it)
        add("B_variant", "advances_smallest5",
            f"Show the 5 SMALLEST approval forms by amount for staff in department {code(d)}: staff name, department code, document number and amount.",
            kind="advances_variant", params={"dept_code": code(d), "top_n": 5, "order": "asc"})

    # Tier C: analytics outside the tools
    for _ in range(2):
        m = rng.randint(1, 12)
        add("C_analytic", "burn_rank",
            f"Which department had the highest burn rate (total used / total net, in %) in month {m} of fiscal 2026? Give the department code and the burn rate.",
            kind="dept_burn_rank", params={"month": m})
    for _ in range(2):
        d = next(it)
        add("C_analytic", "monthly_used",
            f"For department {code(d)}, list the total used budget for each month of fiscal 2026 (month number and total used).",
            kind="monthly_used", params={"dept_code": code(d)})
    for _ in range(2):
        d = next(it)
        thr = round(exp * 12 * rng.choice((0.9, 1.0)), -6)
        add("C_analytic", "count_projects",
            f"How many projects in department {code(d)} have more than {thr:,.0f} THB of total remaining budget over the whole of fiscal 2026 (all months)?",
            kind="count_projects", params={"dept_code": code(d), "min_remain": float(thr)})
    for _ in range(2):
        d = next(it)
        add("C_analytic", "top_staff_total",
            f"Which 3 staff members of department {code(d)} have the largest total amount across all of their approval forms? Show the name and the total amount.",
            kind="top_staff_total", params={"dept_code": code(d), "top_n": 3})
    for _ in range(2):
        d = next(it)
        add("C_analytic", "forms_count",
            f"How many approval forms were filed by staff members of department {code(d)}?",
            kind="forms_count", params={"dept_code": code(d)})

    # Tier D: traps (names instead of codes, relative months)
    for _ in range(2):
        d, m = next(it), rng.randint(1, 12)
        thr = round(exp * 1.0, -3)
        add("D_trap", "delayed_name",
            f"List the delayed projects of \"{name(d)}\" in month {m} of fiscal year 2026 with remaining unspent budget above {thr:,.0f} THB: top 10 by remaining budget, "
            f"with project code, name, net, used, remaining and burn rate (used/net in %).",
            "get_delayed_projects", {"dept_code": code(d), "fiscal_year": 2026, "month": m, "min_remain": float(thr)})
    for _ in range(2):
        a, b = rng.sample(range(1, 21), 2)
        a, b = sorted((a, b))
        m = rng.randint(1, 12)
        add("D_trap", "summary_name",
            f"Compare \"{name(a)}\" and \"{name(b)}\" for {MONTH_NAMES[m-1]} 2026: one row per department with department code, net, used, remaining and burn rate (used/net in %).",
            "get_department_summary", {"dept_codes": [code(a), code(b)], "fiscal_year": 2026, "month": m})
    for mm, label in ((12, "the last month"), (1, "the first month")):
        d = next(it)
        thr = round(exp * 1.0, -3)
        add("D_trap", "delayed_relative",
            f"For department {code(d)}, list the delayed projects in {label} of fiscal year 2026 whose remaining unspent budget exceeds {thr:,.0f} THB: top 10 by remaining, "
            f"with project code, name, net, used, remaining and burn rate (used/net in %).",
            "get_delayed_projects", {"dept_code": code(d), "fiscal_year": 2026, "month": mm, "min_remain": float(thr)})
    for mm, label in ((12, "December"), (1, "January")):
        d = next(it)
        add("D_trap", "advances_alias",
            f"Staff of department {code(d)}: which ten approval forms are the largest? Name, department code, document number, amount. (Fiscal year 2026, {label} reporting.)",
            "reconcile_staff_advances", {"dept_code": code(d)})
    rng.shuffle(qs)
    for i, q in enumerate(qs):
        q["id"] = f"h{i+1:03d}"
    return qs


if __name__ == "__main__":
    rows, out = int(sys.argv[1]), sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    qs = build(rows, seed)
    with open(out, "w") as fh:
        for q in qs:
            fh.write(json.dumps(q) + "\n")
    import collections
    print(out, len(qs), dict(collections.Counter(q["tier"] for q in qs)))
