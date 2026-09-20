---
name: merged
description: Post-merge cleanup and session-close gate for a feature branch whose PR just merged. Use when the user says /merged, "the PR merged, clean it up", "merged cleanup", "clean up the worktree", or any time a PR has landed and its leftover git worktree + local branch need removing. Confirms the PR is actually MERGED, removes its worktree the right way (git worktree remove — never a recursive force-delete), deletes the squash-merged local branch, fast-forwards main, then ends with one of two unmistakable banners: CLEAN (everything cleaned and nothing else from the session is outstanding — safe to close) or STOP (a safety gate halted cleanup, or other session work is still pending — a numbered to-do list follows the banner immediately).
---

# Merged — Post-Merge Worktree Cleanup

When a PR merges, its worktree and local branch are dead weight. This skill removes them **safely**, leaves the local repo in sync, and gives a clear verdict on whether the session can be closed. The non-negotiable part is *how* the worktree is deleted: through git's own plumbing, never a recursive force-delete.

Every run ends with exactly one of two banners (see **Ending**): **CLEAN** means everything is tidy and nothing from this session needs you — close it. **STOP** means either cleanup hit a safety gate or something else from the session is still outstanding, and the banner is followed immediately by a numbered list of what you have to do. The banners exist so the verdict is impossible to miss when you scroll back; never end a `/merged` run without one.

## Why the safety rules matter

`rm -rf` on a worktree path destroys whatever is there with zero recovery — and if the path is wrong, or the worktree still holds uncommitted work, or git's admin metadata is out of sync, you've silently nuked real work. `git worktree remove` is the correct primitive: it refuses when the tree is dirty or locked, which is exactly the signal you want. The rule below is a *ladder* — each rung only taken when the previous one legitimately can't proceed, and the bottom rung (`rmdir`) still can't destroy anything because it only removes an already-empty directory.

These deletes are also hook-blocked in this environment, so "working around" them by reaching for `rm -rf` doesn't just violate intent — it fails. Do it right.

## Inputs

Optional argument: a PR number (e.g. `873`) or a branch name. If omitted, target the **current branch's** PR.

## Workflow

### 1. Resolve the target branch + PR

- Arg is all digits → PR number. Arg looks like a branch → that branch.
- No arg, on a feature branch → `gh pr view --json number,state,headRefName,mergeCommit,headRepository` for the current branch.
- No arg, sitting on `main`/`master` (you already switched back after merging) → find the merged worktree: for each entry in `git worktree list --porcelain`, check its branch's PR state with `gh pr view <branch> --json state,headRefName`. Targets are the ones reporting `MERGED`. If exactly one, take it. If several, list them and ask which (one terse inline question — don't guess).

### 2. Confirm it actually MERGED — never clean an unmerged branch

```
gh pr view <N> --repo <owner/repo> --json state,mergedAt,headRefName,mergeCommit
```

Require `state == "MERGED"`. If it's `OPEN` or closed-without-merge, **STOP and report** — removing that worktree/branch would throw away unpushed work. A squash-merge is still `MERGED` here; that's fine.

**`MERGED` is authoritative — do not second-guess it with git archaeology.** A squash merge rewrites SHAs, so branch commits are *never* ancestors of `main`: `merge-base --is-ancestor`, `branch --contains`, and "my SHA isn't in main" reasoning all report false negatives and prove nothing. Also `mergedAt` is UTC — don't infer push-vs-merge ordering from wall-clock dates. The **only** legitimate race worry is a commit pushed *after* `mergedAt`; if you genuinely suspect that, run exactly one targeted check — `git grep <sentinel-from-that-commit> origin/main -- <file>` — and if it's truly missing, **STOP and report**. Never build rescue branches or cherry-pick experiments inside `/merged`.

**Cost discipline:** this skill runs many times a day. A normal run is ≤6 tool calls — batch the git commands per step, skip investigation the checklist doesn't ask for.

### 3. Locate the leftovers

- Worktree path: `git worktree list --porcelain`, find the block whose `branch` is `refs/heads/<headRefName>`.
- Local branch: `git branch --list <headRefName>`.

