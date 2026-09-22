# Context Tier Framework

## Tier 1: Always Loaded (CLAUDE.md)

Content that MUST be in CLAUDE.md because it's needed on virtually every interaction or prevents serious mistakes.

### What belongs here

- **Project identity**: What the project is, tech stack, one-liner description
- **Build/break rules**: Things that cause compilation errors, broken serialization, or data loss if ignored
  - Example: "Never rename fields on IData-derived objects (breaks JSON deserialization)"
  - Example: "Zero warnings policy -- verify no new warnings before committing"
- **Safety guards**: Rules that prevent destructive or irreversible actions
  - Example: "Never git push without explicit permission"
  - Example: "Never delete production data without confirmation"
- **High-frequency conventions**: Patterns needed on nearly every code change
  - Example: "Always use explicit StringComparison parameter"
  - Example: "Inherit from AuthorizedComponentBase for authenticated pages"
- **Pointers to Tier 2**: Brief table or list linking to .claude/ subfiles with a one-line description of each

### What does NOT belong here

- Detailed explanations of why a rule exists
- Full API documentation or schemas
- Step-by-step workflows for specific tasks
- Examples longer than 2-3 lines
- Historical context or changelog-style notes

### Format guidance

- Use tables and bullet points, not paragraphs
- One rule per line where possible
- If a rule needs more than 2 lines of explanation, move the explanation to a Tier 2 file and keep just the rule + pointer in CLAUDE.md

## Tier 2: On-Demand (.claude/ subfiles)

Content loaded only when relevant to the current task. Referenced from CLAUDE.md with a brief description.

### What belongs here

- **Detailed coding rules**: Full explanation of conventions with examples
- **Architecture docs**: Data model diagrams, component hierarchies, system design
- **Workflow guides**: Step-by-step processes for specific task types (CSS patterns, update procedures, etc.)
- **Domain knowledge**: Business logic, data relationships, edge cases
- **Tool-specific docs**: Syncfusion patterns, analyzer configuration, etc.

### Organization principles

- **One topic per file**: `CODING_RULES.md`, `CSS_ARCHITECTURE.md`, `DATA_MODEL.md`
- **Descriptive filenames**: The filename should tell Claude whether to read the file
- **TOC for long files**: If over 100 lines, add a table of contents at the top
- **Cross-reference sparingly**: Subfiles can reference each other but avoid deep chains

### Naming convention

```
.claude/
  CODING_RULES.md      -- Code conventions and gotchas
  CSS_ARCHITECTURE.md  -- Styling patterns and design tokens
  DATA_MODEL.md        -- Entity relationships and serialization
  WORKFLOWS.md         -- Common multi-step procedures
```

## Tier 3: External (pointed to, not stored)

Content too large, too volatile, or too rarely needed to store in .claude/ files.

### What belongs here

- Full API documentation (link to docs site or wiki)
- Large database schemas (reference by file path in repo)
- Third-party library docs (link to official docs)
- Detailed specs that change frequently

### How to reference

In CLAUDE.md or Tier 2 files, add a pointer:
```markdown
For the full database schema, see `src/Data/` source files.
For Syncfusion component docs, see https://blazor.syncfusion.com/documentation/
```

## Decision Flowchart

For any piece of information, ask:

1. **Would ignoring this break the build or cause data loss?** --> Tier 1
2. **Is this needed to prevent destructive/irreversible actions?** --> Tier 1
3. **Is this needed on >80% of tasks?** --> Tier 1 (concise) + Tier 2 (detailed)
4. **Is this needed on 20-80% of tasks?** --> Tier 2
5. **Is this needed on <20% of tasks?** --> Tier 2 if small, Tier 3 if large
6. **Is this >200 lines or changes frequently outside this repo?** --> Tier 3

## Anti-patterns

| Anti-pattern | Fix |
|-------------|-----|
| CLAUDE.md has 300+ lines with full explanations | Extract details to .claude/ subfiles, keep rules concise |
| Same rule in CLAUDE.md AND .claude/CODING_RULES.md | Single source of truth -- rule in one place, pointer from the other |
| .claude/ file exists but CLAUDE.md doesn't mention it | Add a pointer in CLAUDE.md's "Extended Docs" table |
| Entire file is "things Claude already knows" | Delete or drastically reduce -- only keep project-specific bits |
| Instructions for completed features still present | Remove or archive |
| Verbose paragraphs where a table row would do | Condense to table format |
