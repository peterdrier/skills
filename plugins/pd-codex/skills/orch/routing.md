# Worker routing

Choose a model for the judgment the task requires and a reasoning effort for its ambiguity. Account-level model availability and user preferences take precedence over these defaults.

| Model | Default effort | Route here |
| --- | --- | --- |
| `gpt-6-luna` | low | Straightforward searches, inventories, log summaries, mechanical edits with exact instructions, and command-based checks |
| `gpt-6-sol` | medium | Bounded implementation, investigation, debugging, tests, documentation, and most repository work |
| `gpt-6-astra` | high | Difficult architecture, subtle root-cause analysis, security-sensitive judgment, integration decisions, and adversarial review |

When a preferred GPT-6 worker is unavailable, choose by task and available models: `gpt-5.6-luna` at low effort for mechanical work, `gpt-5.6-terra` at medium effort for routine bounded work, or `gpt-5.6-sol` at medium effort when that work needs stronger coding judgment. For difficult work, keep the primary Astra agent responsible for the decision; use an available strong worker only if a separate investigation is useful. These are fallback routes, not claims that models in different families perform identically.

Use low effort when the brief fully specifies the action, medium when the worker must determine a bounded approach, and high or above only when ambiguity or the cost of a missed issue warrants it. The primary strong model retains planning, architecture, integration, and final review even when an Astra worker advises on a difficult question.

Always request both model and reasoning effort when the delegation interface supports them. Prefer a fresh worker or a limited context fork. In harnesses where full-history forks inherit the parent model and cannot override it, do not use a full-history fork when routing to a different model. Do not hardcode one product's tool names or call signatures; use the native delegation and messaging facilities exposed in the current environment.

Prefer a few substantial workers over many narrow ones. Reuse a worker when the follow-up materially depends on its context; otherwise use a fresh, tightly briefed worker. Do tiny work locally.

If a worker cannot solve its task, use its evidence to refine the brief or escalate effort, then model, as warranted. Avoid repeated identical attempts; surface unresolved decisions when another attempt is unlikely to help.

## Brief

Include:

- the concrete goal and why it matters;
- relevant paths or components, without pasting large source files;
- applicable repository and user constraints;
- explicit file ownership for writers;
- the expected validation;
- a path for bulky findings or logs when needed.

Give each worker its absolute working directory and require it to read the applicable repository instructions; do not assume a fresh worker received them. Require it to follow local worktree, branching, build, test, and concurrency rules. Concurrent writers must own disjoint files. When overlap is unavoidable, run them sequentially or keep one worker read-only.

Ask for a compact response such as:

> Reply in at most 10 lines: STATUS (done, blocked, or failed); CHANGED (paths, branch, or commit); VERIFIED (command and measured result); DECISIONS NEEDED; ARTIFACTS. Do not paste file contents, logs, or diffs when an artifact path is available.

## Verification and integration

The primary agent inspects the actual diff before integration and owns the final judgment. Use an independent worker for checks when independence can expose meaningful mistakes, such as behavior spanning several components, a risky migration, a subtle regression, or a large mechanical edit. A worker's own targeted tests are usually sufficient for routine bounded changes unless repository rules say otherwise.

If a preferred model is unavailable, select the nearest capable available model and tell the user which substitution occurred. Never invent model pricing, claim a guaranteed saving, or weaken correctness merely to use a cheaper worker. If no delegation facility exists, report that limitation and perform the work locally.
