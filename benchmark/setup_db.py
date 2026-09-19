#!/usr/bin/env python3
"""
Enterprise Database Generator for Benchmark Suite
Generates a realistic English enterprise financial & project database (SQLite)
with scalable transaction ledgers (default: 100,000 rows).
"""

import os
import sys
import sqlite3
import random
from datetime import datetime, timedelta

def create_database(db_path: str, num_ledger_rows: int = 100000):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"[Setup] Creating database at: {db_path} with {num_ledger_rows:,} ledger rows...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode for high performance
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")

    # 1. Departments Table
    cursor.execute("""
    CREATE TABLE departments (
        dept_id TEXT PRIMARY KEY,
        dept_code TEXT UNIQUE NOT NULL,
        dept_name TEXT NOT NULL,
        division TEXT NOT NULL,
        allocated_budget REAL NOT NULL
    );
    """)

    departments = [
        ("D101", "10100700", "Division of Planning and Strategy", "Central Administration", 4500000.0),
        ("D102", "10100600", "Division of Finance and Treasury", "Central Administration", 3800000.0),
        ("D103", "10201800", "Faculty of Dentistry", "Health Sciences", 6200000.0),
        ("D104", "10200600", "Faculty of Medicine", "Health Sciences", 12500000.0),
        ("D105", "10300100", "Faculty of Engineering", "Science and Technology", 8900000.0),
        ("D106", "10300200", "School of Information Technology", "Science and Technology", 7400000.0),
        ("D107", "10400100", "Faculty of Business and Economics", "Humanities and Social", 5100000.0),
        ("D108", "10102800", "Office of the President", "Central Administration", 9500000.0),
    ]
    cursor.executemany("INSERT INTO departments VALUES (?, ?, ?, ?, ?)", departments)

    # 2. Projects Table
    cursor.execute("""
    CREATE TABLE projects (
        project_id TEXT PRIMARY KEY,
        project_code TEXT UNIQUE NOT NULL,
        project_name TEXT NOT NULL,
        dept_id TEXT NOT NULL,
        fiscal_year INTEGER NOT NULL,
        approved_budget REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    );
    """)

    sample_project_names = [
        "Procurement and Logistics Capacity Development",
        "Operational Infrastructure and Facilities Maintenance",
        "Personnel Digital Transformation and Upskilling",
        "Institutional Knowledge Management and Repository",
        "Integrity and Transparency Assessment (ITA) Enhancement",
        "Academic Research Innovation and Grant Portfolio",
        "Smart Campus Network and Cybersecurity Modernization",
        "Community Outreach and Social Engagement Program",
        "International Accreditation and Exchange Initiative",
        "Student Career Readiness and Industry Placement"
    ]

    projects = []
    p_idx = 1
    for dept in departments:
        for p_name in sample_project_names:
            p_code = f"PRJ-{dept[1][:4]}-{p_idx:04d}"
            p_budget = round(random.uniform(150000, 900000), 2)
            projects.append((f"P{p_idx:04d}", p_code, f"{p_name} ({dept[2]})", dept[0], 2026, p_budget, "ACTIVE"))
            p_idx += 1

    cursor.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?)", projects)

    # 3. Activities Table
    cursor.execute("""
    CREATE TABLE activities (
        activity_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        activity_name TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
    );
    """)

    activities = []
    act_idx = 1
    for proj in projects:
        num_acts = random.randint(2, 5)
        for a in range(num_acts):
            activities.append((f"ACT{act_idx:05d}", proj[0], f"Sub-Activity Phase {a+1} for {proj[1]}", random.choice([0, 1])))
            act_idx += 1

    cursor.executemany("INSERT INTO activities VALUES (?, ?, ?, ?)", activities)

    # 4. Expense Items / Categories Table
    cursor.execute("""
    CREATE TABLE expense_categories (
        category_id TEXT PRIMARY KEY,
        activity_id TEXT NOT NULL,
        category_name TEXT NOT NULL,
        allocated_amount REAL NOT NULL,
        FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
    );
    """)

    categories = []
    cat_idx = 1
    cat_names = ["Contracted Services", "Equipment Procurement", "Travel & Per Diem", "Materials & Supplies", "Consulting Fees"]
    for act in activities:
        for c_name in random.sample(cat_names, 2):
            categories.append((f"CAT{cat_idx:06d}", act[0], c_name, round(random.uniform(20000, 120000), 2)))
            cat_idx += 1

    cursor.executemany("INSERT INTO expense_categories VALUES (?, ?, ?, ?)", categories)

    # 5. Transaction Ledger (Massive Table for Performance Testing)
    # Stored with TEXT dynamic typing for numerical balances (mirroring real dirty enterprise databases)
    cursor.execute("""
    CREATE TABLE transaction_ledger (
        ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id TEXT NOT NULL,
        dept_id TEXT NOT NULL,
        fiscal_year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        net_budget TEXT NOT NULL,
        disbursed_amount TEXT NOT NULL,
        remain_budget TEXT NOT NULL,
        transaction_date TEXT NOT NULL
    );
    """)

    print(f"[Setup] Generating {num_ledger_rows:,} transaction ledger records...")
    ledger_batch = []
    base_date = datetime(2025, 10, 1)

    for i in range(1, num_ledger_rows + 1):
        cat = random.choice(categories)
        dept = random.choice(departments)
        month = random.randint(1, 12)
        tx_date = (base_date + timedelta(days=random.randint(0, 360))).strftime("%Y-%m-%d")

        net = round(random.uniform(50000, 300000), 2)
        # Simulate realistic burn rates: some lagging (0-30%), some healthy (80-99%)
        burn_rate = random.choice([0.15, 0.35, 0.75, 0.92, 0.98])
        disbursed = round(net * burn_rate, 2)
        remain = round(net - disbursed, 2)

        # Store as string formatted text to replicate SQLite dynamic typing anomalies
        ledger_batch.append((cat[0], dept[0], 2026, month, f"{net:.2f}", f"{disbursed:.2f}", f"{remain:.2f}", tx_date))

        if len(ledger_batch) >= 10000:
            cursor.executemany("""
            INSERT INTO transaction_ledger 
            (category_id, dept_id, fiscal_year, month, net_budget, disbursed_amount, remain_budget, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ledger_batch)
            ledger_batch = []
            sys.stdout.write(f"\r  Inserted {i:,} / {num_ledger_rows:,} records...")
            sys.stdout.flush()

    if ledger_batch:
        cursor.executemany("""
        INSERT INTO transaction_ledger 
        (category_id, dept_id, fiscal_year, month, net_budget, disbursed_amount, remain_budget, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ledger_batch)

    print(f"\n[Setup] Building compound B-tree index for Fast-MCP semantic tool lookups...")
    # Fast-MCP Compound Index:
    cursor.execute("""
    CREATE INDEX idx_ledger_dept_year_month 
    ON transaction_ledger(dept_id, fiscal_year, month);
    """)
    cursor.execute("""
    CREATE INDEX idx_projects_dept_year 
    ON projects(dept_id, fiscal_year);
    """)

    conn.commit()
    conn.close()
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"[Setup] Database generation complete: {db_path} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/enterprise_bench.db")
    rows = 100000
    if len(sys.argv) > 1:
        rows = int(sys.argv[1])
    create_database(db_file, rows)
