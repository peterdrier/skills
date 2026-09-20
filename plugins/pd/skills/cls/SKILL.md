---
name: cls
description: Context-preserving clear. Use when the user says /cls or "clear and continue". Generates a continuation prompt that captures everything a fresh session needs to seamlessly pick up where this one left off.
---

# Context-Preserving Clear

Generate a self-contained continuation prompt so the user can `/clear` and resume without losing context.

## Flow

1. If the user provided a gist with `/cls` (e.g., `/cls finish the PR fixes`), use it as the "next steps" anchor
2. **Triage** — determine what kind of handoff this is (see below)
3. Generate a prompt sized to the handoff type
4. Save it and tell the user how to resume

## Triage: What Kind of Handoff?

Check these in order — use the **first** that matches:

### 1. Plan-ready handoff
A written plan or spec exists for the next session to execute.

**Detect:** Look for plans in `docs/plans/`, `docs/superpowers/plans/`, or any plan file path mentioned in conversation. Also check `docs/features/` for specs just written.

**Prompt:** 3-10 lines. Just point at the plan.

```
Read and execute the implementation plan at `<absolute-path-to-plan>`.

The spec is at `<absolute-path-to-spec>` if you need business context.

<any critical notes not in the plan — e.g., "the ShiftAdmin User include needs verification per Task 6 Step 0">
```

### 2. Mid-task handoff
Work in progress, not yet captured in a document (uncommitted changes, failing tests, partially completed task).

**Detect:** `git status -s` shows modifications, TaskList has in-progress items, or the conversation shows unfinished work.

**Prompt:** 20-50 lines. What's being done, what state it's in, what's left, decisions already made, key file paths.

### 3. Exploratory/multi-topic handoff
Multiple topics, decisions, or context not captured in any document.

**Detect:** Neither of the above matched.

**Prompt:** 40-80 lines. Full context dump.

## Context Gathering

Only gather what the handoff type requires:

| Source | Plan-ready | Mid-task | Exploratory |
|--------|-----------|----------|-------------|
| Plan/spec file paths | yes | if relevant | if relevant |
| Git state | no | yes | yes |
| Active tasks (TaskList) | no | yes | yes |
| Session accomplishments | no | brief | full |
| Key decisions | only if not in plan | yes | yes |
| Key files | no (plan has them) | yes | yes |
| Corrections/preferences | only if critical | yes | yes |

**Git state** — run `git diff --stat` and `git status -s`.

**Active tasks** — check TaskList for incomplete items.

**Memory** — note any memories created/updated this session (new session has them automatically, but calling them out aids continuity).

## Generating the Prompt

First person, direct, no fluff. New Claude starts working immediately. For **mid-task** and **exploratory** handoffs, use this structure (adapt as needed, drop empty sections):

```
I'm continuing work from a previous session. Here's the context:

## Project
[project name, path, brief tech stack if relevant]

## What Was Done
[bullet points of session accomplishments]

## Current State
[what's done, what's in progress, uncommitted changes, branch state]

## Key Decisions
[decisions made and why — these are the hardest to reconstruct]

## Key Files
[absolute paths the new session should read first to rebuild understanding]

## Next Steps
[what to work on next — anchored by user's gist]

## Notes
[gotchas, preferences, corrections given during session, anything the new Claude should know to avoid repeating mistakes]
```

## Saving and Delivery

**Plan-ready handoffs:** No separate file. Tell the user: "After `/clear`, type: `read <plan-path> and execute`".

**Mid-task and exploratory handoffs:**
1. Output the prompt in a fenced code block
2. Save to `local/cls-<random7>.md` if `local/` exists in project root, otherwise `/tmp/cls-<random7>.md`
3. Tell the user where it was saved; they can paste it or type: `read <saved-path> and continue`
