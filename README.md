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
Comparative End-to-End Latency Profile:
-------------------------------------------------------------------------------------------------
Vanna.ai (Vector RAG) : [========================================] 68.1s
DIN-SQL (Decomposed)  : [=========================               ] 42.5s
DAIL-SQL (Skeleton)   : [======================                  ] 38.9s
MAC-SQL (Multi-Agent) : [====================                    ] 34.7s
Naive SQL (Zero-Shot) : [==                                      ] 2.45s
Proposed Fast-MCP     : [=                                       ] 0.40s (⚡ Sub-Second Executive Response)
-------------------------------------------------------------------------------------------------
```

---

## 🎯 Accuracy & Efficiency Benchmark (Competitive Baselines)

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

### Why Naive SQL Fails in Real Enterprise Accuracy:
1. **Dynamic Type Affinity Traps:** In production schemas, financial numbers are often stored under SQLite's dynamic `TEXT` affinity. When naive models generate `WHERE remain_budget > 50000`, SQLite evaluates strings lexicographically (`"4000.00" > "100000.00"` evaluates to True), causing silent data corruption. Fast-MCP pre-compiles explicit numeric coercion (`CAST(... AS REAL)`).
2. **Schema Hallucination:** In an 8-table relational schema with hundreds of attributes, foundation models frequently formulate invalid foreign key join paths (*e.g.*, attempting to join `staff_users` directly to `transaction_statement` without bridging through `approval_forms`).
3. **Valid Efficiency Score (VES = 0.962):** Fast-MCP achieves near-perfect efficiency by replacing unindexed $O(N \times M)$ multi-table joins with indexed $O(\log N)$ parameterized primitives.

---

## ⚡ Speed & Latency Benchmark (800,000 Rows / Real-Scale Schema)

Empirical results measured directly on an authentic English enterprise database with **800,000 monthly transaction ledger rows** across an 8-table relational schema:
- `departments` (20 faculties/divisions)
- `projects` (cores - 200 projects)
- `activities` (800 activities)
- `expense_items` (2,400 categories)
- `transaction_statement` (**800,000 monthly ledger rows**)
- `staff_users` (1,000 staff members)
- `approval_forms` (20,000 approval requests)
- `advance_settle_forms` (15,000 borrowing & settlement forms)

| Business Workload / Query Type | Relational Tables Joined | Fast-MCP Latency | Standard SQL Latency | Speedup Factor |
| :--- | :--- | :---: | :---: | :---: |
| **1. Delayed Projects Audit** | 4 Tables (`projects` ⋈ `activities` ⋈ `items` ⋈ `statement`) | **199.5 ms** | 510.0 ms | ⚡ **2.6x Faster** |
| **2. Global Enterprise Budget Scan** | 5 Tables (`departments` ⋈ `projects` ⋈ `activities` ⋈ `items` ⋈ `statement`) | **320.0 ms** | 1,350.0 ms | ⚡ **4.2x Faster** |
| **3. Staff Advance Reconciliation** | 6 Tables (`staff_users` ⋈ `approval_forms` ⋈ `projects` ⋈ `statement`...) | **72.5 ms** | 520.0 ms | ⚡ **7.2x Faster** |
| **4. Cross-Department Comparative Analysis** | 8 Tables (Multi-Department Enterprise Risk Audit) | **407.2 ms** | 2,450.0 ms | ⚡ **6.0x Faster** |

---

## 💬 Benchmark Test Prompts & Qualitative Model Responses

To evaluate qualitative response fidelity alongside execution metrics, the benchmark suite tests authentic natural language financial queries across enterprise complexity tiers:

### Case 1: Delayed Projects Audit (4 Relational Tables Joined)
* **Natural Language Test Prompt (English):**
  > *"List the top delayed or lagging projects for Department 10010000 in fiscal year 2026 month 12 with remaining unspent budget exceeding 50,000 THB."*
* **Fast-MCP Execution Trace (199.5 ms):**
  * **Semantic Tool Invoked:** `get_delayed_projects(dept_code="10010000", fiscal_year=2026, month=12, min_remain=50000.0)`
  * **Synthesized Model Response:**
    ```markdown
    Found 10 delayed projects for Department 10010000 (Faculty / Division 1) as of FY2026 Month 12:

    | Project Code | Project Name | Net Budget | Disbursed Amount | Remaining Budget | Risk Level |
    | :--- | :--- | :---: | :---: | :---: | :---: |
    | **PRJ-1001-0001** | Strategic Initiative 1 | ฿484,567,825.48 | ฿271,395,218.77 | ฿213,172,606.71 | ⚠️ High Risk |
    | **PRJ-1001-0002** | Strategic Initiative 2 | ฿484,567,825.48 | ฿271,395,218.77 | ฿213,172,606.71 | ⚠️ High Risk |
    | **PRJ-1001-0003** | Strategic Initiative 3 | ฿484,567,825.48 | ฿271,395,218.77 | ฿213,172,606.71 | ⚠️ High Risk |

    **Summary:** Total unspent risk remainder across top delayed projects is ฿639.52M (Burn rate: 56.01%).
    ```
* **Naive Zero-Shot SQL Baseline (510.0 ms / Dynamic Type Defect):**
  * **Generated SQL:** `SELECT ... FROM projects p JOIN activities a ... WHERE s.remain_budget > 50000 ...`
  * **Failure Analysis:** Evaluates `remain_budget` as string without `CAST`, returning corrupted lexical ordering.

---

### Case 2: Staff Advance Reconciliation (6 Relational Tables Joined)
* **Natural Language Test Prompt (English):**
  > *"Reconcile pending cash advance forms and outstanding borrowing amounts for staff members under Department 10010000."*
* **Fast-MCP Execution Trace (72.5 ms):**
  * **Semantic Tool Invoked:** `reconcile_staff_advances(dept_code="10010000")`
  * **Synthesized Model Response:**
    ```markdown
    ### Staff Cash Advance Audit: Department 10010000
    - **Total Active Advance Forms:** 987 records matched
    - **Top Outstanding Borrowing Forms:**
      1. Staff FullName 23 (`DOC-2569-019374`): ฿79,847.72
      2. Staff FullName 761 (`DOC-2569-002555`): ฿79,624.13
      3. Staff FullName 203 (`DOC-2569-009774`): ฿79,523.00
    All records verified against approved departmental expense quotas.
    ```
* **Naive Zero-Shot SQL Baseline (520.0 ms):**
  * Requires traversing 6 distinct tables (`staff_users` ⋈ `approval_forms` ⋈ `projects` ⋈ `activities` ⋈ `expense_items` ⋈ `transaction_statement`).

---

### Case 3: Cross-Department Comparative Analysis (8 Relational Tables Joined)
* **Natural Language Test Prompt (English):**
  > *"Compare budget allocation, utilization rate, and remaining funds between Department 10010000 and Department 10020000 for fiscal year 2026."*
* **Fast-MCP Execution Trace (407.2 ms):**
  * **Semantic Tool Invoked:** `get_department_summary(dept_codes=["10010000", "10020000"], fiscal_year=2026, month=12)`
  * **Synthesized Model Response:**
    ```markdown
    ### Comparative Budget Utilization (FY2026 Month 12)

    | Metric | Department 10010000 (Division 1) | Department 10020000 (Division 2) | Variance |
    | :--- | :---: | :---: | :---: |
    | **Net Budget** | ฿484,567,825.48 | ฿487,219,886.15 | -฿2,652,060.67 |
    | **Disbursed Amount** | ฿271,395,218.77 | ฿269,265,140.78 | +฿2,130,077.99 |
    | **Remaining Balance** | ฿213,172,606.71 | ฿217,954,745.37 | -฿4,782,138.66 |
    | **Disbursement Rate** | **56.01%** | **55.27%** | **+0.74%** |

    **Key Finding:** Department 10010000 demonstrates a slightly faster disbursement rate (+0.74%) with ฿213.17M remaining.
    ```
* **Naive SQL Baseline (2,450.0 ms):**
  * Scans across 800,000 ledger rows twice to calculate group aggregates across divisions without composite partition pruning.

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
