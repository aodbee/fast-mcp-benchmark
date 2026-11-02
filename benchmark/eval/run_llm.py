#!/usr/bin/env python3
"""Live-LLM evaluation of Fast-MCP and seven prompt-level baselines on the 800k-row database.

Every system gets the same question, the same DDL and the same business glossary.
Systems that emit SQL are scored by executing it against the database (read-only) and
comparing with the independent gold (gold.py). Raw per-question records are appended to
results/llm_results.jsonl (resumable). No mock fallback is accepted: a call that
llm_client answers with is_live=False is retried and finally counted as an error.

Usage: python3 run_llm.py --db <db> --questions <jsonl> --gold <json> [--limit N] [--workers 6]
       python3 run_llm.py ... --summarize
"""
import argparse
import json
import math
import os
import re
import sqlite3
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import gen_db  # noqa: E402
from llm_client import get_llm_client, clean_sql  # noqa: E402
from fast_mcp.semantic_tools import SemanticFastTools  # noqa: E402
from fast_mcp.mcp_protocol import TOOL_DEFINITIONS  # noqa: E402

DDL = "\n".join(s.strip() + ";" for s in gen_db.DDL.strip().split(";") if s.strip())
GLOSSARY = """Business glossary (applies to all questions):
- Money columns net_budget, used_budget, remain_budget of transaction_statement are stored as TEXT decimals.
- A project's net/used/remaining budget in a given department, fiscal year and month is the sum of the
  corresponding transaction_statement rows of that project in that department, fiscal year and month.
- transaction_statement.project_id references projects.project_id.
- Burn rate (%) = used budget * 100 / net budget, rounded to 2 decimals.
- 'Approval forms of staff in a department' means approval_forms rows whose staff_id belongs to a staff_users row of that department."""
if os.environ.get("DEFINE_DELAYED") == "1":
    GLOSSARY += ("\n- A project is 'delayed' when its remaining budget (as defined above) exceeds the threshold given in the "
                 "question. No other condition, such as activity completion, applies.")
SYS_SQL = "You are an expert SQLite analyst. Answer with exactly one SQLite query in a ```sql code block and nothing else."
MAX_ROWS = 50

