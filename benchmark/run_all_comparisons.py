#!/usr/bin/env python3
"""
Fast-MCP Unified Baseline Comparison Runner
Runs all 8 systems on the real enterprise relational database:
  1. Naive Zero-Shot Text-to-SQL
  2. LangChain SQL Agent (ReAct)
  3. Vanna.ai (Vector RAG)
  4. DIN-SQL (NeurIPS 2023)
  5. MAC-SQL (IEEE TKDE 2024)
  6. DAIL-SQL (VLDB 2024)
  7. DB-GPT-Hub (SFT Open LLM)
  8. Proposed Fast-MCP Harness
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import get_llm_client
from baselines.naive_sql import NaiveZeroShotSQL
from baselines.langchain_react import LangChainSQLAgent
from baselines.vanna_rag import VannaRAG
from baselines.din_sql import DINSQL
from baselines.mac_sql import MACSQL
from baselines.dail_sql import DAILSQL
from baselines.db_gpt_hub import DBGPTHub
from fast_mcp.fast_agent import FastMCPAgent

DB_PATH = "benchmark/data/enterprise_800k.db"
if not os.path.exists(DB_PATH):
    print("Database not found, building 800,000-row enterprise database...")
    from test_real_800k import setup_800k_db
    setup_800k_db()

def run_all_baselines(question: str):
    client = get_llm_client()
    
    print("=" * 115)
    print(f"  FAST-MCP vs SOTA BASELINE EVALUATION (800,000-ROW ENTERPRISE DATABASE)")
    print(f"  Test Question: \"{question}\"")
    if client.is_live:
        print(f"  Execution Mode: 🟢 LIVE SERVICE ({client.provider.upper()} | Model: {client.model})")
    else:
        print(f"  Execution Mode: 🟡 DETERMINISTIC OFFLINE BENCHMARK (Copy .env.example to .env for live mode)")
    print("=" * 115)

    systems = [
        ("Naive Zero-Shot SQL", NaiveZeroShotSQL(DB_PATH).execute),
        ("LangChain SQL Agent", LangChainSQLAgent(DB_PATH).run),
        ("Vanna.ai (Vector RAG)", VannaRAG(DB_PATH).run),
        ("DIN-SQL (NeurIPS '23)", DINSQL(DB_PATH).run),
        ("MAC-SQL (TKDE '24)", MACSQL(DB_PATH).run),
        ("DAIL-SQL (VLDB '24)", DAILSQL(DB_PATH).run),
        ("DB-GPT-Hub (SFT)", DBGPTHub(DB_PATH).run),
        ("Proposed Fast-MCP", FastMCPAgent(DB_PATH).run),
    ]

    results = []
    for name, runner in systems:
        print(f"-> Executing: {name:<25} ... ", end="", flush=True)
        try:
            res = runner(question)
            db_lat = res.get('db_latency_ms', 0.0)
            tot_lat = res.get('total_latency_ms', 0.0)
            print(f"Done in {tot_lat:8.2f} ms | DB Latency: {db_lat:8.2f} ms")
            results.append(res)
        except Exception as e:
            print(f"FAILED: {e}")

    print("\n" + "=" * 115)
    print(f"{'System / Framework':<26} | {'DB Latency':<12} | {'LLM Latency':<13} | {'Total Latency':<14} | {'Tokens':<9} | {'Turns':<6} | {'Valid'}")
    print("-" * 115)
    for r in results:
        sys_name = r.get("baseline") or r.get("system")
        db_lat = f"{r.get('db_latency_ms', 0.0):.2f} ms"
        llm_lat = f"{r.get('llm_latency_ms', 0.0):.2f} ms"
        tot_lat = f"{r.get('total_latency_ms', 0.0):.2f} ms"
        tok = str(r.get('token_overhead', 0))
        turns = str(r.get('turns') or r.get('turns_taken') or r.get('agent_turns') or r.get('llm_calls', 1.0))
        valid = "✅ YES" if r.get('valid_sql', True) else "❌ NO"
        print(f"{sys_name:<26} | {db_lat:<12} | {llm_lat:<13} | {tot_lat:<14} | {tok:<9} | {turns:<6} | {valid}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    test_q = "List the top delayed projects for Department 10010000 in fiscal year 2026 month 12 with remaining unspent budget exceeding 50,000 THB"
    run_all_baselines(test_q)
