# Fast-MCP Enterprise Benchmark Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](benchmark/test_real_800k.py)
[![Database Scale](https://img.shields.io/badge/Database%20Scale-800%2C000%20Rows-blue.svg)](benchmark/test_real_800k.py)
[![VES Score](https://img.shields.io/badge/VES%20Score-0.962-purple.svg)](benchmark/results/benchmark_summary.csv)
[![Execution Accuracy](https://img.shields.io/badge/Execution%20Accuracy-98.6%25-success.svg)](benchmark/results/benchmark_summary.csv)

Open-source evaluation harness and reproducible benchmark suite for measuring **Speed** and **Accuracy** in Large Language Model (LLM) conversational database interfaces and agentic systems across production-scale relational databases (**800,000+ ledger rows**).

> 📝 **Academic Note:** The associated research manuscript is currently under peer review. This repository provides the standalone evaluation harness, synthetic enterprise database generator, and raw telemetry data to ensure scientific transparency and reproducibility.

---

## ⚡ Overview & Motivation

Natural language interfaces to relational databases (NLIDB) powered by LLMs face severe runtime and accuracy bottlenecks in production enterprise environments. When querying large relational ledgers ($>10^5$ to $10^6$ rows), traditional zero-shot Text-to-SQL and exploratory ReAct database agents repeatedly formulate unindexed multi-table Cartesian joins, causing:
- **Combinatorial Join Timeouts:** Unindexed scans taking $>60$ to $>120$ seconds.
- **Exploratory Tool Thrashing:** ReAct agents squandering 4–8 turns and 6,000–9,000 tokens querying database metadata before execution.
- **Dynamic Typing Traps:** Silent aggregation errors from loose dynamic affinities (*e.g.*, SQLite evaluating numeric text lexicographically).

**Fast-MCP** introduces **Semantic Fast Tools** over the **Model Context Protocol (MCP)**:
- Pre-compiles recurring enterprise join paths into parameterized single-turn $O(\log N)$ primitives.
- Achieves **Sub-Second Streaming Latency (199–407 ms)** even over **800,000 transaction ledger records**.
- Yields a **Valid Efficiency Score (VES) of 0.962** on enterprise financial workloads.
- Eliminates 100% of exploratory tool thrashing, slashing token overhead by **87.5%**.

```
Comparative End-to-End Latency Profile (Logarithmic Scale - Uncapped Execution / No Timeout):
-------------------------------------------------------------------------------------------------
LangChain SQL Agent   : [======================================= ] 276.0s (4.6m / Multi-Turn Tool Thrashing)
DB-GPT-Hub (SFT)      : [======================================= ] 265.5s (4.4m / Full Cartesian Scan)
Naive Zero-Shot SQL   : [======================================= ] 263.5s (4.4m / Unindexed Cross-Join)
Vanna.ai (RAG)        : [===============================         ] 68.1s  (1.1m / DDL Vector RAG + Scan)
DIN-SQL               : [============================            ] 42.5s  (Decomposed 4-Step Pipeline)
DAIL-SQL              : [===========================             ] 38.9s  (Few-Shot Skeleton Prompting)
MAC-SQL               : [===========================             ] 34.7s  (4-Agent Collaboration Debate)
Proposed Fast-MCP     : [=                                       ] 0.40s  (⚡ Sub-Second / 407 ms Execution)
-------------------------------------------------------------------------------------------------
```

---

## 📊 Live Benchmark Results (800,000 Rows / Real-Scale Schema)

Empirical results measured directly on an authentic English enterprise database with **800,000 monthly transaction ledger rows** across an 8-table relational schema:
- `departments` (20 faculties/divisions)
- `projects` (cores - 200 projects)
- `activities` (800 activities)
- `expense_items` (2,400 categories)
- `transaction_statement` (**800,000 monthly ledger rows**)
- `staff_users` (1,000 staff members)
- `approval_forms` (20,000 approval requests)
- `advance_settle_forms` (15,000 borrowing & settlement forms)

| Query / Workload Type | Architecture / Paradigm | Database Latency | Total Turn Latency | Status & Efficiency |
| :--- | :--- | :---: | :---: | :---: |
| **1. Delayed Projects Audit** | **Fast-MCP (Semantic Fast Tool)** | **199.51 ms** | **320 ms** | ⚡ **Sub-Second (<0.2s)** |
| | Naive SQL 4-Table Join (with filter) | 201.63 ms | 510 ms | Normal execution |
| **2. Global Enterprise Scan** | Naive SQL 5-Table Join (omits filter) | 911.46 ms | 1,350 ms | 5-table scan across 800k rows |
| **3. Staff Advance Reconciliation** | 6-Table Join with `OR LIKE` condition | 72.49 ms | 520 ms | Filtered lookup |
| **4. Multi-Hop Risk Comparison** | **Fast-MCP (2x Parallel Tools + Synthesis)** | **407.15 ms** | **1,180 ms** | ⚡ **Sub-Second Execution** |
| | **Naive Multi-Hop Cartesian Cross Join** | **261,440 ms** | **263.5s (4.4 min)** | ⚠️ **Severe Delay (Unindexed Scan)** |

> 💡 **Real-world Impact:** When unindexed Cartesian joins are run on production API gateways with a 120s timeout limit, they terminate with `504 Gateway Timeout`. When executed to completion without timeouts, naive joins take over **4.35 to 4.60 minutes**, whereas **Fast-MCP** completes the exact same workload in **407 ms** (**>650x faster**).

---

## 🚀 Quickstart: Reproducing Results

Clone this repository and execute the automated benchmark runner:

```bash
git clone https://github.com/aodbee/fast-mcp-benchmark.git
cd fast-mcp-benchmark

# 1. Run the 800,000 Rows Real-Scale Multi-Table Join Benchmark
python3 benchmark/test_real_800k.py

# 2. Run the 100,000 Rows Standard Workload Suite (with VES scoring)
python3 benchmark/benchmark_suite.py
```

> 💾 **Database Storage Note:** The SQLite enterprise database file (`benchmark/data/enterprise_800k.db`, ~79 MB) is **generated automatically** by `setup_800k_db()` during script execution in approximately 10–15 seconds. It is excluded from Git tracking via `.gitignore` to keep the repository lightweight.

### Custom Scale Testing
To generate a custom database size (*e.g.*, 500,000 or 1,000,000 rows):
```bash
python3 benchmark/setup_db.py 500000
python3 benchmark/benchmark_suite.py
```

---

## 📁 Repository Structure

```
fast-mcp-benchmark/
├── README.md                          # Repository overview & evaluation guide
├── LICENSE                            # MIT License
└── benchmark/
    ├── test_real_800k.py              # Real-scale 800,000 rows multi-table join benchmark
    ├── setup_db.py                    # Database generator (English enterprise schema)
    ├── benchmark_suite.py             # Main evaluation suite runner
    ├── README.md                      # Benchmark manual & dataset specs
    └── results/
        ├── benchmark_results.json     # Detailed telemetry output
        ├── benchmark_summary.csv      # Tabular summary metrics
        └── scalability_results.csv    # Latency across row scales
```

---

## 📚 Citation

```bibtex
@article{fastmcp2026,
  author    = {Suphachai J.},
  title     = {Fast-MCP: Sub-Second Conversational Database Intelligence via Semantic Tool Abstraction and Empirical Evaluation on Enterprise Benchmarks},
  journal   = {Under Review},
  year      = {2026}
}
```
