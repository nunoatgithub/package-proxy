#!/usr/bin/env bash
# Script: extract_sys_modules.sh
# Description: Parse log.txt for lines mentioning "sys.modules" and extract the
# module name found inside the first [...] token up to the first colon (e.g.
# "importlib._bootstrap" from "[importlib._bootstrap:989]"). Count how many
# lines mention each such module and print counts sorted by frequency.

set -euo pipefail

LOG_FILE="$1"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "Error: log file not found at '$LOG_FILE'" >&2
  exit 2
fi

# Extract lines containing 'sys.modules', pull the first [...] contents, take
# everything before the first ':' in that bracketed token, normalize whitespace,
# and count occurrences. Print results to stdout sorted by descending count.

grep "sys.modules" "$LOG_FILE" \
  | sed -n 's/.*sys.modules:\[\([^]]*\)\].*/\1/p' \
  | sed -E 's/:.*//' \
  | awk '{$1=$1};1' \
  | sort \
  | uniq -c \
  | sort -rn

exit 0

