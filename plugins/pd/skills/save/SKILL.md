---
name: save
description: 'Pre-compaction checkpoint: write everything only the conversation knows (in-progress work, loose threads, decisions, corrections) to durable files before context is compacted.'
when_to_use: Use on /save, "save before compacting", "context is getting full", "checkpoint this", or whenever the user is about to run /compact and wants nothing lost. Not for ending a session (pd:finish) or clearing to a fresh one (pd:cls).
---

# Save — Pre-Compaction Checkpoint

Context is nearly full and the user is about to compact. Compaction keeps the files on disk and loses the conversation: the reasoning behind uncommitted changes, the thread you were halfway through pulling, the correction the user gave three hours ago, the agent still running in the background. This skill moves all of that out of the conversation and into files, then tells the user it is safe to compact.

The session continues after compaction. You are writing for **yourself, a few minutes from now, with a summary instead of a memory**. Not for a fresh session (that is `pd:cls`), and not closing out (that is `pd:finish`).

## Rules

- **Be cheap.** Context is the scarce resource. Write from what you already know. Run only the git commands below; do not re-read files or re-investigate anything to make the checkpoint "complete".
- **Your lane only.** Other sessions' branches, PRs, and commits are not loose threads. The test for every line: did this session do it, decide it, or get asked it?
- **Durable over clever.** Everything goes in a file that survives compaction. Nothing lives only in your reply.
- **No new work.** Do not fix, commit, or resolve anything while saving. If something is half-done, record that it is half-done.
- **If the user gave a gist** (`/save then finish the migration`), use it as the "next step" anchor in the checkpoint.

## Flow

### 1. Quick state check

Run as separate Bash calls, not chained: `git status -sb`, `git diff --stat`, `git log --oneline -5`. Check TaskList for open items if it exists. Note any background agents or tasks this session started that have not reported back.

That is the whole investigation. Everything else comes from the conversation.

### 2. Sort what you know

Walk the session and bin each thing into exactly one of these:

| Bin | What it is | Where it goes |
|-----|-----------|---------------|
| **Durable knowledge** | Corrections the user made, stated preferences, process rules, project facts you had to discover the hard way, decisions and their reasons | Memory (step 3) |
| **Plan or spec state** | A plan file this session is executing: which steps are done, which is current, deviations from the plan | Edit the plan file in place (step 3) |
| **Working state** | What you are in the middle of, uncommitted changes and why, what is left, next step | Checkpoint file (step 4) |
| **Loose threads** | Things noticed and deferred, promises made, questions the user has not answered, agents still running | Checkpoint file (step 4) |
| **Already captured** | Committed, pushed, written to a file, or recorded in memory during the session | Nothing; name it in one line so you do not rewrite it |

If a bin is empty, skip it. Do not pad.

### 3. Write durable knowledge where it belongs

Use whichever memory store this session already uses: the auto memory directory the system prompt named, a project `memory/` convention such as `memory/capture.md` with a category tag (CORRECTION, PROCESS, PREFERENCE, WORKFLOW, INSIGHT), or CLAUDE.md for a build or safety rule the project cannot work without. Follow the store's existing format. One entry per fact, written so it makes sense to a reader who has not seen this session.

Memory is for things that will still be true next week. A half-finished task is not memory; it is working state.

If this session is executing a written plan, mark progress in the plan file itself (done, current, skipped and why). That file is the plan's source of truth and outlives both the conversation and the checkpoint.

### 4. Write the checkpoint

Save to `local/save-<YYYYMMDD-HHMM>.md` if `local/` exists in the project root, otherwise `/tmp/save-<YYYYMMDD-HHMM>.md`. Structure (drop empty sections):

```
# Checkpoint <date time>

## Doing
[the task in one or two sentences, and the user's gist if given]

## State
[branch; uncommitted changes and what they are for; what is done; what is in progress; what is not started]

## Next step
[the single concrete thing to do first after compaction]

## Decisions
[decisions made this session and why; the ones that are hardest to reconstruct]

## Loose threads
[deferred items, promises, questions waiting on the user, background agents and what they are doing]

## Key files
[paths to read first to rebuild understanding, one line each on why]

## Do not repeat
[mistakes made this session, approaches that failed, corrections given]
```

Write it in the second person, direct, as instructions to yourself. Twenty to sixty lines is typical. A plan-execution session with the plan file updated needs far less: point at the plan and record only what is not in it.

### 5. Report and hand off

Reply with, in this order:

1. One line per file written or updated, with the path.
2. One line naming anything already captured that you did not rewrite.
3. The exact command to run, in a code block:

```
/compact Read <checkpoint-path> and continue from "Next step".
```

Putting the path in the compact instruction is what carries it across: the summary is built around that instruction, so the post-compaction session knows where to look. If no checkpoint was needed (everything was already in files and memory), say so in one line and suggest a plain `/compact`.

## Not this

- Not `pd:cls`: that writes a prompt for a fresh session after `/clear`. This session continues.
- Not `pd:finish`: no git hygiene questions, no session outcomes, no wins. Just get the state out.
- Not a time to commit: an uncommitted diff survives compaction fine. What does not survive is why it exists, so write that down instead.
