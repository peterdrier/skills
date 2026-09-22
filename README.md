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
are Sol at medium reasoning for implementation, Luna at low reasoning for
mechanical work, and Astra for difficult judgment. The skill explicitly selects
worker models; it does not require changes to your global Codex configuration.
You can override those preferences in your request. Available models and native
subagent support depend on your Codex client and account; substitutions are
reported. Without delegation tools, the skill reports that limitation and works
locally.

The skill follows the target project's rules for worktrees, validation, and
publishing. It has no project-specific paths, other skill dependencies, hooks,
MCP servers, or credentials. Delegation adds overhead: batching work and limiting
expensive-model context can reduce cost, but savings are not guaranteed.

The Codex catalog is `.agents/plugins/marketplace.json`. The plugin includes a
portable root `plugin.json` plus `.codex-plugin/plugin.json` for Codex
compatibility and presentation. See the [plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).

## Claude Code

`pd` contains three session-hygiene skills:

- `/pd:finish` — end-of-session cleanup (git hygiene, context capture, loose ends)
- `/pd:merged` — post-merge git worktree cleanup with a CLEAN/STOP verdict banner
- `/pd:cls` — context-preserving clear: generates a continuation prompt before `/clear`

### Install

```
/plugin marketplace add peterdrier/skills
/plugin install pd@peterdrier
```

### Cloud sessions

Add to project `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "peterdrier",
      "url": "https://raw.githubusercontent.com/peterdrier/skills/main/.claude-plugin/marketplace.json"
    }
  ],
  "enabledPlugins": {
    "pd@peterdrier": true
  }
}
```

## License

MIT — see [LICENSE](LICENSE).
