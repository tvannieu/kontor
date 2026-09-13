#!/usr/bin/env bash
# check-public.sh — refuse to publish if anything private is present.
# Wire as .git/hooks/pre-push. A local commit is recoverable; a push is not.
#
# The wordlist is deliberately NOT in this repository. Publishing the list of
# names you are protecting publishes the names. It lives outside every repo and
# this script fails closed without it.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2
fail=0
hit() { printf '\033[31mBLOCK\033[0m  %s\n' "$*" >&2; fail=1; }

# A scan that cannot run must fail, not pass. Every check has a population it
# silently excludes; a broken pattern makes that population "everything".
scan() {  # scan <label> <grep-flags> <pattern>
  local label="$1" flags="$2" pat="$3" out rc
  out=$(files | xargs -r grep "$flags" -- "$pat" /dev/null 2>/tmp/.k_err.$$ | head -20); rc=$?
  if [ -s /tmp/.k_err.$$ ]; then
    hit "scan '$label' could not run: $(head -1 /tmp/.k_err.$$)"
  elif [ -n "$out" ]; then
    hit "$label:"; printf '%s\n' "$out" >&2
  fi
  rm -f /tmp/.k_err.$$
}

DENY="${KONTOR_DENY:-$HOME/.config/kontor/deny.txt}"
[ -r "$DENY" ] || { hit "deny-list not readable: $DENY — refusing to run"; exit 2; }

files() { git ls-files -co --exclude-standard | grep -vE 'check-public\.sh$'; }

# 1. the private wordlist
while IFS= read -r t; do
  [ -z "$t" ] && continue
  m=$(files | xargs -r grep -IniF -- "$t" /dev/null 2>/dev/null | head -3)
  [ -n "$m" ] && { hit "private term matched:"; printf '%s\n' "$m" >&2; }
done < <(grep -vE '^\s*(#|$)' "$DENY")

# 2. domain vocabulary — German first, because the private corpus is German
scan "domain vocabulary" -InEi 'VOCABULARY_KEPT_OUTSIDE_THE_REPOSITORY'

# 3. identifiers: statutes, case numbers, IBANs, mail addresses, API keys, phone numbers
scan "identifier pattern" -InE '§ *[0-9]+|[0-9]{1,3} [A-Z] [0-9]{2,5}/[0-9]{2}|DE[0-9]{2}[0-9A-Z ]{12,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(sk-or|tvly|ghp_|github_pat|xoxb)[-_A-Za-z0-9]{12,}|\+?49[ /-][0-9][0-9 /-]{6,}'

# 4. absolute home paths leak a username
scan "absolute home path" -InE '/Users/[a-z]'

# 5. no shared history with any private branch — the unrecoverable failure
git log --format=%H 2>/dev/null | sort > "/tmp/.k_pub.$$"
if [ -s "/tmp/.k_pub.$$" ] && [ -r "${KONTOR_CONF:-$HOME/.config/kontor/branches.conf}" ]; then
  . "${KONTOR_CONF:-$HOME/.config/kontor/branches.conf}"
  for b in "${LOCAL_FIRST[@]}"; do
    [ -d "$KONTOR_ROOT/$b/.git" ] || continue
    if git -C "$KONTOR_ROOT/$b" log --all --format=%H 2>/dev/null | sort \
       | comm -12 - "/tmp/.k_pub.$$" | grep -q .; then
      hit "shares commit history with a private branch — must never happen"
    fi
  done
fi
rm -f "/tmp/.k_pub.$$"

if [ "$fail" = 0 ]; then echo "clean"; else echo "REFUSING TO PUBLISH" >&2; fi
exit "$fail"