(Either may already be gone — that's fine, just skip that step.)

### 4. Verify the worktree is clean *before* touching it

```
git -C "<worktree-path>" status --porcelain
```

Empty output = clean → proceed. **Any output = STOP and report the dirty files.** A "merged" worktree with uncommitted changes means something diverged from what landed; that's the user's call, not yours. Do not remove it, do not `--force` past it.

### 5. Remove the worktree — the right way

```
git worktree remove "<worktree-path>"
```

This is the sanctioned removal. **Never** `rm -rf`, **never** `git worktree remove --force` to paper over a dirty or locked tree.

- If it fails because the worktree is **locked**: `git worktree unlock "<worktree-path>"` then retry the plain `git worktree remove`. Unlocking a merged worktree you own is legitimate; forcing past *dirty state* is not.

### 6. If the folder survives, `rmdir` it — only when empty

Occasionally `git worktree remove` succeeds but leaves the directory behind (stray OS file handles, editor lock files, etc.). If the path still exists:

```
find "<worktree-path>" -mindepth 1 -print -quit    # empty output ⇒ directory is empty
```

- **Empty** → `rmdir "<worktree-path>"`. Plain `rmdir` removes an empty directory and *refuses* on a non-empty one — that refusal is the safety net, which is why we use it instead of `rm -r`.
- **Not empty** → **STOP and report** exactly what's inside. Don't `rm -rf`, don't `rmdir -p`, don't `rm -r`. Unexpected files surviving a clean worktree removal are a signal to look, not to bulldoze.

Then tidy git's bookkeeping:

```
git worktree prune
```

### 7. Delete the local branch

```
git branch -D <headRefName>
```

Use `-D` (capital): a squash-merged branch is **not** an ancestor of `main`, so `-d` would wrongly refuse it. We already confirmed the PR merged in step 2, so `-D` is safe — we're not bypassing a real "unmerged" warning.

### 8. Fast-forward main

```
git checkout main            # (or master) if not already there
git fetch origin --prune
git pull --ff-only origin main
```

`--ff-only` so that if local `main` has somehow diverged, the pull stops loudly instead of silently creating a merge commit.

### 9. Verify

```
git rev-list --left-right --count main...origin/main   # expect: 0   0
git worktree list                                      # target gone
git branch --list <headRefName>                        # empty
```

If any check fails, that's a STOP condition — carry it into the Ending below. Otherwise the worktree side is clean.

### 10. End with a verdict (always)

Go to **Ending** and print exactly one banner. Never finish a `/merged` run silently.

## Ending — CLEAN or STOP

Every run terminates in one of two banners. **The banner must appear in your final written reply — a fenced code block in the message the user reads — not only in tool output.** A `cat` to the terminal lands in a Bash tool result, which the user's view collapses, so they miss it. Instead: `Read` the asset file, then paste its contents **verbatim** into a fenced (```` ``` ````) code block in your reply (strip the line-number prefixes the Read tool adds; reproduce the ASCII art exactly). Pick based on the whole picture, not just the worktree:

**Print CLEAN** when *all* of these hold:
- The PR was MERGED and its worktree + local branch are gone (or were already gone).
- `main` is in sync with its remote (`0  0`).
- Nothing else from this session is left hanging — no uncommitted/unpushed work in another checkout, no failed build/test you were mid-fixing, no follow-up you promised but didn't finish, no question awaiting the user.

`Read "${CLAUDE_PLUGIN_ROOT}/skills/merged/assets/clean-banner.txt"` and paste its contents verbatim into a fenced code block in your reply.

CLEAN is a real all-clear: it tells the user they can close the session without reading further. Don't print it if you're not sure — uncertainty is itself a STOP.

**Print STOP** when *any* of these hold:
- A safety gate halted cleanup: PR not MERGED, worktree dirty, worktree locked and you couldn't cleanly unlock it, the leftover folder wasn't empty, `--ff-only` refused, etc.
- Cleanup succeeded, but something else from the session is still outstanding (see the CLEAN checklist — any "no" flips to STOP).

`Read "${CLAUDE_PLUGIN_ROOT}/skills/merged/assets/stop-banner.txt"` and paste its contents verbatim into a fenced code block in your reply.

### STOP layout — actions first, always

The **very next thing** after the banner is a numbered list of what the user has to do. Nothing may precede it: no recap, no "cleanup finished except…", no framing sentence, no "here's where things stand". They opened this to find out what needs doing; that answer goes on the first line.

One numbered item per action. Imperative mood, one line each, carrying the exact command, path, or PR number. When an item is a decision rather than a command, state the decision in one line. If an item can only be done later, say what triggers it. No sub-bullets, no rationale — a user who wants the why reads the summary underneath.

If the list would be empty, you had no reason to print STOP.

**Below** the list, add a compact "What happened" — a few lines, so they don't redo work already done and know what's blocked on what. Not a step-by-step replay: skip the steps that simply worked, skip why each safety gate exists, and never restate the numbered items in prose.

Example:

```
<stop banner>

1. Commit or discard src/Foo.cs in .worktrees/issue-826, then re-run /merged.
2. Assign issue #828 to a sprint.

PR #873 merged and its branch is deleted. Worktree removal is blocked by (1), which
also leaves main 2 behind origin/main.
```

## The non-negotiables (recap)

- **Never** `rm -rf` / `rm -r` / `rmdir -p` / `--force` to get past a dirty, locked, or non-empty state. The removal ladder is exactly: `git worktree remove` → (locked? unlock + retry) → (folder remains *and* empty? `rmdir`). Anything else → STOP banner + summary.
- **Never** clean a branch whose PR isn't confirmed `MERGED`.
- **Never** touch worktrees or branches other than the resolved target.
- Leave `main` in sync (`0  0`) or say why it isn't (STOP).
- **Always end with a banner in your written reply** — CLEAN or STOP, never silence, never buried in tool output. Source it from the asset file (`Read` + paste verbatim) so the art stays intact and the user actually sees it. CLEAN only when cleanup *and* the rest of the session are genuinely settled; when in doubt, STOP and explain.
- **On STOP, the numbered to-do list comes first** — immediately under the banner, before any recap. The summary goes underneath it, short.
