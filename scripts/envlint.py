#!/usr/bin/env python3
"""Validate .env files against .env.example without emitting values."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, Iterable, List, Sequence, Tuple


KEY_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
DEFAULT_PAIRS = (
    (".env.example", ".env"),
    (".env.example", ".env.local"),
    (".env.example", ".env.production"),
)


def _strip_inline_comment(value: str) -> str:
    """Drop an unquoted ``#`` inline comment from an env value.

    A ``#`` inside a quoted scalar (single- or double-quoted) is preserved.
    A backslash-escape inside a double-quoted scalar is honoured so
    ``KEY="say \\"hi\\" # not a comment"`` keeps its content.
    """
    in_single = False
    in_double = False
    i = 0
    while i < len(value):
        ch = value[i]
        if in_double and ch == "\\" and i + 1 < len(value):
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return value[:i].rstrip()
        i += 1
    return value


def _is_empty_value(value: str) -> bool:
    """A value is considered empty if it's literally blank or only whitespace
    inside a pair of matching quotes."""
    stripped = value.strip()
    if not stripped:
        return True
    for opener, closer in (("'", "'"), ('"', '"')):
        if stripped.startswith(opener) and stripped.endswith(closer) and len(stripped) >= 2:
            inner = stripped[1:-1]
            if not inner.strip():
                return True
    return False


def parse_env(path: str) -> Tuple[List[str], Dict[str, bool]]:
    """Parse an env file into ``(keys_in_order, {key: is_empty})``.

    Reports ``OSError`` to the caller rather than crashing with a traceback —
    a permission-denied or missing-file failure should produce a clean error
    message at the CLI layer (review #2 finding).
    """
    keys: List[str] = []
    empty: Dict[str, bool] = {}
    seen = set()
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = KEY_RE.match(stripped)
            if not match:
                continue
            key = match.group(1)
            if key not in seen:
                keys.append(key)
                seen.add(key)
            raw_value = stripped.split("=", 1)[1]
            cleaned = _strip_inline_comment(raw_value).strip()
            empty[key] = _is_empty_value(cleaned)
    return keys, empty


def existing_pairs() -> List[Tuple[str, str]]:
    return [(example, env) for example, env in DEFAULT_PAIRS if os.path.exists(example) and os.path.exists(env)]


def compare_pair(example: str, env: str) -> dict:
    example_keys, _ = parse_env(example)
    env_keys, env_empty = parse_env(env)
    example_set = set(example_keys)
    env_set = set(env_keys)
    return {
        "example": example,
        "env": env,
        "missing_in_env": [key for key in example_keys if key not in env_set],
        "extra_in_env": [key for key in env_keys if key not in example_set],
        "empty_values": [key for key in env_keys if env_empty.get(key, False)],
    }


def to_markdown(results: Sequence[dict]) -> str:
    lines = ["# env-lint report", ""]
    if not results:
        lines.append("No existing .env pairs found.")
        return "\n".join(lines) + "\n"
    for item in results:
        lines.extend(
            [
                f"## {item['env']} vs {item['example']}",
                "",
                f"- Missing in env: {', '.join(item['missing_in_env']) or 'none'}",
                f"- Extra in env: {', '.join(item['extra_in_env']) or 'none'}",
                f"- Empty values: {', '.join(item['empty_values']) or 'none'}",
                "",
            ]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate .env files against .env.example without printing values.")
    parser.add_argument("--example", help="Example env file path")
    parser.add_argument("--env", help="Environment file path")
    parser.add_argument("--format", choices=("json", "md"), default="json", help="Output format")
    parser.add_argument("--strict", action="store_true",
                        help="Also fail (exit 1) when any required key has an empty value.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.example) != bool(args.env):
        raise SystemExit("--example and --env must be provided together")

    pairs = [(args.example, args.env)] if args.example else existing_pairs()
    try:
        results = [compare_pair(example, env) for example, env in pairs]
    except (OSError, PermissionError) as exc:
        sys.stderr.write(f"env-lint: cannot read env file: {exc}\n")
        return 2
    payload = {"pairs": results}
    if args.format == "md":
        sys.stdout.write(to_markdown(results))
    else:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    has_missing = any(pair["missing_in_env"] for pair in results)
    has_empty = any(pair["empty_values"] for pair in results)
    if has_missing:
        return 1
    if args.strict and has_empty:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
