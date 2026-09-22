#!/usr/bin/env python3
"""Estimate Codex session API-equivalent spend from local rollout JSONL files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


# Standard API prices in USD per million tokens: input, cached input, output.
# Verified 2026-09-23 against:
# https://developers.openai.com/api/docs/pricing
# https://developers.openai.com/api/docs/models/compare
PRICE_AS_OF = "2026-09-23"
PRICES: dict[str, tuple[Decimal, Decimal, Decimal]] = {
    "gpt-6-astra": (Decimal("10"), Decimal("1"), Decimal("50")),
    "gpt-6-sol": (Decimal("2"), Decimal("0.2"), Decimal("10")),
    "gpt-6-luna": (Decimal("0.1"), Decimal("0.01"), Decimal("0.5")),
    "gpt-5.6-sol": (Decimal("4"), Decimal("0.4"), Decimal("20")),
    "gpt-5.6-terra": (Decimal("2"), Decimal("0.2"), Decimal("12")),
    "gpt-5.6-luna": (Decimal("0.2"), Decimal("0.02"), Decimal("1.2")),
}
MILLION = Decimal(1_000_000)


@dataclass
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0

    @classmethod
    def from_dict(cls, value: Any) -> "Usage":
        value = value if isinstance(value, dict) else {}
        return cls(**{
            name: _nonnegative_int(value.get(name, 0))
            for name in cls.__dataclass_fields__
        })

    def add(self, other: "Usage") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))

    @property
    def total_tokens(self) -> int:
        # input_tokens and output_tokens already include their cached/reasoning subsets.
        return self.input_tokens + self.output_tokens


@dataclass
class Bucket:
    model: str
    effort: str
    usage: Usage = field(default_factory=Usage)
    turns: set[str] = field(default_factory=set)
    responses: int = 0
    fallback: bool = False


@dataclass
class Rollout:
    path: Path
    thread_id: str
    session_id: str
    parent_thread_id: str | None
    forked_from_id: str | None
    cwd: str
    timestamp: str
    agent_path: str
    nickname: str
    buckets: dict[tuple[str, str], Bucket]
    malformed_lines: int = 0

    @property
    def is_root(self) -> bool:
        return not self.parent_thread_id and not self.forked_from_id

    @property
    def label(self) -> str:
        if self.is_root:
            return "/root"
        return self.agent_path or self.nickname or self.thread_id[:8]


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                yield {"_malformed": True}
                continue
            if isinstance(value, dict):
                yield value


def parse_rollout(path: Path) -> Rollout | None:
    meta: dict[str, Any] | None = None
    contexts: dict[str, tuple[str, str]] = {}
    current_context = ("unknown", "unknown", "")
    response_usage: list[tuple[str, str, str, Usage]] = []
    last_cumulative: Usage | None = None
    malformed = 0

    for row in _iter_jsonl(path):
        if row.get("_malformed"):
            malformed += 1
            continue
        row_type = row.get("type")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if row_type == "session_meta":
            meta = payload
        elif row_type == "turn_context":
            turn_id = str(payload.get("turn_id") or "unknown")
            model = str(payload.get("model") or "unknown")
            effort = str(payload.get("effort") or "unknown")
            contexts[turn_id] = (model, effort)
            current_context = (model, effort, turn_id)
        elif row_type == "token_usage_record":
            turn_id = str(payload.get("turn_id") or current_context[2] or "unknown")
            model, effort = contexts.get(turn_id, current_context[:2])
            response_usage.append((model, effort, turn_id, Usage.from_dict(payload.get("usage"))))
        elif row_type == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                last_cumulative = Usage.from_dict(info["total_token_usage"])

    if not meta:
        return None

    buckets: dict[tuple[str, str], Bucket] = {}
    if response_usage:
        for model, effort, turn_id, usage in response_usage:
            key = (model, effort)
            bucket = buckets.setdefault(key, Bucket(model=model, effort=effort))
            bucket.usage.add(usage)
            bucket.turns.add(turn_id)
            bucket.responses += 1
        # A just-started or interrupted turn may have context but no usage record yet.
        for turn_id, (model, effort) in contexts.items():
            key = (model, effort)
            bucket = buckets.setdefault(key, Bucket(model=model, effort=effort))
            bucket.turns.add(turn_id)
    elif last_cumulative:
        distinct_models = {model for model, _ in contexts.values()}
        distinct_efforts = {effort for _, effort in contexts.values()}
        model = next(iter(distinct_models)) if len(distinct_models) == 1 else "mixed"
        effort = next(iter(distinct_efforts)) if len(distinct_efforts) == 1 else "mixed"
        turn_id = current_context[2]
        bucket = Bucket(model=model, effort=effort, usage=last_cumulative, fallback=True)
        bucket.turns.update(contexts or {turn_id: (model, effort)})
        buckets[(model, effort)] = bucket
    else:
        # Retain zero-usage turns in the report; active sessions can receive usage later.
        for turn_id, (model, effort) in contexts.items():
            key = (model, effort)
            bucket = buckets.setdefault(key, Bucket(model=model, effort=effort))
            bucket.turns.add(turn_id)

    thread_id = str(meta.get("id") or meta.get("session_id") or path.stem)
    session_id = str(meta.get("session_id") or thread_id)
    return Rollout(
        path=path,
        thread_id=thread_id,
        session_id=session_id,
        parent_thread_id=_optional_str(meta.get("parent_thread_id")),
        forked_from_id=_optional_str(meta.get("forked_from_id")),
        cwd=str(meta.get("cwd") or ""),
        timestamp=str(meta.get("timestamp") or ""),
        agent_path=str(meta.get("agent_path") or ""),
        nickname=str(meta.get("agent_nickname") or ""),
        buckets=buckets,
        malformed_lines=malformed,
    )


def parse_metadata(path: Path) -> Rollout | None:
    """Read only far enough to index a rollout's session metadata."""
    try:
        for row in _iter_jsonl(path):
            if row.get("type") != "session_meta" or not isinstance(row.get("payload"), dict):
                continue
            meta = row["payload"]
            thread_id = str(meta.get("id") or meta.get("session_id") or path.stem)
            return Rollout(
                path=path,
                thread_id=thread_id,
                session_id=str(meta.get("session_id") or thread_id),
                parent_thread_id=_optional_str(meta.get("parent_thread_id")),
                forked_from_id=_optional_str(meta.get("forked_from_id")),
                cwd=str(meta.get("cwd") or ""),
                timestamp=str(meta.get("timestamp") or ""),
                agent_path=str(meta.get("agent_path") or ""),
                nickname=str(meta.get("agent_nickname") or ""),
                buckets={},
            )
    except OSError:
        raise
    return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def load_rollouts(sessions_dir: Path) -> list[Rollout]:
    rollouts: list[Rollout] = []
    for path in sessions_dir.rglob("*.jsonl"):
        try:
            rollout = parse_metadata(path)
        except OSError as exc:
            print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
            continue
        if rollout:
            rollouts.append(rollout)
    return rollouts


