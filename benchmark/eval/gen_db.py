#!/usr/bin/env python3
"""Seeded generator for the evaluation database (7 tables, scalable ledger).

Differences from benchmark/test_real_800k.py:
  - random.Random(seed): output is reproducible.
  - transaction_statement.project_id holds the project of the item's activity
    (the old generator stored the activity_id there).
  - 7 tables. advance_settle_forms is not generated.
  - Indexes are created by create_indexes() so ablations can drop them.

Usage: python3 gen_db.py <db_path> <ledger_rows> [seed]
"""
import os
import sqlite3
import sys
import random

INDEXES = {
    "idx_statement_dept_year_month": "CREATE INDEX idx_statement_dept_year_month ON transaction_statement(dept_code, fiscal_year, month)",
    "idx_statement_item": "CREATE INDEX idx_statement_item ON transaction_statement(item_id)",
    "idx_statement_project_year": "CREATE INDEX idx_statement_project_year ON transaction_statement(project_id, fiscal_year)",
    "idx_projects_dept": "CREATE INDEX idx_projects_dept ON projects(dept_code, fiscal_year)",
    "idx_activities_proj": "CREATE INDEX idx_activities_proj ON activities(project_id)",
    "idx_staff_dept": "CREATE INDEX idx_staff_dept ON staff_users(dept_code)",
    "idx_forms_staff": "CREATE INDEX idx_forms_staff ON approval_forms(staff_id)",
}

DDL = """
CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_code TEXT UNIQUE NOT NULL, dept_name TEXT NOT NULL, division TEXT NOT NULL, allocated_budget REAL NOT NULL);
CREATE TABLE projects (project_id INTEGER PRIMARY KEY, project_code TEXT UNIQUE NOT NULL, project_name TEXT NOT NULL, dept_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL, approved_budget REAL NOT NULL);
CREATE TABLE activities (activity_id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, activity_name TEXT NOT NULL, is_completed INTEGER DEFAULT 0, dept_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL);
CREATE TABLE expense_items (item_id INTEGER PRIMARY KEY, activity_id INTEGER NOT NULL, item_name TEXT NOT NULL, allocated_amount REAL NOT NULL, dept_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL);
CREATE TABLE staff_users (staff_id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL, full_name TEXT NOT NULL, dept_code TEXT NOT NULL, position TEXT NOT NULL);
CREATE TABLE approval_forms (doc_no TEXT PRIMARY KEY, staff_id INTEGER NOT NULL, project_id INTEGER NOT NULL, activity_id INTEGER NOT NULL, amount REAL NOT NULL, dept_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL);
CREATE TABLE transaction_statement (statement_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, project_id INTEGER NOT NULL, dept_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL, month INTEGER NOT NULL, net_budget TEXT NOT NULL, used_budget TEXT NOT NULL, remain_budget TEXT NOT NULL, tx_date TEXT NOT NULL);
"""


def create_indexes(conn, names=None):
    for name, sql in INDEXES.items():
        if names is None or name in names:
            conn.execute(sql)
    conn.commit()


def drop_indexes(conn, names):
    for name in names:
        conn.execute(f"DROP INDEX IF EXISTS {name}")
    conn.commit()


def generate(path, ledger_rows, seed=42):
    rng = random.Random(seed)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.executescript(DDL)

    depts = [(i, f"10{i:02d}0000", f"Faculty / Division {i}", "Academic" if i > 5 else "Administration", 10000000.0 + i * 500000) for i in range(1, 21)]
    conn.executemany("INSERT INTO departments VALUES (?,?,?,?,?)", depts)

    projects, pid = [], 1
    for d in depts:
        for p in range(10):
            projects.append((pid, f"PRJ-{d[1][:4]}-{pid:04d}", f"Strategic Initiative {pid} ({d[2]})", d[1], 2026, 500000.0 + p * 25000))
            pid += 1
    conn.executemany("INSERT INTO projects VALUES (?,?,?,?,?,?)", projects)

    acts, aid = [], 1
    for p in projects:
        for a in range(4):
            acts.append((aid, p[0], f"Activity Phase {a+1} for {p[1]}", rng.choice([0, 1]), p[3], 2026))
            aid += 1
    conn.executemany("INSERT INTO activities VALUES (?,?,?,?,?,?)", acts)

    items, iid = [], 1
    for a in acts:
        for k in range(3):
            items.append((iid, a[0], f"Expense Item {iid} (Category {k+1})", 50000.0, a[4], 2026))
            iid += 1
    conn.executemany("INSERT INTO expense_items VALUES (?,?,?,?,?,?)", items)

    users = []
    for u in range(1, 1001):
        users.append((u, f"FirstName_{u}", f"LastName_{u}", f"Staff FullName {u}", rng.choice(depts)[1], "Staff Analyst"))
    conn.executemany("INSERT INTO staff_users VALUES (?,?,?,?,?,?)", users)

    forms = []
    for f in range(1, 20001):
        a = rng.choice(acts)
        u = rng.choice(users)
        forms.append((f"DOC-2569-{f:06d}", u[0], a[1], a[0], round(rng.uniform(5000, 80000), 2), a[4], 2026))
    conn.executemany("INSERT INTO approval_forms VALUES (?,?,?,?,?,?,?)", forms)

    act_project = {a[0]: a[1] for a in acts}
    batch = []
    sql = "INSERT INTO transaction_statement (item_id, project_id, dept_code, fiscal_year, month, net_budget, used_budget, remain_budget, tx_date) VALUES (?,?,?,?,?,?,?,?,?)"
    for _ in range(ledger_rows):
        it = rng.choice(items)
        month = rng.randint(1, 12)
        net = round(rng.uniform(40000, 250000), 2)
        used = round(net * rng.choice([0.15, 0.40, 0.70, 0.95]), 2)
        remain = round(net - used, 2)
        batch.append((it[0], act_project[it[1]], it[4], 2026, month, f"{net:.2f}", f"{used:.2f}", f"{remain:.2f}", f"2026-{month:02d}-15"))
        if len(batch) >= 50000:
            conn.executemany(sql, batch)
            batch = []
    if batch:
        conn.executemany(sql, batch)
    conn.commit()
    create_indexes(conn)
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    out, rows = sys.argv[1], int(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    generate(out, rows, seed)
    print(f"{out}: {rows} ledger rows, seed={seed}, {os.path.getsize(out)/1e6:.1f} MB")