DEMOS = [
    ("List the delayed projects of department 10050000 in fiscal year 2026, month 2, whose remaining unspent budget exceeds 7,777,000 THB. Show the top 10 by remaining budget with project code, project name, net budget, used budget, remaining budget and burn rate (used/net in %).",
     "SELECT p.project_code, p.project_name, SUM(CAST(s.net_budget AS REAL)) AS net, SUM(CAST(s.used_budget AS REAL)) AS used, SUM(CAST(s.remain_budget AS REAL)) AS remain, ROUND(SUM(CAST(s.used_budget AS REAL))*100.0/SUM(CAST(s.net_budget AS REAL)),2) AS burn FROM transaction_statement s JOIN projects p ON p.project_id=s.project_id WHERE s.dept_code='10050000' AND s.fiscal_year=2026 AND s.month=2 GROUP BY p.project_id HAVING remain>7777000 ORDER BY remain DESC, p.project_code LIMIT 10"),
    ("Reconcile the approval forms of staff in department 10070000: show the top 10 forms by amount with staff name, department code, document number and amount.",
     "SELECT u.full_name, u.dept_code, f.doc_no, f.amount FROM staff_users u JOIN approval_forms f ON f.staff_id=u.staff_id WHERE u.dept_code='10070000' ORDER BY f.amount DESC, f.doc_no LIMIT 10"),
    ("Compare net budget, disbursed amount, remaining balance and burn rate between departments 10030000, 10090000 for fiscal year 2026, March (month 3). Show one row per department with department code, net budget, used budget, remaining budget and burn rate (used/net in %).",
     "SELECT dept_code, SUM(CAST(net_budget AS REAL)), SUM(CAST(used_budget AS REAL)), SUM(CAST(remain_budget AS REAL)), ROUND(SUM(CAST(used_budget AS REAL))*100.0/SUM(CAST(net_budget AS REAL)),2) FROM transaction_statement WHERE dept_code IN ('10030000','10090000') AND fiscal_year=2026 AND month=3 GROUP BY dept_code ORDER BY dept_code"),
    ("List the delayed projects of department 10140000 in fiscal year 2026, month 9, whose remaining unspent budget exceeds 8,888,000 THB. Show the top 10 by remaining budget with project code, project name, net budget, used budget, remaining budget and burn rate (used/net in %).",
     "SELECT p.project_code, p.project_name, SUM(CAST(s.net_budget AS REAL)), SUM(CAST(s.used_budget AS REAL)), SUM(CAST(s.remain_budget AS REAL)) AS remain, ROUND(SUM(CAST(s.used_budget AS REAL))*100.0/SUM(CAST(s.net_budget AS REAL)),2) FROM transaction_statement s JOIN projects p ON p.project_id=s.project_id WHERE s.dept_code='10140000' AND s.fiscal_year=2026 AND s.month=9 GROUP BY p.project_id HAVING remain>8888000 ORDER BY remain DESC, p.project_code LIMIT 10"),
    ("Reconcile the approval forms of staff in department 10170000: show the top 10 forms by amount with staff name, department code, document number and amount.",
     "SELECT u.full_name, u.dept_code, f.doc_no, f.amount FROM staff_users u JOIN approval_forms f ON f.staff_id=u.staff_id WHERE u.dept_code='10170000' ORDER BY f.amount DESC, f.doc_no LIMIT 10"),
    ("Compare net budget, disbursed amount, remaining balance and burn rate between departments 10040000, 10120000, 10190000 for fiscal year 2026, August (month 8). Show one row per department with department code, net budget, used budget, remaining budget and burn rate (used/net in %).",
     "SELECT dept_code, SUM(CAST(net_budget AS REAL)), SUM(CAST(used_budget AS REAL)), SUM(CAST(remain_budget AS REAL)), ROUND(SUM(CAST(used_budget AS REAL))*100.0/SUM(CAST(net_budget AS REAL)),2) FROM transaction_statement WHERE dept_code IN ('10040000','10120000','10190000') AND fiscal_year=2026 AND month=8 GROUP BY dept_code ORDER BY dept_code"),
]


# ---------------------------------------------------------------- LLM wrapper
class Meter:
    def __init__(self):
        self.calls = 0
        self.prompt = 0
        self.completion = 0
        self.total = 0
        self.llm_ms = 0.0
        self.retries = 0

    def add(self, r):
        self.calls += 1
        self.prompt += r.prompt_tokens
        self.completion += r.completion_tokens
        self.total += r.total_tokens
        self.llm_ms += r.latency_ms


class LLMError(Exception):
    pass



# ---------------------------------------------------------------- agy backend (LLM_BACKEND=agy)
class _R:
    pass


def _agy_call(prompt, timeout_s=300):
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cmd = ["agy", "--mode", "plan", "--sandbox", "--print-timeout", f"{timeout_s}s", "--output-format", "json"]
        if os.environ.get("AGY_MODEL"):
            cmd += ["--model", os.environ["AGY_MODEL"]]
        p = subprocess.run(cmd + ["-p", prompt],
                           cwd=d, capture_output=True, text=True, timeout=timeout_s + 30)
    j = json.loads(p.stdout[p.stdout.index("{"):])
    if j.get("status") != "SUCCESS":
        raise RuntimeError(str(j)[:200])
    u = j.get("usage", {})
    r = _R()
    r.text = j.get("response", "")
    r.prompt_tokens = u.get("input_tokens", 0)
    r.completion_tokens = u.get("output_tokens", 0)
    r.total_tokens = u.get("total_tokens", r.prompt_tokens + r.completion_tokens)
    r.latency_ms = j.get("duration_seconds", 0) * 1000.0
    r.is_live = True
    r.tool_name, r.tool_args = None, {}
    return r


