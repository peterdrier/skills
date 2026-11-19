#!/usr/bin/env python3
"""Cost report for a Claude Code session (main thread + every subagent transcript).

Usage: python spend.py [<session-id> | <transcript-path>] [--log]

With no argument, uses the most recently modified session transcript under
`~/.claude/projects/<project-dir>/` for the CURRENT WORKING DIRECTORY's project
(run this from the project root). A bare session id (its transcript's filename,
no `.jsonl`) is searched for across all project dirs. A path is used as-is.

Reads the main transcript plus every file under `<session>/subagents/*.jsonl`.
Each transcript can contain several records per API call (streaming updates) —
they share `requestId`; only the LAST record per `requestId` carries the final
usage tally, so summing is deduped on that key, last-write-wins.

This script does all the transcript reading; nothing here should be read via a
model's own file tools — transcripts are enormous JSONL and would flood context
for no benefit (see the accompanying SKILL.md).

`--log` appends one JSON line (session id, date, per-agent rows, totals) to
`~/.claude/spend-log.jsonl` for later trend analysis. Never pass it during a test
run of this script itself.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# $/MTok: fresh input, output, cache write, cache read (API list prices).
# Re-check against https://www.anthropic.com/pricing if these look stale.
AS_OF = "2026-11-11"
RATES = {
    "fable-5-2": (8, 40, 10.00, 0.20),  # must precede plain "fable"
    "mythos-5-2": (8, 40, 10.00, 0.20),  # must precede plain "mythos"
    "fable-5-1": (10, 50, 12.50, 0.25),
    "mythos-5-1": (10, 50, 12.50, 0.25),
    "fable": (10, 50, 12.50, 1.00),
    "mythos": (10, 50, 12.50, 1.00),
    "opus-5-5": (4, 20, 5.00, 0.20),  # must precede plain "opus"
    "opus": (5, 25, 6.25, 0.50),
    "sonnet-5-5": (2, 10, 2.50, 0.10),  # must precede "sonnet-5"
    "sonnet-5": (2, 10, 2.50, 0.20),  # must precede plain "sonnet"
    "sonnet": (3, 15, 3.75, 0.30),
    "haiku-5-5": (0.10, 0.50, 0.125, 0.01),  # must precede plain "haiku"; ≤100k prompt
    "haiku": (1, 5, 1.25, 0.10),
}
# Haiku 5.5 bills every token at 5× once the request's prompt (input + cache) exceeds 100k.
HAIKU_5_5_LONG = (0.50, 2.50, 0.625, 0.05)

TIER_RE = re.compile(r"-(haiku|sonnet|opus|fable)(-(low|medium|high))?$")


def rate_for(model, prompt_tokens=0):
    if "haiku-5-5" in (model or "") and prompt_tokens > 100_000:
        return HAIKU_5_5_LONG
    for key, r in RATES.items():
        if key in (model or ""):
            return r
    return None  # unpriced: unknown model id


def project_dir_for(cwd):
    return re.sub(r"[:\\/]", "-", cwd)


def default_transcript():
    pdir = Path.home() / ".claude" / "projects" / project_dir_for(os.getcwd())
    candidates = glob.glob(str(pdir / "*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def resolve_transcript(arg):
    if arg is None:
        return default_transcript()
    if os.path.isfile(arg):
        return arg
    matches = glob.glob(str(Path.home() / ".claude" / "projects" / "*" / f"{arg}.jsonl"))
    return matches[0] if matches else None


def usage_records(path):
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except ValueError:
            continue
        msg = j.get("message") or {}
        u = msg.get("usage")
        if u:
            yield j.get("requestId"), j.get("timestamp"), msg.get("model"), u, j.get("effort")


def turn_count(path):
    """User prompts: user records that aren't tool results, meta, or slash-command echoes."""
    n = 0
    for line in open(path, encoding="utf-8", errors="ignore"):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") != "user" or j.get("isMeta"):
            continue
        c = (j.get("message") or {}).get("content")
        if isinstance(c, str):
            n += not c.lstrip().startswith(("<command-", "<local-command-"))
        elif isinstance(c, list):
            n += any(b.get("type") != "tool_result" for b in c if isinstance(b, dict))
    return n


def dedup_last(records):
    """requestId -> (timestamp, model, usage, effort), LAST record per id wins (streaming updates)."""
    by_id = {}
    for i, (rid, t, model, u, effort) in enumerate(records):
        by_id[rid if rid is not None else f"_norid_{i}"] = (t, model, u, effort)
    return by_id


