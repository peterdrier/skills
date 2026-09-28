---
name: cleanup
description: Sweep ALL git worktrees and stale local branches in the current repo and remove the dead ones safely — merged PRs, detached heads already reachable elsewhere, work that landed under another PR, branches deleted on origin. Use when the user says "clean up worktrees", "cleanup", "/cleanup", "prune worktrees", "what worktrees can go", "delete merged branches", or when worktrees have piled up across sessions. Surveys everything in one call, proposes one table, asks one bulk question, removes via git's own plumbing, and ends with a CLEAN or STOP banner. For a single just-merged PR use pd:merged instead.
---

# Cleanup — Sweep Every Dead Worktree

`pd:merged` cleans the one PR that just landed. This skill clears the backlog: every worktree and local branch in the repo, classified, proposed in one table, removed after one bulk answer. It reuses `pd:merged`'s removal ladder and banners, so read the non-negotiables there if anything here is unclear.

Removal is the dangerous part and the rules exist because the survey can be wrong: a worktree that looks dead may belong to another live session, or hold uncommitted tests. So nothing is removed without the user seeing it in the table first, and anything uncertain is a question, not a guess.

## 1. Sync and survey (one call)

Read the repo's CLAUDE.md for its worktree root: default `<repo>/.claude/worktrees`, but some repos use another (e.g. `worktrees/`). Then:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/survey.sh"
```

It runs `git fetch --prune` and changes nothing else. It prints one row per worktree (branch, dirty count, commits ahead of `origin/main`, remote branch, PR state, idle time), the local branches that have no worktree (with `[gone]` when origin deleted them), and the dirty files of each dirty worktree. Columns are defined in [references/classification.md](references/classification.md).

If local `main` is behind and `main` isn't checked out anywhere, fast-forward it with `git fetch origin main:main`. This refuses anything but a fast-forward. If `main` is checked out in the main checkout, leave it: it becomes a to-do item.

## 2. Classify

Apply the rules in [references/classification.md](references/classification.md) to every row, first match wins. In short: merged + clean goes; open PR or unique commits stays; recent with no PR, or real uncommitted files, is a question. A merged PR is authoritative. Never second-guess a squash merge with ancestry checks.

When the user asks "what is X?", answer from `git log --oneline <base>..<branch>`, the ahead count and the PR title before recommending anything.

## 3. Present one table, ask one question

Summarise leftovers by pattern (`public/_spa/** build output`), never as a file dump. Then ask one question covering every *ask* row, so the user can answer in bulk ("codex review can go, rfp stays, X is active elsewhere").

| worktree | state | leftovers | proposed |
|---|---|---|---|
| issue-412-filters | #418 MERGED | none | remove |
| codex-review | #431 MERGED | `*.tsbuildinfo`, `public/_spa/**` | remove --force (junk only) |
| detached-9f2c01ab | detached, reachable | none | remove |
| modules-a1 | no PR, 0 ahead, no remote | none | remove (landed elsewhere) |
| rfp-draft | no PR, 3 ahead | none | keep |
| auth-rework | no PR, 0 ahead, idle 2h | 4 modified `.cs` | ask: active in another session? |
| *(branch)* fix/typo | [gone], #402 MERGED | — | delete branch |

## 4. Remove

Only what the user approved. Run from the current checkout. Never remove the MAIN or CURRENT row, and never `git checkout` anything in the main checkout.

1. Locked trees the user approved: `git worktree unlock <path>`.
2. `git worktree remove <path>` for each. Use `--force` only for trees the user approved as junk-only.
3. A folder that survives: if it's empty, `rmdir` it. If it isn't, STOP and report what's inside. Never `rm -r` anything.
4. `git worktree prune`.
5. `git branch -D <b1> <b2> …` for removed worktrees' branches plus approved no-worktree branches. A squash merge needs `-D`.
6. Offer to delete stray files in the worktree root (e.g. `*-chunks-*.txt`), one plain `rm <file>` per file.

**If the auto-mode classifier blocks a bulk remove, `--force` or `branch -D`**, don't retry it piecemeal or reword it. Print the exact single-line command in a ```bash block for the user to run, then verify once they say it's done.

## 5. Verify and end

Re-run `git worktree list` and `ls <worktree root>`, then check that every removed path and branch is gone. Grep the project's notes (CLAUDE.md, memory, docs) for removed worktree or branch names and update or drop stale references.

End with exactly one banner, pasted verbatim in a fenced block in the final reply. `Read` it from `${CLAUDE_PLUGIN_ROOT}/skills/merged/assets/clean-banner.txt` or `stop-banner.txt`.

- **CLEAN**: every approved removal is done and verified, no command is waiting on the user, and no question is open. Worktrees kept on purpose don't block CLEAN.
- **STOP**: anything else, e.g. a blocked command the user must run, a failed removal, a non-empty leftover folder, `main` checked out and behind. A numbered to-do list comes immediately after the banner, one line per item with the exact command. Put a short "what happened" underneath.

## Gotchas

- Never `git -C <path>`. `cd` in its own Bash call, because `cd <dir> && cmd` is hook-blocked. After a `cd`, check the result for a "cwd was reset" notice before running anything that writes.
- Git Bash mangles `origin/main:path` in `git show`. Prefix it with `MSYS_NO_PATHCONV=1`.
- `gh` MERGED beats ancestry. Squash merges are never ancestors of `main`.
- Cost: the survey is one call. Don't investigate *keep* rows unless the user asks.
