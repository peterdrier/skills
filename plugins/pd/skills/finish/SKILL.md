---
name: finish
description: 'End-of-session check: is it safe to close this session? Silent unless something blocks closing.'
when_to_use: Use on "finish", "wrap up", "done for now", or any variation of ending a work session. Not a summary (that is /summary) and not a life or day review.
---

# Finish: Safe to Close?

The user is about to close this session. The only question is: **is there any reason they shouldn't?**

## Output Contract

- Nothing blocks closing: the entire reply is `done.` Nothing before it, nothing after it.
- Something blocks closing: list only the blockers, one line each, with what's needed to clear it. Nothing else.

Never include, in either case:

- A summary of the session, of what was accomplished, or of what was shipped
- PRs opened, merged, closed, or reverted
- Good news, wins, "you're clean", "all pushed", or any confirmation of things being fine
- Reports of what you checked or that checks passed
- Anything another session did

If the user then asks for a summary or more detail, give it. Not before.

## What Counts as a Blocker

Only things from **this session** that would be lost or left hanging if the session closed now:

- Uncommitted or untracked changes this session made
- Commits this session made that aren't pushed
- A branch this session pushed that needs a PR and doesn't have one
- Background agents, tasks, or watches this session started that are still running
- Something this session promised to do and hasn't, or a question still waiting on the user
- A step only the user can do (a merge, an approval, a credential) that the work depends on

Other sessions' branches, worktrees, PRs, and commits are not blockers and are never mentioned. `git status` and `git log` will show them; read past them.

## Checks (silent)

For each repo this session touched (the working directory always counts), run `git status`, `git diff --stat`, and `git log --oneline -5` as separate Bash calls. Check for this session's running background work. Don't auto-fix anything.

If the user made corrections or decisions during the session that aren't recorded yet, write them to `memory/capture.md` (category: CORRECTION, PROCESS, PREFERENCE, WORKFLOW, or INSIGHT) without mentioning it. If the file or location doesn't exist in this setup, skip it.

Then emit the output above.
