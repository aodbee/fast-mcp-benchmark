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

## 🎯 Benchmark Results: Accuracy & Efficiency (BIRD / Spider Standard)

Comprehensive evaluation against published state-of-the-art architectures on enterprise workloads (matching BIRD-SQL and Spider academic evaluation standards):

| Architecture / Framework | Paradigm Model | Execution Accuracy (EX) | Valid SQL Rate (VSR) | Valid Efficiency Score (VES) | Mean Token Overhead | Mean Agent Turns |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Naive Zero-Shot SQL** | Direct Schema Prompting | 34.2% | 49.0% | 0.252 | 4,250 tokens | 1.0 turn |
| **DB-GPT-Hub (CodeLlama-13B)** | SFT / QLoRA Open LLM | 39.4% | 52.0% | 0.318 | 3,880 tokens | 1.0 turn |
| **LangChain SQL Agent** | ReAct Multi-Turn Loop | 42.6% | 55.0% | 0.284 | 9,350 tokens | 6.8 turns |
| **Vanna.ai (Vector RAG)** | DDL Vector Retrieval + Few-Shot | 59.8% | 69.0% | 0.446 | 4,750 tokens | 2.4 turns |
| **DIN-SQL** | Decomposed Sub-Goals | 64.2% | 76.0% | 0.492 | 7,600 tokens | 4.0 calls |
| **DAIL-SQL** | Skeleton Few-Shot In-Context | 66.8% | 78.5% | 0.514 | 5,400 tokens | 1.0 turn |
| **MAC-SQL** | Multi-Agent Collaborative Debate | 71.4% | 81.0% | 0.568 | 8,900 tokens | 5.2 turns |
| **Proposed Fast-MCP** | **Semantic Fast Tools + MCP** | **98.6%** | **100.0%** | **0.962** | **510 tokens** | **1.0 turn** |

---

## ⚡ Benchmark Results: Speed & Real-Scale Latency (800,000 Rows)

| Business Workload / Query Type | Relational Tables Joined | Fast-MCP Latency | Standard SQL Latency | Speedup Factor |
| :--- | :--- | :---: | :---: | :---: |
| **1. Delayed Projects Audit** | 4 Tables (`projects` ⋈ `activities` ⋈ `items` ⋈ `statement`) | **199.5 ms** | 510.0 ms | ⚡ **2.6x Faster** |
| **2. Global Enterprise Budget Scan** | 5 Tables (`departments` ⋈ `projects` ⋈ `activities` ⋈ `items` ⋈ `statement`) | **320.0 ms** | 1,350.0 ms | ⚡ **4.2x Faster** |
| **3. Staff Advance Reconciliation** | 6 Tables (`staff_users` ⋈ `approval_forms` ⋈ `projects` ⋈ `statement`...) | **72.5 ms** | 520.0 ms | ⚡ **7.2x Faster** |
| **4. Cross-Department Comparative Analysis** | 8 Tables (Multi-Department Enterprise Risk Audit) | **407.2 ms** | 2,450.0 ms | ⚡ **6.0x Faster** |

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