def usage_stats(by_id):
    """-> (model -> {in,out,cw,cr,usd,requests,priced}, first_ts, last_ts)."""
    by_model = {}
    first = last = None
    for t, model, u, _effort in by_id.values():
        i = u.get("input_tokens", 0)
        o = u.get("output_tokens", 0)
        cw = u.get("cache_creation_input_tokens", 0)
        cr = u.get("cache_read_input_tokens", 0)
        key = model or "?"
        b = by_model.setdefault(
            key, {"in": 0, "out": 0, "cw": 0, "cr": 0, "usd": 0.0, "requests": 0, "priced": True}
        )
        b["in"] += i
        b["out"] += o
        b["cw"] += cw
        b["cr"] += cr
        b["requests"] += 1
        r = rate_for(model, i + cw + cr)
        if r is None:
            b["priced"] = False
        else:
            b["usd"] += (i * r[0] + o * r[1] + cw * r[2] + cr * r[3]) / 1e6
        if t:
            first = t if first is None or t < first else first
            last = t if last is None or t > last else last
    return by_model, first, last


def pins_tier(agent_type):
    """True when the agent type's name carries a model tier (e.g. `pd:orch-haiku-low`)."""
    return bool(TIER_RE.search(agent_type or ""))


def efforts_of(by_id):
    """Effort levels the requests actually ran at, as recorded per request by Claude Code."""
    seen = sorted({e for _t, _m, _u, e in by_id.values() if e})
    return "+".join(seen) if seen else "?"  # "?": transcript predates effort recording


def find_agent_files(transcript_path):
    base = transcript_path[: -len(".jsonl")] if transcript_path.endswith(".jsonl") else transcript_path
    return sorted(glob.glob(os.path.join(base, "subagents", "*.jsonl")))


def agent_info(path):
    """-> (title, agent_type) for a subagent transcript.

    The sidecar `<agent>.meta.json` holds the spawn's `description` (the title the
    orchestrator gave it) and `agentType`. Either can be missing (older Claude Code,
    named teammates), so the title falls back to the meta `name`, then the filename.
    """
    meta = {}
    meta_path = path[: -len(".jsonl")] + ".meta.json"
    if os.path.isfile(meta_path):
        try:
            meta = json.load(open(meta_path, encoding="utf-8")) or {}
        except (ValueError, OSError):
            pass
    fname = os.path.basename(path)
    stem = fname[: -len(".jsonl")]
    if fname.startswith("agent-a") and not re.fullmatch(r"agent-a[0-9a-f]{16}", stem):
        # named teammate: agent-a<name>-<16-hex-hash>.jsonl
        fallback = re.sub(r"-[0-9a-f]{16}$", "", stem[len("agent-a") :])
    elif fname.startswith("agent-"):
        fallback = stem[len("agent-") :]
    else:
        fallback = fname
    title = meta.get("description") or meta.get("name") or fallback
    return title, meta.get("agentType") or meta.get("name") or "-"


