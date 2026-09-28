# Classification rules

## Survey columns

| column | meaning |
|---|---|
| `ref` | branch name, or `detached:<sha>` |
| `dirty` | lines of `git status --porcelain` (an untracked dir counts once) |
| `ahead` | commits on the tip that aren't on `origin/main` (or `origin/HEAD`) |
| `remote` | branch: `yes`/`no` = `origin/<branch>` exists after prune. Detached: `reachable` = some ref contains the commit (`git for-each-ref --contains`), `orphan` = none does |
| `pr` | every PR ever opened from that head branch, e.g. `#12 MERGED,#9 CLOSED`, or `none` |
| `pr_head` | `same` = local tip equals a merged PR's head, `DIFF` = the local tip moved after the merge, `-` = no merged PR |
| `idle` | time since the newest of: HEAD move, HEAD commit, dirty-file edit |
| `flags` | `MAIN` (first entry, the main checkout), `CURRENT` (this session), `locked`, `prunable`/`missing` |

Branches without a worktree have `track` instead: `[gone]` means origin deleted the branch, `[ahead N]` means unpushed commits, `[in sync]` means it matches origin, `[no upstream]` means it was never pushed.

## Worktree rules (first match wins)

| # | condition | action | why |
|---|---|---|---|
| 1 | `MAIN` or `CURRENT` | never touch | the main checkout may be on a feature branch with build output. The current one is where you're running |
| 2 | `missing`/`prunable` | `git worktree prune` | the folder is already gone, only metadata remains |
| 3 | any `OPEN` PR | keep | live work |
| 4 | MERGED, `pr_head` = `same`, clean | remove | landed. MERGED is authoritative |
| 5 | MERGED, `pr_head` = `DIFF` | ask. Show `git log --oneline <pr headRefOid>..<branch>` | commits made after the merge would be lost |
| 6 | MERGED, dirty | junk check (below). Junk only: remove `--force` after OK. Otherwise ask | uncommitted work isn't in the PR |
| 7 | detached, `reachable`, clean | remove | the commit survives in another ref |
| 8 | detached, `reachable`, dirty | junk check, as in 6 | |
| 9 | detached, `orphan` | keep and mention it | removing it strands the commits (reflog only) |
| 10 | no PR, `idle` < 48h | ask: "active in another session?" | a fresh worktree has 0 commits and looks dead. Never assume |
| 11 | no PR, 0 ahead, `remote` = no, clean | remove | the work landed under another PR, or never started |
| 12 | no PR, `ahead` > 0 | keep | unique, unreviewed commits |
| 13 | only CLOSED (unmerged) PRs | ask, and say how many commits would be lost | abandoned, but unique |
| 14 | review/scratch tree with real uncommitted files (tests, evidence folders) | ask | may be the only copy |
| — | anything else | ask | a wrong guess destroys work, so default to asking |

## Branches without a worktree

| condition | action |
|---|---|
| any MERGED PR and tip = its head (`same`) | delete (`-D`) |
| `[gone]`, 0 ahead | delete (nothing unique) |
| `[gone]`, ahead > 0, no merged PR | ask. Origin deleted it but local commits are unique |
| OPEN PR, `[ahead N]`, or `[no upstream]` with commits ahead | keep |

## Junk detection (dirty trees)

Summarise by pattern and count, never as a list. A tree is **junk-only** when every dirty entry matches one of:

- build output: `public/_spa/**`, `dist/`, `build/`, `*.tsbuildinfo`, `bin/`/`obj/` if not ignored
- a stray npm install: untracked root `package-lock.json` (when the repo doesn't track one) or `node_modules/.package-lock.json`
- line-ending-only changes: the survey prints `(tracked changes are line-endings only)`. By hand: `git diff` shows nothing but a CRLF warning

Anything else (source files, tests, `evidence/`, notes) is real work → ask. Junk-only trees are removed with `git worktree remove --force`, but only after the user OKs the junk summary. `--force` is the one exception to the no-force rule, and it needs that approval.
