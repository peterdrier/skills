---
name: orch
description: Orchestrate substantial, separable work with lower-cost Codex workers when the user explicitly asks to orch, orchestrate, farm out, or use cheaper workers. Do not use as a general trigger for ordinary multi-step work.
---

# Orchestrate work

The primary agent remains responsible for the plan, architecture, integration, user communication, and final review. Delegate bounded implementation, investigation, searches, mechanical work, and independent checks when doing so saves meaningful time or context.

Read [routing.md](routing.md) before dispatching workers. It defines model and reasoning choices, brief shape, worker ownership, and return contracts.

## Workflow

1. Understand the request and repository instructions before splitting the work. Delegate broad source exploration or log reading to a scout when needed to plan; keep primary-thread reads focused on decisions and final review. Preserve the user's scope and authority.
2. Divide the work into a few substantial, independently useful tasks. Keep tiny tasks local when writing and reviewing a brief would cost more than doing the work.
3. Give concurrent writers disjoint file ownership. Sequence work that touches the same files or depends on earlier results. Follow repository-specific worktree, branch, build, test, and concurrency rules.
4. Dispatch with the available native delegation tools. Select both model and reasoning effort explicitly when the tool supports them. Use fresh or narrowly forked context when selecting a worker model; a full-history fork may prevent model overrides in some harnesses.
5. Keep a small task ledger in the project's permitted scratch location for long-running or multi-wave jobs; use a task-specific temporary directory when none exists. Record task, worker, status, ownership, and result or artifact path; update it on dispatch and return, and reread it after resuming or compaction. A short single-wave delegation does not need a ledger.
6. Integrate the results yourself. Inspect the actual changes and resolve cross-task decisions. Run or commission meaningful independent checks when the risk or complexity justifies them; do not add ceremonial duplicate checks.
7. Review the final diff and report the integrated outcome to the user.

Put bulky findings, logs, and generated material in the same scratch location. Ask workers to return concise status, changed paths, verification results, decisions needed, and artifact paths rather than pasting large outputs into the conversation.

Follow the user's request and repository rules for configuration changes, publishing, and PR handoffs. Delegation itself does not expand authorization.

If delegation tools are unavailable, state that limitation briefly and continue locally. If a preferred model is unavailable, choose the closest available model, disclose the substitution, and avoid claims about exact prices or guaranteed savings.