def _agy_llm(prompt, system, tools, harden=False):
    if tools:
        spec = json.dumps(tools, ensure_ascii=False)
        full = (f"{system}\n\nAvailable tools (JSON schemas): {spec}\n\nReply with ONLY a JSON object "
                f"{{\"tool\": <name or null>, \"arguments\": {{...}}}}.\n\nQuestion: {prompt}")
    else:
        full = f"{system}\n\n{prompt}"
    if harden:
        full = ("Do not use any tools and do not run any commands; answer directly from the text below.\n\n" + full)
    r = _agy_call(full)
    if tools:
        m = re.search(r"\{[\s\S]*\}", r.text)
        try:
            o = json.loads(m.group(0)) if m else {}
        except ValueError:
            o = {}
        r.tool_name = o.get("tool") or None
        r.tool_args = o.get("arguments") or {}
    return r


def _claude_call(prompt, system, timeout_s=300):
    """Claude Code CLI as the model (LLM_BACKEND=claude): no tools, no session persistence."""
    import subprocess
    import tempfile
    cmd = ["claude", "-p", "--model", os.environ.get("CLAUDE_MODEL", "opus"), "--tools", "", "--no-session-persistence",
           "--output-format", "json", "--system-prompt", system or SYS_SQL]
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(cmd + [prompt], cwd=d, capture_output=True, text=True, timeout=timeout_s)
    j = json.loads(p.stdout[p.stdout.index("{"):])
    if j.get("is_error"):
        raise RuntimeError(str(j.get("result"))[:200])
    u = j.get("usage", {})
    r = _R()
    r.text = j.get("result", "")
    r.prompt_tokens = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
    r.completion_tokens = u.get("output_tokens", 0)
    r.total_tokens = r.prompt_tokens + r.completion_tokens
    r.latency_ms = j.get("duration_ms", (time.perf_counter() - t0) * 1000.0)
    r.is_live = True
    r.tool_name, r.tool_args = None, {}
    return r


def _claude_llm(prompt, system, tools):
    if tools:
        spec = json.dumps(tools, ensure_ascii=False)
        full = (f"Available tools (JSON schemas): {spec}\n\nReply with ONLY a JSON object "
                f"{{\"tool\": <name or null>, \"arguments\": {{...}}}}.\n\nQuestion: {prompt}")
    else:
        full = prompt
    r = _claude_call(full, system)
    if tools:
        m = re.search(r"\{[\s\S]*\}", r.text)
        try:
            o = json.loads(m.group(0)) if m else {}
        except ValueError:
            o = {}
        r.tool_name = o.get("tool") or None
        r.tool_args = o.get("arguments") or {}
    return r


def llm(meter, prompt, system=SYS_SQL, tools=None, attempts=5):
    client = get_llm_client()
    use_agy = os.environ.get("LLM_BACKEND") == "agy"
    use_claude = os.environ.get("LLM_BACKEND") == "claude"
    for i in range(attempts):
        try:
            r = _claude_llm(prompt, system, tools) if use_claude else _agy_llm(prompt, system, tools, harden=i > 0) if use_agy else (client.call_tool(prompt, tools, system) if tools else client.generate(prompt, system))
        except Exception as e:  # noqa: BLE001
            print("[agy error]", str(e)[:120], flush=True)
            meter.retries += 1
            time.sleep(2 ** i)
            continue
        if r.is_live and (tools or r.text):
            meter.add(r)
            return r
        print("[empty response]", round(r.latency_ms), flush=True)
        meter.retries += 1
        time.sleep(2 ** i)
    raise LLMError("llm call failed after retries (no live response)")


# ---------------------------------------------------------------- SQL execution
def run_sql(db, sql, timeout_s=20.0):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    t0 = time.perf_counter()
    conn.set_progress_handler(lambda: 1 if time.perf_counter() - t0 > timeout_s else 0, 100000)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_ROWS + 1)
        ms = (time.perf_counter() - t0) * 1000
        return rows, None, ms
    except Exception as e:  # noqa: BLE001
        return [], str(e)[:200], (time.perf_counter() - t0) * 1000
    finally:
        conn.close()


