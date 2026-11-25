#!/usr/bin/env bash
# Installs the local git hooks. Run once after cloning.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
hooks="$root/.git/hooks"
mkdir -p "$hooks"

cat > "$hooks/pre-commit" <<'HOOK'
#!/usr/bin/env bash
# Blocks staged secrets before they are ever written to a commit.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
cd "$root"

if command -v python3 >/dev/null 2>&1; then
  python3 tools/audit-secrets.py || {
    echo
    echo "Commit blocked. Fix the findings above, or allowlist a false positive"
    echo "in .secrets-allow. Bypass once with: git commit --no-verify"
    exit 1
  }
fi

# Refuse to stage anything gitignored that looks like a secret.
if git diff --cached --name-only | grep -Eq '(^|/)\.env($|\.)|\.(pem|key|p12|pfx)$|(^|/)credentials($|\.json$)'; then
  echo "Commit blocked: a secret-bearing filename is staged."
  git diff --cached --name-only | grep -E '(^|/)\.env($|\.)|\.(pem|key|p12|pfx)$|(^|/)credentials($|\.json$)'
  exit 1
fi
HOOK

chmod +x "$hooks/pre-commit"
echo "installed $hooks/pre-commit"
