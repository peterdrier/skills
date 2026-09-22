---
name: create-issue
description: Draft and submit a well-structured GitHub issue. Use when the user says "create an issue", "file an issue", "open an issue", "/create-issue", or describes a bug or feature that should be tracked on GitHub.
argument-hint: "[owner/repo] description of the issue"
disable-model-invocation: false
allowed-tools: Bash(gh repo view *), Bash(gh api *), Bash(gh issue list *), Bash(gh issue create *), Bash(gh label list *), Bash(rm /tmp/*), Read, Write, Edit(**/todos.md), WebFetch, Glob, Grep
---

# Create a GitHub Issue

Create a high-quality GitHub issue for the repository specified in `$ARGUMENTS`. If no repo is explicitly named, use the current working directory's git remote.

## Step 0: Determine the target repo

- If `$ARGUMENTS` starts with an org/repo pattern (e.g. `anthropics/claude-code`), use that and treat the rest as the description.
- Otherwise: `gh repo view --json nameWithOwner -q .nameWithOwner`.

## Step 1: Gather context

**Project conventions.** If `.claude/create-issue.md` exists in the project root, read it and follow it. It is the project's overlay for this skill: which repo(s) issues live on, required labels and their values (size, tier, section, …), extra body sections, and any submit-time rules. Where it conflicts with this file, the project file wins.

For non-trivial issues (architectural, multi-system, unclear conventions), fetch CLAUDE.md:

```
gh api repos/{owner}/{repo}/contents/CLAUDE.md --jq .content | base64 -d
```

Check for duplicates:

```
gh issue list -R {owner}/{repo} --search "{relevant keywords}" --limit 5
```

## Step 2: Draft the issue

**Title:** verb-first ("Add...", "Fix...", "Update..."), under 70 chars, specific.

**Body template:**

```markdown
## Context
Why this matters. Current situation.

## Problem / Motivation
What's broken, missing, or suboptimal. Include file paths, error messages, screenshots when relevant.

## Proposed Solution
Brief sketch. Bullet points fine. Mention alternatives if relevant.

## Acceptance Criteria
- [ ] Concrete, testable conditions for "done"
- [ ] Each criterion independently verifiable
```

**Labels:** Always apply a type label (bug, enhancement, documentation, etc.). Use `gh label list` to see what the repo actually has; never invent a label. Apply any labels the project overlay requires.

**Status labels** when the issue isn't ready to pick up, if the repo has them:
- `blocked:spec-incomplete` — placeholder body or missing acceptance criteria
- `blocked:needs-design` — solution is open-ended; design work needed before implementation

Add a **Key files** line in the body listing likely files to change.

Omit labels you're unsure about — a missing label is better than a wrong one.

## Step 3: Checkpoint

Present the exact title, body, and labels inline as plain text and wait for the user's reply (submit / revise / cancel). Do NOT use AskUserQuestion for this — it is a plain confirmation. Do NOT submit without explicit approval.

## Step 4: Submit

**Always use `--body-file`, never `--body` with an inline string or a heredoc.** Markdown issue bodies routinely contain apostrophes, code fences, backticks, and dollar signs that break shell quoting in maddeningly opaque ways — heredoc EOFs get swallowed, single-quotes inside `'...'` blow up the shell, and you end up retrying the submission three times. The reliable pattern, every time:

1. Use the `Write` tool to write the body to a temp file (e.g. `/tmp/issue-body.md`). The Write tool takes the body as a literal string with no shell-quoting at all, so any character is safe.
2. `gh issue create -R {owner}/{repo} --title "..." --body-file /tmp/issue-body.md [--label "..."]`
3. `rm /tmp/issue-body.md` to clean up.

Return the issue URL.

## Step 5: Update todos.md

If the issue is for the current project, check for `todos.md` in `~/.claude/projects/<project-slug>/todos.md` or the project root. If found: add the issue under the matching priority section as `#### #<number>: <title>` with a brief description. If it supersedes an existing item, update that item instead.
