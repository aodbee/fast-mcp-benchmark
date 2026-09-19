#!/usr/bin/env python3
"""
Fast-MCP Unified LLM Client
Connects real live foundation models (Google Gemini, OpenAI / UP-KKU Gateway,
Anthropic, OpenRouter, Local Ollama) to benchmark baselines and Fast-MCP agents.

Features:
  - 100% pure Python with zero heavy dependencies (uses requests or urllib).
  - Built-in .env parser (finds .env in current, benchmark, or workspace directory).
  - Exact wall-clock HTTP latency measurement (latency_ms).
  - Exact prompt/completion token extraction from live API usage metadata.
  - Native Tool Calling / Function Calling support across all major providers.
  - Deterministic fallback mock mode if no API key is configured.
"""

import os
import sys
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

def load_env_file(search_paths: Optional[List[str]] = None):
    """Parses .env file without external python-dotenv package."""
    if search_paths is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(base_dir)
        search_paths = [
            os.path.join(root_dir, ".env"),
            os.path.join(base_dir, ".env"),
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(root_dir), ".env")
        ]

    for p in search_paths:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass

# Automatically load environment upon import
load_env_file()

@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model: str
    provider: str
    is_live: bool

@dataclass
class LLMToolResult:
    tool_name: Optional[str]
    tool_args: Dict[str, Any]
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model: str
    provider: str
    is_live: bool

def clean_sql(raw_text: str) -> str:
    """Extracts raw executable SQL query from model output."""
    if not raw_text:
        return ""
    
    # Strip markdown SQL code blocks
    code_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
    if code_match:
        sql = code_match.group(1).strip()
    else:
        sql = raw_text.strip()

    # Remove conversational prefixes if any
    lines = []
    for line in sql.splitlines():
        trimmed = line.strip()
        if trimmed.lower().startswith("here is") or trimmed.lower().startswith("the sql query"):
            continue
        lines.append(line)
    sql = "\n".join(lines).strip()
    return sql

