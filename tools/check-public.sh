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
VOCAB="${KONTOR_VOCAB:-$HOME/.config/kontor/vocab.txt}"
[ -r "$VOCAB" ] || { hit "vocabulary list not readable: $VOCAB — refusing to run"; exit 2; }
BCONF="${KONTOR_CONF:-$HOME/.config/kontor/branches.conf}"
self=$(basename "$(git rev-parse --show-toplevel)")

# Two exclusions, and only one of them is defensible.
#
# check-public.sh excludes itself because it would otherwise match on the
# patterns it is searching for.
#
# inbox/ used to be excluded too, on the reasoning that the pouch is a
# delivery mechanism rather than content. That reasoning was wrong, and it
# was wrong in the most expensive possible way: the messages that arrive in
# inbox/ come FROM the other branches, so they are the likeliest place in
# this repository for another branch's names and matters to appear -- and
# they were the one place never scanned. Found 2026-09-20: eight committed
# and pushed files, carrying between one and seventeen distinct deny-listed
# terms each. Every "clean" this script had printed was silent about them.
#
# The rule this cost, twice now: an exclusion is a claim that a population
# cannot contain what you are looking for. The deny-list was empty; the
# inbox was unscanned. Both times the gate reported clean, and both times
# the reason was the scope, not the content.
files() { git ls-files -co --exclude-standard | grep -vE 'check-public\.sh$'; }

# 1. the private wordlist — plus every branch name in the instance config.
# Found 18.09.2026: the deny-list had been empty since it was created, and
# every "clean" this script printed was vacuous for this scan. Names the
# config already knows can never again be missing because nobody typed them;
# the file itself is for people, employers and matters. Whole-word matching,
# because branch names can be ordinary words.
terms() {
  grep -vE '^[[:space:]]*(#|$)' "$DENY"
  if [ -r "$BCONF" ]; then
    # A name written with a hyphen where the directory has an underscore (or
    # the reverse) is the same name to a reader. Found 18.09.2026 in a
    # comment the whole-word scan had walked past.
    ( . "$BCONF"; for b in "${BRANCHES[@]:-}"; do
        [ "$b" = "$self" ] && continue
        printf '%s\n%s\n%s\n' "$b" "${b//_/-}" "${b//-/_}"
      done | sort -u )
  fi
}
if [ "$(terms | wc -l | tr -d ' ')" = 0 ]; then
  hit "private wordlist is empty — $DENY has no terms and $BCONF lists no branches; a scan against nothing is not a scan"
fi
while IFS= read -r t; do
  [ -z "$t" ] && continue
  m=$(files | xargs -r grep -IniwF -- "$t" /dev/null 2>/dev/null | head -3)
  [ -n "$m" ] && { hit "private term matched:"; printf '%s\n' "$m" >&2; }
done < <(terms)

# 2. domain vocabulary — kept outside the repository, like the wordlist: a
# published list of the kinds of matter you are protecting describes them as
# surely as the names would. One extended-regex alternative per line.
pat=$(grep -vE '^[[:space:]]*(#|$)' "$VOCAB" | paste -sd'|' -)
[ -n "$pat" ] || hit "vocabulary list is empty: $VOCAB"
scan "domain vocabulary" -InEi "$pat"

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

# 6. commit messages. This gate read files and never read the history's own
# prose, and that was a hole with two entries in it: one message quoted the
# false positive it had just been blocked on, which was a real branch name, and
# another quoted a word from the private vocabulary list. Both were found by
# hand, after the fact, and both needed the history rewritten and the remote
# recreated. A message is published text like any other.
#
# The Co-Authored-By trailer is excluded, not because it is trusted but because
# its address would trip the mail-shaped pattern on every commit; it names a
# model and nothing else. Session links are refused outright: they point from
# a public repository into a private conversation, and the only thing standing
# between a stranger and that conversation is a sharing setting this script
# cannot see.
msgfile="/tmp/.k_msg.$$"
git log --all --format=%B 2>/dev/null | grep -vE '^Co-Authored-By: ' > "$msgfile"
while IFS= read -r t; do
  [ -z "$t" ] && continue
  m=$(grep -niwF -- "$t" "$msgfile" | head -3)
  [ -n "$m" ] && { hit "private term in a commit message:"; printf '%s\n' "$m" >&2; }
done < <(terms)
m=$(grep -nEi "$pat" "$msgfile" | head -3)
[ -n "$m" ] && { hit "domain vocabulary in a commit message:"; printf '%s\n' "$m" >&2; }
m=$(grep -nE 'claude\.ai/(code|chat|share)/|session_[A-Za-z0-9]{12,}' "$msgfile" | head -3)
[ -n "$m" ] && { hit "session link in a commit message:"; printf '%s\n' "$m" >&2; }
m=$(grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(sk-or|tvly|ghp_|github_pat|xoxb)[-_A-Za-z0-9]{12,}|/Users/[a-z]' "$msgfile" | head -3)
[ -n "$m" ] && { hit "address, key or home path in a commit message:"; printf '%s\n' "$m" >&2; }
rm -f "$msgfile"

if [ "$fail" = 0 ]; then echo "clean"; else echo "REFUSING TO PUBLISH" >&2; fi
exit "$fail"
