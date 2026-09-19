#!/usr/bin/env python3
"""
Baseline 1: Naive Zero-Shot Text-to-SQL
Paradigm: Direct Schema Prompting into a Foundation LLM.
Characteristics:
  - Hands the entire database DDL (all 8 tables) in the prompt context.
  - Generates single SQL query without domain tools or pre-compiled indexes.
  - Susceptible to:
      1. Dynamic type affinity traps (TEXT stored decimals evaluated lexicographically).
      2. Missing index sequential scans on massive tables.
      3. Schema hallucination on deep foreign key join paths.
"""

import time
import sqlite3
from typing import Dict, Any, Tuple
import os
import sys

# Ensure benchmark directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_client import get_llm_client, clean_sql

SCHEMA_DDL = """
CREATE TABLE departments (
    dept_id INTEGER PRIMARY KEY,
    dept_code TEXT UNIQUE NOT NULL,
    dept_name TEXT NOT NULL,
    division TEXT NOT NULL,
    allocated_budget REAL NOT NULL
);
CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    project_code TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL
);
CREATE TABLE activities (
    activity_id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    activity_name TEXT NOT NULL,
    is_completed INTEGER DEFAULT 0,
    dept_code TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL
);
CREATE TABLE expense_items (
    item_id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    dept_code TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL
);
CREATE TABLE transaction_statement (
    statement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    dept_code TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    net_budget TEXT NOT NULL,
    used_budget TEXT NOT NULL,
    remain_budget TEXT NOT NULL,
    tx_date TEXT NOT NULL
);
CREATE TABLE staff_users (
    staff_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    position TEXT NOT NULL
);
CREATE TABLE approval_forms (
    doc_no TEXT PRIMARY KEY,
    staff_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    activity_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    dept_code TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL
);
CREATE TABLE advance_settle_forms (
    form_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    doc_no TEXT NOT NULL,
    advance_amount REAL NOT NULL,
    cleared_amount REAL NOT NULL,
    status TEXT NOT NULL,
    dept_code TEXT NOT NULL
);
"""

class NaiveZeroShotSQL:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.client = get_llm_client()

    def generate_prompt(self, natural_language_question: str) -> str:
        return f"""You are a database expert. Given the SQLite schema below, write an executable SQL query to answer the user's question.
Schema:
{SCHEMA_DDL}

Question: {natural_language_question}
Respond with only the SQL query:"""

    def map_question_to_sql(self, question: str) -> Tuple[str, int, float]:
        """Generates SQL using live LLM service (or deterministic fallback in mock mode)."""
        prompt = self.generate_prompt(question)
        system_prompt = "You are a senior database engineer. Return ONLY executable SQLite SQL without markdown fences or explanations."
        
        res = self.client.generate(prompt, system_prompt)
        sql = clean_sql(res.text)
        return sql, res.total_tokens, res.latency_ms

    def execute(self, question: str) -> Dict[str, Any]:
        sql, token_overhead, llm_latency_ms = self.map_question_to_sql(question)
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        t0 = time.perf_counter()
        valid_sql = True
        error_msg = None
        rows = []

        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except Exception as e:
            valid_sql = False
            error_msg = str(e)
        finally:
            db_time_ms = (time.perf_counter() - t0) * 1000.0
            conn.close()

        total_latency_ms = db_time_ms + llm_latency_ms

        return {
            "baseline": "Naive Zero-Shot SQL",
            "question": question,
            "generated_sql": sql.strip(),
            "valid_sql": valid_sql,
            "error": error_msg,
            "row_count": len(rows),
            "db_latency_ms": round(db_time_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "llm_latency_ms": round(llm_latency_ms, 2),
            "token_overhead": token_overhead,
            "turns": 1.0,
            "is_live": self.client.is_live
        }

if __name__ == "__main__":
    db = "benchmark/data/enterprise_800k.db"
    runner = NaiveZeroShotSQL(db)
    res = runner.execute("List the top delayed projects for Department 10010000 in fiscal year 2026 month 12")
    print(f"[{res['baseline']}] DB: {res['db_latency_ms']} ms | LLM: {res['llm_latency_ms']} ms | Total: {res['total_latency_ms']} ms | Valid: {res['valid_sql']}")
    print(f"SQL Generated:\n{res['generated_sql'][:160]}...")
