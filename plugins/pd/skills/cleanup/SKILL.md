---
name: cleanup
description: Sweep every git worktree and stale local branch in a repo, or every repo under a folder, and safely remove the dead ones.
when_to_use: Use on /cleanup, "clean up worktrees", "prune worktrees", "delete merged branches", or when the disk is full. For the one PR that just merged, use pd:merged instead.
---

# Cleanup — Sweep Every Dead Worktree

`pd:merged` cleans the one PR that just landed. This skill clears the backlog: every worktree and local branch, in one repo or every repo under a drive, classified into *safe*, *ask* and *keep*. The safe ones go first, as one batch, and the reply says how much disk came back. Only then do the doubtful ones get discussed. It reuses `pd:merged`'s removal ladder and banners, so read the non-negotiables there if anything here is unclear.

Removal is the dangerous part and the rules exist because the survey can be wrong: a worktree that looks dead may belong to another live session, or hold uncommitted tests. So the *safe* set is only what the classification rules mark **remove** outright, and anything uncertain is a question, not a guess.

## Emergency mode (drive full)

Engage when the user says the drive is full, out of disk space, or "emergency", or when the survey's first line shows under 2 GB free. Say "emergency mode" in the reply so the user knows why nothing was asked.

The only difference from a normal run: step 3 skips the confirmation. The safe set is removed the moment it's classified, the reclaimed amount is reported, and then the normal flow continues for the *ask* rows. Emergency mode is a shortcut past the question, not past the rules: a row that would have been a question outside emergency mode is still a question, `--force` still needs an OK, `rm -r` is still never used.

## 1. Survey (one call)

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/survey.sh" [path]
```

Default path is the current directory. Inside a repo it surveys that repo. Anywhere else (a drive root like `H:/`, a folder of projects) it finds every repo underneath and surveys each, one `=== repo:` block per repo. Sizes come from `du`, so a drive with many worktrees takes a few minutes.

It runs `git fetch --prune` per repo and changes nothing else. It prints free space on the drive, then per repo: one row per worktree (branch, size in GB, dirty count, commits ahead of `origin/main`, remote branch, PR state, idle time), the local branches that have no worktree (with `[gone]` when origin deleted them), and the dirty files of each dirty worktree. Columns are defined in [references/classification.md](references/classification.md).

If a repo's local `main` is behind and `main` isn't checked out anywhere, fast-forward it with `git fetch origin main:main`. This refuses anything but a fast-forward. If `main` is checked out in the main checkout, leave it: it becomes a to-do item.

## 2. Classify

Apply the rules in [references/classification.md](references/classification.md) to every row, first match wins. In short: merged + clean goes; open PR or unique commits stays; recent with no PR, or real uncommitted files, is a question. A merged PR is authoritative. Never second-guess a squash merge with ancestry checks.

Three buckets come out:

- **safe**: worktree rules 2, 4, 7, 11 and branch rules that say *delete*
- **ask**: every rule that says *ask*, plus junk-only dirty trees (rule 6/8, they need an OK for `--force`)
- **keep**: open PRs, unique commits, orphans, MAIN/CURRENT

When the user asks "what is X?", answer from `git log --oneline <base>..<branch>`, the ahead count and the PR title before recommending anything.

## 3. Report the counts, then remove the safe set

The reply opens with three lines. No table yet, no file lists.

```
Safe to remove: 15 worktrees, 18.2 GB — issue-412 #418, codex-review #431, … (and 4 merged branches)
Needs a look: 3 worktrees, 2.1 GB
Keep: 4 (open PR or unique commits)
```

Then, normal mode: one line, "Removing the 15 now unless you say stop." and wait for the reply. Emergency mode: no wait. Either way the removal is one call per `--force` setting, every path in the call:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/remove.sh" <path> <path> …
```

It cds to each worktree's own repo, runs `git worktree remove`, `rmdir`s an empty leftover folder (a non-empty one is reported as LEFTOVER, never `rm -r`), deletes the worktree's branch with `-D` (a squash merge needs it), prunes, and prints `reclaimed: N GB`. `--force` as the first argument applies to every path in that call, so junk-only trees the user approved go in a call of their own. It refuses a main checkout.

Branches without a worktree: `cd <repo>` in its own Bash call, then one `git branch -D <b1> <b2> …`.

Put the reclaimed amount on its own line in the reply, with the free space now.

**If the auto-mode classifier blocks `remove.sh`, `--force` or `branch -D`**, don't retry it piecemeal or reword it. Print the exact single-line command in a ```bash block for the user to run, then verify once they say it's done.

## 4. Then the ask rows

Only now, one table of the *ask* rows, biggest first, leftovers summarised by pattern (`public/_spa/** build output`), never as a file dump. Then one question covering every row, so the user can answer in bulk ("codex review can go, rfp stays, X is active elsewhere").

| worktree | size | state | leftovers | proposed |
|---|---|---|---|---|
| codex-review | 3.1 GB | #431 MERGED | `*.tsbuildinfo`, `public/_spa/**` | remove --force (junk only) |
| auth-rework | 0.4 GB | no PR, 0 ahead, idle 2h | 4 modified `.cs` | active in another session? |
| old-spike | 0.2 GB | #402 CLOSED, 3 commits | none | abandoned? 3 commits would be lost |

Approved rows go through `remove.sh` as in step 3. Never remove the MAIN or CURRENT row, and never `git checkout` anything in the main checkout. Offer to delete stray files in a worktree root (e.g. `*-chunks-*.txt`), one plain `rm <file>` per file.

## 5. Verify and end

Re-run `git worktree list` per touched repo and `ls <worktree root>`, then check that every removed path and branch is gone. Grep the project's notes (CLAUDE.md, memory, docs) for removed worktree or branch names and update or drop stale references.

End with exactly one banner, pasted verbatim in a fenced block in the final reply. `Read` it from `${CLAUDE_PLUGIN_ROOT}/skills/merged/assets/clean-banner.txt` or `stop-banner.txt`.

- **CLEAN**: every approved removal is done and verified, no command is waiting on the user, and no question is open. Worktrees kept on purpose don't block CLEAN.
- **STOP**: anything else, e.g. a blocked command the user must run, a failed removal, a LEFTOVER folder, `main` checked out and behind. A numbered to-do list comes immediately after the banner, one line per item with the exact command. Put a short "what happened" underneath.

## Gotchas

- Never `git -C <path>`. `cd` in its own Bash call, because `cd <dir> && cmd` is hook-blocked. After a `cd`, check the result for a "cwd was reset" notice before running anything that writes. The scripts take paths as arguments precisely so a drive-wide run needs no `cd` at all.
- Git Bash mangles `origin/main:path` in `git show`. Prefix it with `MSYS_NO_PATHCONV=1`.
- `gh` MERGED beats ancestry. Squash merges are never ancestors of `main`.
- Cost: the survey is one call, the safe removal is one call. Don't investigate *keep* rows unless the user asks.
