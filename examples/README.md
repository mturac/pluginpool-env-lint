# env-lint — examples

Each scenario shows: env-file fixtures, the exact command, the helper's report, and the safety guarantee being enforced.

---

## Scenario 1 — typical local-dev drift

**Fixtures:**

- [`.env.example`](./.env.example) — the canonical template (6 keys)
- [`.env.local`](./.env.local) — a teammate's outdated local file (missing 3 keys, has 1 extra, has 1 empty)

**Command:**

```sh
cd examples
python3 ../scripts/envlint.py --example .env.example --env .env.local --format md
```

**Helper output (verbatim):**

```
# env-lint report

## .env.local vs .env.example

- Missing in env: STRIPE_WEBHOOK_SECRET, SENTRY_DSN, FEATURE_FLAGS
- Extra in env: LEGACY_API_KEY
- Empty values: REDIS_URL
```

**Exit code:** `1` (missing keys present).

---

## Scenario 2 — JSON for tooling

Same fixtures, machine-readable output:

```sh
python3 ../scripts/envlint.py --example .env.example --env .env.local --format json
```

```json
{
  "pairs": [
    {
      "example": ".env.example",
      "env": ".env.local",
      "missing_in_env": ["STRIPE_WEBHOOK_SECRET", "SENTRY_DSN", "FEATURE_FLAGS"],
      "extra_in_env": ["LEGACY_API_KEY"],
      "empty_values": ["REDIS_URL"]
    }
  ]
}
```

Pipe into `jq` to fail your CI on any non-empty `missing_in_env`.

---

## Scenario 3 — the safety guarantee, exercised

The most important property of `env-lint`: **the report never contains a value.**

The test suite enforces this — it writes a fake secret `SUPERSECRETVALUE123` into a temp `.env`, runs both the JSON and markdown reporters, and asserts the string `SUPERSECRETVALUE123` does not appear anywhere in stdout. That test is `test_never_emits_values_in_json_or_markdown` in `tests/test_envlint.py`.

You can re-prove it locally:

```sh
echo 'SECRET=hunter2' > .env.local
echo 'SECRET=' > .env.example
python3 ../scripts/envlint.py --example .env.example --env .env.local --format md | grep -F "hunter2"
# (no output — value never appears)
```

That's the whole point: an `env-lint` report is safe to paste in chat, attach to a ticket, or log to CI.

---

## Workflow tip

CI integration to fail the build when keys are missing:

```yaml
- name: env-lint
  run: python3 ~/.claude/plugins/env-lint/scripts/envlint.py --format md
```

Exit code 1 already fails the step; the markdown is the failure message.