def cell(text):
    """Make free text safe inside a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def short_ts(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00")).strftime("%H:%M:%S")


def duration_str(first, last):
    if not first or not last:
        return "-"
    d = datetime.fromisoformat(last.replace("Z", "+00:00")) - datetime.fromisoformat(
        first.replace("Z", "+00:00")
    )
    secs = int(d.total_seconds())
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m}m"
    if m:
        return f"{m}m{s}s"
    return f"{s}s"


def build_row(label, agent_type, by_id, turns):
    by_model, first, last = usage_stats(by_id)
    tok = {"in": 0, "out": 0, "cw": 0, "cr": 0}
    usd = 0.0
    unpriced = set()
    for model, b in by_model.items():
        for k in tok:
            tok[k] += b[k]
        usd += b["usd"]
        if not b["priced"]:
            unpriced.add(model)
    return {
        "label": label,
        "type": agent_type,
        "effort": efforts_of(by_id),
        "models": by_model,
        "turns": turns,
        "requests": len(by_id),
        "tok": tok,
        "usd": usd,
        "unpriced": unpriced,
        "first": first,
        "last": last,
    }


def merge_model_rollup(rollup, by_model):
    for model, b in by_model.items():
        r = rollup.setdefault(
            model, {"in": 0, "out": 0, "cw": 0, "cr": 0, "usd": 0.0, "requests": 0, "priced": True}
        )
        for k in ("in", "out", "cw", "cr", "requests"):
            r[k] += b[k]
        r["usd"] += b["usd"]
        r["priced"] = r["priced"] and b["priced"]


def main():
    ap = argparse.ArgumentParser(description="Cost report for a Claude Code session.")
    ap.add_argument("target", nargs="?", help="session id or transcript path")
    ap.add_argument("--log", action="store_true", help="append a JSON line to ~/.claude/spend-log.jsonl")
    args = ap.parse_args()

    transcript = resolve_transcript(args.target)
    if not transcript:
        print("No transcript found (pass a session id/path, or run from the project's cwd).", file=sys.stderr)
        return 1

    session_id = os.path.basename(transcript)[: -len(".jsonl")]

    main_by_id = dedup_last(usage_records(transcript))
    rows = [build_row("main (orchestrator)", "-", main_by_id, turn_count(transcript))]
    session_effort = rows[0]["effort"]
    for p in find_agent_files(transcript):
        by_id = dedup_last(usage_records(p))
        if not by_id:
            continue
        label, agent_type = agent_info(p)
        rows.append(build_row(label, agent_type, by_id, turn_count(p)))

    ordered = [rows[0]] + sorted(rows[1:], key=lambda r: r["first"] or "")

    print(f"# Spend report: {session_id}\n")
    print("| Agent | Type | Model | Effort | Turns | Reqs | In | Out | Cache W | Cache R | Est $ | Start | Dur |")
    print("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    total_tok = {"in": 0, "out": 0, "cw": 0, "cr": 0}
    total_usd = 0.0
    all_unpriced = set()
    model_rollup = {}
    orch_usd = ordered[0]["usd"]
    inherited = []
    for r in ordered:
        models = "+".join(m.removeprefix("claude-") for m in sorted(r["models"])) or "?"
        effort = r["effort"]
        if r is not ordered[0] and not pins_tier(r["type"]):
            effort += "*"
            inherited.append(r)
        start = short_ts(r["first"]) if r["first"] else "-"
        t = r["tok"]
        print(
            f"| {cell(r['label'])} | {cell(r['type'])} | {models} | {effort} | {r['turns']} | {r['requests']} "
            f"| {t['in']:,} | {t['out']:,} | {t['cw']:,} | {t['cr']:,} | ${r['usd']:.2f} "
            f"| {start} | {duration_str(r['first'], r['last'])} |"
        )
        for k in total_tok:
            total_tok[k] += t[k]
        total_usd += r["usd"]
        all_unpriced |= r["unpriced"]
        merge_model_rollup(model_rollup, r["models"])
    print(
        f"| **TOTAL** | | | | {sum(r['turns'] for r in ordered)} | {sum(r['requests'] for r in ordered)} | {total_tok['in']:,} | {total_tok['out']:,} "
        f"| {total_tok['cw']:,} | {total_tok['cr']:,} | **${total_usd:.2f}** | | |"
    )
    print()
    print(f"estimated, API list prices as of {AS_OF}; Start is UTC; Effort is what each request actually ran at")
    if inherited:
        print()
        print(
            f"\\* {len(inherited)} agent(s) whose type names no tier: nothing pinned their effort, so they "
            f"most likely inherited the session's ({session_effort}). Spawn a tiered agent type to pin it."
        )
    print()
    print("By model:")
    for model, b in sorted(model_rollup.items(), key=lambda kv: -kv[1]["usd"]):
        flag = "" if b["priced"] else " (unpriced)"
        print(f"- {model}{flag}: {b['requests']} reqs, ${b['usd']:.2f}")
    if all_unpriced:
        print()
        print(f"unpriced models (billed \\$0 above, not guessed): {', '.join(sorted(all_unpriced))}")
    share = (orch_usd / total_usd * 100) if total_usd else 0.0
    print()
    print(f"orchestrator share: {share:.0f}% of est. cost")

    if args.log:
        date = (ordered[0]["first"] or datetime.utcnow().isoformat() + "Z")[:10]
        entry = {
            "session_id": session_id,
            "date": date,
            "agents": [
                {
                    "label": r["label"],
                    "type": r["type"],
                    "effort": r["effort"],
                    "models": sorted(r["models"]),
                    "turns": r["turns"],
                    "requests": r["requests"],
                    "tokens": r["tok"],
                    "usd": round(r["usd"], 6),
                }
                for r in ordered
            ],
            "totals": {"tokens": total_tok, "usd": round(total_usd, 6)},
        }
        log_path = Path.home() / ".claude" / "spend-log.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print()
        print(f"logged to {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
