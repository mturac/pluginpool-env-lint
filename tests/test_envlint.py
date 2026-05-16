import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "envlint.py"


def run_envlint(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )


def test_default_pair_detection_only_existing_pairs(tmp_path):
    (tmp_path / ".env.example").write_text("A=\nB=\n", encoding="utf-8")
    (tmp_path / ".env").write_text("A=1\nB=2\n", encoding="utf-8")
    result = run_envlint(tmp_path)
    data = json.loads(result.stdout)
    assert result.returncode == 0
    assert [(p["example"], p["env"]) for p in data["pairs"]] == [(".env.example", ".env")]


def test_default_detects_local_and_production_pairs(tmp_path):
    (tmp_path / ".env.example").write_text("A=\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("A=1\n", encoding="utf-8")
    (tmp_path / ".env.production").write_text("A=2\n", encoding="utf-8")
    data = json.loads(run_envlint(tmp_path).stdout)
    assert [p["env"] for p in data["pairs"]] == [".env.local", ".env.production"]


def test_missing_extra_and_empty_values(tmp_path):
    example = tmp_path / "example.env"
    env = tmp_path / "actual.env"
    example.write_text("A=\nB=\n", encoding="utf-8")
    env.write_text("A=\nC=value\n", encoding="utf-8")
    result = run_envlint(tmp_path, "--example", str(example), "--env", str(env))
    pair = json.loads(result.stdout)["pairs"][0]
    assert result.returncode == 1
    assert pair["missing_in_env"] == ["B"]
    assert pair["extra_in_env"] == ["C"]
    assert pair["empty_values"] == ["A"]


def test_markdown_format(tmp_path):
    (tmp_path / ".env.example").write_text("A=\nB=\n", encoding="utf-8")
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    result = run_envlint(tmp_path, "--format", "md")
    assert result.returncode == 1
    assert "# env-lint report" in result.stdout
    assert "Missing in env: B" in result.stdout


def test_never_emits_values_in_json_or_markdown(tmp_path):
    secret = "SUPERSECRETVALUE123"
    (tmp_path / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"SECRET={secret}\nEXTRA={secret}\n", encoding="utf-8")
    json_result = run_envlint(tmp_path)
    md_result = run_envlint(tmp_path, "--format", "md")
    assert secret not in json_result.stdout
    assert secret not in md_result.stdout
    assert secret not in json_result.stderr
    assert secret not in md_result.stderr


def test_exit_code_zero_when_no_missing_even_with_extra(tmp_path):
    (tmp_path / ".env.example").write_text("A=\n", encoding="utf-8")
    (tmp_path / ".env").write_text("A=1\nB=2\n", encoding="utf-8")
    result = run_envlint(tmp_path)
    assert result.returncode == 0


def test_help_works():
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], text=True, capture_output=True)
    assert result.returncode == 0
    assert "Validate .env files" in result.stdout
