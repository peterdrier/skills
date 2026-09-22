---
name: context-cleanup
description: "Audit and restructure a project's Claude Code context files (CLAUDE.md, .claude/, memory/, skills) for intentional, efficient use of the context window. Use when context feels bloated, disorganized, or stale -- or periodically as hygiene. Produces a report first, then restructures with approval."
---

# Context Cleanup

Audit all context sources in a project, produce a cleanup report, then restructure with user approval.

## Process

0. **Fresh context check** -- recommend /clear if conversation has prior work
1. **Inventory** -- discover all context sources
2. **Analyze** -- score each source against best practices
3. **Report** -- present findings and proposed changes
4. **Wait for approval** -- do not edit files until the user approves
5. **Restructure** -- execute approved changes

## Step 0: Fresh Context Check

If prior tool calls, edits, skill invocations, or a compaction notice are present, stop and tell the user: "This conversation has prior context loaded. Run `/clear` first, then re-invoke `/context-cleanup`." Otherwise proceed.

## Step 1: Inventory

Discover and read every file that contributes to Claude's context:

| Source | Where to look |
|--------|--------------|
| Project instructions | `CLAUDE.md` in project root |
| Extended docs | `.claude/*.md` files |
| Skills (project) | `.claude/skills/` |
| Skills (user, readonly) | `~/.claude/skills/` |
| Memory atoms | `memory/` + `memory/INDEX.md`, if the project uses them |
| Settings | `.claude/settings.json`, `.claude/settings.local.json` |

Also follow any `See ...` references inside CLAUDE.md.

## Step 2: Analyze

See [references/context-tiers.md](references/context-tiers.md) for the tiering framework.

**Tiers:**
- **Tier 1 (CLAUDE.md)**: Build/break rules, safety rules, high-frequency instructions
- **Tier 2 (.claude/ subfiles)**: Domain details, workflows, reference material
- **Tier 3 (external)**: Large schemas, full API docs, frequently-changing content

**Issues to flag:**
1. **Duplication** -- same instruction in multiple files
2. **Contradiction** -- conflicting instructions
3. **Stale content** -- deleted file refs, completed work listed as pending
4. **Bloat** -- verbose explanations where a concise rule suffices
5. **Missing pointers** -- Tier 2 content inline in CLAUDE.md with no subfile
6. **Orphaned files** -- .claude/ files nothing references

**Size guidelines (soft):** CLAUDE.md under 150 lines; .claude/*.md subfiles under 200 lines.

**Skills audit:** Is the skill still relevant? Does it duplicate CLAUDE.md content? Note user-level skills as readonly.

## Step 3: Report

```
## Context Cleanup Report

### Summary
- Total context files: N
- Estimated always-loaded tokens: ~N
- Issues found: N

### Critical (wrong tier / contradictions)
- [file:line] Issue description

### Cleanup (duplication / bloat / stale)
- [file:line] Issue description

### Suggestions (organization improvements)
- Description

### Proposed Changes
- What moves where (before/after line counts)
- What gets deleted and why
- What gets consolidated and why

### Skills Review
- [skill-name] Status and recommendation
```

## Step 4: Wait for Approval

After presenting the report, ask what to proceed with. Do NOT edit any files until explicitly approved.

## Step 5: Restructure

Execute approved changes. For each change:
1. Make the edit
2. Verify CLAUDE.md still references all .claude/ subfiles that exist
3. Verify no broken references

Present a brief before/after line-count summary when done.

## Key Principles

- **CLAUDE.md is prime real estate** -- every token here loads on every interaction; be ruthless.
- **Pointers over content** -- reference subfiles rather than inlining their content.
- **Don't touch user-level skills** -- report on `~/.claude/skills/` but never modify it.
