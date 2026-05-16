"""Regression tests for env-lint review findings."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import envlint  # noqa: E402


def test_inline_comment_does_not_become_value(tmp_path):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("API_KEY=\n")
    env.write_text("API_KEY= # set this later\n")
    result = envlint.compare_pair(str(example), str(env))
    assert result["empty_values"] == ["API_KEY"]


def test_hash_inside_quoted_value_is_kept(tmp_path):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("PASS=\n")
    env.write_text('PASS="abc#123"\n')
    result = envlint.compare_pair(str(example), str(env))
    assert result["empty_values"] == []  # value is non-empty


def test_quoted_whitespace_counts_as_empty(tmp_path):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("FOO=\n")
    env.write_text('FOO="   "\n')
    result = envlint.compare_pair(str(example), str(env))
    assert result["empty_values"] == ["FOO"]


def test_strict_flag_fails_on_empty_values(tmp_path, capsys, monkeypatch):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("STRIPE=\n")
    env.write_text("STRIPE=\n")
    monkeypatch.chdir(tmp_path)
    # Without --strict, an empty value alone returns 0.
    rc = envlint.main(["--example", str(example), "--env", str(env)])
    assert rc == 0
    capsys.readouterr()
    # With --strict, the empty value triggers exit 1.
    rc = envlint.main(["--example", str(example), "--env", str(env), "--strict"])
    assert rc == 1


def test_missing_file_returns_clean_error(tmp_path, capsys):
    example = tmp_path / ".env.example"
    example.write_text("KEY=\n")
    rc = envlint.main(["--example", str(example), "--env", str(tmp_path / "nope.env")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cannot read env file" in captured.err
    assert "Traceback" not in captured.err
