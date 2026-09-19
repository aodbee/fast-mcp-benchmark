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

## ⚙️ Configuration & Live LLM Integration (.env)

The benchmark suite features a unified, zero-heavy-dependency client (`benchmark/llm_client.py`) that connects all 8 evaluation paradigms to real foundation model APIs or deterministic offline execution.

### Step 1: Copy Environment Template
```bash
cp .env.example .env
```

### Step 2: Configure Provider & API Keys in `.env`

* **Option 1: Google Gemini (Recommended / Direct):**
  ```env
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=your_gemini_api_key_here
  GEMINI_MODEL=gemini-3.8-flash
  ```
* **Option 2: OpenAI / Campus AI Gateway (UP / KKU AI Gateway):**
  ```env
  LLM_PROVIDER=openai
  OPENAI_API_KEY=your_gateway_key_here
  OPENAI_BASE_URL=https://gen.ai.kku.ac.th/upacth/api/v1  # or https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o-mini
  ```
* **Option 3: Anthropic Claude:**
  ```env
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=your_anthropic_api_key_here
  ANTHROPIC_MODEL=claude-3-5-haiku-20241022
  ```
* **Option 4: Offline Deterministic Mock Mode:**
  If no API key is specified or `LLM_PROVIDER=mock`, the benchmark runs locally using deterministic execution traces.

---

## 🚀 Quickstart: Running Benchmarks

### 1. Run the Unified Comparison Evaluating All 8 Architectures (Live or Mock)
```bash
python3 benchmark/run_all_comparisons.py
```

### 2. Run the Real-Scale 800,000 Rows Multi-Table Join Benchmark
```bash
python3 benchmark/test_real_800k.py
```

### 3. Run the Standard 100,000 Rows Workload Suite (with VES Scoring)
```bash
python3 benchmark/benchmark_suite.py
```

### 4. Custom Scale Generation
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