def sql_of(text):
    t = text or ""
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)```", t, re.I)
    s = m.group(1) if m else re.sub(r"^\s*```(?:sql)?", "", t, flags=re.I)
    s = s.replace("```", "").strip()
    return s.split(";")[0].strip()


# ---------------------------------------------------------------- scoring
def num_eq(a, b, tol=0.011):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


def row_matches(gold_vals, got_vals):
    used = [False] * len(got_vals)
    for g in gold_vals:
        for j, v in enumerate(got_vals):
            if not used[j] and num_eq(g, v):
                used[j] = True
                break
        else:
            return False
    return True


def ex_match(gold_rows, got_rows):
    """Order- and column-tolerant: same row count and each gold row matched one-to-one."""
    if len(gold_rows) != len(got_rows):
        return False
    avail = list(range(len(got_rows)))
    for g in gold_rows:
        gv = list(g.values()) if isinstance(g, dict) else list(g)
        for k in avail:
            if row_matches(gv, list(got_rows[k].values()) if isinstance(got_rows[k], dict) else list(got_rows[k])):
                avail.remove(k)
                break
        else:
            return False
    return True


REF_ADV = "SELECT u.full_name, u.dept_code, f.doc_no, f.amount FROM staff_users u JOIN approval_forms f ON u.staff_id=f.staff_id WHERE u.dept_code=? ORDER BY f.amount DESC, f.doc_no ASC LIMIT 10"


def median_ms(fn, n=5):
    fn()
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts)


# ---------------------------------------------------------------- systems
def sys_naive(q, db, m):
    r = llm(m, f"{DDL}\n\n{GLOSSARY}\n\nQuestion: {q}\nSQLite query:")
    return {"sql": sql_of(r.text)}


def sys_dbgpt(q, db, m):
    p = ("I want you to act as a SQL terminal in front of an example database, you need only to return the sql command to me. "
         "Below is an instruction that describes a task, Write a response that appropriately completes the request.\n"
         f"\"\n##Instruction:\nenterprise_budget contains tables such as departments, projects, activities, expense_items, staff_users, approval_forms, transaction_statement.\n"
         f"{DDL}\n\n{GLOSSARY}\n\n###Input:\n{q}\n\n###Response:")
    return {"sql": sql_of(llm(m, p).text)}


def tok(s):
    s = re.sub(r"\d[\d,\.]*", "<n>", s.lower())
    return set(re.findall(r"[a-z<>]+", s))


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def sys_dail(q, db, m):
    qt = tok(q)
    top = sorted(DEMOS, key=lambda d: -jaccard(qt, tok(d[0])))[:3]
    demos = "\n\n".join(f"/* Question: {d[0]} */\n{d[1]};" for d in top)
    p = f"{DDL}\n\n{GLOSSARY}\n\nSimilar solved examples:\n{demos}\n\n/* Question: {q} */\nSQLite query:"
    return {"sql": sql_of(llm(m, p).text)}


def sys_vanna(q, db, m):
    docs = [("ddl", t.strip() + ";") for t in DDL.split(";") if t.strip()] + [("doc", GLOSSARY)] + [("qa", f"Question: {d[0]}\nSQL: {d[1]}") for d in DEMOS]
    qt = tok(q)
    scored = sorted(docs, key=lambda d: -jaccard(qt, tok(d[1])))
    ddls = [d[1] for d in scored if d[0] == "ddl"][:4]
    qas = [d[1] for d in scored if d[0] == "qa"][:3]
    p = "Relevant DDL:\n" + "\n".join(ddls) + f"\n\n{GLOSSARY}\n\nRelevant solved examples:\n" + "\n\n".join(qas) + f"\n\nQuestion: {q}\nSQLite query:"
    return {"sql": sql_of(llm(m, p).text)}


def sql_of_last(text):
    blocks = re.findall(r"```(?:sql)?\s*([\s\S]*?)```", text or "", re.I)
    return (blocks[-1].strip().split(";")[0].strip()) if blocks else sql_of(text)


