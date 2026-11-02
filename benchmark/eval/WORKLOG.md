# Work log: Fast-MCP research manuscript and evaluation

Chronological record of actions taken in the working session of 2026-11-02 (times are Asia/Bangkok where known). Every later action is appended at the bottom. Results files named here are in `benchmark/eval/results/`.

## 1. Setup and audit

1. Read `README.md` and `perplexity/comment.md` (literature suggestions and README review).
2. Created the manuscript as a Claude Docs document, "Fast-MCP: เล่มวิจัย (ฉบับร่าง)" (link: https://claude.ai/artifact/XqVpEqTFbbyxWjMaeT8Ent). Initial skeleton with pending sections.
3. Subagent 1 audited the repo (read-only). Findings:
   - No code computes the README's EX 98.6% / VES 0.962; `ves: 0.962` is a literal in `fast_agent.py:265`.
   - `get_delayed_projects` did not join on `project_id`; the old generator stored `activity_id` in the ledger's `project_id` column.
   - The database has 7 tables, not 8 (`advance_settle_forms` is never created).
   - `benchmark/results/*` came from a simulation (added constant latency, fixed token counts, row-count-only EX).
   - Baselines are prompt-level approximations; DB-GPT-Hub "CodeLlama-13B" has no support in code.
4. Subagent 2 verified the bibliography against primary pages (MAC-SQL is COLING 2025, not TKDE; DB-GPT-Hub first author is Zhou; BIRD/DIN-SQL/Toolformer page ranges not found).
5. Advisor review: do not report unmeasured numbers; use a measured protocol; independent gold; state limitations.

## 2. Offline (no-LLM) evaluation

Files created in `benchmark/eval/`: `gen_db.py`, `qgen.py`, `gold.py` (written by a subagent that did not read the tool code), `run_offline.py`.

- Edited `benchmark/fast_mcp/semantic_tools.py`: join via `project_id`, deterministic ordering, optional index hint and index creation switches.
- Generated databases (seed 42) with 1k / 10k / 100k / 800k ledger rows in `/home/suphachai/fastmcp_eval/` (Linux filesystem, not `/mnt/c`).
- Ran `run_offline.py --sizes 1000,10000,100000,800000 --runs 30 --warmup 3 --sample 10`. Output: `offline_results.json`.
- Results: tools matched gold 120/120 at every size; dropping the compound index slowed delayed_projects 9.4x and department_summary 6.9x at 800k; hand-written multi-join SQL on the same indexes was about as fast; JSON-RPC overhead 0.07 to 0.44 ms.

## 3. Live LLM evaluation (Gemini API, gemini-3.8-flash)

- Created `run_llm.py` (8 systems, shared DDL and glossary, tolerance-based EX, VES against reference SQL) and `rescore.py` (sequential VES re-timing).
- Edited `benchmark/llm_client.py` so `MAX_TOKENS` is used by Gemini `generate()`.
- Pilot runs exposed two harness bugs (hidden thinking tokens truncating SQL at 4096 output tokens; multi-line ReAct actions). Fixed: `MAX_TOKENS=16384`, timeout 150 s exported in the shell, ReAct parsing, `sql_of` fence handling.
- First full run (120-question plan) stopped at HTTP 402 `RESOURCE_EXHAUSTED` (API credit depleted) after about 205 completed jobs; the run was killed. Evidence: `/home/suphachai/fastmcp_eval/run_llm.log`.
- After a credit top-up the user chose 60 in-scope questions per system. Added `--n-in-scope` and a circuit breaker (abort after 16 consecutive LLM failures). Resumed the run; finished with 60 per system, 0 LLM errors. Total 489 jobs (8 x 60 plus 9 out-of-scope for Fast-MCP only).
- Found a bug in the MAC-SQL-style baseline (took the first code block). Fixed (`sql_of_last`), backed up the old records to `llm_results_mac_v1_firstblock_bug.jsonl` (EX 0.117), reran MAC (60 jobs). DIN-SQL-style has the same defect in its final step (2 questions); it was not rerun at that point.
- Rescored VES sequentially (`ves_sequential.json`); summary in `llm_results_summary.json`; run environment in `llm_run_env.json`.
- Final results (60 per system): EX Fast-MCP 60, DAIL-style 60, Vanna-style 60, Naive 56, DB-GPT-style 53, MAC-style 53, DIN-style 46, ReAct-style 8.

## 4. Failure analysis

Subagent analysed every wrong answer (`failure_analysis.json`, `failure_analysis_th.md`). Findings: 26 of 32 wrong answers from non-ReAct SQL systems add `is_completed = 0` ("delayed" is undefined for baselines); DAIL/Vanna correct answers are demo-template copies; 5 of 60 questions have empty gold; ReAct failures are mostly the 8-turn cap.

## 5. Manuscript

1. Expanded Chapters 1, 2, 3 and the threats-to-validity part of Chapter 5 via subagents (files in the session scratchpad), then merged them into the document.
2. Wrote Chapter 4 with the measured results (tables 4.1 to 4.6) and the interpretation.
3. A review subagent produced `consistency_report.md` (about 50 items); four subagents applied the fixes by chapter. A second review (`final_review.md`, 30 items) was applied by three subagents; a final subagent normalised terminology, replaced personal paths and added the out-of-scope selection rule.
4. Fixed one formatting defect (whole paragraph in code font) in section 5.2.1(ก).
5. Open items stated in the manuscript: human expert check of the gold definition (marked `[รอดำเนินการ]`), page ranges for BIRD, DIN-SQL, Toolformer.

## 6. Code changes after the manuscript (this log entry)

- `run_llm.py`: `DEFINE_DELAYED=1` adds the definition of "delayed" to the glossary; DIN-style final step uses the last code block; ReAct supports `REACT_DDL=1` and `REACT_MAX_TURNS`; new backend `LLM_BACKEND=agy` (see below).
- User instructed that further model calls use `agy -p` instead of the Gemini API. Piloted `agy --mode plan --sandbox --output-format json -p` in an empty temp directory: it returns the answer, token usage and duration, but each call carries about 9.5k tokens of agent overhead and the model name is not reported. Pilot: 12 of 12 correct (Fast-MCP, Naive, DAIL-style on 4 questions); `agy_pilot.jsonl` in `/home/suphachai/fastmcp_eval/`.
- Started the rerun through `agy`: `DEFINE_DELAYED=1 REACT_DDL=1 REACT_MAX_TURNS=15 LLM_BACKEND=agy python3 run_llm.py --workers 8 --n-in-scope 60 --out results/llm_results_agy_delayeddef.jsonl` (environment recorded in `llm_run_env_agy.json`). Status at 12:24: about 33 of about 549 jobs done, 0 errors.

## 7. Not done / caveats

- The Gemini API was not called after the user asked to use `agy`.
- Nothing has been committed to git; `README.md` still contains the earlier figures that could not be reproduced.
- The `agy` run uses an unknown default model, so its results are reported as a separate experiment and are not comparable with the Gemini run in tokens or time.

## Log of later actions

(append below)

### Status check (user asked whether work is running)
Run progress was read from the output file and log; the `agy` rerun process was still alive. See the status line in the chat answer for the counts at that time.

### 12:4x Question from user: why does the quota percentage in their own `agy` terminal not decrease
- Checked how the harness calls `agy`: `run_llm.py` `_agy_call()` runs `agy --mode plan --sandbox --print-timeout 300s --output-format json -p "<prompt>"` as a subprocess (one new conversation per call, in an empty temp directory), on the same machine and user account.
- `agy models` lists 13 models (Gemini 4 Argon, Gemini 3.8 Flash, Claude Opus/Sonnet 5.5, GPT-OSS 120B, each with effort levels). The harness passes no `--model`, so the default model is used and its name is not reported in the JSON output.
- `~/.config/agy/config.toml` only holds status-line formatting; it names no model or account.
- Cannot determine from the CLI which quota bucket the user's percentage tracks. Each call reports about 9.5k to 12k tokens of usage in its JSON, so usage is being generated.
- Proposed to the user: pin the model explicitly with `--model` (for comparability with the Gemini API run, `gemini-3.8-flash-medium`) and rerun; awaiting the user's decision. The current run continues meanwhile.

### 12:4x User reply
The user said the quota percentage had simply reset at that time, which explains why it did not decrease. The open question of which model `agy` used by default is unchanged; the run continues with the default model until the user chooses to pin one.

### 12:4x Decision
User chose to continue the current `agy` run unchanged (default model, not pinned). The manuscript must therefore state that the `agy` model is unknown.

### 13:17 agy run finished its first pass; 107 jobs failed
- First pass: 489 of 489 jobs processed with 8 workers (3,246 s). 107 jobs were recorded as `llm_error` after 5 retries each (DIN-style 40, MAC-style 27, DB-GPT-style 21, Naive 19), no `[agy error]` lines in the log, so `agy` returned empty responses rather than raising. Multi-call systems fail more often because any failed call fails the whole job.
- Added a `[empty response]` print to `run_llm.py` and resumed only the failed jobs with 4 workers into the same results file (log `/home/suphachai/fastmcp_eval/run_agy2.log`).

### 13:29 Second pass aborted; root cause of empty `agy` responses found
- The resumed run hit the circuit breaker (16 consecutive failures) at 112 empty responses.
- Diagnosis with a one-line prompt: `agy` prints "a tool required the command permission that headless mode cannot prompt for, so it was auto-denied" and returns an empty `response` (JSON field `denied_actions`: RunCommand). So the empty responses are not a quota or rate problem: the model occasionally tries to run a command and headless mode denies it.
- Did not use `--dangerously-skip-permissions`. Changed `run_llm.py` so that retry attempts (not the first attempt) prepend "Do not use any tools and do not run any commands; answer directly from the text below." Records produced after a retry therefore used a slightly different prompt prefix; this must be disclosed in the manuscript.
- Resumed the failed jobs with 4 workers (log `/home/suphachai/fastmcp_eval/run_agy3.log`). In the first 100 s there were still 11 empty responses.

### 14:34 agy rerun finished (all jobs complete, 0 `llm_error`)
- Passes: first pass 8 workers (489 jobs, 107 failed), second pass 4 workers aborted by the circuit breaker, third pass with the "no tools" retry prefix completed (107/107). Final log `/home/suphachai/fastmcp_eval/run_agy3.log`. Total wall time of the three passes about 4 hours including waiting.
- Conditions: backend `agy` (default model, name not reported), `DEFINE_DELAYED=1`, DIN-style final step uses the last code block, ReAct-style with DDL and `REACT_MAX_TURNS=15`, 60 in-scope questions per system plus 9 out-of-scope for Fast-MCP.
- Results (EX over 60): Fast-MCP 60, Naive 60, Vanna-style 60, DAIL-style 60, ReAct-style 60, DB-GPT-style 59, MAC-style 55 (VSR 0.917, 5 invalid), DIN-style 40. Summary: `llm_results_agy_delayeddef_summary.json`; sequential VES: `ves_sequential_agy.json`.
- Mean tokens per question include about 9k tokens of agent overhead per call; times are not comparable to the Gemini API run.
- Started a failure-analysis subagent for DB-GPT, MAC and DIN wrong answers; outputs will be saved as `failure_analysis_agy*.{json,md}`.

### 14:51 Failure analysis of the agy run (done directly after the analysis subagent hit the 5-hour usage limit of the Claude account)
- The analysis subagent stopped on a rate-limit error (account limit reset 14:50), so the analysis was done directly with a script over `llm_results_agy_delayeddef.jsonl`.
- DB-GPT-style: 1 wrong (staff_advances; filtered on `approval_forms.dept_code`, which differs from the staff department for about 95% of forms).
- MAC-style: 5 wrong, all delayed_projects: 3 execution errors and 2 fragment SQL (partial statement taken as the last code block), no LIMIT in all 5.
- DIN-style: 20 wrong (17 delayed_projects, 3 staff_advances); 17 add an `is_completed` filter despite the glossary. Cause found in the harness: the glossary (with the definition of "delayed") was passed only to DIN's step 3; steps 1 (schema linking) and 4 (correction) did not receive it, so the correction step re-added the filter. This is a harness defect, not evidence about the DIN-SQL method. All 20 wrong records also had retries > 0.
- Fix: `run_llm.py` now passes `GLOSSARY` to DIN steps 1 and 4. Backed up the 60 old DIN records to `results/llm_results_agy_din_v1_glossary_step3_only.jsonl`, removed them from the main file, and started `--systems din_sql_style` with 4 workers (log `/home/suphachai/fastmcp_eval/run_agy_din.log`).

### 14:5x User instruction: continue; what `agy` cannot answer may be done by Opus
- Added `AGY_MODEL` to `run_llm.py` (passes `--model` to `agy`; records get `model = agy:<name>`). Plan: only jobs that stay failed after retries with the default model are rerun with `AGY_MODEL=claude-opus-5-5-medium`; those records are labelled and disclosed in the manuscript, because they come from a different model than the rest of the system's 60 answers.
- Next: write section 4.7 into the manuscript from the 7 completed systems; DIN-style row marked as rerunning until its run finishes.

### 15:0x Manuscript: section 4.7 added
- Inserted section 4.7 "การทดลองเพิ่มเติม: นิยาม delayed ชัดเจน ให้ DDL แก่ ReAct และรันผ่าน agy" before Chapter 5 (doc revision 258), with Table 4.7 for the seven completed systems and six observations; DIN-style row marked as rerunning.
- Still to do after the DIN rerun: fill the DIN row, update the abstract, 5.3, Chapter 6 (tick done items, add H-outcome sentence), and Appendix A/C evidence rows for the `agy` files.

### 15:0x Clarification: "Opus" means the Claude Code CLI itself
- The user clarified that "Opus" means this Claude Code CLI (not an Opus model inside `agy`).
- `claude -p --bare` fails with "Not logged in" (bare mode skips the stored login). Without `--bare`, `claude -p --model opus --tools "" --no-session-persistence --output-format json --system-prompt ...` works (test: correct SQL in about 2 s; the session hooks did not alter the output).
- Added backend `LLM_BACKEND=claude` to `run_llm.py` (`CLAUDE_MODEL`, default `opus`; records get `model = claude:opus`). It runs the same prompts with no tools. Plan: use it only for jobs that remain `llm_error` after the `agy` runs; those records will be reported separately because they come from a different model. Usage counts against the user's Claude account limit (a 5-hour limit was hit earlier in this session), so volume is kept to the residual jobs.

### 15:4x agy exhausted; switch the remaining jobs to the Claude CLI
- User reported that `agy` is exhausted and asked to continue with the Claude CLI. Killed the running `agy` process (DIN-style rerun at 58 of 60 jobs).
- Remaining jobs are run with `LLM_BACKEND=claude` (`claude -p --model opus --tools ""`), so their records carry `model = claude:opus`. They are reported separately in the manuscript.

### 15:5x agy rerun complete; manuscript updated
- The `agy` DIN-style rerun had in fact completed (60 of 60, 0 `llm_error`) when the user reported `agy` exhausted; the process was killed only after completion. No job needed the Claude CLI backend, so no record in the results has `model = claude:opus` (all 489 records are `agy`).
- Final `agy` results (60 per system): Fast-MCP 60, Naive 60, DAIL-style 60, Vanna-style 60, ReAct-style 60, DB-GPT-style 59, MAC-style 55 (VSR 0.917), DIN-style 55 (all 5 wrong in staff_advances, value mismatch from filtering on `approval_forms.dept_code`). Sequential VES recomputed in `ves_sequential_agy.json`; VES values moved by about 4 to 5 percent between two timing runs, so they are reported as coarse only.
- Manuscript (doc rev 269): Table 4.7 filled (DIN row, final VES), DIN paragraph and VES-noise note added; abstract (Thai and English) updated; the hypothesis paragraphs in 1.3, 5.3 and Chapter 6 updated; stale statements about the DIN rerun in 3.6.3, 4.6, 5.2.4 and the Chapter 6 checklist rewritten; Appendix C evidence files and commands for the `agy` run added.
- Not done: the same experiment on `gemini-3.8-flash` with the defined glossary; human check of the gold; page ranges of BIRD, DIN-SQL, Toolformer.

### 16:0x User statement: `agy` is gemini-3.8-flash
- The user stated that `agy` runs gemini-3.8-flash. Not verifiable from the `agy` output (the JSON has no model field and the harness passed no `--model`); the manuscript records it as "identified by the author", with unknown reasoning effort (`agy models` lists low, medium and high variants) and an agent wrapper (about 9k overhead tokens per call).
- Manuscript updated (doc rev 285): replaced "model unknown" statements (abstract Thai and English, 4.6, 4.7, 5.3, Chapter 6, checklist items); accuracy is now described as roughly comparable with the API run, tokens and times as not comparable; "not yet tested on gemini-3.8-flash" changed to "not yet tested through the direct API with the same prompts". The `AGY_MODEL` option remains available to pin `gemini-3.8-flash-medium` if the user wants the effort level fixed.

### 16:1x User feedback: the manuscript's Thai reads like a translation
- User read the manuscript and said the wording sounds translated and asked for subagents to rewrite it in natural Thai.
- Started five subagents, one per section group (abstract and Chapter 1; Chapter 2; Chapter 3; Chapter 4; Chapters 5 and 6 and the appendices). Instructions: shorter sentences, active voice, fewer "ซึ่ง/ถูก/การ" chains, natural connectives; "โมเดล" instead of "แบบจำลอง" for AI models; established technical terms in Latin script (token, prompt, baseline, index, glossary, gold) instead of the transliterations "โทเคน", "พรอมต์", "ระบบฐานเปรียบเทียบ" introduced in the earlier terminology pass; numbers, claims, hedges, citations, code and honesty statements must not change.
- After they finish: spot-check that no number or caveat changed, and report the agents' before/after examples to the user.

### 16:3x Thai naturalisation finished (doc rev 353)
- All five section agents finished (abstract and Chapter 1; Chapter 2: 28 paragraphs; Chapter 3: 71 blocks; Chapter 4; Chapters 5 and 6 and appendices). Rules applied: shorter sentences, fewer "ซึ่ง/ถูก/การ" chains, "โมเดล" for AI models, token/prompt/baseline/gold in Latin script.
- Follow-up fixes by hand: (1) the phrase "ระบบฝั่งผู้ประมวลผล" (my earlier slip) in the DIN paragraph of 4.7 replaced by "ระบบอื่นไม่ได้รับการปรับแบบเท่ากันหลังเห็นผล (MAC-style ได้แก้บั๊กการสกัด SQL ในรอบ API แล้ว)"; (2) the hand-written-SQL gap is now given on both bases in the abstract and 5.3 (3.92 vs 3.25 ms; tool 17 percent lower; 4.4 states both bases); (3) 5.2.2(ช) no longer says the "delayed" definition was not tried (it was, in 4.7); (4) leftover transliterations in appendix tables replaced.
- Verification: searches for "ระบบฐานเปรียบเทียบ" return 0 hits; "แบบจำลอง" remains only in "แบบจำลองข้อมูล" (data model) in 3.3. No numbers were intentionally changed; agents reported the checks they made.

### 16:4x User question: why are Fast-MCP, DAIL-style and Vanna-style tied; test harder questions, simulate with Claude here instead of Gemini
- Reason for the tie: the main question set is easy and template-based, and the DAIL/Vanna demos use the same templates. Harder questions are needed to separate the systems.
- User allowed running the simulation with the models available in this session (both the Gemini API and `agy` quotas are exhausted), not necessarily gemini.
- Created `qgen_hard.py` (38 questions: A paraphrase 12, B variants outside tool parameters 8, C analytics outside the tools 10, D traps 8 such as department names instead of codes and relative months) and `gold_hard.py` (pure-Python gold; tiers A and D reuse `gold.py`). Files: `/home/suphachai/fastmcp_eval/qh_800000.jsonl`, `gold_hard_800000.json` (2 of the 12 tier-A items have empty gold).
- Patched `run_llm.py`: questions with a gold result but no intended tool (tiers B and C) are scored for all systems; Fast-MCP gets `abstained` when it calls no tool.
- Started the run with the Claude CLI backend (`LLM_BACKEND=claude`, `claude -p --model opus --tools ""`), systems fast_mcp, naive_sql, dail_sql_style, vanna_style, 4 workers, `DEFINE_DELAYED=1`, output `results/llm_results_hard_claude.jsonl` (environment `llm_run_env_hard_claude.json`).

### 16:5x Hard question set run finished and written into the manuscript
- Run (152 of 152 jobs, 0 errors, Claude Opus via the Claude Code CLI, 4 workers, `DEFINE_DELAYED=1`): correct per tier, Fast-MCP / Naive / DAIL-style / Vanna-style: A paraphrase 12/12 for all; B variants 2/8, 8/8, 8/8, 8/8; C analytics 0/10, 10/10, 10/10, 10/10; D traps 8/8, 8/8, 6/8, 5/8; total 22, 38, 36, 35 of 38.
- Fast-MCP on tiers B and C: 6 abstentions (3 B, 3 C) and 10 wrong tool calls; for tier C, 7 of 10 questions got a wrong tool call instead of an abstention. The 2 tier-B items it got right were not examined individually.
- DAIL-style and Vanna-style tier-D errors: h017 and h019 read "first/last month of fiscal year 2026" as months 10 and 9 (Thai fiscal year starts in October) whereas the gold and tool description use months 1 to 12; this is an ambiguity in the question, not a clear model error. Vanna-style h021 returned 0 rows with the right month; cause not examined. Two tier-A gold sets are empty (h007, h023).
- Manuscript (doc rev about 360): new section 4.8 with the tier table and limitations; added paragraphs to the Thai and English abstract, section 5.3 and Chapter 6; Appendix C evidence files and command.
- Caveats written in the text: different model (Claude Opus) from the other runs, 38 questions, one run per question, question author is also the tool author, tokens and times not reported (CLI overhead).

### 17:0x User chose the hybrid approach
- Added to `run_llm.py`: `ROUTER_SYSTEM` (strict applicability conditions for the three tools; reply NONE otherwise), `sys_hybrid`, `run_tool`, and two systems: `hybrid` (tool if the router accepts, else zero-shot SQL as in Naive SQL with the glossary) and `fast_mcp_strict` (same strict router, no fallback, abstains on NONE) to separate the effect of the stricter router from the effect of the SQL fallback. Correctness for both is result-based (match to gold), whichever route is used.
- Started the run on the 38 hard questions with the Claude CLI backend (Claude Opus), 4 workers, `DEFINE_DELAYED=1`; output `results/llm_results_hard_hybrid_claude.jsonl`, log `/home/suphachai/fastmcp_eval/run_hybrid.log`.

### 17:1x Hybrid run finished and written into the manuscript (section 4.9)
- 76 of 76 jobs, 0 errors, Claude Opus via the CLI. `hybrid`: A 12/12, B 8/8, C 10/10, D 8/8 = 38/38; routes: tool for all 12 A and 8 D questions, SQL fallback for all 8 B and 10 C questions. `fast_mcp_strict` (same router, no fallback): A 12, B 0, C 0, D 8 = 20/38, with all 18 B and C questions abstained (0 wrong tool calls, against 10 wrong tool calls with the original tool prompt).
- The router prompt (`ROUTER_SYSTEM`) was written after seeing the failures on this same hard set, so 38/38 may be overfitted; stated in the manuscript as an exploratory result. Confirmation needs new questions written after the router is frozen.
- Manuscript: section 4.9 inserted before Chapter 5; 5.3 sentence on the hybrid approach updated from "not tested" to "preliminary test in 4.9".
- Outputs: `results/llm_results_hard_hybrid_claude.jsonl`, log `/home/suphachai/fastmcp_eval/run_hybrid.log`.

### 17:2x User correction of the research title
- The user stated the title must be "Conversational Budget Intelligence: Achieving 99% Latency Reduction via Semantic MCP Fast Tools and Thai Financial NLP". Applied to the manuscript heading and the document name.
- Check against the measurements, flagged to the user: no measurement supports "99% latency reduction" (largest measured reductions: database time 9.4x faster, i.e. about 89 percent less, only against the same SQL without the compound index, and 3 to 17 percent against hand-written SQL on the same index; Fast-MCP LLM median time 3.8 s versus 5.7 s for DAIL-style (33 percent less), 28.8 s Naive SQL (87 percent less), 63 s DIN-style (94 percent less), gemini-3.8-flash runs); and every question in the experiments is in English, so "Thai Financial NLP" is not tested. The title also does not mention the finding that Fast-MCP is not more accurate overall and loses coverage (section 4.8).
- The README citation title and the Chapter 1 wording were not changed.

### 17:3x Title decision
- The user chose option (a): change the title to match the results. New title (heading and document name, doc rev 359): "Conversational Budget Intelligence: Semantic MCP Tools versus Free-form Text-to-SQL on an 800,000-Row Enterprise Ledger". Searches of the manuscript for "99%" and "Sub-Second" return no hits. The README citation block (`@article ... title`) and badges still use the earlier title and figures; not edited.

### 17:4x Naming decision: keep "Fast-MCP"
- The user chose to keep the system name Fast-MCP. Added a naming paragraph at the end of section 1.1 (Semantic MCP tools = the approach; Fast-MCP = the prototype, `fast_mcp` in code; the name does not claim to be faster than every baseline) and adjusted the Thai and English abstract sentences that introduce the system.

### 17:5x Commit and push (user request)
- Exported the manuscript to Markdown (134,656 characters) as `manuscript/thesis_draft.md` in the working tree; that folder is excluded locally through `.git/info/exclude` and was NOT committed, because the repository https://github.com/aodbee/fast-mcp-benchmark is PUBLIC and the README states the manuscript is under peer review. Awaiting the user's decision.
- Created branch `eval-harness-results` (not main), committed 28 files (all of `benchmark/eval/`, plus the edits to `benchmark/fast_mcp/semantic_tools.py` and `benchmark/llm_client.py`) as 6c0b4f1, pushed to origin. Secret scan before commit: no API keys found; `.env` is git-ignored. The other files already modified in the working tree before this session (README.md, baselines, etc.) were not staged. `perplexity/` not committed.
- The log entry above (this paragraph) was written after the commit and is not part of it.
