# Fast-MCP Enterprise Benchmark & Evaluation Suite

This directory contains the reproducible benchmark suite and real evaluation data for the research paper:

> **Fast-MCP: Sub-Second Conversational Database Intelligence via Semantic Tool Abstraction and Empirical Evaluation on Enterprise Benchmarks**  
> *Status:* Under Review

***

## 📊 Overview

The benchmark evaluates the trade-offs between open-ended Text-to-SQL generation and **Semantic Fast Tools** over the **Model Context Protocol (MCP)** across standard English enterprise schemas, measuring:
1. **Execution Accuracy (EX):** Percentage of queries yielding ground-truth result sets.
2. **Valid SQL Rate (VSR):** Syntactic and semantic executability without runtime timeout.
3. **Valid Efficiency Score (VES):** The BIRD-standard efficiency metric penalizing slow, unindexed Cartesian scans relative to optimized gold queries.
4. **Physical Database Latency (ms):** Raw SQL execution time inside the SQLite engine.
5. **End-to-End Wall-Clock Latency (ms):** Total turn response time delivered to the user.
6. **Token & Turn Overhead:** Prompt/completion tokens and conversational turns per task.
7. **Database Row Scalability:** Latency scaling across $1,000$ to **800,000 transaction ledger rows**.

---

## 🗄️ Dataset Architecture & Multi-Table Relational Schema

The benchmark operates over a realistic English enterprise financial schema matching production systems:
- `departments`: Administrative units, division classifications, allocated budgets (20 units).
- `projects`: Strategic initiatives and approved funding (cores - 200 projects).
- `activities`: Sub-activities and operational phases (800 activities).
- `expense_items`: Expenditure categories and approved allocations (2,400 items).
- `transaction_statement`: **800,000 monthly ledger rows** (`TEXT` dynamic storage class).
- `staff_users`: Staff directory (1,000 records).
- `approval_forms`: Official budget requests (memo_forms - 20,000 records).
- `advance_settle_forms`: Cash advances and settlements (15,000 records).

Pre-compiled compound B-tree index for Fast-MCP:
```sql
CREATE INDEX idx_statement_dept_year_month 
ON transaction_statement(dept_code, fiscal_year, month);

CREATE INDEX idx_statement_project_year 
ON transaction_statement(project_id, fiscal_year);
```

---

## 🚀 Quickstart: Running Benchmarks

### 1. Run the Real-Scale 800,000 Rows Multi-Table Join Benchmark
```bash
python3 benchmark/test_real_800k.py
```

### 2. Run the Standard 100,000 Rows Workload Suite (with VES Scoring)
```bash
python3 benchmark/benchmark_suite.py
```

### 3. Custom Scale Generation
To generate a custom database size (*e.g.*, 500,000 rows):
```bash
python3 benchmark/setup_db.py 500000
python3 benchmark/benchmark_suite.py
```

---

## 📈 Real Benchmark Results Summary (800,000 Ledger Rows)

| Query / Workload Type | Architecture / Paradigm | Database Latency | Total Turn Latency | Status & Efficiency |
| :--- | :--- | :---: | :---: | :---: |
| **1. Delayed Projects Audit** | **Fast-MCP (Semantic Fast Tool)** | **199.51 ms** | **320 ms** | ⚡ **Sub-Second (<0.2s)** |
| | Naive SQL 4-Table Join (with filter) | 201.63 ms | 510 ms | Normal execution |
| **2. Global Enterprise Scan** | Naive SQL 5-Table Join (omits filter) | 911.46 ms | 1,350 ms | 5-table scan across 800k rows |
| **3. Staff Advance Reconciliation** | 6-Table Join with `OR LIKE` condition | 72.49 ms | 520 ms | Filtered lookup |
| **4. Multi-Hop Risk Comparison** | **Fast-MCP (2x Parallel Tools + Synthesis)** | **407.15 ms** | **1,180 ms** | ⚡ **Sub-Second Execution** |
| | **Naive Multi-Hop Cartesian Cross Join** | **>261,000 ms** | **>4.35 min** | ❌ **TIMEOUT (>120.0s)** |

> ⚠️ **Root Cause of `>120.0s (TIMEOUT)` in Production:** When LLMs generate unindexed cross-departmental Cartesian joins between large transaction subsets ($39,747 \text{ rows} \times 39,824 \text{ rows} = 1,582,884,528$ comparisons), query execution in SQLite takes **over 4.35 minutes (>261 seconds)**. Production API gateways (with a standard 120s timeout limit) cut off execution with `504 Gateway Timeout`. Fast-MCP completely eliminates this bottleneck by decomposing the query into compound-indexed single-turn queries completing in **407 ms**.

---

## 📁 Output Artifacts

All benchmark runs export structured telemetry to `benchmark/results/`:
- [`benchmark_results.json`](results/benchmark_results.json): Full execution telemetry, timestamps, and parameters.
- [`benchmark_summary.csv`](results/benchmark_summary.csv): Tabular metric breakdown across workloads.
- [`scalability_results.csv`](results/scalability_results.csv): Physical database query execution times across row scales.

---

## 📚 Citation

If you use this benchmark or Fast-MCP architecture in your research, please cite:

```bibtex
@article{fastmcp2026,
  author    = {Suphachai J.},
  title     = {Fast-MCP: Sub-Second Conversational Database Intelligence via Semantic Tool Abstraction and Empirical Evaluation on Enterprise Benchmarks},
  journal   = {Under Review},
  year      = {2026}
}
```
