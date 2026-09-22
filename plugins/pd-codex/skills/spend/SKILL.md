---
name: spend
description: Estimate the API list-price equivalent of a Codex session, including linked subagents, from local session records. Use when asked what a session or orchestrated run cost, for a per-agent cost breakdown, or where its tokens went.
---

# Session spend

Run the adjacent `scripts/spend.py` with Python from the project directory:

```text
python <path-to-this-skill>/scripts/spend.py [<session-id> | <rollout-path>] [--log]
```

With no argument, the script uses `CODEX_THREAD_ID` (or `CODEX_SESSION_ID`) to select the active Codex thread when available, then follows its parent links to include the root and linked subagents. If neither variable is available, it falls back to the latest root session for the current working directory. Pass an explicit session ID or rollout path when reporting a different session.

Show the script's report, which puts model and reasoning level, completed turns (plus any currently active turn), and estimated cost first. Briefly explain any missing usage, unknown models, or incomplete agent linkage that the report flags. Do not read full rollout files into model context; the script streams them and prints only the summary. If the script cannot identify the intended session, ask for its session ID or path.

The dollars are a rough **Standard API list-price equivalent**, not the amount charged for a Codex subscription or a final invoice. The estimate uses recorded token usage and dated rates in the script. It omits tool, sandbox, regional, processing-mode, and long-context adjustments when those details are unavailable. Usage in an active session may still change. Check current official OpenAI model pricing before updating the rate table.

Use `--log` only when the user requests a persistent spend history; it appends a summary to `~/.codex/spend-log.jsonl`.
