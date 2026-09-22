# peterdrier/skills

A plugin marketplace for Claude Code and Codex.

## Codex

`pd-codex` provides `orch`: keep planning, architecture, integration, and final
review with the main agent, while focused subagents handle implementation and
investigation.

Install with a current Codex CLI:

```sh
codex plugin marketplace add peterdrier/skills
codex plugin add pd-codex@peterdrier
```

On Windows PowerShell, use `codex.cmd` if execution policy blocks the npm
PowerShell launcher. Start a new Codex chat after installation. Select `orch`
from the skills picker, or ask:

```text
Use the orch skill from pd-codex to implement this feature. Keep architecture
and final review in the main thread; delegate bounded work to cheaper workers.
```

Use a capable main model, such as GPT-6 Astra. The bundled routing preferences
are GPT-6 Sol at medium reasoning for implementation, GPT-6 Luna at low reasoning
for mechanical work, and GPT-6 Astra for difficult judgment. GPT-5.6 Luna,
Terra, and Sol are fallback options when a preferred worker is unavailable. The
skill explicitly selects worker models; it does not require changes to your
global Codex configuration.
You can override those preferences in your request. Available models and native
subagent support depend on your Codex client and account; substitutions are
reported. Without delegation tools, the skill reports that limitation and works
locally.

`pd-codex` also provides `spend` for a rough per-agent cost report from local
Codex session records. Ask for the session's spend or select the skill directly.
It shows each agent's model and reasoning level, turns, and estimated Standard
API list-price equivalent; it does not report a Codex subscription charge.

The `orch` skill follows the target project's rules for worktrees, validation, and
publishing. It has no project-specific paths, other skill dependencies, hooks,
MCP servers, or credentials. Delegation adds overhead: batching work and limiting
expensive-model context can reduce cost, but savings are not guaranteed.

The Codex catalog is `.agents/plugins/marketplace.json`. The plugin includes a
portable root `plugin.json` plus `.codex-plugin/plugin.json` for Codex
compatibility and presentation. See the [plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).

## Claude Code

`pd` contains:

- `/pd:orch` — orchestrate multi-part work by delegating to cheaper subagents with an
  explicit model/effort tier per task; ships the `orch-*` worker agents (haiku, sonnet and
  opus at low/medium/high, fable-high) and the routing rule other skills point to
- `/pd:steward` — tending a PR after ready-for-review: the builder hands it to a thin
  steward session that classifies each event and dispatches one round worker, under a
  five-round review ceiling; a project adds its verification gate and triage rules in
  `.claude/steward.md`. Needs the Claude Code Remote tools
- `/pd:spend` — after-the-fact cost report for a session: tokens and dollars per agent
- `/pd:ask` — roll up everything a session is waiting on the user to answer, readable cold
- `/pd:create-issue` — draft and submit a GitHub issue; a project can add its own label
  and body conventions in `.claude/create-issue.md`
- `/pd:context-cleanup` — audit and restructure a project's CLAUDE.md, `.claude/`, memory
  and skills for efficient context use
- `/pd:finish` — end-of-session cleanup (git hygiene, context capture, loose ends)
- `/pd:merged` — post-merge git worktree cleanup with a CLEAN/STOP verdict banner
- `/pd:cls` — context-preserving clear: generates a continuation prompt before `/clear`

### Install

```
/plugin marketplace add peterdrier/skills
/plugin install pd@peterdrier
```

### Cloud sessions

Cloud sessions (claude.ai/code) ignore a repository's `enabledPlugins` and
`extraKnownMarketplaces`. Enable `pd` on your claude.ai account instead, and cloud
sessions load it as a synced plugin. A project may still list the marketplace in its
`.claude/settings.json` so local sessions on a fresh machine pick it up:

```json
{
  "extraKnownMarketplaces": {
    "peterdrier": { "source": { "source": "github", "repo": "peterdrier/skills" } }
  },
  "enabledPlugins": { "pd@peterdrier": true }
}
```

## License

MIT — see [LICENSE](LICENSE).
