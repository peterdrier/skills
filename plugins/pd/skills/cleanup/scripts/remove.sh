#!/usr/bin/env bash
# Remove worktrees through git's own plumbing, delete their branches, print disk reclaimed.
# usage: remove.sh [--force] <worktree-path>...
#   --force applies to every path in the call (junk-only trees the user approved); run a second call for the rest.
# Never rm -r: a folder that survives `git worktree remove` is rmdir'd if empty, otherwise reported as LEFTOVER.
set -u
force=; [ "${1:-}" = --force ] && { force=--force; shift; }
[ $# -gt 0 ] || { echo "usage: remove.sh [--force] <worktree-path>..."; exit 2; }
avail() { df -k --output=avail "$1" | tail -1; }
before=$(avail "$(dirname "$1")")
fail=0
for wt in "$@"; do
  wt=${wt%/}
  [ -d "$wt" ] || { echo "SKIP $wt: no such directory"; fail=1; continue; }
  repo=$(cd "$wt" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || { echo "SKIP $wt: not a worktree"; fail=1; continue; }
  repo=${repo%/.git}
  [ "$(cd "$wt" && pwd)" = "$repo" ] && { echo "SKIP $wt: this is the main checkout"; fail=1; continue; }
  branch=$(cd "$wt" && git symbolic-ref -q --short HEAD)
  if (cd "$repo" && git worktree remove $force "$wt"); then
    if [ -d "$wt" ] && ! rmdir "$wt" 2>/dev/null; then
      echo "LEFTOVER $wt: folder not empty after remove, inspect by hand"; fail=1
    fi
    if [ -n "$branch" ]; then
      (cd "$repo" && git branch -D "$branch" >/dev/null) && echo "removed $wt (branch $branch)" || echo "removed $wt (branch $branch NOT deleted)"
    else
      echo "removed $wt"
    fi
    (cd "$repo" && git worktree prune)
  else
    echo "FAILED $wt"; fail=1
  fi
done
after=$(avail "$(dirname "$1")")
echo "reclaimed: $(awk -v a="$after" -v b="$before" 'BEGIN{d=a-b; if (d>=1048576) printf "%.1f GB", d/1048576; else printf "%d MB", d/1024}') (drive of $1)"
exit $fail