def sys_din(q, db, m):
    links = llm(m, f"{DDL}\n\n{GLOSSARY}\n\nQuestion: {q}\nList the tables, columns and join keys needed. Be concise.", "You are a schema linking module.").text
    cls = llm(m, f"Question: {q}\nSchema links:\n{links}\nClassify as EASY, NON-NESTED or NESTED. Answer with one word.", "You are a query classifier.").text.strip()
    gen = llm(m, f"{DDL}\n\n{GLOSSARY}\n\nQuestion: {q}\nSchema links:\n{links}\nClass: {cls}\nLet's think step by step, then give the final SQLite query in a ```sql block.").text
    fixed = llm(m, f"{DDL}\n\n{GLOSSARY}\n\nQuestion: {q}\nDraft SQL:\n{sql_of(gen)}\nFix any bug (join paths, TEXT columns, filters). Return the corrected SQLite query in a ```sql block.").text
    return {"sql": sql_of_last(fixed) or sql_of_last(gen)}


def sys_mac(q, db, m):
    sel = llm(m, f"{DDL}\n\nQuestion: {q}\nSelect only the tables and columns needed; output a pruned schema.", "You are the Selector agent.").text
    dec = llm(m, f"Question: {q}\nPruned schema:\n{sel}\n{GLOSSARY}\nDecompose into numbered sub-questions with the SQL fragment for each, then give the final SQLite query in a ```sql block.", "You are the Decomposer agent.").text
    sql = sql_of_last(dec)
    for _ in range(2):
        rows, err, _ = run_sql(db, sql) if sql else ([], "empty sql", 0)
        if not err and rows:
            break
        sql = sql_of(llm(m, f"{DDL}\n\nQuestion: {q}\nSQL:\n{sql}\nExecution feedback: {err or 'returned no rows'}\nReturn a corrected SQLite query in a ```sql block.", "You are the Refiner agent.").text) or sql
    return {"sql": sql}


def sys_react(q, db, m):
    tools = ("Tools (reply with exactly one line starting with 'Action:'):\n"
             "Action: list_tables\nAction: describe <table>\nAction: query <one SQLite query>\nAction: final\n"
             "Use 'Action: final' when the last query result answers the question.")
    tables = [r[0] for r in run_sql(db, "SELECT name FROM sqlite_master WHERE type='table'")[0]]
    transcript = f"{GLOSSARY}\n\nQuestion: {q}\n"
    if os.environ.get("REACT_DDL") == "1":
        transcript += f"\nDatabase schema:\n{DDL}\n"
    last_sql, last_rows = "", []
    for _ in range(int(os.environ.get("REACT_MAX_TURNS", "8"))):
        out = llm(m, transcript + "\nNext action:", "You are a SQL agent working step by step.\n" + tools).text
        mm = re.search(r"Action:\s*([\s\S]*)", out, re.I)
        act = mm.group(1).strip() if mm else ""
        transcript += f"\nAction: {act}\n"
        if act.lower().startswith("final"):
            break
        if act.lower().startswith("list_tables"):
            transcript += "Observation: " + ", ".join(tables) + "\n"
        elif act.lower().startswith("describe"):
            t = act.split(None, 1)[1].strip().strip("`'\"") if " " in act else ""
            ddl = "".join(r[0] or "" for r in run_sql(db, f"SELECT sql FROM sqlite_master WHERE name='{re.sub(r'[^A-Za-z_]', '', t)}'")[0])
            transcript += f"Observation: {ddl or 'unknown table'}\n"
        elif act.lower().startswith("query"):
            sql = sql_of(act[5:])
            rows, err, _ = run_sql(db, sql)
            if err:
                transcript += f"Observation: ERROR {err}\n"
            else:
                last_sql, last_rows = sql, rows
                transcript += f"Observation: {rows[:5]}\n"
        else:
            transcript += "Observation: invalid action\n"
    return {"sql": last_sql}