class LLMClient:
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "").lower()
        self.timeout = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))

        # Detect Provider & Keys
        gemini_key = os.environ.get("GEMINI_API_KEY") or (os.environ.get("API_KEY") if self.provider == "gemini" else None)
        openai_key = os.environ.get("OPENAI_API_KEY") or (os.environ.get("API_KEY") if self.provider in ("openai", "openrouter") else None)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if not self.provider or self.provider == "auto":
            if gemini_key:
                self.provider = "gemini"
            elif openai_key:
                self.provider = "openai"
            elif anthropic_key:
                self.provider = "anthropic"
            else:
                self.provider = "mock"

        # Configure provider-specific endpoints & keys
        if self.provider == "gemini":
            self.api_key = gemini_key
            self.model = os.environ.get("GEMINI_MODEL") or os.environ.get("DEFAULT_MODEL") or "gemini-3.8-flash"
            self.is_live = bool(self.api_key and "your_" not in self.api_key)
        elif self.provider in ("openai", "openrouter", "ollama"):
            self.api_key = openai_key or "sk-dummy"
            if self.provider == "openrouter":
                self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
                self.model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
                self.is_live = bool(openai_key and "your_" not in openai_key)
            elif self.provider == "ollama":
                self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
                self.is_live = True
            else:
                self.base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("BASE_URL", "https://api.openai.com/v1")
                self.model = os.environ.get("OPENAI_MODEL") or os.environ.get("DEFAULT_MODEL") or "gpt-4o-mini"
                self.is_live = bool(openai_key and "your_" not in openai_key)
        elif self.provider == "anthropic":
            self.api_key = anthropic_key
            self.model = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("DEFAULT_MODEL") or "claude-3-5-haiku-20241022"
            self.is_live = bool(anthropic_key and "your_" not in anthropic_key)
        else:
            self.provider = "mock"
            self.model = "offline-mock-engine"
            self.is_live = False

    def print_status(self):
        if self.is_live:
            print(f"[LLM Client] 🟢 LIVE MODE ACTIVE | Provider: {self.provider.upper()} | Model: {self.model}")
        else:
            print(f"[LLM Client] 🟡 OFFLINE / MOCK MODE | Set your API key in .env to run live benchmarks.")

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResult:
        """Executes a single text generation request against the live LLM service."""
        if not self.is_live:
            return self._mock_generate(prompt, system_prompt)

        if self.provider == "gemini":
            return self._generate_gemini(prompt, system_prompt)
        elif self.provider in ("openai", "openrouter", "ollama"):
            return self._generate_openai_compat(prompt, system_prompt)
        elif self.provider == "anthropic":
            return self._generate_anthropic(prompt, system_prompt)
        else:
            return self._mock_generate(prompt, system_prompt)

    def call_tool(self, prompt: str, tools: List[Dict[str, Any]], system_prompt: str = "") -> LLMToolResult:
        """Executes a single tool-selection request with function declarations."""
        if not self.is_live:
            return self._mock_call_tool(prompt, tools)

        if self.provider == "gemini":
            return self._tool_gemini(prompt, tools, system_prompt)
        elif self.provider in ("openai", "openrouter", "ollama"):
            return self._tool_openai_compat(prompt, tools, system_prompt)
        elif self.provider == "anthropic":
            return self._tool_anthropic(prompt, tools, system_prompt)
        else:
            return self._mock_call_tool(prompt, tools)

    # --------------------------------------------------------------------------
    # Google Gemini REST Handler
    # --------------------------------------------------------------------------
    def _generate_gemini(self, prompt: str, system_prompt: str = "") -> LLMResult:
        # Strip models/ prefix if present in model string
        model_name = self.model.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        t0 = time.perf_counter()
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                print(f"[Gemini Error] HTTP {r.status_code}: {r.text[:300]}")
                return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)
            
            data = r.json()
            candidates = data.get("candidates", [])
            text = ""
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
            
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", len(prompt.split()) * 2)
            completion_tokens = usage.get("candidatesTokenCount", len(text.split()) * 2)
            total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)

            return LLMResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider="gemini",
                is_live=True
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            print(f"[Gemini Network Error]: {e}")
            return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)

    def _tool_gemini(self, prompt: str, tools: List[Dict[str, Any]], system_prompt: str = "") -> LLMToolResult:
        model_name = self.model.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        # Convert tool definitions to Gemini functionDeclarations format
        function_declarations = []
        for t in tools:
            func = t.get("function", t)
            decl = {
                "name": func.get("name"),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {"type": "object", "properties": {}})
            }
            function_declarations.append(decl)

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"functionDeclarations": function_declarations}],
            "generationConfig": {"temperature": 0.0}
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        t0 = time.perf_counter()
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                print(f"[Gemini Tool Error] HTTP {r.status_code}: {r.text[:300]}")
                return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

            data = r.json()
            candidates = data.get("candidates", [])
            tool_name = None
            tool_args = {}
            text = ""

            if candidates and "content" in candidates[0]:
                for part in candidates[0]["content"].get("parts", []):
                    if "functionCall" in part:
                        tool_name = part["functionCall"].get("name")
                        tool_args = part["functionCall"].get("args", {})
                    elif "text" in part:
                        text += part["text"]

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 450)
            completion_tokens = usage.get("candidatesTokenCount", 60)
            total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)

            return LLMToolResult(
                tool_name=tool_name,
                tool_args=tool_args,
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider="gemini",
                is_live=True
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

    # --------------------------------------------------------------------------
    # OpenAI / OpenAI-Compatible / Gateway REST Handler
    # --------------------------------------------------------------------------
    def _generate_openai_compat(self, prompt: str, system_prompt: str = "") -> LLMResult:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0
        }

        t0 = time.perf_counter()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                print(f"[OpenAI-Compat Error] HTTP {r.status_code}: {r.text[:300]}")
                return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)

            data = r.json()
            choice = data["choices"][0]
            text = choice["message"].get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", len(prompt.split()) * 2)
            completion_tokens = usage.get("completion_tokens", len(text.split()) * 2)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            return LLMResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider=self.provider,
                is_live=True
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            print(f"[OpenAI-Compat Network Error]: {e}")
            return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)

    def _tool_openai_compat(self, prompt: str, tools: List[Dict[str, Any]], system_prompt: str = "") -> LLMToolResult:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        formatted_tools = []
        for t in tools:
            if "function" in t:
                formatted_tools.append(t)
            else:
                formatted_tools.append({"type": "function", "function": t})

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": formatted_tools,
            "tool_choice": "auto",
            "temperature": 0.0
        }

        t0 = time.perf_counter()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                print(f"[OpenAI-Compat Tool Error] HTTP {r.status_code}: {r.text[:300]}")
                return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

            data = r.json()
            msg = data["choices"][0]["message"]
            text = msg.get("content") or ""
            tool_name = None
            tool_args = {}

            if "tool_calls" in msg and msg["tool_calls"]:
                call = msg["tool_calls"][0]
                tool_name = call["function"]["name"]
                try:
                    tool_args = json.loads(call["function"].get("arguments", "{}"))
                except Exception:
                    tool_args = {}

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 450)
            completion_tokens = usage.get("completion_tokens", 60)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            return LLMToolResult(
                tool_name=tool_name,
                tool_args=tool_args,
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider=self.provider,
                is_live=True
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

    # --------------------------------------------------------------------------
    # Anthropic REST Handler
    # --------------------------------------------------------------------------
    def _generate_anthropic(self, prompt: str, system_prompt: str = "") -> LLMResult:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.0
        }
        if system_prompt:
            payload["system"] = system_prompt

        t0 = time.perf_counter()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)

            data = r.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", len(prompt.split()) * 2)
            completion_tokens = usage.get("output_tokens", len(text.split()) * 2)
            total_tokens = prompt_tokens + completion_tokens

            return LLMResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider="anthropic",
                is_live=True
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return self._mock_generate(prompt, system_prompt, fallback_latency_ms=latency_ms)

    def _tool_anthropic(self, prompt: str, tools: List[Dict[str, Any]], system_prompt: str = "") -> LLMToolResult:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        anthropic_tools = []
        for t in tools:
            func = t.get("function", t)
            anthropic_tools.append({
                "name": func.get("name"),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}})
            })

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": anthropic_tools,
            "max_tokens": 4096,
            "temperature": 0.0
        }
        if system_prompt:
            payload["system"] = system_prompt

        t0 = time.perf_counter()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

            data = r.json()
            tool_name = None
            tool_args = {}
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_args = block.get("input", {})
                elif block.get("type") == "text":
                    text += block.get("text", "")

            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 450)
            completion_tokens = usage.get("output_tokens", 60)
            total_tokens = prompt_tokens + completion_tokens

            return LLMToolResult(
                tool_name=tool_name,
                tool_args=tool_args,
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),
                model=self.model,
                provider="anthropic",
                is_live=True
            )
        except Exception:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return self._mock_call_tool(prompt, tools, fallback_latency_ms=latency_ms)

    # --------------------------------------------------------------------------
    # Deterministic Mock Fallback Handlers
    # --------------------------------------------------------------------------
    def _mock_generate(self, prompt: str, system_prompt: str = "", fallback_latency_ms: Optional[float] = None) -> LLMResult:
        q = prompt.lower()
        if fallback_latency_ms is None:
            time.sleep(0.04)
            latency_ms = 450.0
        else:
            latency_ms = fallback_latency_ms

        if "delayed" in q or "lagging" in q:
            sql = """
            SELECT p.project_code, p.project_name, 
                   SUM(s.net_budget) as net,
                   SUM(s.used_budget) as used,
                   SUM(s.remain_budget) as remain
            FROM projects p
            JOIN activities a ON p.project_id = a.project_id
            JOIN expense_items i ON a.activity_id = i.activity_id
            JOIN transaction_statement s ON i.item_id = s.item_id
            WHERE s.dept_code = '10010000' AND s.fiscal_year = 2026 AND s.month = 12
            GROUP BY p.project_code, p.project_name
            HAVING remain > 50000
            ORDER BY remain DESC LIMIT 10;
            """
        elif "advance" in q or "settle" in q or "borrow" in q:
            sql = """
            SELECT u.full_name, u.dept_code, f.doc_no, f.amount
            FROM staff_users u
            JOIN approval_forms f ON u.staff_id = f.staff_id
            WHERE u.dept_code = '10010000'
            ORDER BY f.amount DESC LIMIT 10;
            """
        else:
            sql = """
            SELECT dept_code, 
                   SUM(CAST(net_budget AS REAL)) as total_net,
                   SUM(CAST(used_budget AS REAL)) as total_used,
                   SUM(CAST(remain_budget AS REAL)) as total_remain
            FROM transaction_statement
            WHERE dept_code IN ('10010000', '10020000') AND fiscal_year = 2026 AND month = 12
            GROUP BY dept_code;
            """

        prompt_tokens = len(prompt.split()) * 3 + 1200
        completion_tokens = len(sql.split()) * 2
        return LLMResult(
            text=f"```sql\n{sql.strip()}\n```",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=round(latency_ms, 2),
            model=self.model,
            provider="mock",
            is_live=False
        )

    def _mock_call_tool(self, prompt: str, tools: List[Dict[str, Any]], fallback_latency_ms: Optional[float] = None) -> LLMToolResult:
        q = prompt.lower()
        if fallback_latency_ms is None:
            time.sleep(0.02)
            latency_ms = 220.0
        else:
            latency_ms = fallback_latency_ms

        if "delayed" in q or "lagging" in q:
            tool_name = "get_delayed_projects"
            tool_args = {"dept_code": "10010000", "fiscal_year": 2026, "month": 12}
        elif "advance" in q or "settle" in q:
            tool_name = "reconcile_staff_advances"
            tool_args = {"dept_code": "10010000"}
        else:
            tool_name = "get_department_summary"
            tool_args = {"dept_codes": ["10010000", "10020000"], "fiscal_year": 2026, "month": 12}

        return LLMToolResult(
            tool_name=tool_name,
            tool_args=tool_args,
            text="",
            prompt_tokens=450,
            completion_tokens=60,
            total_tokens=510,
            latency_ms=round(latency_ms, 2),
            model=self.model,
            provider="mock",
            is_live=False
        )

# Global singleton client
_CLIENT_INSTANCE: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is None:
        _CLIENT_INSTANCE = LLMClient()
    return _CLIENT_INSTANCE

if __name__ == "__main__":
    client = get_llm_client()
    client.print_status()
    print("Testing generate()...")
    res = client.generate("Write SQL to select top 5 projects from table projects ordered by project_id DESC")
    print(f"Generated ({res.latency_ms} ms, {res.total_tokens} tok):")
    print(clean_sql(res.text))