def select_root(rollouts: list[Rollout], selection: str | None, cwd: Path) -> Rollout:
    by_id = {rollout.thread_id: rollout for rollout in rollouts}
    selected: Rollout | None = None
    if selection:
        candidate = Path(selection).expanduser()
        if candidate.is_file():
            selected = parse_metadata(candidate.resolve())
            if not selected:
                raise ValueError(f"no session metadata found in {candidate}")
            by_id.setdefault(selected.thread_id, selected)
        else:
            selected = by_id.get(selection)
            if not selected:
                matches = [item for item in rollouts if item.thread_id.startswith(selection)]
                if len(matches) == 1:
                    selected = matches[0]
                elif len(matches) > 1:
                    raise ValueError(f"session prefix {selection!r} is ambiguous")
                else:
                    raise ValueError(f"session {selection!r} was not found")
        seen: set[str] = set()
        while selected and not selected.is_root and selected.thread_id not in seen:
            seen.add(selected.thread_id)
            parent_id = selected.parent_thread_id or selected.forked_from_id
            parent = by_id.get(parent_id or "")
            if not parent:
                raise ValueError(f"parent session {parent_id!r} was not found for {selected.thread_id}")
            selected = parent
        return selected

    wanted_cwd = _normalized_path(cwd)
    roots = [item for item in rollouts if item.is_root and _normalized_path(Path(item.cwd)) == wanted_cwd]
    if not roots:
        raise ValueError(f"no root Codex session found for cwd {cwd}")
    # A resumed session keeps its creation timestamp but its rollout mtime advances.
    return max(roots, key=lambda item: (item.path.stat().st_mtime, _timestamp_key(item.timestamp)))


def _normalized_path(path: Path) -> str:
    try:
        value = str(path.expanduser().resolve())
    except OSError:
        value = str(path.expanduser().absolute())
    return os.path.normcase(value.rstrip("\\/"))


