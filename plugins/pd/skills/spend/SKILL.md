---
name: spend
description: 'After-the-fact cost report for a Claude Code session: tokens and estimated dollars per agent, parsed from transcripts.'
when_to_use: Use on /spend, "what did that cost", "cost breakdown", "where did the tokens go", or after an orchestrated run. Unlike the built-in /cost, it breaks down per agent.
---

# spend

A script reads the transcripts; you never do. They are enormous JSONL files and
opening one directly would flood context for a report that should cost almost
nothing to produce.

## Run it

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/spend/scripts/spend.py" [<session-id> | <transcript-path>] [--log]
```

If the project carries its own copy at `.claude/skills/spend/scripts/spend.py`, prefer that
one — it may be newer.

No argument: reports the most recent session for the current working directory's
project (run from the project root). Add `--log` after an orchestrated run to
append the totals to `~/.claude/spend-log.jsonl` for later trend analysis — skip
it for a plain "what did that cost" lookup.

Show the printed markdown table verbatim. Then add up to three lines of
observations, e.g.:
- orchestrator share vs. the cheapest way this could have gone
- the priciest agent, and whether its tier matches its actual cost
- anything shown as `untagged` (no tier suffix) or under "unpriced models"

Never open a transcript file directly (`Read`, `cat`, grep-and-page-through) to
answer a cost question — they can be tens of megabytes per session and dwarf any
answer they'd produce. If the script's output is insufficient, extend the script.
