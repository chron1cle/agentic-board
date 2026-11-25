# Security policy

## Secrets must never enter this repository

This repo is public. Treat every commit as published and permanent.

### What is blocked

`.env` and variants, private keys (`*.pem`, `*.key`, `id_rsa`, `id_ed25519`),
`credentials.json`, `token.json`, `.netrc`, `.npmrc`, `.pypirc`, cloud config
directories, Terraform variables and state, and any credential with a recognizable
prefix (GitHub, AWS, OpenAI, Anthropic, Stripe, Slack, Google, npm, PyPI, GitLab,
Hugging Face, Twilio, SendGrid, Discord, Telegram), plus embedded basic-auth URLs,
PEM blocks, JWTs, and high-entropy strings with no known prefix.

### The gate

`tools/audit-secrets.py` is the in-repo scanner. Stdlib only, no install step.

```bash
python3 tools/audit-secrets.py              # working tree
python3 tools/audit-secrets.py --history    # working tree + every git blob
python3 tools/audit-secrets.py --json       # machine readable
python3 tools/audit-secrets.py --baseline   # candidate allowlist entries
```

It runs three ways:

1. **pre-commit hook** — run `tools/install-hooks.sh` once per clone. Blocks staged
   secrets before they are ever written to a commit.
2. **CI** — `.github/workflows/audit.yml` runs it with `--history` on every push and
   PR, so a secret pushed on a branch is caught too.
3. **on demand**, as above.

A second independent scanner (gitleaks) runs in CI as an advisory check.

### Allowlisting

Findings are fingerprinted `path:rule:hash`. Add the **fingerprint** to
`.secrets-allow`, never a whole path or whole rule — a path-level allowlist would
hide a real credential sitting next to the false positive. Every allowlist entry is
reviewable in a pull request.

### If you commit a secret anyway

The hook and CI are nets, not guarantees. If a credential reaches a commit:

1. **Rotate it first.** Assume it is compromised the moment it is committed. Removal
   does not un-leak it.
2. Purge from history (`git filter-repo --replace-text` or BFG), force-push, and ask
   an admin to have the old objects expunged.
3. Note the rotation in the PR so the record is clear.

Force-pushing to `main` requires two people in the loop.

## Personal data

Commits in this repo are authored with the GitHub noreply address
(`chron1cle@users.noreply.github.com`), configured repo-locally, so the public history
does not publish a personal email address. Keep it that way — do not override
`user.email` in this repo.

Do not commit: personal paths in logs or fixtures, real usernames or hostnames,
internal ticket references, client names, or anything from a private repo. Stage
fixtures are synthetic by rule.

## Sandbox security

The engine will run untrusted agent-generated code. That is a separate threat model
and gets its own document before the engine is built. It is tracked as an open item in
[DESIGN.md](DESIGN.md) §14.
