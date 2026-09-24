#!/usr/bin/env bash
# archive-sent.sh — the mechanical half of "draft here, record of sending
# there" (see ../docs/outbox.md).
#
# Once a drafted piece of correspondence has actually gone out, copies every
# file out of its drafts folder into wherever the receiving repo keeps its
# sent-correspondence record, prefixed with today's date and a SENT
# marker, then removes the now-empty drafts folder. Judgement about *which*
# repo and *which* category a piece of correspondence belongs to stays with
# the session — this script only does the part that's identical every time.
#
# Usage:
#   archive-sent.sh <draft-dir> <archive-dir>
#
# Convention:
#   <archive-dir>/YYYY-MM-DD_SENT_<original-stem>.<ext>
#
# A file already at the destination is left alone and reported, never
# overwritten — a move into a collection folder is a replacement, not a
# copy, and the docs/lessons.md entry on that exists because a silent
# overwrite once lost the newer of two same-named files.
set -euo pipefail

draft_dir="${1:?Usage: archive-sent.sh <draft-dir> <archive-dir>}"
archive_dir="${2:?Usage: archive-sent.sh <draft-dir> <archive-dir>}"

[ -d "$draft_dir" ] || { echo "Not a directory: $draft_dir" >&2; exit 1; }

regular=()
for f in "$draft_dir"/*; do
    [ -f "$f" ] || continue
    # The register is not correspondence. Both names are skipped: the folders
    # were called 00_LIESMICH.txt before the documentation was put into English
    # on 2026-09-20, and a rename on disk is the operator's to do, not this
    # script's to assume.
    case "$(basename "$f")" in 00_README.txt|00_LIESMICH.txt) continue;; esac
    regular+=("$f")
done
if [ "${#regular[@]}" -eq 0 ]; then
    echo "No files to archive in $draft_dir (looked past the register, 00_README.txt)" >&2
    exit 1
fi

mkdir -p "$archive_dir"
stamp="$(date +%Y-%m-%d)"
echo "Archiving ${#regular[@]} file(s) from $draft_dir to $archive_dir:"
skipped=0
for f in "${regular[@]}"; do
    base="$(basename "$f")"
    if [[ "$base" == *.* && "$base" != .* ]]; then
        stem="${base%.*}"
        ext="${base##*.}"
        dest="$archive_dir/${stamp}_SENT_${stem}.${ext}"
    else
        dest="$archive_dir/${stamp}_SENT_${base}"
    fi
    if [ -e "$dest" ]; then
        echo "  SKIP (already exists): $(basename "$dest")" >&2
        skipped=$((skipped + 1))
        continue
    fi
    cp "$f" "$dest"
    echo "  $base -> $(basename "$dest")"
done

if [ "$skipped" -gt 0 ] && [ "$skipped" -eq "${#regular[@]}" ]; then
    echo "Every file already had an archived copy — leaving $draft_dir in place." >&2
    exit 1
fi

rm -rf "$draft_dir"
echo "Removed $draft_dir"
echo
echo "Not done automatically — add to the recipient's register by hand:"
echo "  ${stamp} SENT — archived to ${archive_dir}"
