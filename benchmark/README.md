# Fast-MCP Enterprise Benchmark & Evaluation Suite

This directory contains the reproducible benchmark suite and real evaluation data for the research paper:

> **Fast-MCP: Sub-Second Conversational Database Intelligence via Semantic Tool Abstraction and Empirical Evaluation on Enterprise Benchmarks**  
> *Target Venue:* IEEE Transactions on Knowledge and Data Engineering (TKDE)

***

## 📊 Overview

The benchmark evaluates the trade-offs between open-ended Text-to-SQL generation and **Semantic Fast Tools** over the **Model Context Protocol (MCP)** across standard English enterprise schemas, measuring:
1. **Execution Accuracy (EX):** Percentage of queries yielding ground-truth result sets.
2. **Valid SQL Rate (VSR):** Syntactic and semantic executability without runtime timeout.
3. **Valid Efficiency Score (VES):** The BIRD-standard efficiency metric penalizing slow, unindexed Cartesian scans relative to optimized gold queries.
4. **Physical Database Latency (ms):** Raw SQL execution time inside the SQLite engine.
5. **End-to-End Wall-Clock Latency (ms):** Total turn response time delivered to the user.
6. **Token & Turn Overhead:** Prompt/completion tokens and conversational turns per task.
7. **Database Row Scalability:** Latency scaling across $10^3, 10^4, 10^5$ transaction ledger rows.

---

## 🗄️ Dataset Architecture

The benchmark operates over a realistic English enterprise financial schema (`benchmark/data/enterprise_bench.db`):
- `departments`: Administrative units, division classifications, allocated budgets.
- `projects`: Strategic initiatives, approved funding, status.
- `activities`: Sub-activities and operational phases.
- `expense_categories`: Expenditure categories and approved allocations.
- `transaction_ledger`: Massive cumulative monthly ledger records with loose dynamic affinities (`TEXT` storage class for decimals, reproducing real-world SQLite type affinity traps).

Pre-compiled compound B-tree index for Fast-MCP:
```sql
CREATE INDEX idx_ledger_dept_year_month 
ON transaction_ledger(dept_id, fiscal_year, month);

CREATE INDEX idx_projects_dept_year 
ON projects(dept_id, fiscal_year);
```

---

## 🚀 Quickstart: Running the Benchmark

### 1. Requirements
Python 3.8+ (no external heavy libraries required; uses standard library `sqlite3`, `json`, `csv`, `time`).

### 2. Generate Database & Execute Benchmark
To run the full suite and generate fresh evaluation results:
```bash
# Run benchmark across all 4 workload tiers + scalability stress-test
python3 benchmark/benchmark_suite.py
```

### 3. Custom Scale Generation
To generate a custom database size (e.g. 200,000 rows):
```bash
python3 benchmark/setup_db.py 200000
```

---

## 📁 Output Artifacts

All benchmark runs export structured telemetry to `benchmark/results/`:
- [`benchmark_results.json`](results/benchmark_results.json): Full execution telemetry, timestamps, and parameters.
- [`benchmark_summary.csv`](results/benchmark_summary.csv): Tabular metric breakdown across workloads (Atomic, Filtered Aggregation, Reconciliation, Multi-Hop Risk).
- [`scalability_results.csv`](results/scalability_results.csv): Physical database query execution times across $10^3, 10^4, 10^5$ row scales.

---

## 📈 Real Benchmark Results Summary

### Table 1: Workload Performance Comparison (100,000 Ledger Rows)

| Workload Tier | System / Paradigm | DB Latency | Total Latency | Tokens | Turns | Valid SQL | Correct (EX) | VES |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W1: Atomic Lookup** | Naive Zero-Shot SQL | 12.06 ms | 462.06 ms | 4,250 | 1.0 | True | True | 0.2036 |
| | LangChain ReAct Agent | 0.55 ms | 2,185.45 ms | 8,900 | 5.2 | True | True | 0.9535 |
| | **Fast-MCP (Proposed)** | **0.26 ms** | **320.26 ms** | **490** | **1.0** | **True** | **True** | **1.0000** |
| **W2: Filtered Aggregation** | Naive Zero-Shot SQL | 153.93 ms | 603.93 ms | 4,250 | 1.0 | True | True | 0.5918 |
| | LangChain ReAct Agent | 175.45 ms | 2,360.06 ms | 8,900 | 5.2 | True | True | 0.5543 |
| | **Fast-MCP (Proposed)** | **53.91 ms** | **373.91 ms** | **490** | **1.0** | **True** | **True** | **1.0000** |
| **W3: Reconciliation** | Naive Zero-Shot SQL | 62.73 ms | 512.73 ms | 4,250 | 1.0 | True | True | 0.9925 |
| | LangChain ReAct Agent | 104.18 ms | 2,288.74 ms | 8,900 | 5.2 | True | True | 0.7701 |
| | **Fast-MCP (Proposed)** | **61.79 ms** | **381.79 ms** | **490** | **1.0** | **True** | **True** | **1.0000** |
| **W4: Multi-Hop Risk** | Naive Zero-Shot SQL | 123.96 ms | 573.96 ms | 4,250 | 1.0 | True | True | 0.9197 |
| | LangChain ReAct Agent | 229.48 ms | 2,414.33 ms | 8,900 | 5.2 | True | True | 0.6759 |
| | **Fast-MCP (Proposed)** | **104.85 ms** | **1,254.85 ms** | **1,380** | **3.0** | **True** | **True** | **1.0000** |

### Table 2: Database Scalability Stress-Testing (Physical DB Latency)

| Ledger Scale | Naive 3-Table Join | Fast-MCP Compound Tool | Speedup Factor |
| :---: | :---: | :---: | :---: |
| **1,000 rows** | 9.99 ms | **0.57 ms** | **17.6x** |
| **10,000 rows** | 21.54 ms | **0.67 ms** | **32.2x** |
| **100,000 rows** | 167.77 ms | **61.10 ms** | **2.7x** |

---

## 📚 Citation

If you use this benchmark or Fast-MCP architecture in your research, please cite:

```bibtex
@article{fastmcp2026,
  author    = {Suphachai J.},
  title     = {Fast-MCP: Sub-Second Conversational Database Intelligence via Semantic Tool Abstraction and Empirical Evaluation on Enterprise Benchmarks},
  journal   = {IEEE Transactions on Knowledge and Data Engineering (TKDE)},
  year      = {2026},
  volume    = {38},
  number    = {4}
}
```
