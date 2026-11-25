# AGENTS.md

Rules for coding agents working in this repository. Read
[DESIGN.md](DESIGN.md) before changing anything substantive.

## Hard rules

**Never write a secret to this repo.** No `.env` files, no API keys, no tokens, no
private keys, no real credentials in fixtures or logs. This repo is public and every
commit is permanent.

Before committing:

```bash
python3 tools/audit-secrets.py
```

If it reports a finding, delete the value. Do not allowlist your way past a real
credential. If you genuinely have a false positive, add the printed fingerprint to
`.secrets-allow` and say so in the commit message.

Never use `git commit --no-verify` to skip the hook unless a human explicitly asks.

Never commit personal data: personal filesystem paths, real usernames or hostnames,
client names, internal ticket references. Stage fixtures are synthetic.

Do not change the repo-local `user.email`. It is the GitHub noreply address so the
public history does not publish a personal email.

## Design discipline

- **DECIDED** in DESIGN.md means argued and settled. Do not quietly reverse one in
  code. Open an issue, give a reason, get agreement, update the doc.
- The verification tier is a design decision, not an implementation detail. If you
  cannot make a stage verifiable at tier A–F, the stage is wrong, not the oracle.
- Never weaken an oracle to make an agent pass. Calibrate by measuring, not by
  adjusting until the answer looks right.
- Every stage needs both controls: a no-op that must pass and a do-nothing that must
  fail. A stage that passes for a do-nothing agent is broken.
- The oracle is never callable by the agent under test. If you find yourself adding
  that, stop.

## Working style

- Python for the engine, no framework unless DESIGN.md changes its mind.
- Every stage definition is a directory under `stages/<id>/` with a `stage.yaml`.
- Determinism is a feature: pin images by digest, pin locale and timezone, sort
  directory traversal.
- Prefer boring code. This is a measurement instrument.

## Layout

```
stages/<id>/stage.yaml     stage definition
stages/<id>/workspace/     fixture files given to the agent
stages/<id>/oracle/        verification, never shipped to the sandbox
engine/                    orchestrator, oracle runner, harness adapters
board/                     three.js / react-three-fiber renderer
docs/                      design detail
tools/                     repo tooling
```

Directories are planned and do not all exist yet. Create them when you build the thing
that lives in them.
