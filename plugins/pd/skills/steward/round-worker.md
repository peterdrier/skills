# Round worker brief

The steward dispatches one of these per actionable wake, as `orch-opus-medium`. Fill the
angle brackets; paste nothing else. The worker starts with zero context and reads what it
needs from the repo and the PR.

```
Review round on <owner>/<repo>#<N>, branch <branch>. Rounds spent before this one: <k>.
Trigger: <one line: "<bot> review on <sha>, comment ids …" | "CI check <name> failed on <sha>" | "merge conflict with <base>" | "user: <their words>">.

Load the pd:steward skill (sections "Project overlay", "Rounds and the ceiling" and
"The round itself"), its round-worker.md, and the project's .claude/steward.md if it
exists, then do the whole round yourself.
Report file: <scratchpad>/steward/<N>-round-<k+1>.md.
```

**A question from the user is not a round.** The steward sends the same brief with
`Trigger: user asks: <their words>` and the line `Answer only: no triage, no edit, no
commit.` That worker reads whatever it needs and answers: a question gets an answer, not
a commit. Where the question came in as a PR comment, the answer is a reply on that comment
and the report is one line. Where the user asked the steward directly there is no thread
to reply in, so the answer goes back **verbatim in the report**, under an
`ANSWER (relay verbatim):` line, and the steward relays it into its reply; the steward
cannot read files, so that block is the only copy that reaches them. None of the steps
below apply to either.

## What the worker does

1. **Workspace.** In a cloud container the repo root is fine. Locally, `git worktree list`
   first: the branch is usually already checked out in the builder's worktree, and
   `git worktree add` on a branch checked out elsewhere fails outright. Reuse that
   worktree, and only add one (where the overlay says, else `.claude/worktrees/steward-<N>`)
   when no worktree holds the branch. Fetch fresh, work only there.
2. **Count, then branch on the trigger.** Recount spent rounds from the PR (command in
   SKILL.md). Where the count and the brief disagree, the PR wins; say so in the report.
   A merge conflict or something the user asked for is not a round **at any count**: do
   that work (steps 3 and 6, no trailer) and **skip step 5 entirely** (folding a bot
   finding into an untrailered commit spends a round the count never sees), then report
   the ceiling as still standing. Only a round trigger, an automated review finding or a
   CI failure, meets the ceiling: at 5 or more spent, skip to step 7, which fetches the
   open threads itself (the trigger line is not the list of open items).
3. **Merge conflict first.** Merge the base into the branch with a merge commit, resolve,
   regenerate generated files and lockfiles with the project's tooling, never rewrite
   history. Not a round.
4. **CI failure.** Read the failed job's log tail once. Rule out a failure that isn't this
   PR's: a test the diff doesn't touch that hit a timeout under runner load, or a check red
   on the base too. That gets one re-run (or the next push serves as one) and no commit. A
   real failure in code the PR touches is a round: fix it, except at 4 spent, where the
   last commit belongs to the most serious open item: gather the unresolved threads
   (step 5) first, then choose between them and the failure.
5. **Findings**, round triggers only; a non-round wake skips this step (step 2).
   Triage every unresolved thread (on a fork PR, both repos) per SKILL.md "The round
   itself" and the overlay's triage skill or rules, and print the triage table into the
   report file. Fix only what survives and sits inside the ceiling table's bar for this
   round. `gh` where present; otherwise the github MCP tools
   (`pull_request_read get_review_comments`, `add_reply_to_pull_request_comment`,
   `resolve_review_thread`).
6. **One commit, then the gate.** All of this wake's fixes in one commit, carrying the
   session's attribution trailers. The `Review-round: <k+1>` trailer goes on a commit
   answering an automated review finding or a CI failure, and only there: a commit doing
   what the user asked, or a mechanical one (base merge, conflict resolution), carries no
   trailer and spends no round (SKILL.md, "Rounds and the ceiling"). Then run the
   overlay's verification gate and read its result, never trusting a test run against a
   stale build. No gate named anywhere: don't push; report `STATUS: blocked` with the
   commit local. Push the way the overlay says. Then reply in every thread with its
   disposition and the sha, react, resolve; leave open only a thread genuinely waiting on
   the user.
7. **Ceiling.** At 5 spent, or when the table says stop: first fetch the unresolved
   threads (on a fork PR, both repos), read-only, no triage, no patch, no commit, so the
   handoff lists the findings that are actually open. Then write the ceiling comment
   (what is open, what you'd do about each, what needs deciding, ending with the
   attribution footer your harness requires on GitHub posts) into the report file **and
   verbatim into your reply**, below the return block. The steward cannot read files, so
   the reply is the only copy it can post.

## What the worker never does

- Steward: it does not subscribe, read notifications, or wait for anything.
- Push more than one commit for the wake; leave the trailer off a review round, or put one
  on a commit that is not a round.
- Skip, disable or quarantine a test; use `--no-verify`; hand-edit state.
- Merge, or ask the user whether to fix a finding: the triage decides.
- Put logs, diffs or file contents in the reply. The ceiling comment of step 7 is the one
  thing that belongs there in full.

## Return contract

Reply in at most 12 lines, plus the ceiling comment verbatim when `STATUS: ceiling`:

```
STATUS: done | ceiling | blocked
HEAD: <sha pushed, or "no push">
ROUNDS SPENT: <n after this round>
TRIGGER HANDLED: <one line>
FINDINGS: fixed <a> · declined <b> · deferred/filed <c> · left open for the user <d>
CI: <green on <sha> | red: <check>, <why it is not this PR's> | not yet run>
OPEN: <anything the steward must relay to the user, one line each, or "none">
REPORT: <path>
```

`STATUS: ceiling` adds the ceiling comment below that block, under a
`CEILING COMMENT (post verbatim):` line; the steward posts it as-is.