def sys_fastmcp(q, db, m, tools_obj):
    defs = [{"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]} for t in TOOL_DEFINITIONS]
    r = llm(m, q, "Answer by calling exactly one of the provided tools. If no tool fits the question, do not call any tool.", tools=defs)
    return {"tool": r.tool_name, "args": r.tool_args}


ROUTER_SYSTEM = ("You route enterprise-database questions. Call a tool ONLY if the question asks exactly for what the tool returns: "
                 "get_delayed_projects = the top 10 delayed projects (by remaining budget, descending) for ONE department in ONE month; "
                 "reconcile_staff_advances = the 10 largest approval forms of the staff of ONE department; "
                 "get_department_summary = per-department net, used, remaining budget and burn rate for the given departments in ONE month. "
                 "If the question asks for a different number of rows, a different order, several months combined, a different metric, "
                 "a ranking across departments, a count, or anything else, call NO tool and reply with the single word NONE. "
                 "Department arguments must be department codes such as 10070000; 'Faculty / Division N' is the code 10 followed by N as two digits and 0000.")


def sys_hybrid(q, db, m, fallback=True):
    defs = [{"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]} for t in TOOL_DEFINITIONS]
    r = llm(m, q, ROUTER_SYSTEM, tools=defs)
    if r.tool_name in ("get_delayed_projects", "reconcile_staff_advances", "get_department_summary"):
        return {"route": "tool", "tool": r.tool_name, "args": r.tool_args}
    if not fallback:
        return {"route": "abstain"}
    return {"route": "sql", "sql": sys_naive(q, db, m)["sql"]}


def run_tool(tools_obj, name, args):
    args = dict(args)
    if "dept_codes" in args and isinstance(args["dept_codes"], str):
        args["dept_codes"] = [args["dept_codes"]]
    for k in ("fiscal_year", "month"):
        if k in args:
            args[k] = int(args[k])
    if "min_remain" in args:
        args["min_remain"] = float(args["min_remain"])
    return getattr(tools_obj, name)(**args)["data"], args


SQL_SYSTEMS = {"naive_sql": sys_naive, "db_gpt_hub_style": sys_dbgpt, "dail_sql_style": sys_dail, "vanna_style": sys_vanna,
               "din_sql_style": sys_din, "mac_sql_style": sys_mac, "langchain_react_style": sys_react}


def to_plain(v):
    if isinstance(v, dict):
        return {k: to_plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [to_plain(x) for x in v]
    if isinstance(v, float) and v.is_integer():
        return int(v) if abs(v) < 1e15 else v
    return v


def evaluate(system, q, db, gold, tools_obj, ref_cache):
    m = Meter()
    rec = {"system": system, "qid": q["id"], "intent": q["intent"], "model": ("agy:" + os.environ.get("AGY_MODEL", "default")) if os.environ.get("LLM_BACKEND") == "agy" else ("claude:" + os.environ.get("CLAUDE_MODEL", "opus")) if os.environ.get("LLM_BACKEND") == "claude" else get_llm_client().model}
    t_start = time.perf_counter()
    try:
        if system == "fast_mcp":
            out = sys_fastmcp(q["question"], db, m, tools_obj)
            rec.update(tool=out["tool"], args=to_plain(out["args"]))
            gold_item = gold.get(q["id"])
            if q["gold_tool"] is None and q["id"] not in gold:
                rec.update(valid=True, correct=out["tool"] is None, abstained=out["tool"] is None)
            else:
                rec["tool_ok"] = out["tool"] == q["gold_tool"] if q["gold_tool"] else False
                if q["gold_tool"] is None and out["tool"] is None:
                    rec["abstained"] = True
                data, err = None, None
                if out["tool"] in ("get_delayed_projects", "reconcile_staff_advances", "get_department_summary"):
                    try:
                        args = dict(out["args"])
                        if "dept_codes" in args and isinstance(args["dept_codes"], str):
                            args["dept_codes"] = [args["dept_codes"]]
                        for k in ("fiscal_year", "month"):
                            if k in args:
                                args[k] = int(args[k])
                        if "min_remain" in args:
                            args["min_remain"] = float(args["min_remain"])
                        rec["args_ok"] = to_plain(args) == to_plain(q["gold_args"]) if out["tool"] == q["gold_tool"] and q["gold_tool"] else False
                        t0 = time.perf_counter()
                        data = getattr(tools_obj, out["tool"])(**args)["data"]
                        rec["db_ms"] = (time.perf_counter() - t0) * 1000
                        rec["exec_args"] = to_plain(args)
                    except Exception as e:  # noqa: BLE001
                        err = str(e)[:200]
                else:
                    err = f"no/unknown tool: {out['tool']}"
                rec["valid"] = data is not None
                rec["error"] = err
                rec["correct"] = bool(data is not None and (out["tool"] == q["gold_tool"] or q["gold_tool"] is None) and ex_match(gold_item["data"], data))
                if rec["correct"]:
                    rec["e_pred_ms"] = median_ms(lambda: getattr(tools_obj, out["tool"])(**args))
        elif system in ("hybrid", "fast_mcp_strict"):
            out = sys_hybrid(q["question"], db, m, fallback=(system == "hybrid"))
            rec["route"] = out["route"]
            gold_rows = gold[q["id"]]["data"]
            if out["route"] == "tool":
                rec.update(tool=out["tool"], args=to_plain(out["args"]))
                try:
                    data, args = run_tool(tools_obj, out["tool"], out["args"])
                    rec.update(valid=True, error=None, correct=bool(ex_match(gold_rows, data)))
                except Exception as e:  # noqa: BLE001
                    rec.update(valid=False, error=str(e)[:200], correct=False)
            elif out["route"] == "abstain":
                rec.update(valid=False, error="abstained", correct=False, abstained=True)
            else:
                sql = out["sql"]
                rec["sql"] = sql
                rows, err, ms = run_sql(db, sql) if sql else ([], "no sql produced", 0.0)
                rec.update(valid=err is None, error=err, db_ms=ms, n_rows=len(rows), correct=bool(err is None and ex_match(gold_rows, rows)))
        else:
            out = SQL_SYSTEMS[system](q["question"], db, m)
            sql = out["sql"]
            rec["sql"] = sql
            rows, err, ms = run_sql(db, sql) if sql else ([], "no sql produced", 0.0)
            rec.update(valid=err is None, error=err, db_ms=ms, n_rows=len(rows))
            rec["correct"] = bool(err is None and ex_match(gold[q["id"]]["data"], rows))
            if rec["correct"]:
                rec["e_pred_ms"] = median_ms(lambda: run_sql(db, sql))
    except LLMError as e:
        rec.update(valid=False, correct=False, error=f"LLM_ERROR {e}", llm_error=True)
    except Exception as e:  # noqa: BLE001
        rec.update(valid=False, correct=False, error=f"HARNESS {type(e).__name__}: {e}"[:200], llm_error=False)
    rec.update(calls=m.calls, prompt_tokens=m.prompt, completion_tokens=m.completion, total_tokens=m.total,
               llm_ms=m.llm_ms, retries=m.retries, wall_ms=(time.perf_counter() - t_start) * 1000)
    if q["gold_tool"] and q["id"] in ref_cache:
        rec["e_ref_ms"] = ref_cache[q["id"]]
    return rec


def build_ref_cache(db, questions):
    import run_offline as ro
    cache = {}
    for q in questions:
        if not q["gold_tool"]:
            continue
        n, a = q["gold_tool"], q["gold_args"]
        if n == "reconcile_staff_advances":
            fn = lambda a=a: run_sql(db, REF_ADV.replace("?", f"'{a['dept_code']}'"))
        else:
            fn = lambda n=n, a=a: ro.ref_sql(db, n, a)
        cache[q["id"]] = median_ms(fn)
    return cache


# ---------------------------------------------------------------- summary
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def summarize(path):
    last = {}
    for l in open(path):
        r = json.loads(l)
        last[(r['system'], r['qid'])] = r
    recs = list(last.values())
    out = {}
    for s in sorted({r["system"] for r in recs}):
        rs = [r for r in recs if r["system"] == s and r["intent"] != "out_of_scope"]
        n = len(rs)
        ex = sum(r["correct"] for r in rs)
        vsr = sum(r["valid"] for r in rs)
        ves = sum(math.sqrt(r["e_ref_ms"] / max(r["e_pred_ms"], 1e-3)) for r in rs if r["correct"] and "e_ref_ms" in r and "e_pred_ms" in r) / max(1, n)
        tot = [r["llm_ms"] + r.get("db_ms", 0) for r in rs]
        d = {"n": n, "EX": ex / n, "EX_ci95": wilson(ex, n), "VSR": vsr / n, "VSR_ci95": wilson(vsr, n), "VES": ves,
             "tokens_mean": statistics.mean(r["total_tokens"] for r in rs), "prompt_tokens_mean": statistics.mean(r["prompt_tokens"] for r in rs),
             "completion_tokens_mean": statistics.mean(r["completion_tokens"] for r in rs), "calls_mean": statistics.mean(r["calls"] for r in rs),
             "llm_ms_median": statistics.median(r["llm_ms"] for r in rs), "db_ms_median": statistics.median(r.get("db_ms", 0) for r in rs),
             "total_ms_median": statistics.median(tot), "llm_errors": sum(bool(r.get("llm_error")) for r in rs), "retries": sum(r["retries"] for r in rs),
             "EX_by_intent": {i: f"{sum(r['correct'] for r in rs if r['intent'] == i)}/{sum(1 for r in rs if r['intent'] == i)}" for i in sorted({r['intent'] for r in rs})}}
        if s == "fast_mcp":
            d["tool_selection_acc"] = sum(r.get("tool_ok", False) for r in rs) / n
            d["argument_acc"] = sum(r.get("args_ok", False) for r in rs) / n
            oos = [r for r in recs if r["system"] == s and r["intent"] == "out_of_scope"]
            d["out_of_scope_abstain"] = f"{sum(r['correct'] for r in oos)}/{len(oos)}"
        out[s] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/home/suphachai/fastmcp_eval/db_800000.db")
    ap.add_argument("--questions", default="/home/suphachai/fastmcp_eval/q_800000.jsonl")
    ap.add_argument("--gold", default="/home/suphachai/fastmcp_eval/gold_800000.json")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "llm_results.jsonl"))
    ap.add_argument("--systems", default="fast_mcp," + ",".join(SQL_SYSTEMS))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--n-in-scope", type=int, default=0, help="keep questions (file order) until this many in-scope ones")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args()
    if a.summarize:
        s = summarize(a.out)
        json.dump(s, open(a.out.replace(".jsonl", "_summary.json"), "w"), indent=1)
        print(json.dumps(s, indent=1))
        return
    questions = [json.loads(l) for l in open(a.questions)]
    if a.limit:
        questions = questions[: a.limit]
    if a.n_in_scope:
        kept, k = [], 0
        for q in questions:
            kept.append(q)
            k += bool(q["gold_tool"])
            if k >= a.n_in_scope:
                break
        questions = kept
    gold = json.load(open(a.gold))
    get_llm_client().print_status()
    tools_obj = SemanticFastTools(a.db, ensure_indexes=False)
    ref_cache = build_ref_cache(a.db, questions)
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            r = json.loads(l)
            if not r.get("llm_error"):
                done.add((r["system"], r["qid"]))
    jobs = [(s, q) for q in questions for s in a.systems.split(",") if (s, q["id"]) not in done and (q["gold_tool"] or q["id"] in gold or s == "fast_mcp")]
    lock = threading.Lock()
    fh = open(a.out, "a")
    streak = [0]

    def work(job):
        s, q = job
        r = evaluate(s, q, a.db, gold, tools_obj, ref_cache)
        with lock:
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            streak[0] = streak[0] + 1 if r.get("llm_error") else 0
            if streak[0] >= 16:
                print("ABORT: 16 consecutive LLM failures (credit/quota?)", flush=True)
                os._exit(3)
        return r

    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(work, jobs), 1):
            if i % 20 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} done, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
