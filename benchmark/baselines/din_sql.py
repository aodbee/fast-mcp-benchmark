#!/usr/bin/env python3
"""
Baseline 4: DIN-SQL (NeurIPS 2023)
Paper: "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction"
Characteristics:
  - Decomposes Text-to-SQL into 4 distinct sequential LLM sub-tasks:
      Step 1: Schema Linking (identifying referenced tables and foreign keys)
      Step 2: Query Classification (Easy, Non-Nested Complex, Nested Complex)
      Step 3: Decomposed SQL Generation (solving sub-problems separately)
      Step 4: Self-Correction (checking syntax errors and conditions)
  - High accuracy at the cost of 4.0 sequential LLM calls and substantial token overhead.
"""

import os
import sys
import time
import sqlite3
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_client import get_llm_client, clean_sql

class DINSQL:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.client = get_llm_client()

    def step1_schema_linking(self, question: str) -> Tuple[str, int, float]:
        prompt = f"Schema Linking: Given the enterprise financial database (tables: departments, projects, activities, expense_items, transaction_statement, staff_users, approval_forms, advance_settle_forms), identify all tables and columns needed to answer:\nQuestion: {question}\nList the schema links:"
        res = self.client.generate(prompt)
        return res.text.strip(), res.total_tokens, res.latency_ms

    def step2_query_classification(self, question: str, links: str) -> Tuple[str, int, float]:
        prompt = f"Classify the SQL query complexity for this question as EASY, NON-NESTED COMPLEX, or NESTED COMPLEX.\nQuestion: {question}\nSchema Links: {links}\nClassification:"
        res = self.client.generate(prompt)
        return res.text.strip(), res.total_tokens, res.latency_ms

    def step3_generate_decomposed_sql(self, question: str, links: str, cls_type: str) -> Tuple[str, int, float]:
        prompt = f"""Generate a decomposed SQLite query for this question using CTEs if complex.
Schema: tables include projects (project_id, project_code, project_name, dept_code, fiscal_year), transaction_statement (statement_id, project_id, dept_code, fiscal_year, month, net_budget, used_budget, remain_budget). Note: budget amounts are stored as TEXT and need CAST(... AS REAL).
Question: {question}
Links: {links}
Complexity: {cls_type}
Generate SQLite SQL:"""
        res = self.client.generate(prompt)
        return clean_sql(res.text), res.total_tokens, res.latency_ms

    def step4_self_correction(self, raw_sql: str) -> Tuple[str, int, float]:
        prompt = f"Review this SQLite query for syntax errors, group by issues, and type casting. Output ONLY the corrected executable SQL:\n{raw_sql}"
        res = self.client.generate(prompt)
        return clean_sql(res.text), res.total_tokens, res.latency_ms

    def run(self, question: str) -> Dict[str, Any]:
        if not self.client.is_live:
            return self._run_mock(question)

        # 4 Sequential LLM Steps
        links, tok1, lat1 = self.step1_schema_linking(question)
        cls_type, tok2, lat2 = self.step2_query_classification(question, links)
        raw_sql, tok3, lat3 = self.step3_generate_decomposed_sql(question, links, cls_type)
        final_sql, tok4, lat4 = self.step4_self_correction(raw_sql)

        total_tokens = tok1 + tok2 + tok3 + tok4
        total_llm_latency_ms = lat1 + lat2 + lat3 + lat4

        # Execute on database
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        t_db_start = time.perf_counter()
        valid_sql = True
        error_msg = None
        rows = []
        try:
            cur.execute(final_sql)
            rows = cur.fetchall()
        except Exception as e:
            valid_sql = False
            error_msg = str(e)
        finally:
            db_ms = (time.perf_counter() - t_db_start) * 1000.0
            conn.close()

        total_latency_ms = db_ms + total_llm_latency_ms

        return {
            "baseline": "DIN-SQL (NeurIPS 2023)",
            "question": question,
            "classification": cls_type[:40],
            "schema_links": links[:60],
            "generated_sql": final_sql.strip(),
            "db_latency_ms": round(db_ms, 2),
            "llm_latency_ms": round(total_llm_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "token_overhead": total_tokens,
            "llm_calls": 4.0,
            "turns": 4.0,
            "valid_sql": valid_sql,
            "error": error_msg,
            "row_count": len(rows),
            "is_live": True
        }

    def _run_mock(self, question: str) -> Dict[str, Any]:
        time.sleep(0.12) # simulated 4 steps
        sql = """
        WITH DeptStatement AS (
            SELECT statement_id, item_id, project_id, dept_code, fiscal_year, month,
                   CAST(net_budget AS REAL) as net,
                   CAST(used_budget AS REAL) as used,
                   CAST(remain_budget AS REAL) as remain
            FROM transaction_statement
            WHERE dept_code = '10010000' AND fiscal_year = 2026 AND month = 12
        )
        SELECT p.project_code, p.project_name,
               SUM(s.net) as total_net,
               SUM(s.used) as total_used,
               SUM(s.remain) as total_remain
        FROM projects p
        JOIN DeptStatement s ON p.project_id = s.project_id
        GROUP BY p.project_code, p.project_name
        HAVING total_remain > 50000
        ORDER BY total_remain DESC LIMIT 10;
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        t_db_start = time.perf_counter()
        cur.execute(sql)
        rows = cur.fetchall()
        db_ms = (time.perf_counter() - t_db_start) * 1000.0
        conn.close()

        total_latency_ms = db_ms + 1800.0 + 120.0

        return {
            "baseline": "DIN-SQL (NeurIPS 2023)",
            "question": question,
            "classification": "NON-NESTED COMPLEX (JOIN + GROUP BY)",
            "schema_links": "projects, transaction_statement",
            "generated_sql": sql.strip(),
            "db_latency_ms": round(db_ms, 2),
            "llm_latency_ms": 1920.0,
            "total_latency_ms": round(total_latency_ms, 2),
            "token_overhead": 7600,
            "llm_calls": 4.0,
            "turns": 4.0,
            "valid_sql": True,
            "row_count": len(rows),
            "is_live": False
        }

if __name__ == "__main__":
    db = "benchmark/data/enterprise_800k.db"
    dinsql = DINSQL(db)
    res = dinsql.run("List the top delayed projects for Department 10010000 in fiscal year 2026 month 12")
    print(f"[{res['baseline']}] Calls: {res['llm_calls']} | Total: {res['total_latency_ms']} ms | Valid: {res['valid_sql']}")