def _timestamp_key(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def linked_tree(root: Rollout, rollouts: list[Rollout]) -> list[Rollout]:
    by_parent: dict[str, list[Rollout]] = defaultdict(list)
    for item in rollouts:
        parent = item.parent_thread_id or item.forked_from_id
        if parent:
            by_parent[parent].append(item)

    result: list[Rollout] = []
    seen: set[str] = set()

    def visit(item: Rollout) -> None:
        if item.thread_id in seen:
            return
        seen.add(item.thread_id)
        result.append(item)
        for child in sorted(by_parent.get(item.thread_id, []), key=lambda entry: entry.timestamp):
            visit(child)

    visit(root)
    return result


def estimate_cost(model: str, usage: Usage) -> Decimal | None:
    rates = PRICES.get(model)
    if not rates:
        return None
    input_rate, cached_rate, output_rate = rates
    cached = min(usage.cached_input_tokens, usage.input_tokens)
    cache_write = min(usage.cache_write_input_tokens, max(0, usage.input_tokens - cached))
    uncached = max(0, usage.input_tokens - cached - cache_write)
    return (
        Decimal(uncached) * input_rate
        + Decimal(cached) * cached_rate
        + Decimal(cache_write) * input_rate * Decimal("1.25")
        + Decimal(usage.output_tokens) * output_rate
    ) / MILLION


def render_report(root: Rollout, tree: list[Rollout]) -> str:
    rows: list[list[str]] = []
    total_usage = Usage()
    total_cost = Decimal(0)
    unpriced: set[str] = set()
    fallbacks = 0
    malformed = 0

    for agent in tree:
        malformed += agent.malformed_lines
        if not agent.buckets:
            rows.append([agent.label, "unknown", "unknown", "0", "$0.0000", "0", "0/0/0/0", "waiting"])
            continue
        for bucket in agent.buckets.values():
            total_usage.add(bucket.usage)
            cost = estimate_cost(bucket.model, bucket.usage)
            if cost is None:
                unpriced.add(bucket.model)
                cost_text = "unpriced"
            else:
                total_cost += cost
                cost_text = f"${cost:.4f}"
            note = "fallback" if bucket.fallback else ""
            if bucket.fallback:
                fallbacks += 1
            rows.append([
                agent.label,
                bucket.model,
                bucket.effort,
                str(len(bucket.turns)),
                cost_text,
                _compact_int(bucket.usage.total_tokens),
                "/".join(_compact_int(value) for value in (
                    max(0, bucket.usage.input_tokens - bucket.usage.cached_input_tokens - bucket.usage.cache_write_input_tokens),
                    bucket.usage.cached_input_tokens,
                    bucket.usage.cache_write_input_tokens,
                    bucket.usage.output_tokens,
                )),
                note,
            ])

    headers = ["Agent", "Model", "Level", "Turns", "Est. cost", "Tokens", "In/cache/write/out", "Note"]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    table = ["  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))]
    table.append("  ".join("-" * width for width in widths))
    table.extend("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in rows)

    lines = [
        f"Codex spend estimate - root {root.thread_id}",
        f"Workspace: {root.cwd or '(unknown)'}",
        "",
        *table,
        "",
        f"Agents: {len(tree)}    Tokens: {_compact_int(total_usage.total_tokens)}    Estimated priced total: ${total_cost:.4f}",
    ]
    if unpriced:
        lines.append("Unpriced models (excluded from total): " + ", ".join(sorted(unpriced)))
    caveats = [
        f"API-equivalent estimate using Standard list rates checked {PRICE_AS_OF}; rates can change and subscription billing may differ.",
        "Cached input is priced separately; visible cache writes use 1.25x the input rate.",
        "Reasoning tokens are included in output_tokens and are not charged twice.",
        "The estimate omits tool fees, regional/processing adjustments, and long-context premiums.",
        "Usage records can arrive late, so an active session may be incomplete.",
    ]
    if fallbacks:
        caveats.append(f"{fallbacks} row(s) used final cumulative token_count because per-response records were absent.")
    if malformed:
        caveats.append(f"Ignored {malformed} malformed/incomplete JSONL line(s), possibly from an active writer.")
    lines.extend(["", "Caveats:", *(f"- {item}" for item in caveats)])
    return "\n".join(lines)


def _compact_int(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    current_session = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    parser.add_argument(
        "session",
        nargs="?",
        default=current_session,
        help="root session ID/prefix or rollout JSONL path (default: current Codex thread when available)",
    )
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="workspace used to select the latest root")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions",
        help="Codex sessions directory (default: $CODEX_HOME/sessions or ~/.codex/sessions)",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="append a machine-readable summary to ~/.codex/spend-log.jsonl",
    )
    return parser


def append_log(root: Rollout, tree: list[Rollout]) -> Path:
    usage = Usage()
    priced_cost = Decimal(0)
    unpriced: set[str] = set()
    for agent in tree:
        for bucket in agent.buckets.values():
            usage.add(bucket.usage)
            cost = estimate_cost(bucket.model, bucket.usage)
            if cost is None:
                unpriced.add(bucket.model)
            else:
                priced_cost += cost
    path = Path.home() / ".codex" / "spend-log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": datetime.now().astimezone().isoformat(),
        "price_as_of": PRICE_AS_OF,
        "root_session_id": root.thread_id,
        "cwd": root.cwd,
        "agents": len(tree),
        "tokens": usage.total_tokens,
        "estimated_priced_usd": str(priced_cost.quantize(Decimal("0.000001"))),
        "unpriced_models": sorted(unpriced),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sessions_dir = args.sessions_dir.expanduser()
    if not sessions_dir.is_dir():
        print(f"error: sessions directory does not exist: {sessions_dir}", file=sys.stderr)
        return 2
    try:
        rollouts = load_rollouts(sessions_dir)
        root_index = select_root(rollouts, args.session, args.cwd)
        tree_index = linked_tree(root_index, rollouts)
        tree = [item for item in (parse_rollout(index.path) for index in tree_index) if item]
        if not tree:
            raise ValueError(f"selected session could not be read: {root_index.path}")
        root = tree[0]
        report = render_report(root, tree)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(report)
    if args.log:
        log_path = append_log(root, tree)
        print(f"\nAppended summary to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
