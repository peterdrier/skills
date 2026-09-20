# peterdrier/skills

A Claude Code plugin marketplace with one plugin, `pd`, containing three session-hygiene skills:

- `/pd:finish` — end-of-session cleanup (git hygiene, context capture, loose ends)
- `/pd:merged` — post-merge git worktree cleanup with a CLEAN/STOP verdict banner
- `/pd:cls` — context-preserving clear: generates a continuation prompt before `/clear`

## Install

```
/plugin marketplace add peterdrier/skills
/plugin install pd@peterdrier
```

## Cloud sessions

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
